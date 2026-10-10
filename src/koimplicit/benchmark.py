"""LLM Benchmark Runner 최소 실행 버전.

runner.run_items(독립 요청·캐시·재시도·기록) → normalize(파싱) → gold join → metrics 요약.
run_dir에 config.json, requests.jsonl, responses.jsonl, normalized.jsonl, per_sample.csv, metrics.json을 남긴다.
비용은 configs/models.json의 price_per_million으로 추정한다(provider가 토큰 수를 돌려줄 때만).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Iterable, Optional

from .metrics import benchmark_summary
from .normalize import map_qa_answer, parse_mcq
from .runner import file_sha256, load_prompt, run_items
from .schema import read_jsonl, write_jsonl

DEFAULT_MODELS_FILE = Path("configs") / "models.json"


def load_model_config(models_file: Path, model_label: str) -> dict:
    cfg = json.loads(Path(models_file).read_text(encoding="utf-8"))
    if model_label not in cfg["models"]:
        raise KeyError(f"model {model_label!r} not in {models_file}; available: {sorted(cfg['models'])}")
    model = dict(cfg["models"][model_label])
    model["model_label"] = model_label
    model.setdefault("decoding", {})
    model["output_schema"] = cfg.get("output_schema", "")
    model["qa_output_schema"] = cfg.get("qa_output_schema", "")
    model["structured"] = cfg.get("structured", True)
    model["system"] = cfg.get("system", "")
    return model


def normalize_responses(responses: Iterable[dict], items: list[dict], structured: bool) -> list[dict]:
    by_item = {i["item_id"]: i for i in items}
    rows = []
    for r in responses:
        item = by_item.get(r["item_id"])
        if item is None:
            continue
        if "qa" in r["condition"]:
            parsed = map_qa_answer(r.get("raw_text"), item["candidates"], item["target_speaker_label"])
        else:
            parsed = parse_mcq(r.get("raw_text"), item["candidates"], structured=structured)
        if r.get("status") == "missing":
            parsed = {"predicted_entity_id": None, "parse_status": "missing", "note": r.get("error") or "no response"}
        rows.append({
            "item_id": r["item_id"], "condition": r["condition"], "model_label": r.get("model_label"),
            "payload_hash": r.get("payload_hash"), "raw_text": r.get("raw_text"), "retries": r.get("retries"),
            "input_tokens": r.get("input_tokens"), "output_tokens": r.get("output_tokens"), "latency_ms": r.get("latency_ms"),
            "finish_reason": r.get("finish_reason"), "response_model": r.get("response_model"),
            "predicted_entity_id": parsed.get("predicted_entity_id"), "parse_status": parsed.get("parse_status"),
            "parse_note": parsed.get("note"), "candidates": item["candidates"], "pair_id": item.get("pair_id"), "pair_ids": item.get("pair_ids") or [],
            "family_id": item.get("family_id"), "conversation_id": item.get("conversation_id"), "version": item.get("version"),
        })
    return rows


def join_gold(rows: Iterable[dict], gold_rows: Iterable[dict]) -> list[dict]:
    by_item = {g["item_id"]: g for g in gold_rows}
    out = []
    for r in rows:
        g = by_item.get(r["item_id"])
        if g is None:
            continue
        joined = {**r, **{k: v for k, v in g.items() if k != "item_id"}}
        joined["predicted_role"] = (g.get("entity_roles") or {}).get(r.get("predicted_entity_id"))
        out.append(joined)
    return out


def estimate_cost(rows: Iterable[dict], price: Optional[dict]) -> dict:
    rows = list(rows)
    tokens_in = sum(r.get("input_tokens") or 0 for r in rows)
    tokens_out = sum(r.get("output_tokens") or 0 for r in rows)
    known = sum(1 for r in rows if r.get("input_tokens") is not None)
    cost = None
    if price and price.get("input") is not None and price.get("output") is not None:
        cost = tokens_in / 1e6 * price["input"] + tokens_out / 1e6 * price["output"]
    return {"n_requests": len(rows), "n_with_usage": known, "input_tokens": tokens_in, "output_tokens": tokens_out,
            "estimated_cost_usd": cost, "price_per_million": price}


def write_per_sample(rows: list[dict], path: Path) -> None:
    fields = ["item_id", "condition", "model_label", "gold_entity_id", "predicted_entity_id", "correct", "parse_status",
              "gold_role", "predicted_role", "referent_changed", "speaker_changed", "referent_role_changed", "distractor_present",
              "designated_distractor_id", "turn_distance", "pair_id", "dataset", "raw_text"]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({**r, "correct": int(r.get("parse_status") == "ok" and r.get("predicted_entity_id") == r.get("gold_entity_id"))})


def run_benchmark(items: list[dict], gold_rows: list[dict], conditions: list[str], adapter, prompt: dict, model_config: dict,
                  run_dir: Path, seed: int = 0, items_path: Optional[Path] = None, prompt_path: Optional[Path] = None, sleep=None) -> dict:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {**model_config, "seed": seed, "items_sha256": file_sha256(items_path), "prompt_sha256": file_sha256(prompt_path),
              "conditions": conditions, "run_date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    kwargs = {"sleep": sleep} if sleep else {}
    run_summary = run_items(items, conditions, adapter, prompt, config, run_dir, seed=seed, **kwargs)
    responses = read_jsonl(run_dir / "responses.jsonl")
    normalized = normalize_responses(responses, items, structured=bool(model_config.get("structured", True)))
    write_jsonl(normalized, run_dir / "normalized.jsonl")
    joined = join_gold(normalized, gold_rows)
    write_per_sample(joined, run_dir / "per_sample.csv")
    metrics = benchmark_summary(joined)
    cost = estimate_cost(normalized, model_config.get("price_per_million"))
    report = {"run": run_summary, "model_label": model_config.get("model_label"), "model_id": model_config.get("model_id"),
              "provider": model_config.get("provider"), "prompt_version": prompt["version"], "conditions": conditions,
              "n_items": len(items), "cost": cost, "metrics": metrics}
    (run_dir / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_baselines(items: list[dict], gold_rows: list[dict], names: Optional[list[str]] = None) -> dict:
    from . import baselines as B

    available = {"most_recent_entity": B.most_recent_entity, "current_speaker": B.current_speaker, "current_addressee": B.current_addressee}
    names = names or list(available)
    out = {}
    for name in names:
        rows = join_gold(B.apply_baseline(items, available[name]), gold_rows)
        out[name] = {"metrics": benchmark_summary(rows), "mapping_failure": B.mapping_failure_rate(rows), "rows": rows}
    return out
