"""모델 실행기. 요청 생성, payload 해시 캐시, 재시도, 실행 기록을 담당한다.

규칙(설계안 11.1, 11.5):
- 항목마다 독립 요청. history를 쌓지 않는다.
- 요청 생성 함수는 gold를 받지 않는다. gold 키가 있으면 ValueError.
- 네트워크·서버 오류(TransientError)만 같은 payload로 최대 2회 재시도.
- 재시도 뒤에도 실패하면 status=missing으로 기록하고 넘어간다.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Iterable, Protocol

GOLD_KEYS = ("gold_entity_id", "gold_role", "gold_referent_id", "gold_referent_role", "designated_distractor_id",
             "distractor_id", "anchor_referent_id", "author_rationale", "restored_form", "gold")
PROMPT_SLOTS = ("dialogue", "target_utterance", "target_marker", "target_speaker_label", "candidates", "output_schema")
LOCAL_CONDITION_MARKERS = ("local", "target_only")
MAX_RETRIES = 2


class TransientError(Exception):
    """timeout, 연결 실패, 5xx 등 같은 payload로 재시도할 수 있는 오류. retry_after(초)를 붙일 수 있다."""

    def __init__(self, message: str = "", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class PermanentError(Exception):
    """인증 실패, 4xx, 형식 거부 등 재시도하지 않는 오류."""


class PromptNotApproved(Exception):
    """template이 비어 있는 prompt 파일. 승인 전에는 실행할 수 없다."""


class ProviderAdapter(Protocol):
    def complete(self, request: dict) -> dict:
        """request: {model_id, system, user, decoding, output_schema, seed}
        반환: {raw_text, input_tokens, output_tokens, latency_ms, finish_reason}
        네트워크 오류는 TransientError, 그 외는 PermanentError를 던진다."""


def load_prompt(path: Path, allowed_slots: tuple = PROMPT_SLOTS) -> dict:
    prompt = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("version", "slots", "template"):
        if key not in prompt:
            raise ValueError(f"prompt file missing {key!r}: {path}")
    unknown = set(prompt["slots"]) - set(allowed_slots)
    if unknown:
        raise ValueError(f"unknown prompt slots {sorted(unknown)} in {path}")
    return prompt


def template_slots(template: str) -> set[str]:
    out = set()
    i = 0
    while True:
        start = template.find("{", i)
        if start == -1:
            return out
        end = template.find("}", start)
        if end == -1:
            return out
        out.add(template[start + 1:end])
        i = end + 1


def validate_prompt(prompt: dict) -> list[str]:
    """template이 선언된 slot만 쓰는지 확인한다. 문제 목록을 돌려준다(빈 목록이면 통과)."""
    problems = []
    if not prompt["template"].strip():
        return problems  # 승인 전 빈 template은 slot 선언만 검사 대상이다
    used = template_slots(prompt["template"])
    declared = set(prompt["slots"])
    for slot in sorted(used - declared):
        problems.append(f"template uses undeclared slot {{{slot}}}")
    for slot in sorted(declared - used):
        problems.append(f"declared slot {{{slot}}} unused in template")
    return problems


def render_prompt(prompt: dict, values: dict) -> str:
    if not prompt["template"].strip():
        raise PromptNotApproved(f"prompt {prompt['version']} has no approved template")
    text = prompt["template"]
    for slot in prompt["slots"]:
        if slot not in values:
            raise KeyError(f"missing value for slot {slot}")
        text = text.replace("{" + slot + "}", str(values[slot]))
    return text


def strip_gold(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in GOLD_KEYS}


def format_candidates(candidates: Iterable[dict]) -> str:
    """후보 목록을 ID와 라벨만으로 적는다. role·의미 힌트를 넣지 않는다."""
    lines = []
    for c in candidates:
        label = c.get("label")
        lines.append(f"{c['entity_id']}: {label}" if label else str(c["entity_id"]))
    return "\n".join(lines)


def build_request(item: dict, condition: str, prompt: dict, run_config: dict) -> dict:
    """항목 하나와 조건으로 provider 요청을 만든다. item에 gold 키가 있으면 거부한다."""
    present = [k for k in GOLD_KEYS if k in item]
    if present:
        raise ValueError(f"item {item.get('item_id')} carries gold keys {present}; call strip_gold first")
    if any(marker in condition for marker in LOCAL_CONDITION_MARKERS):
        dialogue = item["local_text"]
    else:
        dialogue = item["full_text"]
    include_candidates = "qa" not in condition
    values = {
        "dialogue": dialogue,
        "target_utterance": item.get("local_text", ""),
        "target_marker": item["target_marker"]["form"] if isinstance(item.get("target_marker"), dict) else item.get("target_marker", ""),
        "target_speaker_label": item["target_speaker_label"],
        "candidates": format_candidates(item["candidates"]) if include_candidates else "",
        "output_schema": run_config.get("output_schema", "") if include_candidates else run_config.get("qa_output_schema", run_config.get("output_schema", "")),
    }
    user = render_prompt(prompt, values)
    return {
        "task": "resolve",
        "item_id": item["item_id"],
        "condition": condition,
        "candidate_ids": [c["entity_id"] for c in item["candidates"]] if include_candidates else [],
        "model_id": run_config["model_id"],
        "system": run_config.get("system", ""),
        "user": user,
        "decoding": run_config.get("decoding", {}),
        "output_schema": values["output_schema"],
        "seed": run_config.get("seed"),
        "prompt_version": prompt["version"],
    }


def payload_hash(request: dict) -> str:
    material = {k: request.get(k) for k in ("model_id", "system", "user", "decoding", "output_schema", "seed", "prompt_version")}
    return hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def call_with_retry(adapter: ProviderAdapter, request: dict, max_retries: int = MAX_RETRIES, sleep=time.sleep) -> tuple[dict | None, int, str | None]:
    """(response, retries, error). TransientError만 재시도한다."""
    retries = 0
    while True:
        try:
            return adapter.complete(request), retries, None
        except TransientError as error:
            if retries >= max_retries:
                return None, retries, f"transient: {error}"
            retries += 1
            sleep(max(min(2 ** retries, 8), float(getattr(error, "retry_after", None) or 0)))
        except PermanentError as error:
            return None, retries, f"permanent: {error}"


RUN_IDENTITY_KEYS = ("model_id", "prompt_version", "items_sha256", "prompt_sha256", "system", "output_schema", "decoding")


def _check_same_run(run_dir: Path, run_config: dict, prompt: dict) -> None:
    """같은 run_dir를 다른 모델·프롬프트·입력으로 재사용하면 거부한다."""
    path = run_dir / "config.json"
    if not path.exists():
        return
    previous = json.loads(path.read_text(encoding="utf-8"))
    current = {**run_config, "prompt_version": prompt["version"]}
    differing = [k for k in RUN_IDENTITY_KEYS if previous.get(k) != current.get(k)]
    if differing:
        raise ValueError(f"run_dir {run_dir} was used with a different configuration ({differing}); use a new run_dir")


def _append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def file_sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_items(
    items: Iterable[dict],
    conditions: Iterable[str],
    adapter: ProviderAdapter,
    prompt: dict,
    run_config: dict,
    run_dir: Path,
    seed: int = 0,
    sleep=time.sleep,
) -> dict:
    """items × conditions를 독립 요청으로 실행하고 run_dir에 기록한다. 요약 dict를 돌려준다."""
    run_dir = Path(run_dir)
    cache_dir = run_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    _check_same_run(run_dir, run_config, prompt)
    # requests/responses는 이번 실행의 기록이다. 재개는 cache/가 담당하므로 로그는 새로 쓴다.
    for name in ("requests.jsonl", "responses.jsonl"):
        (run_dir / name).write_text("", encoding="utf-8")
    items = [strip_gold(i) for i in items]
    jobs = [(item, condition) for item in items for condition in conditions]
    random.Random(seed).shuffle(jobs)
    config = {
        **run_config,
        "prompt_version": prompt["version"],
        "conditions": list(conditions),
        "n_items": len(items),
        "order_seed": seed,
        "max_retries": MAX_RETRIES,
        "started": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (run_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"ok": 0, "missing": 0, "cached": 0, "permanent_error": 0}
    for order, (item, condition) in enumerate(jobs):
        request = build_request(item, condition, prompt, run_config)
        digest = payload_hash(request)
        _append_jsonl(run_dir / "requests.jsonl", {
            "item_id": item["item_id"], "condition": condition, "model_label": run_config.get("model_label"),
            "payload_hash": digest, "order": order,
        })
        cache_file = cache_dir / f"{digest}.json"
        if cache_file.exists():
            record = json.loads(cache_file.read_text(encoding="utf-8"))
            # 같은 payload를 다른 item이 재사용할 수 있으므로 현재 job 정보로 덮어쓴다.
            record.update({"item_id": item["item_id"], "condition": condition, "model_label": run_config.get("model_label"), "from_cache": True})
            summary["cached"] += 1
        else:
            response, retries, error = call_with_retry(adapter, request, sleep=sleep)
            record = {
                "item_id": item["item_id"], "condition": condition, "model_label": run_config.get("model_label"),
                "payload_hash": digest, "retries": retries, "error": error, "from_cache": False,
                "raw_text": response.get("raw_text") if response else None,
                "input_tokens": response.get("input_tokens") if response else None,
                "output_tokens": response.get("output_tokens") if response else None,
                "latency_ms": response.get("latency_ms") if response else None,
                "finish_reason": response.get("finish_reason") if response else None,
                "response_model": response.get("model") if response else None,
                "request_id": response.get("request_id") if response else None,
                "system_fingerprint": response.get("system_fingerprint") if response else None,
                "stop_details": response.get("stop_details") if response else None,
                "cache_read_input_tokens": response.get("cache_read_input_tokens") if response else None,
                "status": "ok" if response and response.get("raw_text") is not None else "missing",
            }
            if response is not None:
                cache_file.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            if error and error.startswith("permanent"):
                summary["permanent_error"] += 1
        summary[record["status"]] += 1
        _append_jsonl(run_dir / "responses.jsonl", record)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
