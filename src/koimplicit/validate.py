"""자동 데이터 검증.

코드가 판정하는 것: 스키마, 턴·화자 정합성, gold 식별 가능성(후보 안에 있는가), 중복, 조건 불균형,
pair·시나리오 연결, 평가 입력의 gold 누수, 생성 출처·검수 상태.
코드가 판정하지 않는 것: 의미상 모호한지. 이는 human_review_flags로 사람에게 넘긴다.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

from .payload import to_gold, to_item
from .runner import GOLD_KEYS, build_request, load_prompt, strip_gold
from .scenarios import Scenario
from .schema import Sample, load_dataset

ROLE_WORDS = ("speaker", "addressee", "third_party", "gold", "정답", "anchor", "distractor")
LEAK_CONFIG = {"model_id": "leak-check", "model_label": "leak-check", "output_schema": "{}"}


def issue(level: str, sample_id: Optional[str], code: str, message: str) -> dict:
    return {"level": level, "sample_id": sample_id, "code": code, "message": message}


def check_structure(s: Sample) -> list[dict]:
    out = []
    rec, lab, der = s.record, s.label, s.derived
    ids = {p.entity_id for p in rec.participants}
    if lab.gold_referent_id is not None and lab.gold_referent_id not in ids:
        out.append(issue("error", s.sample_id, "GOLD_NOT_CANDIDATE", "gold_referent_id not in participants"))
    if lab.gold_referent_id is not None and der.gold_referent_role is None:
        out.append(issue("error", s.sample_id, "ROLE_UNDETERMINED", "gold is a dialogue participant but addressee cannot be determined (3-party); set addressee_id or leave gold None"))
    if lab.addressee_id is not None:
        if lab.addressee_id not in rec.in_dialogue_ids() or lab.addressee_id == rec.speaker_id:
            out.append(issue("error", s.sample_id, "ADDRESSEE_INVALID", "addressee_id must be another in-dialogue participant"))
    if lab.anchor_turn is not None:
        if lab.anchor_turn >= rec.target_turn:
            out.append(issue("error", s.sample_id, "ANCHOR_AFTER_TARGET", "anchor_turn must precede target_turn"))
        if lab.anchor_referent_id not in ids:
            out.append(issue("error", s.sample_id, "ANCHOR_NOT_CANDIDATE", "anchor_referent_id not in participants"))
    if lab.distractor_id is not None:
        if lab.distractor_id not in ids:
            out.append(issue("error", s.sample_id, "DISTRACTOR_NOT_CANDIDATE", "distractor_id not in participants"))
        elif lab.distractor_id == lab.gold_referent_id:
            out.append(issue("error", s.sample_id, "DISTRACTOR_IS_GOLD", "distractor_id equals gold"))
        elif not der.distractor_present:
            out.append(issue("warning", s.sample_id, "DISTRACTOR_NOT_RECENT", "declared distractor is not mentioned more recently than the gold referent"))
    if lab.gold_referent_id is None and lab.ambiguity_status in ("unreviewed",):
        out.append(issue("warning", s.sample_id, "NO_GOLD_UNREVIEWED", "no gold and ambiguity_status unreviewed; mark ambiguous/uncertain or add gold"))
    if lab.anchor_turn is None and rec.dataset == "controlled":
        out.append(issue("warning", s.sample_id, "ANCHOR_MISSING", "controlled sample without anchor: shift variables are None"))
    if not rec.generation_metadata.model and rec.creation_method.startswith("llm"):
        out.append(issue("error", s.sample_id, "GEN_MODEL_MISSING", "llm creation_method requires generation_metadata.model"))
    if not rec.generation_metadata.created:
        out.append(issue("warning", s.sample_id, "CREATED_MISSING", "generation_metadata.created is empty"))
    # 사람 검수 대상 표시(코드가 판정하지 않는다)
    flags = []
    if lab.ambiguity_status == "unreviewed":
        flags.append("gold_unverified")
    if der.gold_referent_role in ("speaker", "addressee") and der.turn_distance is None:
        flags.append("deictic_no_text_mention")
    if der.n_participants == 3:
        flags.append("multi_party_addressee")
    if der.distractor_present:
        flags.append("distractor_check_gold_still_unique")
    if flags:
        out.append(issue("review", s.sample_id, "HUMAN_REVIEW", ",".join(flags)))
    return out


def check_duplicates(samples: list[Sample]) -> list[dict]:
    out = []
    seen_text: dict[str, str] = {}
    seen_target: dict[str, str] = {}
    for s in samples:
        text = "\n".join(f"{t.speaker_id}\t{t.text}" for t in s.record.dialogue)
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        key = f"{h}:{s.record.target_turn}:{s.record.target_predicate}"
        if key in seen_target:
            out.append(issue("error", s.sample_id, "DUPLICATE_SAMPLE", f"identical dialogue and target as {seen_target[key]}"))
        elif h in seen_text:
            out.append(issue("warning", s.sample_id, "DUPLICATE_DIALOGUE", f"identical dialogue text as {seen_text[h]} (different target)"))
        seen_text.setdefault(h, s.sample_id)
        seen_target.setdefault(key, s.sample_id)
    return out


def check_links(samples: list[Sample], scenarios: Optional[list[Scenario]]) -> list[dict]:
    out = []
    by_scenario = {sc.scenario_id: sc for sc in scenarios} if scenarios else None
    pairs: dict[str, list[Sample]] = {}
    for s in samples:
        if by_scenario is not None and s.record.scenario_id not in by_scenario:
            out.append(issue("error", s.sample_id, "SCENARIO_UNKNOWN", f"scenario {s.record.scenario_id} not in scenario file"))
        elif by_scenario is not None:
            sc = by_scenario[s.record.scenario_id]
            if {p.entity_id for p in sc.participants} != {p.entity_id for p in s.record.participants}:
                out.append(issue("warning", s.sample_id, "ROSTER_MISMATCH", "participants differ from scenario roster"))
            if s.record.variant != "base" and sc.variant(s.record.variant) is None:
                out.append(issue("warning", s.sample_id, "VARIANT_UNKNOWN", f"variant {s.record.variant} not declared in scenario"))
        for pid in s.record.pair_ids:
            pairs.setdefault(pid, []).append(s)
    for pid, members in pairs.items():
        if len(members) != 2:
            out.append(issue("error", None, "PAIR_SIZE", f"pair {pid} has {len(members)} members"))
            continue
        a, b = members
        if a.record.scenario_id != b.record.scenario_id:
            out.append(issue("error", None, "PAIR_SCENARIO", f"pair {pid} spans scenarios"))
        if {p.entity_id for p in a.record.participants} != {p.entity_id for p in b.record.participants}:
            out.append(issue("error", None, "PAIR_CANDIDATES", f"pair {pid} candidate sets differ"))
    return out


def check_leakage(samples: list[Sample], prompt_path: Optional[Path]) -> list[dict]:
    """평가 입력 item과 렌더링된 프롬프트에 gold 정보가 없는지 확인한다."""
    out = []
    prompt = load_prompt(prompt_path) if prompt_path else None
    for s in samples:
        item = to_item(s, seed=0)
        present = [k for k in GOLD_KEYS if k in item]
        if present:
            out.append(issue("error", s.sample_id, "ITEM_HAS_GOLD_KEY", f"item carries {present}"))
        serialized = json.dumps(item, ensure_ascii=False)
        if s.label.author_rationale and s.label.author_rationale in serialized:
            out.append(issue("error", s.sample_id, "ITEM_HAS_RATIONALE", "author_rationale leaked into item"))
        if prompt and prompt["template"].strip() and s.label.gold_referent_id:
            for condition in ("full_mcq", "target_only_mcq"):
                text = build_request(strip_gold(item), condition, prompt, LEAK_CONFIG)["user"]
                low = text.lower()
                hits = [w for w in ROLE_WORDS if w in low]
                if hits:
                    out.append(issue("error", s.sample_id, "PROMPT_ROLE_WORD", f"{condition}: prompt contains {hits}"))
                if "role" in low:
                    out.append(issue("error", s.sample_id, "PROMPT_ROLE_FIELD", f"{condition}: prompt contains 'role'"))
        # 대화 뒤 발화 유출: full_text가 목표 발화 뒤를 포함하면 안 된다
        if item["full_text"].count("\n") + 1 != s.record.target_turn:
            out.append(issue("error", s.sample_id, "FUTURE_CONTEXT", "full_text must end at the target turn"))
    return out


def balance(samples: Iterable[Sample]) -> dict:
    samples = list(samples)

    def count(key):
        return dict(sorted(Counter(str(key(s)) for s in samples).items()))

    return {
        "n": len(samples),
        "by_dataset": count(lambda s: s.record.dataset),
        "by_role": count(lambda s: s.derived.gold_referent_role),
        "by_referent_changed": count(lambda s: s.derived.referent_changed),
        "by_speaker_changed": count(lambda s: s.derived.speaker_changed),
        "by_role_changed": count(lambda s: s.derived.referent_role_changed),
        "by_distractor_present": count(lambda s: s.derived.distractor_present),
        "by_turn_distance": count(lambda s: s.derived.turn_distance),
        "by_n_participants": count(lambda s: s.derived.n_participants),
        "by_n_turns": count(lambda s: s.derived.n_turns),
        "by_annotation_status": count(lambda s: s.label.annotation_status),
        "by_ambiguity_status": count(lambda s: s.label.ambiguity_status),
        "by_creation_method": count(lambda s: s.record.creation_method),
        "n_pairs": len({s.record.pair_id for s in samples if s.record.pair_id}),
        "n_scenarios": len({s.record.scenario_id for s in samples}),
    }


def check_balance(samples: list[Sample]) -> list[dict]:
    out = []
    b = balance(samples)
    for role in ("speaker", "addressee", "third_party"):
        if b["by_role"].get(role, 0) == 0:
            out.append(issue("warning", None, "ROLE_CELL_EMPTY", f"no sample with gold role {role}"))
    for key, label in (("by_referent_changed", "referent shift"), ("by_distractor_present", "distractor")):
        if not ({"True", "False"} <= set(b[key])):
            out.append(issue("warning", None, "CONDITION_CELL_EMPTY", f"{label} does not have both True and False cells"))
    if b["by_annotation_status"].get("accepted", 0) == 0:
        out.append(issue("info", None, "NO_ACCEPTED", "no accepted samples yet; evaluation payload will be empty without --include-unreviewed"))
    return out


def validate_samples(samples: list[Sample], scenarios: Optional[list[Scenario]] = None, prompt_path: Optional[Path] = None) -> dict:
    issues = []
    for s in samples:
        issues += check_structure(s)
    issues += check_duplicates(samples)
    issues += check_links(samples, scenarios)
    issues += check_leakage(samples, prompt_path)
    issues += check_balance(samples)
    counts = Counter(i["level"] for i in issues)
    return {
        "n_samples": len(samples),
        "n_errors": counts.get("error", 0),
        "n_warnings": counts.get("warning", 0),
        "n_review_flags": counts.get("review", 0),
        "balance": balance(samples),
        "issues": issues,
    }


def validate_dataset(folder: Path, scenarios: Optional[list[Scenario]] = None, prompt_path: Optional[Path] = None) -> dict:
    try:
        samples = load_dataset(folder)
    except ValueError as e:
        return {"n_samples": 0, "n_errors": 1, "n_warnings": 0, "n_review_flags": 0, "balance": {},
                "issues": [issue("error", None, "SCHEMA", str(e))]}
    return validate_samples(samples, scenarios, prompt_path)


def review_markdown(samples: list[Sample], report: Optional[dict] = None) -> str:
    """사람이 읽는 Pilot Review 문서. 정답은 접힌 블록 뒤에 둔다(검수자는 먼저 대화만 본다)."""
    lines = ["# Pilot Review", "", "대화를 먼저 읽고 생략 주어를 판단한 뒤, '작성자 라벨'을 펼쳐 비교한다. 작성자 라벨은 검수 전 후보값이다.", ""]
    if report:
        lines += ["## 자동 검증 요약", "", f"- 표본 {report['n_samples']}개, 오류 {report['n_errors']}, 경고 {report['n_warnings']}, 사람 검수 표시 {report['n_review_flags']}", ""]
        b = report["balance"]
        lines += ["| 축 | 분포 |", "|---|---|"]
        for key in ("by_dataset", "by_role", "by_referent_changed", "by_speaker_changed", "by_distractor_present", "by_turn_distance", "by_n_participants"):
            lines.append(f"| {key} | {json.dumps(b.get(key, {}), ensure_ascii=False)} |")
        lines.append("")
    by_scenario: dict[str, list[Sample]] = {}
    for s in samples:
        by_scenario.setdefault(s.record.scenario_id, []).append(s)
    for scenario_id, members in by_scenario.items():
        lines += [f"## {scenario_id}", ""]
        for s in members:
            rec, lab, der = s.record, s.label, s.derived
            names = ", ".join(f"{p.entity_id}={p.name}" + ("" if p.in_dialogue else "(비참여)") for p in rec.participants)
            lines += [f"### {s.sample_id} ({rec.dataset}, variant={rec.variant}, pairs={','.join(rec.pair_ids) or '-'})", "",
                      f"- 인물: {names}", f"- 목표: {rec.target_turn}번 발화, 서술어 `{rec.target_predicate}`, 화자 {rec.participant(rec.speaker_id).name}", "", "```text"]
            lines += rec_lines(s)
            lines += ["```", "", "<details><summary>작성자 라벨 (검수 전)</summary>", ""]
            gold_name = rec.participant(lab.gold_referent_id).name if lab.gold_referent_id else "(없음)"
            lines += [f"- gold: {lab.gold_referent_id} {gold_name} / role={der.gold_referent_role}",
                      f"- anchor: turn {lab.anchor_turn} → {lab.anchor_referent_id}; speaker_changed={der.speaker_changed}, referent_changed={der.referent_changed}, role_changed={der.referent_role_changed}",
                      f"- distractor: {lab.distractor_id} present={der.distractor_present}; turn_distance={der.turn_distance}; most_recent={der.most_recent_mentioned_id}",
                      f"- cues: {', '.join(lab.linguistic_cues) or '-'}; manipulated: {', '.join(lab.manipulated_variables) or '-'}; expected_gold_change={lab.expected_gold_change}",
                      f"- 상태: ambiguity={lab.ambiguity_status}, annotation={lab.annotation_status}, creation={rec.creation_method}",
                      f"- 근거: {lab.author_rationale or '-'}", "", "</details>", ""]
            if report:
                flagged = [i for i in report["issues"] if i["sample_id"] == s.sample_id]
                if flagged:
                    lines += ["검증 표시: " + "; ".join(f"{i['level']}:{i['code']}({i['message']})" for i in flagged), ""]
    return "\n".join(lines)


def rec_lines(s: Sample) -> list[str]:
    from .schema import render_dialogue
    return render_dialogue(s.record, up_to=len(s.record.dialogue), mark_predicate=True).split("\n")
