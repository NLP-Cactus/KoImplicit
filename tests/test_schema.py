"""스키마 검증과 파생 변수 계산. fixture는 짧은 자리표시 대화를 쓴다."""

import tempfile
import unittest
from pathlib import Path

from koimplicit.schema import DialogueRecord, LabelRecord, Participant, Turn, build_sample, derive, load_dataset, save_dataset

PARTS = [Participant(entity_id="P1", name="가"), Participant(entity_id="P2", name="나"),
         Participant(entity_id="T1", name="다", aliases=["다 선배"], in_dialogue=False), Participant(entity_id="T2", name="라", in_dialogue=False)]


def record(texts, target_turn=None, predicate="문장", **extra):
    turns = [Turn(turn_index=i, speaker_id=s, text=t) for i, (s, t) in enumerate(texts, start=1)]
    target_turn = target_turn or len(turns)
    base = dict(sample_id="x1", dataset="controlled", scenario_id="SX", participants=PARTS, dialogue=turns,
                speaker_id=turns[target_turn - 1].speaker_id, target_turn=target_turn, target_predicate=predicate, creation_method="human_authored")
    base.update(extra)
    return DialogueRecord(**base)


class SchemaRules(unittest.TestCase):
    def test_predicate_must_occur_once(self):
        with self.assertRaises(ValueError):
            record([("P1", "문장 문장"), ("P2", "문장 문장")])
        rec = record([("P1", "앞 문장"), ("P2", "뒤 문장")], predicate="뒤 문장")
        self.assertEqual(rec.target_predicate_span, (0, 4))

    def test_entity_id_not_in_text(self):
        with self.assertRaises(ValueError):
            record([("P1", "P1이 말함"), ("P2", "문장")])

    def test_speaker_consistency(self):
        with self.assertRaises(ValueError):
            record([("P1", "문장"), ("P2", "문장")], speaker_id="P1")
        with self.assertRaises(ValueError):
            record([("T1", "문장"), ("P2", "문장")])

    def test_turn_bounds(self):
        with self.assertRaises(ValueError):
            record([("P1", "문장")])
        with self.assertRaises(ValueError):
            record([("P1", "문장")] * 7)

    def test_label_consistency(self):
        with self.assertRaises(ValueError):
            LabelRecord(sample_id="x1", anchor_turn=1)
        with self.assertRaises(ValueError):
            LabelRecord(sample_id="x1", gold_referent_id=None, annotation_status="accepted", ambiguity_status="unambiguous")
        with self.assertRaises(ValueError):
            LabelRecord(sample_id="x1", gold_referent_id=None, ambiguity_status="unambiguous")


class Derivation(unittest.TestCase):
    def test_roles_relative_to_target_speaker(self):
        rec = record([("P1", "다 왔어?"), ("P2", "문장")])
        self.assertEqual(derive(rec, LabelRecord(sample_id="x1", gold_referent_id="P2")).gold_referent_role, "speaker")
        self.assertEqual(derive(rec, LabelRecord(sample_id="x1", gold_referent_id="P1")).gold_referent_role, "addressee")
        self.assertEqual(derive(rec, LabelRecord(sample_id="x1", gold_referent_id="T1")).gold_referent_role, "third_party")

    def test_shift_variables_separate_speaker_and_referent(self):
        rec = record([("P1", "다 왔어?"), ("P2", "문장")])
        d = derive(rec, LabelRecord(sample_id="x1", gold_referent_id="T1", anchor_turn=1, anchor_referent_id="T1"))
        self.assertEqual((d.speaker_changed, d.referent_changed, d.referent_role_changed), (True, False, False))
        d = derive(rec, LabelRecord(sample_id="x1", gold_referent_id="P2", anchor_turn=1, anchor_referent_id="P2"))
        # 같은 사람(P2)이 1번 발화 기준 청자 → 2번 발화 기준 화자: entity 유지, role 변경
        self.assertEqual((d.referent_changed, d.referent_role_changed, d.anchor_referent_role), (False, True, "addressee"))

    def test_shift_is_none_without_anchor(self):
        rec = record([("P1", "문장 하나"), ("P2", "문장")])
        d = derive(rec, LabelRecord(sample_id="x1", gold_referent_id="T1"))
        self.assertIsNone(d.speaker_changed)
        self.assertIsNone(d.referent_changed)

    def test_distance_and_distractor(self):
        rec = record([("P1", "다 선배가 왔어"), ("P2", "라도 왔어"), ("P1", "그래서 문장")], predicate="문장")
        d = derive(rec, LabelRecord(sample_id="x1", gold_referent_id="T1"))
        self.assertEqual((d.gold_last_mention_turn, d.turn_distance), (1, 2))
        self.assertEqual(d.most_recent_mentioned_id, "T2")
        self.assertTrue(d.distractor_present)
        d = derive(rec, LabelRecord(sample_id="x1", gold_referent_id="T2"))
        self.assertFalse(d.distractor_present)
        d = derive(rec, LabelRecord(sample_id="x1", gold_referent_id="T1", distractor_id="P2"))
        self.assertFalse(d.distractor_present)  # 지정 distractor가 텍스트에 없음

    def test_mentions_stop_at_predicate(self):
        rec = record([("P1", "문장"), ("P2", "라 문장 다")], predicate="문장")
        d = derive(rec, LabelRecord(sample_id="x1", gold_referent_id="T1"))
        self.assertEqual(d.most_recent_mentioned_id, "T2")
        self.assertIsNone(d.turn_distance)

    def test_three_party_addressee_unknown_gives_none_role(self):
        parts = PARTS + [Participant(entity_id="P3", name="마")]
        turns = [Turn(turn_index=1, speaker_id="P1", text="문장 하나"), Turn(turn_index=2, speaker_id="P3", text="문장 둘"), Turn(turn_index=3, speaker_id="P2", text="문장")]
        rec = DialogueRecord(sample_id="x1", dataset="controlled", scenario_id="SX", participants=parts, dialogue=turns, speaker_id="P2",
                             target_turn=3, target_predicate="문장", creation_method="human_authored")
        self.assertIsNone(derive(rec, LabelRecord(sample_id="x1", gold_referent_id="P1")).gold_referent_role)
        self.assertEqual(derive(rec, LabelRecord(sample_id="x1", gold_referent_id="P1", addressee_id="P1")).gold_referent_role, "addressee")
        self.assertEqual(derive(rec, LabelRecord(sample_id="x1", gold_referent_id="P3", addressee_id="P1")).gold_referent_role, "third_party")


class DatasetIO(unittest.TestCase):
    def test_roundtrip_and_missing_label(self):
        rec = record([("P1", "다 왔어?"), ("P2", "문장")], pair_ids=["SX:base~v"])
        s = build_sample(rec, LabelRecord(sample_id="x1", gold_referent_id="T1"))
        self.assertEqual(s.record.pair_id, "SX:base~v")
        with tempfile.TemporaryDirectory() as tmp:
            save_dataset([s], Path(tmp))
            loaded = load_dataset(Path(tmp))
            self.assertEqual(loaded[0].flat()["gold_referent_role"], "third_party")
            (Path(tmp) / "labels.jsonl").write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_dataset(Path(tmp))


if __name__ == "__main__":
    unittest.main()
