"""Structure audit of the NIKL Zero Anaphora 2025 spoken corpus.

Reports counts only. Sentence text is never printed; the optional case list
holds source IDs and must be written under the git-ignored data/ folder.
"""

import json
import re
from collections import Counter
from pathlib import Path

DEFAULT_CORPUS_PATTERN = "SXZA25*.json"  # 2025 spoken file, anywhere under data/raw

# Singular first/second person pronoun with an optional particle.
# 우리/저희 and kinship or title address terms are not covered.
_PARTICLE = r"(가|는|도|만|랑|한테|를)?"
FIRST_PERSON = re.compile(rf"^(나|내|저|제|난|전){_PARTICLE}$")
SECOND_PERSON = re.compile(rf"^(너|네|니|넌){_PARTICLE}$")
PARTICIPANT_LABEL = re.compile(r"^(화자|청자)")
NONREFERENTIAL = re.compile(r"^(누군가|무언가|무엇|어딘가)")


def person(form: str) -> str:
    form = form.strip()
    if FIRST_PERSON.match(form):
        return "1p"
    if SECOND_PERSON.match(form):
        return "2p"
    return "other"


def find_corpus(root: Path) -> Path:
    matches = sorted((root / "data" / "raw").rglob(DEFAULT_CORPUS_PATTERN))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one {DEFAULT_CORPUS_PATTERN} under data/raw, found {len(matches)}")
    return matches[0]


def is_two_party(document: dict) -> bool:
    metadata = document["metadata"]
    return metadata.get("title", "").startswith("2인") and len(metadata.get("speaker", [])) == 2


def classify_subject(ellipsis: dict, target: dict, sentences: dict) -> tuple:
    """Return (category, cross_speaker) for one restored subject."""
    restored = ellipsis["restored"].get("form", "")
    linked = [a for a in ellipsis["antecedent"] if a.get("form") not in (None, "#")]
    if PARTICIPANT_LABEL.match(restored):
        return "participant_label", False
    if not linked:
        if NONREFERENTIAL.match(restored):
            return "nonreferential", False
        return "no_antecedent_other", False
    antecedent = linked[0]
    source = sentences.get(antecedent["sentence_id"])
    if source is None:
        return "antecedent_missing", False
    cross = source["speaker_id"] != target["speaker_id"]
    if person(antecedent["form"]) != "other":
        return "participant_pronoun", cross
    return "other_np", cross


def audit(corpus: dict) -> dict:
    documents = corpus["document"]
    dialogues = [d for d in documents if is_two_party(d)]

    sentence_total = 0
    missing_speaker = roster_mismatch = numbering_gaps = cleaned_differs = 0
    adjacent_pairs = adjacent_same = speaker_runs = 0
    id_depth = Counter()
    ellipsis_types = Counter()
    restored_label = Counter()
    categories = Counter()
    cross_tab = Counter()
    per_dialogue = {}
    speaker_dialogues = Counter()
    cases = []

    for document in dialogues:
        roster = {s["id"] for s in document["metadata"]["speaker"]}
        for speaker_id in roster:
            speaker_dialogues[speaker_id] += 1
        ordered = document["sentence"]
        by_id = {s["id"]: s for s in ordered}
        sentence_total += len(ordered)
        numbers = []
        previous = None
        for sentence in ordered:
            parts = sentence["id"].split(".")
            id_depth[len(parts)] += 1
            numbers.append(int(parts[-1]))
            speaker_id = sentence.get("speaker_id")
            if not speaker_id:
                missing_speaker += 1
            elif speaker_id not in roster:
                roster_mismatch += 1
            if sentence["form"] != sentence.get("original_form"):
                cleaned_differs += 1
            if previous is None or previous != speaker_id:
                speaker_runs += 1
            else:
                adjacent_same += 1
            if previous is not None:
                adjacent_pairs += 1
            previous = speaker_id
        numbering_gaps += sum(1 for a, b in zip(numbers, numbers[1:]) if b != a + 1)

        doc_counts = Counter()
        for sentence in ordered:
            for za in sentence.get("ZA", []):
                for ellipsis in za["ellipsis"]:
                    kind = ellipsis["restored"].get("type", "<missing>")
                    ellipsis_types[kind] += 1
                    if kind != "subject":
                        continue
                    form = ellipsis["restored"]["form"]
                    if PARTICIPANT_LABEL.match(form) or NONREFERENTIAL.match(form):
                        restored_label[re.sub(r"(가|께서|도)$", "", form)] += 1
                    category, cross = classify_subject(ellipsis, sentence, by_id)
                    categories[category] += 1
                    doc_counts[category] += 1
                    for antecedent in ellipsis["antecedent"]:
                        source = by_id.get(antecedent["sentence_id"])
                        if antecedent.get("form") in (None, "#") or source is None:
                            continue
                        pair = (person(form), person(antecedent["form"]))
                        if pair == ("other", "other"):
                            continue
                        side = "cross" if source["speaker_id"] != sentence["speaker_id"] else "same"
                        cross_tab[f"{pair[0]}<-{pair[1]}|{side}"] += 1
                    if category == "participant_pronoun" and cross:
                        doc_counts["cross_speaker_pronoun"] += 1
                        linked = next(a for a in ellipsis["antecedent"] if a.get("form") not in (None, "#"))
                        cases.append({
                            "document_id": document["id"],
                            "sentence_id": sentence["id"],
                            "predicate_begin": za["predicate"]["begin"],
                            "antecedent_sentence_id": linked["sentence_id"],
                            "target_speaker_id": sentence["speaker_id"],
                        })
        per_dialogue[document["id"]] = dict(doc_counts)

    def spread(key: str) -> dict:
        values = sorted(counts.get(key, 0) for counts in per_dialogue.values())
        if not values:
            return {}
        return {"min": values[0], "median": values[len(values) // 2], "max": values[-1], "total": sum(values)}

    return {
        "documents": len(documents),
        "document_titles": dict(Counter(d["metadata"]["title"] for d in documents)),
        "two_party_dialogues": len(dialogues),
        "sentences": sentence_total,
        "sentence_id_depth": {str(k): v for k, v in sorted(id_depth.items())},
        "missing_speaker_id": missing_speaker,
        "speaker_not_in_roster": roster_mismatch,
        "numbering_gaps": numbering_gaps,
        "cleaned_form_differs": cleaned_differs,
        "adjacent_same_speaker_ratio": round(adjacent_same / adjacent_pairs, 3) if adjacent_pairs else None,
        "speaker_runs": speaker_runs,
        "distinct_speakers": len(speaker_dialogues),
        "speakers_in_multiple_dialogues": sum(1 for n in speaker_dialogues.values() if n > 1),
        "ellipsis_types": dict(ellipsis_types),
        "subject_categories": dict(categories),
        "restored_labels_without_antecedent": dict(restored_label.most_common()),
        "person_cross_tab": dict(sorted(cross_tab.items())),
        "cross_speaker_pronoun_links": len(cases),
        "per_dialogue_spread": {
            key: spread(key)
            for key in ("participant_label", "participant_pronoun", "other_np", "cross_speaker_pronoun")
        },
        "_cases": cases,
    }


def run_audit(root: Path, corpus_path: Path = None, cases_path: Path = None) -> dict:
    root = root.resolve()
    corpus_path = (corpus_path or find_corpus(root)).resolve()
    report = audit(json.loads(corpus_path.read_text(encoding="utf-8")))
    cases = report.pop("_cases")
    report["corpus_file"] = corpus_path.name
    if cases_path is not None:
        cases_path = cases_path.resolve()
        if not cases_path.is_relative_to(root / "data"):
            raise ValueError("Case lists contain source IDs and must be written under data/")
        cases_path.parent.mkdir(parents=True, exist_ok=True)
        cases_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
        report["cases_file"] = str(cases_path.relative_to(root))
    return report
