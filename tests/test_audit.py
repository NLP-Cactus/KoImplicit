"""Check audit counting on a synthetic corpus with placeholder text."""

import json
import tempfile
import unittest
from pathlib import Path

from koimplicit.audit import audit, person, render_audit_sheet, run_audit, sample_audit_items
from koimplicit.corpus import flatten_targets, flatten_utterances


def sentence(number, speaker, za=()):
    return {"id": f"D1.1.1.{number}", "form": f"s{number}", "original_form": f"s{number}",
            "speaker_id": speaker, "ZA": list(za)}


def subject(restored, antecedent_form, antecedent_number):
    antecedent_id = "D1.1.1.0" if antecedent_number is None else f"D1.1.1.{antecedent_number}"
    return {"predicate": {"form": "s", "word_id": 1, "begin": 0, "end": 1},
            "ellipsis": [{"restored": {"form": restored, "type": "subject"},
                          "antecedent": [{"form": antecedent_form, "sentence_id": antecedent_id}]}]}


CORPUS = {"document": [{
    "id": "D1.1",
    "metadata": {"title": "2인 일상 대화", "speaker": [{"id": "A"}, {"id": "B"}]},
    "sentence": [
        sentence(1, "A"),
        sentence(2, "A", [subject("내가", "나", 1)]),
        sentence(3, "B", [subject("내가", "나", 1)]),
        sentence(4, "B", [subject("화자가", "#", None)]),
        sentence(5, "A", [subject("누군가가", "#", None)]),
    ],
}]}


class AuditCheck(unittest.TestCase):
    def test_person(self):
        self.assertEqual(person("내가"), "1p")
        self.assertEqual(person("넌"), "2p")
        self.assertEqual(person("제품들이"), "other")

    def test_counts(self):
        report = audit(CORPUS)
        self.assertEqual(report["two_party_dialogues"], 1)
        self.assertEqual(report["speaker_runs"], 3)
        self.assertEqual(report["adjacent_same_speaker_ratio"], 0.5)
        self.assertEqual(report["subject_categories"],
                         {"participant_pronoun": 2, "participant_label": 1, "nonreferential": 1})
        self.assertEqual(report["person_cross_tab"], {"1p<-1p|cross": 1, "1p<-1p|same": 1})
        self.assertEqual(report["cross_speaker_pronoun_links"], 1)
        self.assertEqual(report["_cases"][0]["sentence_id"], "D1.1.1.3")

    def test_cases_stay_under_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "corpus.json"
            corpus.write_text(json.dumps(CORPUS, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                run_audit(root, corpus, root / "cases.json")
            report = run_audit(root, corpus, root / "data" / "interim" / "cases.json")
            self.assertEqual(report["cases_file"], str(Path("data/interim/cases.json")))
            self.assertNotIn("_cases", report)


class AuditSheetCheck(unittest.TestCase):
    def setUp(self):
        self.utterances = flatten_utterances(CORPUS["document"][0])
        self.targets, self.hints = flatten_targets(CORPUS["document"][0], self.utterances)

    def test_sampling_is_stratified_and_repeatable(self):
        strata = (("perspective_conflict", 1), ("speaker", 2))
        first = sample_audit_items(self.utterances, self.targets, self.hints, 7, strata)
        again = sample_audit_items(self.utterances, self.targets, self.hints, 7, strata)
        self.assertEqual([t["target_id"] for _, t, _ in first], [t["target_id"] for _, t, _ in again])
        self.assertEqual([s for s, _, _ in first], ["perspective_conflict", "speaker"])  # one dialogue: cap 2

    def test_sheet_hides_answers(self):
        items = sample_audit_items(self.utterances, self.targets, self.hints, 7, (("speaker", 1),))
        sheet, key, tsv = render_audit_sheet(items, {"D1.1": self.utterances})
        self.assertIn("[[", sheet)
        self.assertNotIn("내가", sheet)  # restored form only in the key
        self.assertIn("내가", key)
        self.assertEqual(len(tsv.strip().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
