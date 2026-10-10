"""Sample → 평가 입력(item)과 정답 파일(gold) 분리.

- item에는 정답·역할·anchor·distractor·청자·작성 근거가 들어가지 않는다. validate.check_payload가 실제 파일로 다시 확인한다.
- 후보 ID는 모델에 중립 ID(E1, E2, ...)로 노출한다. 원래 P/T 접두사는 참여 여부를 알려 주는 메타 단서라 쓰지 않는다.
  매핑은 family 단위로 seed에 고정되어 같은 family의 변형은 같은 순서·같은 ID를 쓴다. gold 파일이 id_map을 보관한다.
- 기본으로 annotation_status == accepted인 sample만 포함한다. include_unreviewed는 pilot 점검용이다.
"""

from __future__ import annotations

import random
from typing import Iterable

from .schema import Sample, infer_addressee, render_dialogue, role_of

CONDITIONS = ("full_mcq", "target_only_mcq", "full_qa")


def neutral_id_map(sample: Sample, seed: int) -> dict[str, str]:
    """원래 entity_id → 중립 ID. family 안에서는 고정, family 사이에서는 seed로 섞는다."""
    ids = sorted(p.entity_id for p in sample.record.participants)
    key = sample.record.family_id or sample.record.scenario_id or sample.sample_id
    rng = random.Random(f"{seed}:{key}")
    rng.shuffle(ids)
    return {orig: f"E{i}" for i, orig in enumerate(ids, start=1)}


def to_item(sample: Sample, seed: int = 0) -> dict:
    rec = sample.record
    target = rec.target()
    name = rec.participant(rec.speaker_id).name
    local_text = f"{name}: {target.text}"
    b, e = rec.target_predicate_span
    offset = len(name) + 2
    id_map = neutral_id_map(sample, seed)
    by_orig = {p.entity_id: p for p in rec.participants}
    order = sorted(id_map, key=lambda o: int(id_map[o][1:]))
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
        "target_speaker_id": id_map[rec.speaker_id],
        "speaker_sequence": [id_map[t.speaker_id] for t in rec.dialogue[: rec.target_turn]],
        "dialogue_participants": [id_map[p] for p in rec.in_dialogue_ids()],
        "candidates": [{"entity_id": id_map[o], "label": by_orig[o].name, "aliases": by_orig[o].surface_forms()} for o in order],
    }


def to_gold(sample: Sample, seed: int = 0) -> dict:
    rec, lab, der = sample.record, sample.label, sample.derived
    id_map = neutral_id_map(sample, seed)
    m = lambda x: id_map.get(x) if x else None  # noqa: E731
    addressee = infer_addressee(rec, rec.speaker_id, lab.addressee_id)
    entity_roles = {id_map[p.entity_id]: role_of(p.entity_id, rec.speaker_id, addressee, rec) for p in rec.participants}
    return {
        "item_id": sample.sample_id,
        "gold_entity_id": m(lab.gold_referent_id),
        "gold_role": der.gold_referent_role,
        "entity_roles": entity_roles,
        "addressee_id": m(addressee),
        "designated_distractor_id": m(lab.distractor_id),
        "speaker_changed": der.speaker_changed,
        "referent_changed": der.referent_changed,
        "referent_role_changed": der.referent_role_changed,
        "turn_distance": der.turn_distance,
        "distractor_present": der.distractor_present,
        "most_recent_mentioned_id": m(der.most_recent_mentioned_id),
        "dataset": rec.dataset,
        "creation_method": rec.creation_method,
        "annotation_status": lab.annotation_status,
        "ambiguity_status": lab.ambiguity_status,
        "context_need": lab.validation_metadata.get("context_need"),
        "linguistic_cues": lab.linguistic_cues,
        "manipulated_variables": lab.manipulated_variables,
        "id_map": {v: k for k, v in id_map.items()},  # 중립 ID → 원래 ID (분석용)
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
        gold.append(to_gold(s, seed))
    return items, gold, skipped
