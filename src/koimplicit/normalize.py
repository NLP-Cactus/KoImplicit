"""모델 출력 정규화. MCQ 응답에서 entity ID를 읽고 QA 응답을 entity ID로 매핑한다.

parse_status:
  ok        후보 집합 안의 entity ID 하나로 정해짐
  invalid   후보 밖 ID, 복수 ID, 빈 응답, JSON 오류
  abstain   모델이 명시적으로 답을 거부함 (오답으로 세되 invalid와 따로 집계)
  missing   응답 자체가 없음 (전송 실패). runner가 부여한다
  unmapped  QA 응답을 entity로 매핑하지 못함
"""

from __future__ import annotations

import json
import re
from typing import Iterable

# QA 매핑에서 목표 발화 기준으로 화자·청자를 가리키는 표현. 실제 응답을 보고 보강한다.
SPEAKER_PRONOUNS = ("화자", "말하는 사람", "발화자", "나", "내가", "저", "제가", "본인")
ADDRESSEE_PRONOUNS = ("청자", "듣는 사람", "상대방", "상대", "너", "네가", "당신", "그쪽")
# 구조화 출력에서 거부를 뜻하는 값. 프롬프트의 output_schema와 함께 고정한다.
ABSTAIN_VALUES = ("abstain", "unknown", "none", "null", "")
# 자유 서술에서 거부로 볼 표현. 프롬프트 승인 뒤 개발 자료로 보정한다.
ABSTAIN_PATTERNS = ("알 수 없", "판단할 수 없", "확인할 수 없", "모르겠", "특정할 수 없", "cannot determine", "not enough")


def _candidate_ids(candidates: Iterable) -> list[str]:
    ids = []
    for c in candidates:
        ids.append(c["entity_id"] if isinstance(c, dict) else str(c))
    return ids


def _find_ids(text: str, ids: list[str]) -> list[str]:
    """텍스트에 정확히(단어 경계) 나타난 후보 ID 목록. 긴 ID가 짧은 ID를 포함할 때 중복을 막는다."""
    found = []
    for cid in sorted(ids, key=len, reverse=True):
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(cid) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, text):
            found.append(cid)
            text = re.sub(pattern, " ", text)
    return found


def _extract_json(text: str):
    """응답 안의 첫 JSON 객체를 꺼낸다. 코드 펜스를 허용한다."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no json object")
    return json.loads(text[start:end + 1])


def parse_mcq(raw_text: str | None, candidates: Iterable, structured: bool = False, answer_field: str = "entity_id") -> dict:
    """MCQ 응답 하나를 {predicted_entity_id, parse_status, note}로 바꾼다."""
    ids = _candidate_ids(candidates)
    if raw_text is None:
        return {"predicted_entity_id": None, "parse_status": "missing", "note": "no response"}
    text = raw_text.strip()
    if not text:
        return {"predicted_entity_id": None, "parse_status": "invalid", "note": "empty"}
    if structured:
        try:
            payload = _extract_json(text)
        except (ValueError, json.JSONDecodeError):
            return {"predicted_entity_id": None, "parse_status": "invalid", "note": "json error"}
        value = payload.get(answer_field)
        if value is None or (isinstance(value, str) and value.strip().lower() in ABSTAIN_VALUES):
            return {"predicted_entity_id": None, "parse_status": "abstain", "note": "abstain value"}
        if isinstance(value, list):
            return {"predicted_entity_id": None, "parse_status": "invalid", "note": "multiple ids"}
        value = str(value).strip()
        if value in ids:
            return {"predicted_entity_id": value, "parse_status": "ok", "note": ""}
        return {"predicted_entity_id": None, "parse_status": "invalid", "note": "id not in candidates"}
    found = _find_ids(text, ids)
    if len(found) == 1:
        return {"predicted_entity_id": found[0], "parse_status": "ok", "note": ""}
    if len(found) > 1:
        return {"predicted_entity_id": None, "parse_status": "invalid", "note": "multiple ids"}
    if any(p in text for p in ABSTAIN_PATTERNS):
        return {"predicted_entity_id": None, "parse_status": "abstain", "note": "abstain pattern"}
    return {"predicted_entity_id": None, "parse_status": "invalid", "note": "no candidate id"}


def build_alias_map(roster: Iterable[dict], target_speaker_label: str, participant_labels: tuple[str, str] = ("A", "B")) -> dict[str, str]:
    """QA 매핑 표. alias 문자열 -> entity_id.

    roster 항목: {entity_id, label, aliases?: [..], role?: speaker|addressee|third_party}
    화자·청자 대명사는 목표 발화의 화자 라벨과 다른 참여자 라벨로 연결한다.
    """
    alias_map: dict[str, str] = {}
    by_label = {}
    for entry in roster:
        entity_id = entry["entity_id"]
        by_label[entry.get("label")] = entity_id
        alias_map[entity_id] = entity_id
        if entry.get("label"):
            alias_map[entry["label"]] = entity_id
        for alias in entry.get("aliases") or []:
            alias_map[alias] = entity_id
    speaker_entity = by_label.get(target_speaker_label)
    other_label = participant_labels[1] if target_speaker_label == participant_labels[0] else participant_labels[0]
    addressee_entity = by_label.get(other_label)
    if speaker_entity:
        for p in SPEAKER_PRONOUNS:
            alias_map.setdefault(p, speaker_entity)
    if addressee_entity:
        for p in ADDRESSEE_PRONOUNS:
            alias_map.setdefault(p, addressee_entity)
    return alias_map


def map_qa_answer(raw_text: str | None, roster: Iterable[dict], target_speaker_label: str) -> dict:
    """QA 응답을 entity ID로 매핑한다. 인물 하나로 정해지지 않으면 unmapped."""
    if raw_text is None:
        return {"predicted_entity_id": None, "parse_status": "missing", "matched": [], "note": "no response"}
    text = raw_text.strip()
    if not text:
        return {"predicted_entity_id": None, "parse_status": "invalid", "matched": [], "note": "empty"}
    alias_map = build_alias_map(list(roster), target_speaker_label)
    matched: dict[str, list[str]] = {}
    remaining = text
    for alias in sorted(alias_map, key=len, reverse=True):
        if not alias:
            continue
        if alias in remaining:
            matched.setdefault(alias_map[alias], []).append(alias)
            remaining = remaining.replace(alias, " ")
    if len(matched) == 1:
        entity_id = next(iter(matched))
        return {"predicted_entity_id": entity_id, "parse_status": "ok", "matched": matched[entity_id], "note": ""}
    if any(p in text for p in ABSTAIN_PATTERNS) and not matched:
        return {"predicted_entity_id": None, "parse_status": "abstain", "matched": [], "note": "abstain pattern"}
    note = "no alias matched" if not matched else "multiple entities"
    return {"predicted_entity_id": None, "parse_status": "unmapped", "matched": sorted(a for v in matched.values() for a in v), "note": note}


def review_queue(rows: Iterable[dict]) -> list[dict]:
    """unmapped 행을 인간 검토용으로 추린다. 모델 이름과 gold를 가린다."""
    queue = []
    for r in rows:
        if r.get("parse_status") != "unmapped":
            continue
        queue.append({
            "review_id": f"{r['item_id']}:{r['condition']}:{r.get('payload_hash', '')[:8]}",
            "raw_text": r.get("raw_text"),
            "roster": r.get("roster"),
            "target_speaker_label": r.get("target_speaker_label"),
            "reviewer_entity_id": None,
            "reviewer_id": None,
        })
    return queue
