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
    "distractor": {"distractor_present", "distractor_id", "distractor_last_mention_turn", "most_recent_mentioned_id",
                   "turn_distance", "gold_last_mention_turn"},
    "context_distance": {"turn_distance", "gold_last_mention_turn", "n_turns", "anchor_turn", "anchor_referent_id",
                         "speaker_changed", "most_recent_mentioned_id", "distractor_last_mention_turn"},
    "speaker_role": {"speaker_id", "addressee_id", "gold_referent_role", "speaker_changed", "referent_role_changed",
                     "anchor_turn", "anchor_referent_id", "gold_referent_id", "referent_changed", "turn_distance",
                     "gold_last_mention_turn", "most_recent_mentioned_id", "distractor_present"},
    "linguistic_cue": {"linguistic_cues", "target_predicate"},
}


GOLD_DEPENDENT = {"gold_referent_id", "gold_referent_role", "referent_changed", "referent_role_changed", "turn_distance",
                  "gold_last_mention_turn", "distractor_present", "most_recent_mentioned_id", "addressee_id"}


def claimed_manipulations(a: Sample, b: Sample, pair_id: Optional[str]) -> list[str]:
    """pair_id '{scenario}:{base}~{variant}'의 variant 쪽 표본이 주장한 조작. 방향을 알 수 없으면 두 표본의 합집합."""
    for s in (a, b):
        if pair_id and pair_id in s.label.pair_claims:
            return sorted(s.label.pair_claims[pair_id])
    if pair_id and ":" in pair_id and "~" in pair_id:
        _, names = pair_id.split(":", 1)
        _, variant_name = names.split("~", 1)
        for s in (a, b):
            if s.record.variant == variant_name:
                return sorted(s.label.manipulated_variables)
    return sorted(set(a.label.manipulated_variables) | set(b.label.manipulated_variables))


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
    expected = b.label.expected_gold_change if b.label.expected_gold_change is not None else a.label.expected_gold_change
    return {
        "pair_id": pair_id or next(iter(set(a.record.pair_ids) & set(b.record.pair_ids)), None),
        "scenario_id": a.record.scenario_id,
        "a": a.sample_id, "b": b.sample_id,
        "variants": [a.record.variant, b.record.variant],
        "claimed_manipulations": claimed,
        "differing_variables": differing,
        "differing_turns": differing_turns,
        "same_target_utterance": a.record.target().text == b.record.target().text,
        "same_candidate_set": cands_a == cands_b,
        "expected_gold_change": expected,
        "observed_gold_change": observed_change,
        "gold_change_matches_expectation": (expected is None or observed_change is None or expected == observed_change),
        "unclaimed_differences": unclaimed,
        "evaluable": not gold_missing,
        "is_single_variable_pair": not unclaimed and len(claimed) == 1,
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
        d = pair_diff(a, b, pair_id)
        if not d["gold_change_matches_expectation"]:
            problems.append(f"pair {pair_id}: expected_gold_change={d['expected_gold_change']} but observed {d['observed_gold_change']}")
        pairs.append(d)
    return {
        "n_pairs": len(pairs),
        "n_single_variable": sum(p["is_single_variable_pair"] for p in pairs),
        "n_compound": sum(not p["is_single_variable_pair"] for p in pairs),
        "problems": problems,
        "pairs": pairs,
    }
