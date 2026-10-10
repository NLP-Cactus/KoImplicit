"""Structure audit of the NIKL Zero Anaphora 2025 spoken corpus.

Reports counts only. Sentence text is never printed; the optional case list
holds source IDs and must be written under the git-ignored data/ folder.
"""

import json
import random
import re
from collections import Counter
from pathlib import Path

from .corpus import find_spoken_release as find_corpus
from .corpus import load_spoken_release, parse_release, person

PARTICIPANT_LABEL = re.compile(r"^(화자|청자)")
NONREFERENTIAL = re.compile(r"^(누군가|무언가|무엇|어딘가)")


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
    report = audit(load_spoken_release(corpus_path))
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


# --- Review sheet for the human structure audit (implementation guide §4) ---------------------

# (stratum, items). perspective_conflict is drawn first so it is never crowded out.
AUDIT_STRATA = (("perspective_conflict", 6), ("speaker", 8), ("addressee", 8),
                ("third_party_relation", 7), ("name_placeholder", 5), ("manual_check", 6))
CONTEXT_WINDOW = 15  # sentences before the target, the guideline's antecedent search range
SHEET_COLUMNS = (
    "item", "stratum", "target_id",
    # Fill these BEFORE opening audit_key.md.
    "대화연결_OK", "발화자_OK", "순서_OK", "발화경계_문제", "서술어위치_OK", "원문차이_영향",
    "근거유형(텍스트/참여자지시/미래/비지시/불명)", "내판정_인물(A/B/제3자:누구/불명)", "5단ID_메모", "메모",
    # Fill this AFTER opening audit_key.md.
    "원주석_비교(일치/형태복사/오연결/기타)",
)
_STRATUM_OF = {"speaker_pronoun": "speaker", "speaker_deictic": "speaker",
               "addressee_pronoun": "addressee", "addressee_deictic": "addressee",
               "third_party_relation": "third_party_relation", "name_placeholder": "name_placeholder",
               "other": "manual_check"}


def audit_stratum(hint: dict):
    if hint["perspective_conflict"]:
        return "perspective_conflict"
    return _STRATUM_OF.get(hint["hint_category"])  # generic_or_plural is not audited


def sample_audit_items(utterances: list, targets: list, hints: list, seed: int,
                       strata=AUDIT_STRATA) -> list:
    """Stratified sample, one item per conversation where possible, two at most."""
    dyads = {u["conversation_id"] for u in utterances if u["conversation_type"].startswith("2인")}
    pools = {name: [] for name, _ in strata}
    for target, hint in zip(targets, hints):
        stratum = audit_stratum(hint)
        if target["conversation_id"] in dyads and stratum in pools:
            pools[stratum].append((target, hint))
    rng = random.Random(seed)
    used = Counter()
    chosen = []
    for name, wanted in strata:
        pool = sorted(pools[name], key=lambda pair: pair[0]["target_id"])
        rng.shuffle(pool)
        picked = []
        for cap in (1, 2):
            for target, hint in pool:
                if len(picked) == wanted:
                    break
                if used[target["conversation_id"]] < cap and all(t is not target for _, t, _ in picked):
                    picked.append((name, target, hint))
                    used[target["conversation_id"]] += 1
        chosen += picked
    return chosen


def _mark_predicate(form: str, begin: int, end: int) -> str:
    return f"{form[:begin]}[[{form[begin:end]}]]{form[end:]}"


def render_audit_sheet(items: list, utterances_by_conversation: dict) -> tuple:
    """Return (sheet_markdown, key_markdown, tsv_text). The sheet hides restored forms and antecedents."""
    sheet = ["# 구조 audit 검토 시트", "",
             "읽는 법과 판정 열 설명은 `docs/말뭉치_활용_구현가이드.md` 4절을 따른다.",
             "판정은 `audit_sheet.tsv`에 적고, 모두 적은 뒤에만 `audit_key.md`를 연다.", ""]
    key = ["# 구조 audit 정답 키 (판정을 마친 뒤에 연다)", ""]
    rows = ["\t".join(SHEET_COLUMNS)]
    for number, (stratum, target, hint) in enumerate(items, 1):
        rows_of_doc = utterances_by_conversation[target["conversation_id"]]
        order = target["order"]
        start = max(0, order - CONTEXT_WINDOW)
        run = [u for u in rows_of_doc if u["run_index"] == rows_of_doc[order]["run_index"]]
        position = [u["order"] for u in run].index(order) + 1
        sheet += [f"## {number:02d}. [{stratum}] {target['target_id']}", ""]
        if start:
            sheet.append(f"(대화 앞부분 {start}문장 생략)")
            sheet.append("")
        for u in rows_of_doc[start:order + 1]:
            text = u["form"]
            if u["order"] == order:
                text = "**" + _mark_predicate(text, target["predicate_begin"], target["predicate_end"]) + "**"
            depth = len(u["sentence_id"].split("."))
            suffix = f"  `5단 ID {u['sentence_id']}`" if depth == 5 else ""
            sheet.append(f"- {u['speaker_label']}: {text}{suffix}")
        sheet.append("")
        differs = [u for u in rows_of_doc[start:order + 1] if u["form_differs"]]
        if differs:
            sheet.append("원 전사문(form과 다른 문장만):")
            sheet += [f"- {u['speaker_label']}: {u['original_form']}" for u in differs]
            sheet.append("")
        sheet += [f"목표: {rows_of_doc[order]['speaker_label']}의 서술어 `{target['predicate_form']}`의 생략 주어. "
                  f"이 문장은 화자 run의 {position}/{len(run)}번째 문장이다.", ""]

        label_of = {u["sentence_id"]: u["speaker_label"] for u in rows_of_doc}
        order_of = {u["sentence_id"]: u["order"] for u in rows_of_doc}
        key += [f"## {number:02d}. [{stratum}] {target['target_id']}", "",
                f"- 원 복원형: `{hint['restored_form']}`",
                f"- 자동 힌트: {hint['hint_category']} (근거 {hint['hint_basis']}, "
                f"화자 전환 {hint['perspective_conflict']}, 대명사 선행어 충돌 {hint['pronoun_antecedent_conflict']})"]
        for a in target["antecedents"] or [{"form": "(없음)", "relation": "missing"}]:
            if a["relation"] in ("same", "earlier", "later"):
                where = f"{label_of[a['sentence_id']]}의 문장, 목표 기준 {order_of[a['sentence_id']] - order:+d}문장"
            else:
                where = a["relation"]
            key.append(f"- 원 선행어: `{a['form']}` ({where})")
        key.append("")
        rows.append("\t".join([f"{number:02d}", stratum, target["target_id"]] + [""] * (len(SHEET_COLUMNS) - 3)))
    return "\n".join(sheet) + "\n", "\n".join(key) + "\n", "\n".join(rows) + "\n"


def run_audit_sample(root: Path, corpus_path: Path = None, out_dir: Path = None,
                     seed: int = 20261010) -> dict:
    root = root.resolve()
    corpus_path = (corpus_path or find_corpus(root)).resolve()
    out_dir = (out_dir or root / "data" / "interim").resolve()
    if not out_dir.is_relative_to(root / "data"):
        raise ValueError("Audit sheets contain corpus text and must be written under data/")
    utterances, targets, hints, _ = parse_release(load_spoken_release(corpus_path))
    by_conversation = {}
    for u in utterances:
        by_conversation.setdefault(u["conversation_id"], []).append(u)
    items = sample_audit_items(utterances, targets, hints, seed)
    sheet, key, tsv = render_audit_sheet(items, by_conversation)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in (("audit_sheet.md", sheet), ("audit_key.md", key), ("audit_sheet.tsv", tsv)):
        (out_dir / name).write_text(text, encoding="utf-8")
    return {
        "seed": seed,
        "items": len(items),
        "conversations": len({t["conversation_id"] for _, t, _ in items}),
        "per_stratum": dict(Counter(stratum for stratum, _, _ in items)),
        "files": [str((out_dir / name).relative_to(root))
                  for name in ("audit_sheet.md", "audit_sheet.tsv", "audit_key.md")],
    }
