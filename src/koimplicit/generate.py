"""시나리오 → 한국어 대화 초안 생성.

- provider는 providers 레지스트리를 재사용한다(mock 포함).
- 생성 프롬프트에는 시나리오의 의도(의도한 지시 대상 포함)가 들어간다. 생성은 평가가 아니므로
  정답 비노출 규칙의 대상이 아니다. 대신 생성 결과의 gold는 **시나리오의 의도값을 복사한 후보**이며
  annotation_status=candidate, ambiguity_status=unreviewed로만 저장된다. 모델 응답으로 gold를 확정하지 않는다.
- 생성 기록(generation_log.jsonl)에 프롬프트 버전·해시·모델·원문 응답을 남긴다.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Optional

from .runner import call_with_retry, load_prompt, payload_hash, render_prompt
from .scenarios import Scenario
from .schema import DialogueRecord, GenerationMetadata, LabelRecord, Turn, write_jsonl

GENERATE_SLOTS = ("scenario", "variant", "constraints", "output_schema")
OUTPUT_SCHEMA = (
    '다음 JSON 형식으로만 답하세요: {"turns": [{"speaker": "<참여자 이름>", "text": "<발화>"}, ...], '
    '"target_turn": <생략 주어가 있는 발화 번호(1부터)>, "target_predicate": "<그 발화 안의 서술어 문자열(그대로)>"}'
)


def load_generation_prompt(path: Path) -> dict:
    return load_prompt(path, allowed_slots=GENERATE_SLOTS)


def scenario_view(scenario: Scenario, variant: Optional[str]) -> dict:
    """생성 모델에 줄 시나리오 정보. 참여자 이름·관계·필요한 문맥·의도 지시 대상을 포함한다."""
    spec = scenario.variant(variant) if variant else None
    gold = (spec.expected_gold_id if spec and spec.expected_gold_id else scenario.intended_gold_id)
    name_of = {p.entity_id: p.name for p in scenario.participants}
    return {
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "setting": scenario.setting,
        "participants": [{"name": p.name, "in_dialogue": p.in_dialogue, "note": p.note} for p in scenario.participants],
        "n_turns": scenario.conditions.n_turns,
        "target_role": scenario.conditions.target_role,
        "intended_referent": name_of.get(gold) if gold else None,
        "previous_referent": name_of.get(scenario.previous_referent_id) if scenario.previous_referent_id else None,
        "distractor": name_of.get(scenario.distractor_id) if scenario.distractor_id else None,
        "required_context": scenario.required_context,
        "variant": variant,
        "variant_description": spec.description if spec else None,
    }


def build_generation_request(scenario: Scenario, variant: Optional[str], prompt: dict, run_config: dict) -> dict:
    view = scenario_view(scenario, variant)
    constraints = scenario.naturalness_constraints + scenario.cue_constraints
    values = {
        "scenario": json.dumps(view, ensure_ascii=False, indent=1),
        "variant": variant or "base",
        "constraints": "\n".join(f"- {c}" for c in constraints) or "- (없음)",
        "output_schema": OUTPUT_SCHEMA,
    }
    return {
        "task": "generate",
        "item_id": f"{scenario.scenario_id}:{variant or 'base'}",
        "condition": "generate",
        "scenario": view,
        "model_id": run_config.get("model_id", "unset"),
        "system": run_config.get("system", ""),
        "user": render_prompt(prompt, values),
        "decoding": run_config.get("decoding", {}),
        "output_schema": OUTPUT_SCHEMA,
        "seed": run_config.get("seed"),
        "prompt_version": prompt["version"],
    }


def parse_generation(raw_text: str, scenario: Scenario) -> tuple[list[Turn], int, str]:
    """생성 응답을 Turn 목록으로 바꾼다. 이름을 entity_id로 매핑한다. 실패하면 ValueError."""
    text = raw_text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no json object in generation response")
    payload = json.loads(text[start:end + 1])
    id_of = {p.name: p.entity_id for p in scenario.participants if p.in_dialogue}
    turns = []
    for i, t in enumerate(payload.get("turns") or [], start=1):
        speaker = t.get("speaker")
        if speaker not in id_of:
            raise ValueError(f"turn {i}: unknown speaker {speaker!r}")
        turns.append(Turn(turn_index=i, speaker_id=id_of[speaker], text=str(t.get("text", "")).strip()))
    if not turns:
        raise ValueError("no turns")
    target_turn = int(payload.get("target_turn") or len(turns))
    predicate = str(payload.get("target_predicate") or "").strip()
    if not predicate:
        raise ValueError("no target_predicate")
    return turns, target_turn, predicate


def generate_drafts(scenarios: list[Scenario], adapter, prompt: dict, run_config: dict, out_dir: Path,
                    variants: str = "all", sleep=None) -> dict:
    """시나리오(와 변형)마다 초안을 만들어 out_dir에 dialogues.jsonl / labels.jsonl / generation_log.jsonl로 저장한다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    dialogues, labels, log = [], [], []
    summary = {"requested": 0, "ok": 0, "failed": 0, "parse_error": 0}
    for scenario in scenarios:
        names = [None] + [v.variant for v in scenario.variants] if variants == "all" else [None]
        for variant in names:
            request = build_generation_request(scenario, variant, prompt, run_config)
            summary["requested"] += 1
            kwargs = {"sleep": sleep} if sleep else {}
            response, retries, error = call_with_retry(adapter, request, **kwargs)
            entry = {"scenario_id": scenario.scenario_id, "variant": variant or "base", "prompt_version": prompt["version"],
                     "payload_hash": payload_hash(request), "model_id": run_config.get("model_id"), "retries": retries,
                     "error": error, "raw_text": response.get("raw_text") if response else None, "created": created}
            log.append(entry)
            if not response or response.get("raw_text") is None:
                summary["failed"] += 1
                continue
            try:
                turns, target_turn, predicate = parse_generation(response["raw_text"], scenario)
                sample_id = f"{scenario.scenario_id}-{variant or 'base'}"
                spec = scenario.variant(variant) if variant else None
                record = DialogueRecord(
                    sample_id=sample_id, dataset=scenario.dataset, scenario_id=scenario.scenario_id,
                    family_id=scenario.scenario_id, pair_ids=_pair_ids(scenario, variant), variant=variant or "base",
                    participants=scenario.participants, dialogue=turns, speaker_id=turns[target_turn - 1].speaker_id,
                    target_turn=target_turn, target_predicate=predicate, creation_method="llm_generated_api",
                    generation_metadata=GenerationMetadata(model=response.get("model") or run_config.get("model_id"),
                                                           provider=run_config.get("provider"), prompt_version=prompt["version"], created=created),
                )
                gold = spec.expected_gold_id if spec and spec.expected_gold_id else scenario.intended_gold_id
                labels.append(LabelRecord(
                    sample_id=sample_id, gold_referent_id=gold,
                    distractor_id=scenario.distractor_id if scenario.distractor_id != gold else None,
                    ambiguity_status="unreviewed", annotation_status="candidate",
                    manipulated_variables=spec.manipulated_variables if spec else [],
                    expected_gold_change=spec.expected_gold_change if spec else None,
                    author_rationale="생성 모델 초안. gold는 시나리오 의도값 복사본이며 검수 전이다.",
                    validation_metadata={"generation_payload_hash": entry["payload_hash"]},
                ))
                dialogues.append(record)
                summary["ok"] += 1
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                entry["parse_error"] = str(e)
                summary["parse_error"] += 1
    write_jsonl((d.model_dump(mode="json") for d in dialogues), out_dir / "dialogues.jsonl")
    write_jsonl((l.model_dump(mode="json") for l in labels), out_dir / "labels.jsonl")
    write_jsonl(log, out_dir / "generation_log.jsonl")
    (out_dir / "generation_config.json").write_text(json.dumps({**run_config, "prompt_version": prompt["version"], "created": created, "summary": summary}, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _pair_ids(scenario: Scenario, variant: Optional[str]) -> list[str]:
    """variant.pair_with로 pair_id 목록을 만든다. 형식 '{scenario}:{a}~{b}'."""
    name = variant or "base"
    out = []
    for v in scenario.variants:
        if v.pair_with == name:
            out.append(f"{scenario.scenario_id}:{name}~{v.variant}")
        if v.variant == name and v.pair_with:
            out.append(f"{scenario.scenario_id}:{v.pair_with}~{name}")
    return out
