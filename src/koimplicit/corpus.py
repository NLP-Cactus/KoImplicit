"""Flatten the ZA 2025 spoken release into JSONL files (implementation guide §2).

Outputs under data/interim/ (git-ignored, they hold corpus text):
- utterances.jsonl  one row per sentence
- targets.jsonl     one row per restored subject; no restored form
- gold_hints.jsonl  restored form and role hints, isolated from later stages
"""

import json
import re
from collections import Counter
from pathlib import Path

SPOKEN_2025_PATTERN = "SXZA25*.json"

# Singular first/second person pronoun with an optional particle.
# 우리/저희 and address terms (형, 선생님 ...) are not covered.
_PARTICLE = r"(가|는|도|만|랑|한테|를)?"
FIRST_PERSON = re.compile(rf"^(나|내|저|제|난|전){_PARTICLE}$")
SECOND_PERSON = re.compile(rf"^(너|네|니|넌){_PARTICLE}$")
NAME_PLACEHOLDER = re.compile(r"^name\d+")
_STEM_SUFFIX = re.compile(r"(께서|이가|이|가|은|는|도)$")
_POSSESSIVE_PREFIX = re.compile(r"^(우리|저희|내|제|그|저|이) ")

# Word lists decided 2026-10-10 from the dyad frequency table (guide §3.2).
# Exact restored forms counted as generic or plural.
GENERIC_OR_PLURAL = frozenset({
    "누군가가", "무언가가", "우리가", "저희가", "사람들이", "사람이", "애들이",
    "친구들이", "가족이", "부모님이", "그게", "그것이",
})
# Stems of singular people other than the two participants: included as third-party candidates.
THIRD_PARTY_RELATION = frozenset({
    "엄마", "아빠", "어머니", "어머님", "아버지", "아버님", "언니", "오빠", "형", "누나",
    "동생", "이모", "고모", "고모부", "고모부님", "삼촌", "할머니", "할아버지", "남편", "아내",
    "와이프", "집사람", "시어머니", "남자친구", "여자친구", "남친", "여친", "친구", "선배",
    "후배", "선생님", "교수님", "사장님", "그분", "걔", "그 친구", "그 사람", "상대방",
})
# Stems left to a person on purpose (category stays "other"):
# occupations are often generic (연예인이 ...); 자기/본인/지 may be the addressee or reflexive.
MANUAL_STEMS = frozenset({"배우", "연예인", "사진사", "유튜버", "코미디언", "대학생", "알바",
                          "학생", "직원", "가수", "자기", "본인", "지"})
# Not human, outside the singular-human scope: excluded by the candidate filter.
NONHUMAN_STEMS = frozenset({"강아지", "고양이"})
_PLURAL_STEMS = frozenset({"걔네", "얘네", "부모님"})


def noun_stem(form: str) -> tuple:
    """(stem, bare): particle-stripped form, and the same without a possessive/demonstrative prefix."""
    stem = _STEM_SUFFIX.sub("", form.strip().rstrip(".,?!"))
    return stem, _POSSESSIVE_PREFIX.sub("", stem)


def person(form: str) -> str:
    form = form.strip().rstrip(".,?!")  # some restored forms keep sentence punctuation (나는.)
    if FIRST_PERSON.match(form):
        return "1p"
    if SECOND_PERSON.match(form):
        return "2p"
    return "other"


def find_spoken_release(root: Path) -> Path:
    matches = sorted((root / "data" / "raw").rglob(SPOKEN_2025_PATTERN))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one {SPOKEN_2025_PATTERN} under data/raw, found {len(matches)}")
    return matches[0]


def load_spoken_release(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def flatten_utterances(doc: dict) -> list:
    """One row per sentence. Order is the array position, never parsed from the ID."""
    labels = {}
    rows = []
    run_index = -1
    previous = None
    for order, sentence in enumerate(doc["sentence"]):
        speaker_id = sentence["speaker_id"]
        if speaker_id not in labels:
            labels[speaker_id] = chr(ord("A") + len(labels))
        if speaker_id != previous:
            run_index += 1
            previous = speaker_id
        rows.append({
            "conversation_id": doc["id"],
            "conversation_type": doc["metadata"]["title"],
            "order": order,
            "sentence_id": sentence["id"],
            "speaker_id": speaker_id,
            "speaker_label": labels[speaker_id],
            "run_index": run_index,
            "form": sentence["form"],
            "original_form": sentence.get("original_form", sentence["form"]),
            "form_differs": sentence["form"] != sentence.get("original_form", sentence["form"]),
        })
    return rows


def antecedent_relation(antecedent: dict, target_order: int, order_of: dict) -> str:
    if antecedent.get("form") == "#":
        return "none"  # its sentence_id is unreliable for '#' (guide §1.3)
    source = order_of.get(antecedent.get("sentence_id"))
    if source is None:
        return "missing_sentence"
    if source == target_order:
        return "same"
    return "earlier" if source < target_order else "later"


def role_hint(restored_form: str, antecedents: list, target_speaker: str, roster: list,
              speaker_of: dict) -> dict:
    """Role of the restored subject relative to the TARGET speaker (guide §2.2, revised).

    Restored forms copy the antecedent's person (ZA 2025 guideline 2.2.3.2), so a
    pronoun antecedent is resolved through the speaker of the sentence it sits in.
    """
    form = restored_form.strip()
    if form.startswith("화자"):
        return {"hint_category": "speaker_deictic", "hint_basis": "label", "perspective_conflict": False,
                "pronoun_antecedent_conflict": False}
    if form.startswith("청자"):
        return {"hint_category": "addressee_deictic", "hint_basis": "label", "perspective_conflict": False,
                "pronoun_antecedent_conflict": False}

    # Every pronoun antecedent is resolved; the first decides the hint. Antecedents that
    # point at different people are flagged for a person to check (pronoun_antecedent_conflict).
    resolved = []
    for antecedent in antecedents:
        if antecedent["relation"] in ("none", "missing_sentence"):
            continue
        grammatical = person(antecedent["form"])
        if grammatical == "other":
            continue
        anchor = speaker_of[antecedent["sentence_id"]]
        others = [s for s in roster if s != anchor]
        referent = anchor if grammatical == "1p" else (others[0] if len(others) == 1 else None)
        if referent is not None:  # None: monologue or roster problem
            resolved.append((anchor, referent))
    if resolved:
        anchor, referent = resolved[0]
        return {
            "hint_category": "speaker_pronoun" if referent == target_speaker else "addressee_pronoun",
            "hint_basis": "antecedent_speaker",
            "perspective_conflict": anchor != target_speaker,
            "pronoun_antecedent_conflict": len({r for _, r in resolved}) > 1,
        }

    grammatical = person(form)
    if grammatical == "1p":
        category = "speaker_pronoun"
    elif grammatical == "2p":
        category = "addressee_pronoun"
    elif NAME_PLACEHOLDER.match(form):
        category = "name_placeholder"
    elif form in GENERIC_OR_PLURAL:
        category = "generic_or_plural"
    else:
        stem, bare = noun_stem(form)
        if stem in THIRD_PARTY_RELATION or bare in THIRD_PARTY_RELATION:
            category = "third_party_relation"
        elif bare.endswith("들") or bare in _PLURAL_STEMS:
            category = "generic_or_plural"
        else:
            category = "other"  # includes MANUAL_STEMS and NONHUMAN_STEMS; the filter tells them apart
    return {"hint_category": category, "hint_basis": "restored_form", "perspective_conflict": False,
                "pronoun_antecedent_conflict": False}


def flatten_targets(doc: dict, utterances: list) -> tuple:
    """Rows for restored subjects: (targets, gold_hints). Other types are only counted."""
    order_of = {u["sentence_id"]: u["order"] for u in utterances}
    speaker_of = {u["sentence_id"]: u["speaker_id"] for u in utterances}
    label_of = {u["speaker_id"]: u["speaker_label"] for u in utterances}
    roster = [s["id"] for s in doc["metadata"].get("speaker", [])]
    targets, hints = [], []
    for order, sentence in enumerate(doc["sentence"]):
        for za in sentence.get("ZA", []):
            predicate = za["predicate"]
            for index, ellipsis in enumerate(za["ellipsis"]):
                if ellipsis["restored"].get("type") != "subject":
                    continue
                target_id = f"{doc['id']}:{sentence['id']}:{predicate['word_id']}:{index}"
                antecedents = [
                    {"form": a.get("form"), "sentence_id": a.get("sentence_id"),
                     "begin": a.get("begin"), "end": a.get("end"),
                     "relation": antecedent_relation(a, order, order_of)}
                    for a in ellipsis["antecedent"]
                ]
                textual = [a for a in antecedents if a["relation"] != "none"]
                backward = [order - order_of[a["sentence_id"]] for a in antecedents
                            if a["relation"] in ("same", "earlier")]
                targets.append({
                    "target_id": target_id,
                    "conversation_id": doc["id"],
                    "sentence_id": sentence["id"],
                    "order": order,
                    "speaker_id": sentence["speaker_id"],
                    "speaker_label": label_of[sentence["speaker_id"]],
                    "predicate_form": predicate["form"],
                    "predicate_word_id": predicate["word_id"],
                    "predicate_begin": predicate["begin"],
                    "predicate_end": predicate["end"],
                    "restored_type": "subject",
                    "antecedents": antecedents,
                    "has_textual_antecedent": bool(textual),
                    "has_future_antecedent": any(a["relation"] == "later" for a in antecedents),
                    "antecedent_missing": not antecedents,
                    "last_textual_antecedent_distance": min(backward) if backward else None,
                })
                hint = role_hint(ellipsis["restored"]["form"], antecedents, sentence["speaker_id"],
                                 roster, speaker_of)
                hints.append({"target_id": target_id, "restored_form": ellipsis["restored"]["form"], **hint})
    return targets, hints


def write_jsonl(rows: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _id_key(sentence_id: str) -> tuple:
    return tuple(int(part) for part in sentence_id.split(".")[1:])


def parse_release(release: dict) -> tuple:
    """Return (utterances, targets, gold_hints, report). The report mirrors guide §1.4."""
    utterances, targets, hints = [], [], []
    report = Counter()
    ellipsis_types = Counter()
    for doc in release["document"]:
        rows = flatten_utterances(doc)
        forms = {row["sentence_id"]: row["form"] for row in rows}
        roster = {s["id"] for s in doc["metadata"].get("speaker", [])}
        report["documents"] += 1
        report["sentences"] += len(rows)
        report["form_differs"] += sum(row["form_differs"] for row in rows)
        report["speaker_not_in_roster"] += sum(row["speaker_id"] not in roster for row in rows)
        ids = [row["sentence_id"] for row in rows]
        report["documents_with_id_order_mismatch"] += ids != sorted(ids, key=_id_key)
        for sentence in doc["sentence"]:
            for za in sentence.get("ZA", []):
                report["predicates"] += 1
                p = za["predicate"]
                report["predicate_offset_mismatch"] += forms.get(p["sentence_id"], "")[p["begin"]:p["end"]] != p["form"]
                for ellipsis in za["ellipsis"]:
                    report["ellipses"] += 1
                    ellipsis_types[ellipsis["restored"].get("type", "<missing>")] += 1
                    report["empty_antecedent"] += not ellipsis["antecedent"]
                    report["multi_antecedent"] += len(ellipsis["antecedent"]) > 1
                    for a in ellipsis["antecedent"]:
                        if a.get("form") == "#":
                            continue
                        text = forms.get(a.get("sentence_id"))
                        report["antecedent_offset_mismatch"] += (
                            text is None or text[int(a["begin"]):int(a["end"])] != a["form"])
        doc_targets, doc_hints = flatten_targets(doc, rows)
        utterances += rows
        targets += doc_targets
        hints += doc_hints
    report = dict(report)
    report["ellipsis_types"] = dict(ellipsis_types)
    report["subject_targets"] = len(targets)
    report["duplicate_target_ids"] = len(targets) - len({t["target_id"] for t in targets})
    report["hint_category"] = dict(Counter(h["hint_category"] for h in hints))
    report["perspective_conflict"] = sum(h["perspective_conflict"] for h in hints)
    report["pronoun_antecedent_conflict"] = sum(h["pronoun_antecedent_conflict"] for h in hints)
    return utterances, targets, hints, report


def run_parse(root: Path, raw_path: Path = None, out_dir: Path = None) -> dict:
    root = root.resolve()
    raw_path = (raw_path or find_spoken_release(root)).resolve()
    out_dir = (out_dir or root / "data" / "interim").resolve()
    if not out_dir.is_relative_to(root / "data"):
        raise ValueError("Parsed files contain corpus text and must be written under data/")
    utterances, targets, hints, report = parse_release(load_spoken_release(raw_path))
    write_jsonl(utterances, out_dir / "utterances.jsonl")
    write_jsonl(targets, out_dir / "targets.jsonl")
    write_jsonl(hints, out_dir / "gold_hints.jsonl")
    report["source_file"] = raw_path.name
    (out_dir / "parse_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
