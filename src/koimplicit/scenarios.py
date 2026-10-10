"""시나리오 명세(Scenario Specification). 대화문과 분리해 관리한다.

시나리오는 "어떤 조건의 대화가 필요한가"를 적는다. 실제 대화문(DialogueRecord)은
시나리오를 보고 사람 또는 생성 모델이 쓴다. 생성 모델의 응답만으로 gold를 확정하지 않는다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schema import DatasetKind, Participant, Role, read_jsonl, write_jsonl


class VariantSpec(BaseModel):
    """base 사례에서 바꾸는 실험 조건 하나."""
    model_config = ConfigDict(extra="forbid")
    variant: str = Field(min_length=1)
    description: str
    manipulated_variables: list[str] = Field(default_factory=list)  # referent_shift, distractor, context_distance, speaker_role, linguistic_cue
    expected_gold_id: Optional[str] = None
    expected_gold_change: Optional[bool] = None  # base 대비 정답이 바뀌어야 하는가
    pair_with: Optional[str] = None  # 비교할 variant 이름


class ScenarioConditions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_role: Optional[Role] = None  # 의도한 정답 역할(목표 발화 기준)
    referent_shift: Optional[bool] = None
    distractor: Optional[bool] = None
    context_distance: Optional[int] = None  # 정답의 마지막 언급과 목표 발화 사이 턴 거리 목표
    speaker_change: Optional[bool] = None
    n_turns: Optional[int] = None


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(min_length=1)
    dataset: DatasetKind
    title: str
    setting: str  # 관계·상황 설명
    participants: list[Participant]
    intended_gold_id: Optional[str] = None  # 작성 의도. 검수 전에는 gold가 아니다
    previous_referent_id: Optional[str] = None
    distractor_id: Optional[str] = None
    conditions: ScenarioConditions = Field(default_factory=ScenarioConditions)
    required_context: list[str] = Field(default_factory=list)  # 앞 문맥이 반드시 세워야 하는 사실
    naturalness_constraints: list[str] = Field(default_factory=list)
    cue_constraints: list[str] = Field(default_factory=list)  # 어미·어휘만으로 정답이 정해지지 않게 하는 제약
    variants: list[VariantSpec] = Field(default_factory=list)
    source_note: Optional[str] = None  # 참고한 언어학적 현상·문헌(원문 인용 없음)

    @model_validator(mode="after")
    def _links(self) -> "Scenario":
        ids = {p.entity_id for p in self.participants}
        for field in ("intended_gold_id", "previous_referent_id", "distractor_id"):
            value = getattr(self, field)
            if value is not None and value not in ids:
                raise ValueError(f"{field}={value!r} not in participants")
        names = [v.variant for v in self.variants]
        if len(names) != len(set(names)):
            raise ValueError("duplicate variant names")
        for v in self.variants:
            if v.expected_gold_id is not None and v.expected_gold_id not in ids:
                raise ValueError(f"variant {v.variant}: expected_gold_id not in participants")
            if v.pair_with is not None and v.pair_with != "base" and v.pair_with not in names:
                raise ValueError(f"variant {v.variant}: pair_with {v.pair_with!r} unknown")
        return self

    def variant(self, name: str) -> Optional[VariantSpec]:
        for v in self.variants:
            if v.variant == name:
                return v
        return None


def load_scenarios(path: Path) -> list[Scenario]:
    errors, out = [], []
    for row in read_jsonl(path):
        try:
            out.append(Scenario.model_validate(row))
        except Exception as e:
            errors.append(f"{row.get('scenario_id')}: {e}")
    ids = [s.scenario_id for s in out]
    if len(ids) != len(set(ids)):
        errors.append("duplicate scenario_id")
    if errors:
        raise ValueError("scenario errors:\n- " + "\n- ".join(errors))
    return out


def save_scenarios(scenarios: list[Scenario], path: Path) -> None:
    write_jsonl((s.model_dump(mode="json") for s in scenarios), path)


def scenario_summary(scenarios: list[Scenario]) -> dict:
    from collections import Counter

    return {
        "n_scenarios": len(scenarios),
        "n_variants": sum(len(s.variants) for s in scenarios),
        "by_dataset": dict(Counter(s.dataset for s in scenarios)),
        "by_target_role": dict(Counter(str(s.conditions.target_role) for s in scenarios)),
        "by_n_participants": dict(Counter(sum(p.in_dialogue for p in s.participants) for s in scenarios)),
    }
