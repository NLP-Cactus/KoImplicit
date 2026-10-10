"""Parser conventions on a placeholder fixture, plus a regression check on the real release."""

import tempfile
import unittest
from pathlib import Path

from koimplicit.corpus import (find_spoken_release, flatten_targets, flatten_utterances,
                               load_spoken_release, parse_release, person, role_hint,
                               run_parse)

ROOT = Path(__file__).resolve().parents[1]


def sentence(sentence_id, speaker, za=()):
    form = f"s{sentence_id.split('.')[-1]}"
    return {"id": sentence_id, "form": form, "original_form": form, "speaker_id": speaker,
            "word": [], "ZA": list(za)}


def subject(restored, *antecedents, word_id=1):
    return {"predicate": {"form": "s", "sentence_id": "", "word_id": word_id, "begin": 0, "end": 1},
            "ellipsis": [{"restored": {"form": restored, "type": "subject"},
                          "antecedent": [{"form": f, "sentence_id": sid, "begin": 0, "end": len(f)}
                                         for f, sid in antecedents]}]}


DOC = {
    "id": "D1.1",
    "metadata": {"title": "2인 일상 대화", "speaker": [{"id": "A1"}, {"id": "B1"}]},
    "sentence": [
        sentence("D1.1.1.1", "A1"),
        sentence("D1.1.1.2", "A1", [subject("내가", ("나", "D1.1.1.1"))]),          # same speaker
        sentence("D1.1.1.3", "B1", [subject("내가", ("나", "D1.1.1.1"))]),          # other speaker's 나
        sentence("D1.1.1.3.1", "B1", [subject("화자가", ("#", "D1.1.1.1"))]),       # 5-level ID, '#'
        sentence("D1.1.1.4", "A1", [subject("엄마가", ("엄마", "D1.1.1.5"))]),      # future antecedent
        sentence("D1.1.1.5", "A1", [subject("자기가"), subject("선생님께서", word_id=2)]),  # empty antecedent
        sentence("D1.1.1.6", "B1", [subject("내가", ("나", "D1.1.1.1"), ("내", "D1.1.1.3"))]),  # A's 나 and B's 내
    ],
}


class Conventions(unittest.TestCase):
    def setUp(self):
        self.utterances = flatten_utterances(DOC)
        targets, hints = flatten_targets(DOC, self.utterances)
        self.targets = {t["sentence_id"] + f":{t['predicate_word_id']}": t for t in targets}
        self.hints = {t["sentence_id"] + f":{t['predicate_word_id']}": h for t, h in zip(targets, hints)}

    def test_order_labels_and_runs(self):
        self.assertEqual([u["order"] for u in self.utterances], list(range(7)))
        self.assertEqual([u["speaker_label"] for u in self.utterances], list("AABBAAB"))
        self.assertEqual([u["run_index"] for u in self.utterances], [0, 0, 1, 1, 2, 2, 3])

    def test_relations_and_flags(self):
        self.assertEqual(self.targets["D1.1.1.2:1"]["antecedents"][0]["relation"], "earlier")
        self.assertEqual(self.targets["D1.1.1.2:1"]["last_textual_antecedent_distance"], 1)
        deictic = self.targets["D1.1.1.3.1:1"]
        self.assertEqual(deictic["antecedents"][0]["relation"], "none")
        self.assertFalse(deictic["has_textual_antecedent"])
        self.assertTrue(self.targets["D1.1.1.4:1"]["has_future_antecedent"])
        self.assertTrue(self.targets["D1.1.1.5:1"]["antecedent_missing"])

    def test_targets_hide_restored_form(self):
        for target in self.targets.values():
            self.assertNotIn("restored_form", target)

    def test_role_follows_antecedent_speaker(self):
        same = self.hints["D1.1.1.2:1"]
        self.assertEqual((same["hint_category"], same["perspective_conflict"]), ("speaker_pronoun", False))
        crossed = self.hints["D1.1.1.3:1"]
        # B restored 내가 but the 나 was A's: the referent is B's addressee.
        self.assertEqual((crossed["hint_category"], crossed["perspective_conflict"]), ("addressee_pronoun", True))
        self.assertEqual(self.hints["D1.1.1.3.1:1"]["hint_category"], "speaker_deictic")

    def test_conflicting_pronoun_antecedents_are_flagged(self):
        hint = self.hints["D1.1.1.6:1"]
        self.assertTrue(hint["pronoun_antecedent_conflict"])
        self.assertFalse(self.hints["D1.1.1.2:1"]["pronoun_antecedent_conflict"])

    def test_person_ignores_trailing_punctuation(self):
        self.assertEqual(person("나는."), "1p")

    def test_restored_form_fallbacks(self):
        self.assertEqual(self.hints["D1.1.1.5:1"]["hint_category"], "other")  # 자기가
        self.assertEqual(self.hints["D1.1.1.5:2"]["hint_category"], "third_party_relation")

    def test_lexicon_decisions(self):
        def category(form):
            return role_hint(form, [], "A1", ["A1", "B1"], {})["hint_category"]
        self.assertEqual(category("우리 언니가"), "third_party_relation")
        self.assertEqual(category("고모부께서"), "third_party_relation")
        self.assertEqual(category("아이들이"), "generic_or_plural")
        self.assertEqual(category("걔네가"), "generic_or_plural")
        self.assertEqual(category("강아지가"), "other")   # non-human: the filter excludes it
        self.assertEqual(category("연예인이"), "other")   # occupation: a person decides

    def test_output_stays_under_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                run_parse(Path(temporary), ROOT / "missing.json", Path(temporary) / "out")


class ReleaseRegression(unittest.TestCase):
    """Guide §1.4 numbers. Skipped when the licensed corpus is not on this machine."""

    def test_guide_numbers(self):
        try:
            path = find_spoken_release(ROOT)
        except FileNotFoundError:
            self.skipTest("ZA 2025 spoken JSON not under data/raw")
        _, _, _, report = parse_release(load_spoken_release(path))
        expected = {
            "documents": 75, "sentences": 16439, "predicates": 18535, "ellipses": 24871,
            "speaker_not_in_roster": 0, "documents_with_id_order_mismatch": 0,
            "predicate_offset_mismatch": 0, "antecedent_offset_mismatch": 0,
            "form_differs": 3597, "empty_antecedent": 5, "multi_antecedent": 2616,
            "subject_targets": 16838, "duplicate_target_ids": 0, "perspective_conflict": 352,  # 347 before punctuation-stripped pronouns
        }
        self.assertEqual({key: report[key] for key in expected}, expected)


if __name__ == "__main__":
    unittest.main()
