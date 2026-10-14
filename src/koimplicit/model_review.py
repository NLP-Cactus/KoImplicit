"""모델 검수자(사람 검수를 대신하는 대체 절차).

사람 검수자를 구할 수 없을 때, 서로 다른 계열의 모델 2개가 사람과 같은 시트(Local → Full)를 독립적으로 채운다.
- 입력은 `annotate sheets`가 만든 CSV 그대로(정답·작성 의도 없음). 출력도 같은 CSV 형식이라 agreement/adjudicate에 바로 들어간다.
- 모델에게 주는 것: 대화(Local은 목표 발화만), 후보 목록, 판정 항목 설명. 작성자 라벨은 주지 않는다.
- 기록: 검수자 이름을 `model:<model_id>`로 두고, 원문 응답을 sheet 옆 `<sheet>.responses.jsonl`에 남긴다.
- 한계: 모델 검수는 사람 검수가 아니다. 채택된 표본의 validation_metadata와 데이터셋 README에 그 사실을 적어야 하고,
  검수 모델과 평가 모델이 겹치면 순환이 생기므로 평가 보고 때 함께 명시한다.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Optional

from .annotation import JUDGEMENT_FIELDS, SHEET_FIELDS
from .runner import call_with_retry

LOCAL_PROMPT = """다음은 한국어 대화의 한 발화와 후보 인물 목록입니다. 앞 문맥은 주어지지 않습니다.
[[ ]] 안의 서술어의 생략된 주어가 누구인지, 이 한 줄과 후보만으로 확정할 수 있는지 판정하세요.
앞 문맥 없이는 확정할 수 없는 것이 정상이며, 후보 중에서 추측하지 마세요. 어미·호격·어휘 같은 이 발화 안의 근거를 짚어 설명할 수 있을 때만 "unambiguous"를 고르세요.

[발화]
{dialogue}

[후보] (ID=이름)
{candidates}

JSON 한 줄로만 답하세요:
{{"ambiguity": "unambiguous|ambiguous|uncertain", "referent_id": "<확정일 때만 후보 ID, 아니면 빈 문자열>", "context_sufficient": "yes|no", "notes": "<근거 한 문장>"}}"""

FULL_PROMPT = """다음은 한국어 대화입니다. 각 줄은 "이름: 발화" 형식이고 마지막 줄이 판정 대상 발화입니다. 대상 발화 뒤의 대화는 없습니다.
마지막 발화에서 [[ ]] 안의 서술어의 생략된 주어가 후보 중 누구인지 판정하세요.
- 근거 표현을 짚어 설명할 수 있을 때만 "unambiguous"로 확정하고, 둘 이상이 가능하면 "ambiguous", 판단이 불안정하면 "uncertain"으로 두고 referent_id는 비웁니다.
- context_sufficient: 이 대화만으로 판정하기에 정보가 충분한가.
- naturalness_1to5: 대화가 자연스러운 한국어인가(1 부자연 ~ 5 자연).
{addressee_block}
[대화]
{dialogue}

[후보] (ID=이름)
{candidates}

JSON 한 줄로만 답하세요:
{{"referent_id": "<후보 ID 또는 빈 문자열>", "ambiguity": "unambiguous|ambiguous|uncertain", "context_sufficient": "yes|no", "naturalness_1to5": "1|2|3|4|5"{addressee_key}, "notes": "<근거 한 문장>"}}"""

ADDRESSEE_BLOCK = """- addressee_id: 이 대화는 참여자가 세 명입니다. 마지막 발화가 누구에게 하는 말인지 호격, 또는 직전 발화와 내용으로만 확정하고, 확정할 수 없으면 빈 문자열로 둡니다.
"""


def build_prompt(row: dict, condition: str) -> str:
    three = row.get("candidates", "").count("=") >= 3 and _n_dialogue_participants(row) == 3
    if condition == "local":
        return LOCAL_PROMPT.format(dialogue=row["dialogue"], candidates=_format_candidates(row["candidates"]))
    return FULL_PROMPT.format(dialogue=row["dialogue"], candidates=_format_candidates(row["candidates"]),
                              addressee_block=ADDRESSEE_BLOCK if three else "",
                              addressee_key=', "addressee_id": "<참여자 ID 또는 빈 문자열>"' if three else "")


def _format_candidates(cands: str) -> str:
    return "\n".join(c.strip() for c in cands.split(";") if c.strip())


def _n_dialogue_participants(row: dict) -> int:
    speakers = {line.split(":", 1)[0].strip() for line in row["dialogue"].split("\n") if ":" in line}
    names = {c.split("=", 1)[1].strip() for c in row["candidates"].split(";") if "=" in c}
    return len(speakers & names) if speakers & names else len(speakers)


def parse_judgement(raw: Optional[str], candidate_ids: set[str], condition: str) -> dict:
    out = {f: "" for f in JUDGEMENT_FIELDS}
    if not raw:
        out["notes"] = "(no response)"
        return out
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    try:
        payload = json.loads(text[start:end + 1]) if start != -1 and end > start else {}
    except json.JSONDecodeError:
        payload = {}
    if not payload:
        out["notes"] = "(unparsable) " + raw[:120].replace("\n", " ")
        return out
    amb = str(payload.get("ambiguity", "")).strip().lower()
    out["ambiguity"] = amb if amb in ("unambiguous", "ambiguous", "uncertain") else ""
    ref = str(payload.get("referent_id", "") or "").strip()
    out["referent_id"] = ref if (ref in candidate_ids and out["ambiguity"] == "unambiguous") else ""
    cs = str(payload.get("context_sufficient", "")).strip().lower()
    out["context_sufficient"] = cs if cs in ("yes", "no") else ""
    if condition == "full":
        nat = str(payload.get("naturalness_1to5", "")).strip()
        out["naturalness_1to5"] = nat if nat in ("1", "2", "3", "4", "5") else ""
        adr = str(payload.get("addressee_id", "") or "").strip()
        out["addressee_id"] = adr if adr in candidate_ids else ""
    out["notes"] = str(payload.get("notes", "") or "")[:300]
    return out


def fill_sheet(sheet_path: Path, out_path: Path, adapter, model_config: dict, condition: str, sleep=None, only_empty: bool = False) -> dict:
    """빈 시트를 모델 판정으로 채워 out_path에 쓴다. 원문 응답은 out_path.responses.jsonl에 남긴다.
    only_empty=True면 ambiguity가 비어 있는 행(실패·파싱 불가)만 다시 묻고 나머지는 유지한다."""
    rows = []
    with Path(sheet_path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or SHEET_FIELDS
        rows = list(reader)
    log_path = Path(str(out_path) + ".responses.jsonl")
    summary = {"n": len(rows), "ok": 0, "failed": 0, "unparsable": 0, "resumed": 0}
    kwargs = {"sleep": sleep} if sleep else {}
    # 이어하기: 이전 실행 로그에 판정이 남아 있으면 시트에 복구한다(행 단위로 기록되므로 중단된 실행도 재활용 가능)
    if only_empty and log_path.exists():
        done = {}
        for line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            j = entry.get("judged") or {}
            if entry.get("condition") == condition and j.get("ambiguity") and not str(j.get("notes", "")).startswith("(unparsable)"):
                done[entry.get("review_id")] = j
        for row in rows:
            if not (row.get("ambiguity") or "").strip() and row.get("review_id") in done:
                row.update(done[row["review_id"]])
                summary["resumed"] += 1
    with log_path.open("a" if only_empty else "w", encoding="utf-8") as log:
        for row in rows:
            if only_empty and (row.get("ambiguity") or "").strip():
                summary["ok"] += 1
                continue
            cand_ids = {c.split("=", 1)[0].strip() for c in row["candidates"].split(";") if "=" in c}
            request = {"task": "review", "item_id": row.get("review_id"), "condition": condition, "candidate_ids": sorted(cand_ids),
                       "model_id": model_config.get("model_id", "unset"), "system": model_config.get("system", ""),
                       "user": build_prompt(row, condition), "decoding": model_config.get("decoding", {}), "seed": None}
            response, retries, error = call_with_retry(adapter, request, **kwargs)
            raw = response.get("raw_text") if response else None
            judged = parse_judgement(raw, cand_ids, condition)
            if response is None:
                summary["failed"] += 1
            elif judged["notes"].startswith("(unparsable)"):
                summary["unparsable"] += 1
            else:
                summary["ok"] += 1
            row.update(judged)
            log.write(json.dumps({"review_id": row.get("review_id"), "condition": condition, "model": (response or {}).get("model") or model_config.get("model_id"),
                                  "raw_text": raw, "retries": retries, "error": error, "judged": judged}, ensure_ascii=False) + "\n")
            log.flush()  # 중단돼도 행 단위로 남긴다
            # 시트도 행마다 갱신해 중단 시점까지의 판정을 보존한다
            with Path(out_path).open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
    with Path(out_path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return summary
