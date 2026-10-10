"""Controlled Variation 구조.

변형 대화문 자체는 사람 또는 생성 모델이 쓴다(자동 치환으로 한국어 대화를 바꾸지 않는다).
이 모듈은 "어떤 변수를 바꿨다고 주장하는지"와 "실제로 무엇이 달라졌는지"를 대조한다.

- pair_diff: 같은 pair_id의 두 sample에서 달라진 실험 변수·발화·정답을 전부 나열한다.
- unclaimed_differences: 주장한 조작(manipulated_variables)으로 설명되지 않는 차이. 비어 있지 않으면
  단일 변수 minimal pair라고 부르지 않고 compound 변형으로 기록한다.
"""

from __future__ import annotations

from typing import Iterable, Optional

from .schema import Sample

CONTROLLED_VARIABLES = (
    "gold_referent_id", "gold_referent_role", "speaker_id", "addressee_id",
    "speaker_changed", "referent_changed", "referent_role_changed",
    "turn_distance", "gold_last_mention_turn", "most_recent_mentioned_id",
    "distractor_present", "distractor_id", "distractor_last_mention_turn",
    "n_turns", "n_participants", "target_predicate", "anchor_turn", "anchor_referent_id", "linguistic_cues",
)

# 주장한 조작 하나가 바꿀 수 있는 변수들. 이 밖의 차이는 unclaimed로 보고한다.
MANIPULATION_SCOPE = {
    "referent_shift": {"gold_referent_id", "gold_referent_role", "referent_changed", "referent_role_changed",
                       "turn_distance", "gold_last_mention_turn", "most_recent_mentioned_id", "distractor_present",
                       "distractor_id", "distractor_last_mention_turn", "anchor_turn", "anchor_referent_id"},
    "distractor": {"distractor_present", "distractor_id", "distractor_last_mention_turn", "most_recent_mentioned_id"},
    "context_distance": {"turn_distance", "gold_last_mention_turn", "n_turns", "anchor_turn", "most_recent_mentioned_id",
                         "distractor_last_mention_turn"},
    "speaker_role": {"speaker_id", "addressee_id", "gold_referent_role", "speaker_changed", "referent_role_changed",
                     "anchor_turn", "anchor_referent_id", "gold_referent_id", "referent_changed", "turn_distance",
                     "gold_last_mention_turn", "most_recent_mentioned_id", "distractor_present"},
    "linguistic_cue": {"linguistic_cues", "target_predicate"},
}


GOLD_DEPENDENT = {"gold_referent_id", "gold_referent_role", "referent_changed", "referent_role_changed", "turn_distance",
                  "gold_last_mention_turn", "distractor_present", "most_recent_mentioned_id", "addressee_id"}


def pair_sides(pair_id: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """'{scenario}:{a}~{b}' → (a, b). a가 기준, b가 변형."""
    if not pair_id or ":" not in pair_id or "~" not in pair_id:
        return None, None
    names = pair_id.split(":", 1)[1]
    a, _, b = names.partition("~")
    return a, b


def variant_side(a: Sample, b: Sample, pair_id: Optional[str]) -> Optional[Sample]:
    _, name = pair_sides(pair_id)
    for s in (a, b):
        if name and s.record.variant == name:
            return s
    return None


def claimed_manipulations(a: Sample, b: Sample, pair_id: Optional[str]) -> list[str]:
    """pair별 주장 조작. 우선순위: 두 표본의 pair_claims(충돌하면 ValueError) → 변형 쪽 manipulated_variables → 합집합."""
    claims = [s.label.pair_claims[pair_id] for s in (a, b) if pair_id and pair_id in s.label.pair_claims]
    if claims:
        if len(claims) == 2 and sorted(claims[0]) != sorted(claims[1]):
            raise ValueError(f"pair {pair_id}: conflicting pair_claims {claims}")
        return sorted(claims[0])
    side = variant_side(a, b, pair_id)
    if side is not None:
        return sorted(side.label.manipulated_variables)
    return sorted(set(a.label.manipulated_variables) | set(b.label.manipulated_variables))


def expected_change(a: Sample, b: Sample, pair_id: Optional[str]) -> Optional[bool]:
    """pair별 정답 변경 의도. pair_expected_gold_change → 변형 쪽 expected_gold_change(base 비교일 때만)."""
    for s in (a, b):
        if pair_id and pair_id in s.label.pair_expected_gold_change:
            return s.label.pair_expected_gold_change[pair_id]
    base_name, _ = pair_sides(pair_id)
    side = variant_side(a, b, pair_id)
    if side is not None and base_name == "base":
        return side.label.expected_gold_change
    return None


def pair_diff(a: Sample, b: Sample, pair_id: Optional[str] = None) -> dict:
    fa, fb = a.flat(), b.flat()
    differing = {k: [fa.get(k), fb.get(k)] for k in CONTROLLED_VARIABLES if fa.get(k) != fb.get(k)}
    turns_a = {t.turn_index: (t.speaker_id, t.text) for t in a.record.dialogue}
    turns_b = {t.turn_index: (t.speaker_id, t.text) for t in b.record.dialogue}
    differing_turns = sorted(i for i in set(turns_a) | set(turns_b) if turns_a.get(i) != turns_b.get(i))
    claimed = claimed_manipulations(a, b, pair_id)
    allowed = set().union(*(MANIPULATION_SCOPE.get(c, set()) for c in claimed)) if claimed else set()
    gold_missing = a.label.gold_referent_id is None or b.label.gold_referent_id is None
    unclaimed = sorted(k for k in differing if k not in allowed and not (gold_missing and k in GOLD_DEPENDENT))
    cands_a = sorted(p.entity_id for p in a.record.participants)
    cands_b = sorted(p.entity_id for p in b.record.participants)
    observed_change = (a.label.gold_referent_id != b.label.gold_referent_id) if (a.label.gold_referent_id and b.label.gold_referent_id) else None
    expected = expected_change(a, b, pair_id)
    same_target = a.record.target().text == b.record.target().text
    same_cands = cands_a == cands_b
    # 구조 조건: 후보 집합 유지, 목표 발화 유지(linguistic_cue 조작은 목표 발화가 바뀌는 것이 조작 자체다)
    structural_ok = same_cands and (same_target or "linguistic_cue" in claimed)
    return {
        "pair_id": pair_id or next(iter(set(a.record.pair_ids) & set(b.record.pair_ids)), None),
        "scenario_id": a.record.scenario_id,
        "a": a.sample_id, "b": b.sample_id,
        "variants": [a.record.variant, b.record.variant],
        "claimed_manipulations": claimed,
        "differing_variables": differing,
        "differing_turns": differing_turns,
        "same_target_utterance": same_target,
        "same_candidate_set": same_cands,
        "structural_conditions_met": structural_ok,
        "expected_gold_change": expected,
        "observed_gold_change": observed_change,
        "gold_change_matches_expectation": (expected is None or observed_change is None or expected == observed_change),
        "unclaimed_differences": unclaimed,
        "evaluable": not gold_missing,
        "is_single_variable_pair": not unclaimed and len(claimed) == 1 and structural_ok,
        "check_level": "automatic_structural_only",  # 사람 검수(pair_valid)가 끝나야 minimal pair로 보고한다
    }


def pair_manifest(samples: Iterable[Sample]) -> dict:
    groups: dict[str, list[Sample]] = {}
    for s in samples:
        for pid in s.record.pair_ids:
            groups.setdefault(pid, []).append(s)
    pairs, problems = [], []
    for pair_id, members in sorted(groups.items()):
        if len(members) != 2:
            problems.append(f"pair {pair_id} has {len(members)} members")
            continue
        a, b = sorted(members, key=lambda s: s.sample_id)
        if a.record.scenario_id != b.record.scenario_id:
            problems.append(f"pair {pair_id} spans scenarios")
        try:
            d = pair_diff(a, b, pair_id)
        except ValueError as e:
            problems.append(str(e))
            continue
        if not d["gold_change_matches_expectation"]:
            problems.append(f"pair {pair_id}: expected_gold_change={d['expected_gold_change']} but observed {d['observed_gold_change']}")
        pairs.append(d)
    return {
        "check_level": "automatic_structural_only",
        "n_pairs": len(pairs),
        "n_single_variable": sum(p["is_single_variable_pair"] for p in pairs),
        "n_compound": sum(not p["is_single_variable_pair"] for p in pairs),
        "problems": problems,
        "pairs": pairs,
    }
