import unittest

from koimplicit.normalize import build_alias_map, map_qa_answer, parse_mcq, review_queue

CANDS = [{"entity_id": "A", "label": "A"}, {"entity_id": "B", "label": "B"}, {"entity_id": "T1", "label": "name1"}, {"entity_id": "T10", "label": "name2"}]


class McqParsing(unittest.TestCase):
    def test_single_id_ok(self):
        self.assertEqual(parse_mcq("답: T1", CANDS)["predicted_entity_id"], "T1")
        self.assertEqual(parse_mcq("T10", CANDS)["predicted_entity_id"], "T10")

    def test_multiple_ids_invalid(self):
        self.assertEqual(parse_mcq("A 또는 B", CANDS)["parse_status"], "invalid")

    def test_unknown_or_empty_invalid(self):
        self.assertEqual(parse_mcq("Z", CANDS)["parse_status"], "invalid")
        self.assertEqual(parse_mcq("   ", CANDS)["parse_status"], "invalid")

    def test_missing_and_abstain(self):
        self.assertEqual(parse_mcq(None, CANDS)["parse_status"], "missing")
        self.assertEqual(parse_mcq("판단할 수 없습니다.", CANDS)["parse_status"], "abstain")

    def test_structured(self):
        self.assertEqual(parse_mcq('{"entity_id": "B"}', CANDS, structured=True)["predicted_entity_id"], "B")
        self.assertEqual(parse_mcq('```json\n{"entity_id": "T1"}\n```', CANDS, structured=True)["predicted_entity_id"], "T1")
        self.assertEqual(parse_mcq('{"entity_id": null}', CANDS, structured=True)["parse_status"], "abstain")
        self.assertEqual(parse_mcq('{"entity_id": ["A", "B"]}', CANDS, structured=True)["parse_status"], "invalid")
        self.assertEqual(parse_mcq('{"entity_id": "Z"}', CANDS, structured=True)["parse_status"], "invalid")
        self.assertEqual(parse_mcq("not json", CANDS, structured=True)["parse_status"], "invalid")


class QaMapping(unittest.TestCase):
    roster = [{"entity_id": "A", "label": "A"}, {"entity_id": "B", "label": "B"}, {"entity_id": "T1", "label": "name1", "aliases": ["name1", "엄마"]}]

    def test_pronouns_follow_target_speaker(self):
        alias_map = build_alias_map(self.roster, "B")
        self.assertEqual(alias_map["화자"], "B")
        self.assertEqual(alias_map["청자"], "A")
        self.assertEqual(map_qa_answer("화자 자신", self.roster, "B")["predicted_entity_id"], "B")
        self.assertEqual(map_qa_answer("상대방", self.roster, "A")["predicted_entity_id"], "B")

    def test_alias_maps_third_party(self):
        result = map_qa_answer("엄마", self.roster, "A")
        self.assertEqual((result["predicted_entity_id"], result["parse_status"]), ("T1", "ok"))

    def test_multiple_or_none_unmapped(self):
        self.assertEqual(map_qa_answer("name1 아니면 상대방", self.roster, "A")["parse_status"], "unmapped")
        self.assertEqual(map_qa_answer("어떤 사람", self.roster, "A")["parse_status"], "unmapped")
        self.assertEqual(map_qa_answer(None, self.roster, "A")["parse_status"], "missing")

    def test_review_queue_hides_model_and_gold(self):
        rows = [{"item_id": "i1", "condition": "full_qa_subset", "model_label": "model_a", "gold_entity_id": "T1",
                 "parse_status": "unmapped", "raw_text": "x", "roster": self.roster, "target_speaker_label": "A", "payload_hash": "abcdef0123"}]
        queue = review_queue(rows)
        self.assertEqual(len(queue), 1)
        self.assertNotIn("model_label", queue[0])
        self.assertNotIn("gold_entity_id", queue[0])


if __name__ == "__main__":
    unittest.main()
