"""기준선(설계안 11.2). 각 함수는 항목 하나에 대해 predicted_entity_id와 상태를 돌려준다.

- majority_role_prior: 개발 자료의 gold role 분포에서 최빈 role을 고르고 entity로 매핑한다.
- most_recent_explicit_np: prefix 텍스트에서 마지막으로 나타난 roster 표현을 고른다.
- most_recent_entity_oracle: 인간 mention 주석(위치, entity)에서 마지막 entity를 고른다. gold 도움을 받는 진단용이다.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from .metrics import role_of

THIRD_PARTY_RULE = "most_recent_third_party_mention"


def fit_majority_role(dev_rows: Iterable[dict]) -> dict:
    """개발 자료 gold role 분포를 고정한다. 반환값을 held-out에 그대로 쓴다."""
    counts = Counter(role_of(r, r.get("gold_entity_id")) for r in dev_rows)
    counts.pop(None, None)
    if not counts:
        raise ValueError("no gold roles in development rows")
    role, _ = max(sorted(counts.items()), key=lambda kv: kv[1])
    return {"majority_role": role, "distribution": dict(counts), "third_party_rule": THIRD_PARTY_RULE}


def _participant_for_role(item: dict, role: str) -> str | None:
    for c in item.get("candidates") or []:
        if c.get("role") == role:
            return c["entity_id"]
    return None


def _mentions_in_text(text: str, roster: Iterable[dict]) -> list[tuple[int, str]]:
    """(위치, entity_id) 목록. roster의 label과 aliases가 텍스트에 나타난 모든 자리."""
    found = []
    for entry in roster:
        names = [entry.get("label")] + list(entry.get("aliases") or [])
        for name in names:
            if not name:
                continue
            start = 0
            while True:
                pos = text.find(name, start)
                if pos == -1:
                    break
                found.append((pos, entry["entity_id"]))
                start = pos + len(name)
    return sorted(found)


def majority_role_prior(item: dict, fitted: dict) -> dict:
    """후보 항목에 role이 있어야 한다(목표 발화 기준 speaker/addressee/third_party)."""
    role = fitted["majority_role"]
    if role in ("speaker", "addressee"):
        entity = _participant_for_role(item, role)
        return {"predicted_entity_id": entity, "parse_status": "ok" if entity else "unmapped", "rule": role}
    third = [c for c in item.get("candidates") or [] if c.get("role") == "third_party"]
    if not third:
        return {"predicted_entity_id": None, "parse_status": "unmapped", "rule": THIRD_PARTY_RULE}
    mentions = [m for m in _mentions_in_text(item.get("full_text", ""), third)]
    if mentions:
        return {"predicted_entity_id": mentions[-1][1], "parse_status": "ok", "rule": THIRD_PARTY_RULE}
    return {"predicted_entity_id": third[0]["entity_id"], "parse_status": "ok", "rule": "first_third_party"}


def most_recent_explicit_np(item: dict) -> dict:
    """prefix에서 마지막으로 관측된 명시 지칭을 고른다. 참여자 라벨(A:, B:)은 지칭이 아니므로 제외한다."""
    roster = [c for c in item.get("candidates") or [] if c.get("aliases")]
    mentions = _mentions_in_text(item.get("full_text", ""), roster)
    if not mentions:
        return {"predicted_entity_id": None, "parse_status": "unmapped", "rule": "no explicit mention"}
    return {"predicted_entity_id": mentions[-1][1], "parse_status": "ok", "rule": "most_recent_explicit_np"}


def most_recent_entity_oracle(item: dict) -> dict:
    """item['mentions'] = [{position, entity_id}] (인간 주석). 목표 predicate 이전 마지막 entity."""
    mentions = sorted((m["position"], m["entity_id"]) for m in item.get("mentions") or [])
    limit = item.get("target_position")
    if limit is not None:
        mentions = [m for m in mentions if m[0] < limit]
    if not mentions:
        return {"predicted_entity_id": None, "parse_status": "unmapped", "rule": "no prior mention"}
    return {"predicted_entity_id": mentions[-1][1], "parse_status": "ok", "rule": "most_recent_entity_oracle"}


def apply_baseline(items: Iterable[dict], baseline, **kwargs) -> list[dict]:
    """baseline(item, **kwargs)를 적용해 normalize 결과와 같은 모양의 행을 만든다."""
    rows = []
    for item in items:
        result = baseline(item, **kwargs)
        rows.append({
            "item_id": item["item_id"],
            "condition": "baseline",
            "model_label": baseline.__name__,
            "conversation_id": item.get("conversation_id"),
            "gold_entity_id": item.get("gold_entity_id"),
            "entity_roles": {c["entity_id"]: c.get("role") for c in item.get("candidates") or []},
            "candidates": item.get("candidates"),
            **result,
        })
    return rows


def mapping_failure_rate(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    failed = sum(1 for r in rows if r.get("parse_status") != "ok")
    return {"failed": failed, "total": len(rows), "rate": failed / len(rows) if rows else None}


# --------------------------------------------------------------------------- 독립 창작 데이터셋용 기준선

def _strip_speaker_labels(full_text: str, candidates: Iterable[dict]) -> list[str]:
    """'이름: 발화' 줄에서 발화자 라벨을 뗀다. 라벨은 언급이 아니다."""
    labels = sorted({c.get("label") for c in candidates if c.get("label")}, key=len, reverse=True)
    lines = []
    for line in full_text.split("\n"):
        for label in labels:
            if line.startswith(label + ": "):
                line = line[len(label) + 2:]
                break
        lines.append(line)
    return lines


def most_recent_entity(item: dict) -> dict:
    """목표 서술어 앞까지의 텍스트(발화자 라벨 제외)에서 마지막으로 언급된 후보를 고른다."""
    candidates = item.get("candidates") or []
    lines = _strip_speaker_labels(item.get("full_text", ""), candidates)
    marker = item.get("target_marker") or {}
    label = item.get("target_speaker_label") or ""
    if lines and isinstance(marker, dict) and marker.get("begin") is not None:
        cut = marker["begin"] - (len(label) + 2)
        lines[-1] = lines[-1][:max(cut, 0)]
    text = "\n".join(lines)
    mentions = _mentions_in_text(text, candidates)
    if not mentions:
        return {"predicted_entity_id": None, "parse_status": "unmapped", "rule": "no explicit mention"}
    return {"predicted_entity_id": mentions[-1][1], "parse_status": "ok", "rule": "most_recent_entity"}


def current_speaker(item: dict) -> dict:
    speaker = item.get("target_speaker_id")
    if speaker is None:
        for c in item.get("candidates") or []:
            if c.get("label") == item.get("target_speaker_label"):
                speaker = c["entity_id"]
    if speaker is None:
        return {"predicted_entity_id": None, "parse_status": "unmapped", "rule": "current_speaker"}
    return {"predicted_entity_id": speaker, "parse_status": "ok", "rule": "current_speaker"}


def current_addressee(item: dict) -> dict:
    """2인 대화면 상대 참여자, 3인 대화면 목표 발화 직전에 말한 다른 참여자(인접쌍 휴리스틱)."""
    speaker = item.get("target_speaker_id")
    participants = [p for p in item.get("dialogue_participants") or [] if p != speaker]
    if len(participants) == 1:
        return {"predicted_entity_id": participants[0], "parse_status": "ok", "rule": "other_participant"}
    for prior in reversed((item.get("speaker_sequence") or [])[:-1]):
        if prior != speaker:
            return {"predicted_entity_id": prior, "parse_status": "ok", "rule": "previous_speaker"}
    return {"predicted_entity_id": None, "parse_status": "unmapped", "rule": "current_addressee"}
