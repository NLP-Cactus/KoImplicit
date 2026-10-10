"""KoImplicit 독립 창작 데이터셋 스키마.

설계 원칙:
- 모델에 보여도 되는 정보(DialogueRecord)와 정답·실험 메타데이터(LabelRecord)를
  서로 다른 레코드·파일로 분리한다. Sample은 둘을 sample_id로 합친 분석용 뷰다.
- Speaker / Addressee / Third-party는 항상 **목표 발화의 화자** 기준으로 계산한다.
- 발화자 변화(speaker_changed)와 참조 대상 변화(referent_changed)는 별개 변수다.
- anchor(이전 참조 대상)를 확인할 수 없으면 shift 변수는 None으로 둔다. False로 두지 않는다.
- 정답이 불명확하면 gold_referent_id는 None이고 ambiguity_status로 표시한다.

파일 형식은 JSONL이다. read_jsonl / write_jsonl, load_dataset을 쓴다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["speaker", "addressee", "third_party"]
DatasetKind = Literal["controlled", "naturalistic"]
CreationMethod = Literal["human_authored", "llm_authored", "llm_generated_api", "llm_generated_human_edited", "template"]
AnnotationStatus = Literal["candidate", "in_review", "adjudicated", "accepted", "rejected"]
AmbiguityStatus = Literal["unreviewed", "unambiguous", "ambiguous", "uncertain"]

MIN_TURNS, MAX_TURNS = 2, 6
MIN_PARTICIPANTS, MAX_PARTICIPANTS = 2, 3


class Participant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)  # 언급 탐지용 표현. name은 자동 포함
    in_dialogue: bool = True
    note: Optional[str] = None

    def surface_forms(self) -> list[str]:
        forms = [self.name] + [a for a in self.aliases if a]
        return sorted(set(forms), key=len, reverse=True)


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_index: int = Field(ge=1)
    speaker_id: str
    text: str = Field(min_length=1)


class GenerationMetadata(BaseModel):
    """생성 출처. 모델명·프롬프트 버전·날짜를 기록한다. 사람이 쓴 경우 model은 None."""
    model_config = ConfigDict(extra="allow")
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_version: Optional[str] = None
    created: Optional[str] = None
    author: Optional[str] = None
    edited_by: list[str] = Field(default_factory=list)


class DialogueRecord(BaseModel):
    """모델 입력에 쓸 수 있는 부분. 정답 정보를 넣지 않는다."""
    model_config = ConfigDict(extra="forbid")
    sample_id: str = Field(min_length=1)
    dataset: DatasetKind
    scenario_id: str = Field(min_length=1)
    template_id: Optional[str] = None
    family_id: Optional[str] = None
    pair_ids: list[str] = Field(default_factory=list)  # 속한 pair 전부. 한 표본이 여러 pair에 들어갈 수 있다
    variant: str = "base"
    participants: list[Participant]
    dialogue: list[Turn]
    speaker_id: str  # 목표 발화의 화자
    target_turn: int = Field(ge=1)
    target_predicate: str = Field(min_length=1)
    target_predicate_span: Optional[tuple[int, int]] = None
    omitted_argument: Literal["subject"] = "subject"
    creation_method: CreationMethod
    generation_metadata: GenerationMetadata = Field(default_factory=GenerationMetadata)
    version: str = "v0"

    @field_validator("dialogue")
    @classmethod
    def _turns_contiguous(cls, turns: list[Turn]) -> list[Turn]:
        if not MIN_TURNS <= len(turns) <= MAX_TURNS:
            raise ValueError(f"dialogue must have {MIN_TURNS}-{MAX_TURNS} turns, got {len(turns)}")
        expected = list(range(1, len(turns) + 1))
        if [t.turn_index for t in turns] != expected:
            raise ValueError("turn_index must be 1..n in order")
        return turns

    @model_validator(mode="after")
    def _check_links(self) -> "DialogueRecord":
        ids = [p.entity_id for p in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate entity_id in participants")
        in_dialogue = {p.entity_id for p in self.participants if p.in_dialogue}
        if not MIN_PARTICIPANTS <= len(in_dialogue) <= MAX_PARTICIPANTS:
            raise ValueError(f"dialogue participants must be {MIN_PARTICIPANTS}-{MAX_PARTICIPANTS}, got {len(in_dialogue)}")
        for turn in self.dialogue:
            if turn.speaker_id not in in_dialogue:
                raise ValueError(f"turn {turn.turn_index} speaker {turn.speaker_id!r} is not an in-dialogue participant")
        if self.target_turn > len(self.dialogue):
            raise ValueError("target_turn beyond dialogue length")
        target = self.dialogue[self.target_turn - 1]
        if target.speaker_id != self.speaker_id:
            raise ValueError("speaker_id must equal the target turn speaker")
        if self.target_predicate_span is None:
            count = target.text.count(self.target_predicate)
            if count != 1:
                raise ValueError(f"target_predicate must occur exactly once in the target turn (found {count}); set target_predicate_span")
            start = target.text.index(self.target_predicate)
            object.__setattr__(self, "target_predicate_span", (start, start + len(self.target_predicate)))
        else:
            b, e = self.target_predicate_span
            if target.text[b:e] != self.target_predicate:
                raise ValueError("target_predicate_span does not match target_predicate")
        for turn in self.dialogue:
            for pid in ids:
                if pid in turn.text:
                    raise ValueError(f"entity_id {pid!r} appears literally in turn {turn.turn_index}; dialogue text must use names only")
        return self

    @property
    def pair_id(self) -> Optional[str]:
        return self.pair_ids[0] if self.pair_ids else None

    def participant(self, entity_id: str) -> Participant:
        for p in self.participants:
            if p.entity_id == entity_id:
                return p
        raise KeyError(entity_id)

    def in_dialogue_ids(self) -> list[str]:
        return [p.entity_id for p in self.participants if p.in_dialogue]

    def target(self) -> Turn:
        return self.dialogue[self.target_turn - 1]


class LabelRecord(BaseModel):
    """정답과 실험 메타데이터. 모델 입력·주석 화면에 넣지 않는다."""
    model_config = ConfigDict(extra="forbid")
    sample_id: str = Field(min_length=1)
    addressee_id: Optional[str] = None  # 다자 대화에서 식별 불가면 None
    gold_referent_id: Optional[str] = None  # 의미상 불명확하면 None
    anchor_turn: Optional[int] = Field(default=None, ge=1)  # 이전 참조 대상이 주어인 가장 가까운 선행 발화
    anchor_referent_id: Optional[str] = None
    anchor_addressee_id: Optional[str] = None
    distractor_id: Optional[str] = None  # 작성자가 지정한 경쟁 개체
    ambiguity_status: AmbiguityStatus = "unreviewed"
    annotation_status: AnnotationStatus = "candidate"
    linguistic_cues: list[str] = Field(default_factory=list)
    manipulated_variables: list[str] = Field(default_factory=list)  # base 대비 바꾼 변수
    pair_claims: dict[str, list[str]] = Field(default_factory=dict)  # pair_id별 주장 조작(base가 아닌 변형끼리 비교할 때)
    pair_expected_gold_change: dict[str, Optional[bool]] = Field(default_factory=dict)  # pair_id별 정답 변경 의도
    expected_gold_change: Optional[bool] = None  # 변형이면 base 대비 정답 변경 의도
    author_rationale: Optional[str] = None
    validation_metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _consistency(self) -> "LabelRecord":
        if (self.anchor_turn is None) != (self.anchor_referent_id is None):
            raise ValueError("anchor_turn and anchor_referent_id must be set together")
        if self.annotation_status == "accepted":
            if self.gold_referent_id is None or self.ambiguity_status != "unambiguous":
                raise ValueError("accepted samples need a gold referent and ambiguity_status=unambiguous")
        if self.gold_referent_id is None and self.ambiguity_status == "unambiguous":
            raise ValueError("ambiguity_status=unambiguous requires a gold referent")
        return self


class Derived(BaseModel):
    """DialogueRecord + LabelRecord에서 계산되는 실험 변수."""
    model_config = ConfigDict(extra="forbid")
    gold_referent_role: Optional[Role] = None
    anchor_referent_role: Optional[Role] = None
    speaker_changed: Optional[bool] = None
    referent_changed: Optional[bool] = None
    referent_role_changed: Optional[bool] = None
    gold_last_mention_turn: Optional[int] = None
    turn_distance: Optional[int] = None  # 목표 발화와 정답의 마지막 명시 언급 사이 거리. 언급 없으면 None
    most_recent_mentioned_id: Optional[str] = None
    distractor_present: Optional[bool] = None  # gold가 없으면 None
    distractor_last_mention_turn: Optional[int] = None
    n_turns: int = 0
    n_participants: int = 0


class Sample(BaseModel):
    """분석용 통합 뷰. 모델 입력으로 직접 쓰지 않는다(payload.to_item을 쓴다)."""
    model_config = ConfigDict(extra="forbid")
    record: DialogueRecord
    label: LabelRecord
    derived: Derived

    @property
    def sample_id(self) -> str:
        return self.record.sample_id

    def flat(self) -> dict:
        out = self.record.model_dump(mode="json")
        out["pair_id"] = self.record.pair_id
        out.update(self.label.model_dump(mode="json"))
        out.update(self.derived.model_dump(mode="json"))
        return out


# --------------------------------------------------------------------------- 파생 변수

def surface_forms_of(participants: Iterable) -> list[tuple[str, str]]:
    """모든 참여자의 (표면형, entity_id)를 긴 표현부터 정렬한다. 참여자별이 아니라 전체 기준이라 '형'이 '형수님'을 가로채지 않는다."""
    forms = []
    for p in participants:
        if isinstance(p, Participant):
            names, eid = p.surface_forms(), p.entity_id
        else:  # item candidates: {entity_id, label, aliases}
            names, eid = sorted({p.get("label"), *(p.get("aliases") or [])} - {None, ""}, key=len, reverse=True), p["entity_id"]
        forms += [(f, eid) for f in names if f]
    return sorted(forms, key=lambda fe: (-len(fe[0]), fe[0]))


def find_mentions(text: str, forms: list[tuple[str, str]]) -> list[tuple[int, str]]:
    """(위치, entity_id). 긴 표면형부터 찾고 한 번 잡힌 구간은 다시 쓰지 않는다."""
    consumed = [False] * len(text)
    found = []
    for form, eid in forms:
        start = 0
        while True:
            pos = text.find(form, start)
            if pos == -1:
                break
            if not any(consumed[pos: pos + len(form)]):
                found.append((pos, eid))
                for i in range(pos, pos + len(form)):
                    consumed[i] = True
            start = pos + len(form)
    return sorted(found)


def mentions_by_turn(record: DialogueRecord, up_to_target_predicate: bool = True) -> list[tuple[int, int, str]]:
    """(turn_index, position, entity_id) 목록. 목표 발화는 서술어 앞까지만 본다.

    발화자 라벨("이름:")은 언급이 아니므로 세지 않는다. 텍스트 안의 표면형만 찾는다.
    """
    forms = surface_forms_of(record.participants)
    found = []
    for turn in record.dialogue:
        if turn.turn_index > record.target_turn:
            break
        text = turn.text
        if turn.turn_index == record.target_turn and up_to_target_predicate and record.target_predicate_span:
            text = text[: record.target_predicate_span[0]]
        found += [(turn.turn_index, pos, eid) for pos, eid in find_mentions(text, forms)]
    return sorted(found)


def role_of(entity_id: Optional[str], speaker_id: str, addressee_id: Optional[str], record: DialogueRecord) -> Optional[Role]:
    """목표 발화 기준 역할. 다자 대화에서 청자를 모르는데 entity가 발화 참여자이면 None."""
    if entity_id is None:
        return None
    if entity_id == speaker_id:
        return "speaker"
    if addressee_id is not None:
        return "addressee" if entity_id == addressee_id else "third_party"
    in_dialogue = record.in_dialogue_ids()
    if entity_id in in_dialogue:
        others = [p for p in in_dialogue if p != speaker_id]
        return "addressee" if len(others) == 1 else None
    return "third_party"


def infer_addressee(record: DialogueRecord, speaker_id: str, declared: Optional[str]) -> Optional[str]:
    if declared is not None:
        return declared
    others = [p for p in record.in_dialogue_ids() if p != speaker_id]
    return others[0] if len(others) == 1 else None


def derive(record: DialogueRecord, label: LabelRecord) -> Derived:
    gold = label.gold_referent_id
    addressee = infer_addressee(record, record.speaker_id, label.addressee_id)
    gold_role = role_of(gold, record.speaker_id, addressee, record)

    anchor_role = speaker_changed = referent_changed = role_changed = None
    if label.anchor_turn is not None and label.anchor_referent_id is not None:
        if not 1 <= label.anchor_turn < record.target_turn:
            raise ValueError(f"anchor_turn {label.anchor_turn} must be in [1, target_turn)")
        anchor_turn = record.dialogue[label.anchor_turn - 1]
        anchor_addressee = infer_addressee(record, anchor_turn.speaker_id, label.anchor_addressee_id)
        anchor_role = role_of(label.anchor_referent_id, anchor_turn.speaker_id, anchor_addressee, record)
        speaker_changed = anchor_turn.speaker_id != record.speaker_id
        if gold is not None:
            referent_changed = label.anchor_referent_id != gold
            if anchor_role is not None and gold_role is not None:
                role_changed = anchor_role != gold_role

    mentions = mentions_by_turn(record)
    last_turn_of: dict[str, int] = {}
    for turn_index, _, entity_id in mentions:
        last_turn_of[entity_id] = turn_index
    gold_last = last_turn_of.get(gold) if gold else None
    most_recent = mentions[-1][2] if mentions else None

    distractor_last = last_turn_of.get(label.distractor_id) if label.distractor_id else None
    if gold is None:
        present = None
    elif label.distractor_id is not None:
        present = distractor_last is not None and (gold_last is None or _after(mentions, label.distractor_id, gold))
    else:
        present = most_recent is not None and most_recent != gold
    return Derived(
        gold_referent_role=gold_role,
        anchor_referent_role=anchor_role,
        speaker_changed=speaker_changed,
        referent_changed=referent_changed,
        referent_role_changed=role_changed,
        gold_last_mention_turn=gold_last,
        turn_distance=(record.target_turn - gold_last) if gold_last is not None else None,
        most_recent_mentioned_id=most_recent,
        distractor_present=present,
        distractor_last_mention_turn=distractor_last,
        n_turns=len(record.dialogue),
        n_participants=len(record.in_dialogue_ids()),
    )


def _after(mentions: list[tuple[int, int, str]], a: str, b: Optional[str]) -> bool:
    """a의 마지막 언급이 b의 마지막 언급보다 뒤에 있는가."""
    last_a = max((m for m in mentions if m[2] == a), default=None)
    last_b = max((m for m in mentions if m[2] == b), default=None)
    if last_a is None:
        return False
    if last_b is None:
        return True
    return last_a[:2] > last_b[:2]


def build_sample(record: DialogueRecord, label: LabelRecord) -> Sample:
    if record.sample_id != label.sample_id:
        raise ValueError("record/label sample_id mismatch")
    return Sample(record=record, label=label, derived=derive(record, label))


# --------------------------------------------------------------------------- JSONL

def read_jsonl(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(rows: Iterable[dict], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


DIALOGUE_FILE = "dialogues.jsonl"
LABEL_FILE = "labels.jsonl"


def load_dataset(folder: Path, dialogue_file: str = DIALOGUE_FILE, label_file: str = LABEL_FILE) -> list[Sample]:
    """folder/dialogues.jsonl + folder/labels.jsonl → Sample 목록. 스키마 오류는 ValueError로 모아 던진다."""
    folder = Path(folder)
    records = {}
    errors = []
    for row in read_jsonl(folder / dialogue_file):
        try:
            rec = DialogueRecord.model_validate(row)
            if rec.sample_id in records:
                errors.append(f"duplicate sample_id {rec.sample_id}")
            records[rec.sample_id] = rec
        except Exception as e:  # pydantic ValidationError
            errors.append(f"dialogue {row.get('sample_id')}: {e}")
    labels = {}
    for row in read_jsonl(folder / label_file):
        try:
            lab = LabelRecord.model_validate(row)
            if lab.sample_id in labels:
                errors.append(f"duplicate label sample_id {lab.sample_id}")
            labels[lab.sample_id] = lab
        except Exception as e:
            errors.append(f"label {row.get('sample_id')}: {e}")
    for sid in records:
        if sid not in labels:
            errors.append(f"missing label for {sid}")
    for sid in labels:
        if sid not in records:
            errors.append(f"label without dialogue: {sid}")
    if errors:
        raise ValueError("dataset schema errors:\n- " + "\n- ".join(errors))
    samples = []
    for sid, rec in records.items():
        try:
            samples.append(build_sample(rec, labels[sid]))
        except (IndexError, KeyError, ValueError) as e:
            errors.append(f"derive {sid}: {e}")
    if errors:
        raise ValueError("dataset derivation errors:\n- " + "\n- ".join(errors))
    return samples


def save_dataset(samples: Iterable[Sample], folder: Path) -> None:
    samples = list(samples)
    write_jsonl((s.record.model_dump(mode="json") for s in samples), Path(folder) / DIALOGUE_FILE)
    write_jsonl((s.label.model_dump(mode="json") for s in samples), Path(folder) / LABEL_FILE)


def render_dialogue(record: DialogueRecord, up_to: Optional[int] = None, mark_predicate: bool = False) -> str:
    """'이름: 발화' 형식. up_to(기본: 목표 발화)까지만. mark_predicate면 서술어를 [[ ]]로 감싼다."""
    limit = up_to or record.target_turn
    lines = []
    for turn in record.dialogue[:limit]:
        text = turn.text
        if mark_predicate and turn.turn_index == record.target_turn and record.target_predicate_span:
            b, e = record.target_predicate_span
            text = text[:b] + "[[" + text[b:e] + "]]" + text[e:]
        lines.append(f"{record.participant(turn.speaker_id).name}: {text}")
    return "\n".join(lines)
