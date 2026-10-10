"""Human Annotation Workflow.

흐름:
1. make_sheets(condition=full|local): 검수자별 CSV. sample_id 대신 불투명 review_id를 쓰고(id_map.json에 대응표),
   작성자 gold·anchor·근거·family·variant를 숨기며 순서를 검수자별 seed로 섞는다.
   local 시트는 목표 발화만 보여 준다(RQ1의 Local 충분성 판정).
2. 검수자가 CSV를 채운다(독립 판정).
3. load_sheet + agreement: 최초 독립 판정을 보존한 채 일치도(percent, Cohen's κ)를 계산한다. κ가 정의되지 않으면 None.
4. make_pair_sheet: 독립 판정이 끝난 뒤 pair 두 버전을 나란히 보고 minimal pair 타당성을 판정한다.
5. adjudicate: Full 판정으로 gold·anchor·청자를 확정한다. 전원 일치 → accepted, 전원 모호 → rejected,
   불일치 → decisions로 수정 또는 제외. Local 판정이 있으면 context_need를 분류한다.
   최초 판정은 validation_metadata.annotator_votes에 전부 보존한다.

검수 파일은 annotations/ 아래(Git 제외)에 둔다.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import random
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

from .schema import LabelRecord, Sample, infer_addressee, render_dialogue, role_of

SHEET_FIELDS = ["order", "review_id", "dialogue", "target_turn", "target_predicate", "target_speaker", "candidates",
                "naturalness_1to5", "referent_id", "referent_role", "addressee_id", "context_sufficient", "ambiguity",
                "previous_referent_id", "previous_referent_turn", "notes"]
JUDGEMENT_FIELDS = ["naturalness_1to5", "referent_id", "referent_role", "addressee_id", "context_sufficient", "ambiguity",
                    "previous_referent_id", "previous_referent_turn", "notes"]
AGREEMENT_FIELDS = ("referent_id", "referent_role", "addressee_id", "context_sufficient", "ambiguity", "previous_referent_id", "previous_referent_turn")
PAIR_FIELDS = ["pair_id", "sample_a", "sample_b", "claimed_manipulations", "dialogue_a", "dialogue_b",
               "pair_valid", "only_claimed_changed", "gold_change_as_intended", "notes"]
VALID_AMBIGUITY = ("unambiguous", "ambiguous", "uncertain")
CONDITIONS = ("full", "local")
ID_MAP_FILE = "id_map.json"


# --------------------------------------------------------------------------- 시트 생성

def review_id_map(samples: Iterable[Sample], seed: int) -> dict[str, str]:
    """review_id → sample_id. 작성자 의도가 드러나는 sample_id를 숨긴다."""
    ids = sorted(s.sample_id for s in samples)
    random.Random(f"{seed}:id_map").shuffle(ids)
    return {f"R{i:03d}": sid for i, sid in enumerate(ids, start=1)}


def sheet_row(sample: Sample, order: int, review_id: str, condition: str) -> dict:
    rec = sample.record
    cands = "; ".join(f"{p.entity_id}={p.name}" for p in rec.participants)
    if condition == "full":
        dialogue = render_dialogue(rec, mark_predicate=True)
    else:
        name = rec.participant(rec.speaker_id).name
        text = rec.target().text
        b, e = rec.target_predicate_span
        dialogue = f"{name}: {text[:b]}[[{text[b:e]}]]{text[e:]}"
    return {
        "order": order, "review_id": review_id, "dialogue": dialogue,
        "target_turn": rec.target_turn if condition == "full" else "", "target_predicate": rec.target_predicate,
        "target_speaker": rec.participant(rec.speaker_id).name, "candidates": cands,
        **{f: "" for f in JUDGEMENT_FIELDS},
    }


def make_sheets(samples: Iterable[Sample], annotators: list[str], out_dir: Path, seed: int = 0, condition: str = "full") -> list[Path]:
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}")
    samples = list(samples)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    id_map_path = out_dir / ID_MAP_FILE
    if id_map_path.exists():
        id_map = json.loads(id_map_path.read_text(encoding="utf-8"))
    else:
        id_map = review_id_map(samples, seed)
        id_map_path.write_text(json.dumps(id_map, ensure_ascii=False, indent=2), encoding="utf-8")
    review_of = {sid: rid for rid, sid in id_map.items()}
    paths = []
    for annotator in annotators:
        order = list(samples)
        random.Random(f"{seed}:{condition}:{annotator}").shuffle(order)
        path = out_dir / f"sheet_{condition}_{annotator}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
            writer.writeheader()
            for i, s in enumerate(order, start=1):
                writer.writerow(sheet_row(s, i, review_of[s.sample_id], condition))
        paths.append(path)
    return paths


def load_sheet(path: Path, annotator: Optional[str] = None, condition: Optional[str] = None, id_map: Optional[dict] = None) -> list[dict]:
    """채워진 시트를 읽는다. 이름 sheet_{condition}_{annotator}.csv에서 조건·검수자를 뽑고 id_map.json으로 sample_id를 복원한다."""
    path = Path(path)
    stem = path.stem
    parts = stem.split("_", 2)
    if condition is None:
        condition = parts[1] if len(parts) >= 3 and parts[0] == "sheet" and parts[1] in CONDITIONS else "full"
    if annotator is None:
        annotator = parts[2] if len(parts) >= 3 and parts[0] == "sheet" and parts[1] in CONDITIONS else stem.replace("sheet_", "")
    if id_map is None:
        map_path = path.parent / ID_MAP_FILE
        id_map = json.loads(map_path.read_text(encoding="utf-8")) if map_path.exists() else {}
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            review_id = (row.get("review_id") or "").strip()
            sample_id = id_map.get(review_id, row.get("sample_id") or review_id)
            judged = {k: (row.get(k) or "").strip() for k in JUDGEMENT_FIELDS}
            rows.append({"annotator": annotator, "condition": condition, "sample_id": sample_id, "review_id": review_id, **judged})
    return rows


# --------------------------------------------------------------------------- 일치도

def _kappa(a: list[str], b: list[str]) -> Optional[float]:
    """Cohen's κ. 기대 일치가 1(모두 같은 범주)이면 정의되지 않으므로 None."""
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if expected >= 1:
        return None
    return (observed - expected) / (1 - expected)


def agreement(rows: list[dict], fields: tuple = AGREEMENT_FIELDS) -> dict:
    """조건별·검수자 쌍별 일치도. 빈 응답은 분모에서 빼고 n_missing으로 보고한다."""
    out = {"n_rows": len(rows), "by_condition": {}}
    for condition in sorted({r.get("condition", "full") for r in rows}):
        subset = [r for r in rows if r.get("condition", "full") == condition]
        by_annotator: dict[str, dict[str, dict]] = {}
        for r in subset:
            by_annotator.setdefault(r["annotator"], {})[r["sample_id"]] = r
        names = sorted(by_annotator)
        result = {"annotators": names, "pairs": {}}
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = by_annotator[names[i]], by_annotator[names[j]]
                common = sorted(set(a) & set(b))
                stats = {"n_common": len(common), "fields": {}}
                for field in fields:
                    both = [s for s in common if a[s].get(field) and b[s].get(field)]
                    va, vb = [a[s][field] for s in both], [b[s][field] for s in both]
                    kappa = _kappa(va, vb)
                    stats["fields"][field] = {
                        "n": len(va), "n_missing": len(common) - len(va),
                        "percent_agreement": (sum(x == y for x, y in zip(va, vb)) / len(va)) if va else None,
                        "cohen_kappa": kappa,
                        "kappa_note": None if kappa is not None or not va else "undefined: single category",
                    }
                nat = [(a[s].get("naturalness_1to5"), b[s].get("naturalness_1to5")) for s in common if a[s].get("naturalness_1to5") and b[s].get("naturalness_1to5")]
                try:
                    diffs = [abs(int(x) - int(y)) for x, y in nat]
                    stats["naturalness"] = {"n": len(diffs), "mean_abs_diff": (sum(diffs) / len(diffs)) if diffs else None,
                                            "within_1": (sum(d <= 1 for d in diffs) / len(diffs)) if diffs else None}
                except ValueError:
                    stats["naturalness"] = {"n": len(nat), "error": "non-integer naturalness"}
                stats["disagreements"] = [s for s in common if a[s].get("referent_id") != b[s].get("referent_id") or a[s].get("ambiguity") != b[s].get("ambiguity")]
                result["pairs"][f"{names[i]}~{names[j]}"] = stats
        out["by_condition"][condition] = result
    return out


# --------------------------------------------------------------------------- pair 시트

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


# --------------------------------------------------------------------------- 조정

def load_decisions(path: Optional[Path]) -> dict[str, dict]:
    """조정 파일 열: sample_id, adjudicator, decision(accept|reject), final_referent_id, final_ambiguity,
    final_addressee_id, final_anchor_turn, final_anchor_referent_id, reason."""
    if path is None or not Path(path).exists():
        return {}
    out = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            out[row["sample_id"]] = {k: (v or "").strip() for k, v in row.items() if k}
    return out


def _check_votes(samples: list[Sample], rows: list[dict]) -> dict[str, list[dict]]:
    """(annotator, sample_id, condition) 중복과 후보 밖 ID를 거부하고 sample_id별 Full 판정을 모은다."""
    by_id = {s.sample_id: s for s in samples}
    seen = set()
    problems = []
    votes: dict[str, list[dict]] = {}
    for r in rows:
        key = (r["annotator"], r["sample_id"], r.get("condition", "full"))
        if key in seen:
            problems.append(f"duplicate vote {key}")
        seen.add(key)
        s = by_id.get(r["sample_id"])
        if s is None:
            problems.append(f"vote for unknown sample {r['sample_id']}")
            continue
        ids = {p.entity_id for p in s.record.participants}
        r.setdefault("condition", "full")
        for field in JUDGEMENT_FIELDS:
            r.setdefault(field, "")
        for field in ("referent_id", "previous_referent_id", "addressee_id"):
            if r.get(field) and r[field] not in ids:
                problems.append(f"{r['annotator']}/{r['sample_id']}: {field}={r[field]!r} not a candidate")
        if r.get("ambiguity") and r["ambiguity"] not in VALID_AMBIGUITY:
            problems.append(f"{r['annotator']}/{r['sample_id']}: ambiguity={r['ambiguity']!r} invalid")
        if r.get("condition", "full") == "full":
            votes.setdefault(r["sample_id"], []).append(r)
    if problems:
        raise ValueError("annotation sheet problems:\n- " + "\n- ".join(problems))
    return votes


def _unanimous(values: list[str]) -> Optional[str]:
    """전원 같은 값(빈 값 포함)이면 그 값, 아니면 None."""
    return values[0] if values and len(set(values)) == 1 else None


def classify_context_need(final_gold: Optional[str], local_votes: list[dict]) -> Optional[str]:
    """RQ1 분류. Full gold와 Local 판정을 비교한다(설계안 5.4)."""
    if final_gold is None or not local_votes:
        return None
    ids = [r["referent_id"] for r in local_votes]
    amb = [r["ambiguity"] for r in local_votes]
    if all(a == "unambiguous" and i == final_gold for a, i in zip(amb, ids)):
        return "locally_recoverable"
    if all(a in ("ambiguous", "uncertain") or not i for a, i in zip(amb, ids)):
        return "discourse_dependent"
    return "conflict"


def adjudicate(samples: Iterable[Sample], rows: list[dict], decisions: dict[str, dict], min_annotators: int = 2) -> tuple[list[LabelRecord], dict]:
    """최초 판정을 보존하고 최종 라벨을 만든다. Full 판정이 gold·anchor·청자를 정하고 Local 판정은 context_need에 쓴다.

    규칙:
    - 서로 다른 검수자 수 < min_annotators: in_review.
    - 전원 referent_id 일치 + 전원 unambiguous: accepted. 작성자 gold와 다르면 기록.
    - 전원 referent_id 비움 + 전원 같은 ambiguous/uncertain: rejected.
    - 그 외: decisions의 accept(final_referent_id 필수)/reject, 없으면 in_review.
    - anchor·청자: 전원 일치하면 그 값(빈 값 일치면 None), 불일치면 decisions의 final_* 또는 작성자 값 유지 + disputed 기록.
    """
    samples = list(samples)
    votes = _check_votes(samples, rows)
    local_votes: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("condition") == "local":
            local_votes.setdefault(r["sample_id"], []).append(r)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    labels, summary = [], Counter()
    for s in samples:
        lab = s.label.model_copy(deep=True)
        v = votes.get(s.sample_id, [])
        meta = dict(lab.validation_metadata)
        meta["annotator_votes"] = [{k: r.get(k, "") for k in ("annotator", "condition", *JUDGEMENT_FIELDS)} for r in rows if r["sample_id"] == s.sample_id]
        meta["adjudicated_at"] = now
        original = {"gold": lab.gold_referent_id, "anchor_turn": lab.anchor_turn, "anchor_referent_id": lab.anchor_referent_id, "addressee_id": lab.addressee_id}
        decision = decisions.get(s.sample_id) or {}
        distinct = {r["annotator"] for r in v}
        if len(distinct) < min_annotators:
            lab.annotation_status = "in_review"
            summary["in_review"] += 1
        else:
            referent = _unanimous([r["referent_id"] for r in v])
            ambiguity = _unanimous([r["ambiguity"] for r in v])
            if referent and ambiguity == "unambiguous":
                lab.gold_referent_id, lab.ambiguity_status, lab.annotation_status = referent, "unambiguous", "accepted"
                meta["agreement"] = "unanimous"
                summary["accepted_unanimous"] += 1
            elif referent == "" and ambiguity in ("ambiguous", "uncertain"):
                lab.gold_referent_id, lab.ambiguity_status, lab.annotation_status = None, ambiguity, "rejected"
                meta["agreement"] = "unanimous_ambiguous"
                summary["rejected_unanimous_ambiguous"] += 1
            elif decision.get("decision") == "accept" and decision.get("final_referent_id"):
                lab.gold_referent_id, lab.ambiguity_status, lab.annotation_status = decision["final_referent_id"], "unambiguous", "accepted"
                meta["adjudication"] = decision
                summary["accepted_adjudicated"] += 1
            elif decision.get("decision") == "reject":
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
            # anchor
            anchor_id = _unanimous([r["previous_referent_id"] for r in v])
            anchor_turn = _unanimous([r["previous_referent_turn"] for r in v])
            if decision.get("final_anchor_referent_id") or decision.get("final_anchor_turn"):
                lab.anchor_referent_id = decision.get("final_anchor_referent_id") or None
                lab.anchor_turn = int(decision["final_anchor_turn"]) if decision.get("final_anchor_turn") else None
            elif anchor_id is not None and anchor_turn is not None:
                if anchor_id and anchor_turn:
                    lab.anchor_referent_id, lab.anchor_turn = anchor_id, int(anchor_turn)
                elif not anchor_id and not anchor_turn:
                    lab.anchor_referent_id = lab.anchor_turn = None
                else:
                    meta["anchor_disputed"] = "inconsistent unanimous values"
            else:
                meta["anchor_disputed"] = [{"annotator": r["annotator"], "id": r["previous_referent_id"], "turn": r["previous_referent_turn"]} for r in v]
            # 청자(다자 대화)
            addressee = _unanimous([r["addressee_id"] for r in v])
            if decision.get("final_addressee_id"):
                lab.addressee_id = decision["final_addressee_id"]
            elif addressee:
                lab.addressee_id = addressee
            elif addressee is None and any(r["addressee_id"] for r in v):
                meta["addressee_disputed"] = [{"annotator": r["annotator"], "id": r["addressee_id"]} for r in v]
            # 역할 대조
            mismatches = [r["annotator"] for r in v if r["referent_id"] and r["referent_role"] and role_check(s, r["referent_id"]) != r["referent_role"]]
            if mismatches:
                meta["role_mismatch"] = mismatches
        changed = {k: {"from": original[k], "to": new} for k, new in (("gold", lab.gold_referent_id), ("anchor_turn", lab.anchor_turn),
                   ("anchor_referent_id", lab.anchor_referent_id), ("addressee_id", lab.addressee_id)) if original[k] != new}
        if changed:
            meta["author_values_overridden"] = changed
        context_need = classify_context_need(lab.gold_referent_id if lab.annotation_status == "accepted" else None, local_votes.get(s.sample_id, []))
        if context_need:
            meta["context_need"] = context_need
            summary[f"context_need_{context_need}"] += 1
        lab.validation_metadata = meta
        labels.append(LabelRecord.model_validate(lab.model_dump()))
    return labels, dict(summary)


def role_check(sample: Sample, referent_id: str) -> Optional[str]:
    """검수자가 적은 referent_id로 역할을 계산한다(검수자의 referent_role과 대조용)."""
    rec = sample.record
    addressee = infer_addressee(rec, rec.speaker_id, sample.label.addressee_id)
    return role_of(referent_id, rec.speaker_id, addressee, rec)
