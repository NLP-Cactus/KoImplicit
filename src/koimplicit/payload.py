"""Sample → 평가 입력(item)과 정답 파일(gold) 분리.

- item에는 정답·역할·anchor·distractor·작성 근거가 들어가지 않는다. runner.GOLD_KEYS와 validate의
  누수 검사가 이를 다시 확인한다.
- 후보 순서는 seed와 pair_id(없으면 family_id, 없으면 sample_id)로 정해 pair 안에서는 같고
  pair 사이에서는 달라진다.
- 기본으로 annotation_status == accepted인 sample만 포함한다. --include-unreviewed는 pilot 점검용이다.
"""

from __future__ import annotations

import random
from typing import Iterable

from .schema import Sample, infer_addressee, render_dialogue, role_of

CONDITIONS = ("full_mcq", "target_only_mcq", "full_qa")


def candidate_order(sample: Sample, seed: int) -> list[str]:
    ids = [p.entity_id for p in sample.record.participants]
    key = sample.record.family_id or sample.sample_id  # family 안에서는 후보 순서를 고정한다
    rng = random.Random(f"{seed}:{key}")
    rng.shuffle(ids)
    return ids


def to_item(sample: Sample, seed: int = 0) -> dict:
    rec = sample.record
    target = rec.target()
    name = rec.participant(rec.speaker_id).name
    local_text = f"{name}: {target.text}"
    b, e = rec.target_predicate_span
    offset = len(name) + 2
    order = candidate_order(sample, seed)
    by_id = {p.entity_id: p for p in rec.participants}
    return {
        "item_id": sample.sample_id,
        "dataset": rec.dataset,
        "conversation_id": rec.scenario_id,  # cluster 단위
        "family_id": rec.family_id or rec.scenario_id,
        "pair_id": rec.pair_id,
        "pair_ids": list(rec.pair_ids),
        "version": rec.variant,
        "full_text": render_dialogue(rec),
        "local_text": local_text,
        "target_turn": rec.target_turn,
        "target_marker": {"form": rec.target_predicate, "begin": b + offset, "end": e + offset},
        "target_speaker_label": name,
        "target_speaker_id": rec.speaker_id,
        "speaker_sequence": [t.speaker_id for t in rec.dialogue[: rec.target_turn]],
        "dialogue_participants": rec.in_dialogue_ids(),
        "candidates": [{"entity_id": cid, "label": by_id[cid].name, "aliases": by_id[cid].surface_forms()} for cid in order],
    }


def to_gold(sample: Sample) -> dict:
    rec, lab, der = sample.record, sample.label, sample.derived
    addressee = infer_addressee(rec, rec.speaker_id, lab.addressee_id)
    entity_roles = {p.entity_id: role_of(p.entity_id, rec.speaker_id, addressee, rec) for p in rec.participants}
    return {
        "item_id": sample.sample_id,
        "gold_entity_id": lab.gold_referent_id,
        "gold_role": der.gold_referent_role,
        "entity_roles": entity_roles,
        "addressee_id": addressee,
        "designated_distractor_id": lab.distractor_id,
        "speaker_changed": der.speaker_changed,
        "referent_changed": der.referent_changed,
        "referent_role_changed": der.referent_role_changed,
        "turn_distance": der.turn_distance,
        "distractor_present": der.distractor_present,
        "most_recent_mentioned_id": der.most_recent_mentioned_id,
        "dataset": rec.dataset,
        "annotation_status": lab.annotation_status,
        "ambiguity_status": lab.ambiguity_status,
        "linguistic_cues": lab.linguistic_cues,
        "manipulated_variables": lab.manipulated_variables,
    }


def build_payload(samples: Iterable[Sample], seed: int = 0, include_unreviewed: bool = False) -> tuple[list[dict], list[dict], list[str]]:
    """(items, gold_rows, skipped). gold가 없는 sample은 항상 제외한다."""
    items, gold, skipped = [], [], []
    for s in samples:
        if s.label.gold_referent_id is None:
            skipped.append(f"{s.sample_id}: no gold (ambiguity={s.label.ambiguity_status})")
            continue
        if s.label.annotation_status != "accepted" and not include_unreviewed:
            skipped.append(f"{s.sample_id}: annotation_status={s.label.annotation_status}")
            continue
        items.append(to_item(s, seed))
        gold.append(to_gold(s))
    return items, gold, skipped
