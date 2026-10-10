"""Human Annotation Workflow.

흐름:
1. make_sheets: 검수자별 CSV. 작성자 gold·anchor·근거를 숨기고 순서를 검수자별 seed로 섞는다.
2. 검수자가 CSV를 채운다(독립 판정).
3. load_sheets + agreement: 최초 독립 판정을 보존한 채 일치도(percent, Cohen's kappa)를 계산한다.
4. make_pair_sheet: 독립 판정이 끝난 뒤 pair 두 버전을 나란히 보고 minimal pair 타당성을 판정한다.
5. adjudicate: 일치 → accepted, 불일치 → 조정 파일(decisions)로 수정 또는 rejected. 최초 판정은 validation_metadata에 보존한다.

검수 파일은 annotations/ 아래(Git 제외)에 둔다.
"""

from __future__ import annotations

import csv
import datetime as dt
import random
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

from .schema import LabelRecord, Sample, infer_addressee, render_dialogue, role_of

SHEET_FIELDS = ["order", "sample_id", "dialogue", "target_turn", "target_predicate", "target_speaker", "candidates",
                "naturalness_1to5", "referent_id", "referent_role", "context_sufficient", "ambiguity",
                "previous_referent_id", "previous_referent_turn", "notes"]
JUDGEMENT_FIELDS = ["naturalness_1to5", "referent_id", "referent_role", "context_sufficient", "ambiguity",
                    "previous_referent_id", "previous_referent_turn", "notes"]
PAIR_FIELDS = ["pair_id", "sample_a", "sample_b", "claimed_manipulations", "dialogue_a", "dialogue_b",
               "pair_valid", "only_claimed_changed", "gold_change_as_intended", "notes"]
VALID_AMBIGUITY = ("unambiguous", "ambiguous", "uncertain")


def sheet_row(sample: Sample, order: int) -> dict:
    rec = sample.record
    cands = "; ".join(f"{p.entity_id}={p.name}" for p in rec.participants)
    return {
        "order": order, "sample_id": sample.sample_id,
        "dialogue": render_dialogue(rec, mark_predicate=True),
        "target_turn": rec.target_turn, "target_predicate": rec.target_predicate,
        "target_speaker": rec.participant(rec.speaker_id).name, "candidates": cands,
        **{f: "" for f in JUDGEMENT_FIELDS},
    }


def make_sheets(samples: Iterable[Sample], annotators: list[str], out_dir: Path, seed: int = 0) -> list[Path]:
    samples = list(samples)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for annotator in annotators:
        order = list(samples)
        random.Random(f"{seed}:{annotator}").shuffle(order)
        path = out_dir / f"sheet_{annotator}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
            writer.writeheader()
            for i, s in enumerate(order, start=1):
                writer.writerow(sheet_row(s, i))
        paths.append(path)
    return paths


def load_sheet(path: Path, annotator: Optional[str] = None) -> list[dict]:
    """채워진 시트를 읽는다. annotator가 없으면 파일 이름 sheet_{name}.csv에서 뽑는다."""
    path = Path(path)
    name = annotator or path.stem.replace("sheet_", "")
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            judged = {k: (row.get(k) or "").strip() for k in JUDGEMENT_FIELDS}
            rows.append({"annotator": name, "sample_id": row["sample_id"], **judged})
    return rows


def _kappa(a: list[str], b: list[str]) -> Optional[float]:
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)


def agreement(rows: list[dict], fields: tuple = ("referent_id", "referent_role", "context_sufficient", "ambiguity", "previous_referent_id")) -> dict:
    """두 검수자의 최초 판정으로 필드별 일치도를 계산한다. 셋 이상이면 쌍별로 계산한다."""
    by_annotator: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_annotator.setdefault(r["annotator"], {})[r["sample_id"]] = r
    names = sorted(by_annotator)
    out = {"annotators": names, "n_rows": len(rows), "pairs": {}}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = by_annotator[names[i]], by_annotator[names[j]]
            common = sorted(set(a) & set(b))
            stats = {"n_common": len(common), "fields": {}}
            for field in fields:
                va = [a[s][field] for s in common if a[s][field] and b[s][field]]
                vb = [b[s][field] for s in common if a[s][field] and b[s][field]]
                stats["fields"][field] = {
                    "n": len(va),
                    "percent_agreement": (sum(x == y for x, y in zip(va, vb)) / len(va)) if va else None,
                    "cohen_kappa": _kappa(va, vb),
                }
            nat = [(a[s]["naturalness_1to5"], b[s]["naturalness_1to5"]) for s in common if a[s]["naturalness_1to5"] and b[s]["naturalness_1to5"]]
            try:
                diffs = [abs(int(x) - int(y)) for x, y in nat]
                stats["naturalness"] = {"n": len(diffs), "mean_abs_diff": (sum(diffs) / len(diffs)) if diffs else None,
                                        "within_1": (sum(d <= 1 for d in diffs) / len(diffs)) if diffs else None}
            except ValueError:
                stats["naturalness"] = {"n": len(nat), "error": "non-integer naturalness"}
            stats["disagreements"] = [s for s in common if a[s]["referent_id"] != b[s]["referent_id"] or a[s]["ambiguity"] != b[s]["ambiguity"]]
            out["pairs"][f"{names[i]}~{names[j]}"] = stats
    return out


def make_pair_sheet(samples: Iterable[Sample], out_path: Path) -> Path:
    from .variations import pair_manifest

    samples = list(samples)
    by_id = {s.sample_id: s for s in samples}
    manifest = pair_manifest(samples)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PAIR_FIELDS)
        writer.writeheader()
        for p in manifest["pairs"]:
            writer.writerow({
                "pair_id": p["pair_id"], "sample_a": p["a"], "sample_b": p["b"],
                "claimed_manipulations": ",".join(p["claimed_manipulations"]),
                "dialogue_a": render_dialogue(by_id[p["a"]].record, mark_predicate=True),
                "dialogue_b": render_dialogue(by_id[p["b"]].record, mark_predicate=True),
                "pair_valid": "", "only_claimed_changed": "", "gold_change_as_intended": "", "notes": "",
            })
    return out_path


def load_decisions(path: Optional[Path]) -> dict[str, dict]:
    """조정 파일: sample_id, adjudicator, decision(accept|reject), final_referent_id, final_ambiguity, reason."""
    if path is None or not Path(path).exists():
        return {}
    out = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            out[row["sample_id"]] = {k: (v or "").strip() for k, v in row.items()}
    return out


def adjudicate(samples: Iterable[Sample], rows: list[dict], decisions: dict[str, dict], min_annotators: int = 2) -> tuple[list[LabelRecord], dict]:
    """최초 판정을 보존하고 최종 라벨을 만든다.

    규칙:
    - 판정자 수 < min_annotators: in_review 유지.
    - 전원 referent_id 일치 + 전원 ambiguity=unambiguous: accepted, gold=합의값. 작성자 gold와 다르면 기록.
    - 전원 referent_id 비움 + 전원 같은 ambiguous/uncertain: rejected(평가셋 제외), gold None.
    - 그 외: decisions에 accept(final_referent_id 필수)가 있으면 accepted, reject면 rejected, 없으면 in_review.
    """
    votes: dict[str, list[dict]] = {}
    for r in rows:
        votes.setdefault(r["sample_id"], []).append(r)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    labels, summary = [], Counter()
    for s in samples:
        lab = s.label.model_copy(deep=True)
        v = votes.get(s.sample_id, [])
        meta = dict(lab.validation_metadata)
        meta["annotator_votes"] = [{k: r[k] for k in ("annotator", "referent_id", "referent_role", "context_sufficient", "ambiguity", "previous_referent_id", "naturalness_1to5", "notes")} for r in v]
        meta["adjudicated_at"] = now
        original_gold = lab.gold_referent_id
        if len(v) < min_annotators:
            lab.annotation_status = "in_review"
            summary["in_review"] += 1
        else:
            referents = {r["referent_id"] for r in v}
            unanimous = len(referents) == 1 and "" not in referents and all(r["ambiguity"] == "unambiguous" for r in v)
            decision = decisions.get(s.sample_id)
            ambiguities = {r["ambiguity"] for r in v}
            unanimous_ambiguous = referents == {""} and len(ambiguities) == 1 and ambiguities <= {"ambiguous", "uncertain"}
            if unanimous_ambiguous:
                lab.gold_referent_id = None
                lab.ambiguity_status = next(iter(ambiguities))
                lab.annotation_status = "rejected"
                meta["agreement"] = "unanimous_ambiguous"
                summary["rejected_unanimous_ambiguous"] += 1
            elif unanimous:
                lab.gold_referent_id = next(iter(referents))
                lab.ambiguity_status = "unambiguous"
                lab.annotation_status = "accepted"
                meta["agreement"] = "unanimous"
                summary["accepted_unanimous"] += 1
            elif decision and decision.get("decision") == "accept" and decision.get("final_referent_id"):
                lab.gold_referent_id = decision["final_referent_id"]
                lab.ambiguity_status = "unambiguous"
                lab.annotation_status = "accepted"
                meta["adjudication"] = decision
                summary["accepted_adjudicated"] += 1
            elif decision and decision.get("decision") == "reject":
                lab.annotation_status = "rejected"
                lab.ambiguity_status = decision.get("final_ambiguity") or "ambiguous"
                if lab.ambiguity_status == "unambiguous":
                    lab.ambiguity_status = "uncertain"
                lab.gold_referent_id = None
                meta["adjudication"] = decision
                summary["rejected"] += 1
            else:
                lab.annotation_status = "in_review"
                meta["agreement"] = "disagreement_pending"
                summary["pending"] += 1
        if lab.gold_referent_id != original_gold:
            meta["author_gold_overridden"] = {"from": original_gold, "to": lab.gold_referent_id}
        if lab.gold_referent_id is not None and lab.ambiguity_status == "unreviewed" and lab.annotation_status != "accepted":
            pass  # 검수 전 상태 유지
        lab.validation_metadata = meta
        labels.append(LabelRecord.model_validate(lab.model_dump()))
    return labels, dict(summary)


def role_check(sample: Sample, referent_id: str) -> Optional[str]:
    """검수자가 적은 referent_id로 역할을 계산한다(검수자의 referent_role과 대조용)."""
    rec = sample.record
    addressee = infer_addressee(rec, rec.speaker_id, sample.label.addressee_id)
    return role_of(referent_id, rec.speaker_id, addressee, rec)
