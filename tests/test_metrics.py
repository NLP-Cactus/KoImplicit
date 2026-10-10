"""지표 계산 검사. 더미 레이블 표만 쓰고 대화 텍스트는 만들지 않는다."""

import unittest

from koimplicit import metrics as m


def row(item, pred, gold="e1", status="ok", **extra):
    base = {"item_id": item, "condition": "full_mcq", "model_label": "model_a", "gold_entity_id": gold,
            "predicted_entity_id": pred, "parse_status": status,
            "entity_roles": {"e1": "speaker", "e2": "addressee", "e3": "third_party", "e4": "third_party"},
            "candidates": [{"entity_id": "e1"}, {"entity_id": "e2"}, {"entity_id": "e3"}, {"entity_id": "e4"}],
            "conversation_id": "c1"}
    base.update(extra)
    return base


class EntityMetrics(unittest.TestCase):
    def test_accuracy_counts_only_ok_rows(self):
        rows = [row("i1", "e1"), row("i2", "e2"), row("i3", "e1", status="invalid"), row("i4", None, status="abstain"), row("i5", None, status="missing")]
        result = m.entity_accuracy(rows)
        self.assertEqual((result.numerator, result.denominator), (1, 5))
        self.assertEqual(m.status_counts(rows), {"ok": 2, "invalid": 1, "abstain": 1, "missing": 1, "unmapped": 0})

    def test_empty_denominator_gives_none(self):
        self.assertIsNone(m.entity_accuracy([]).value)
        self.assertIsNone(m.pair_accuracy([]).value)

    def test_role_accuracy_and_same_role_wrong_entity(self):
        rows = [row("i1", "e1"), row("i2", "e4", gold="e3"), row("i3", "e2", gold="e3")]
        self.assertEqual(m.role_accuracy(rows).numerator, 2)
        self.assertEqual(m.same_role_wrong_entity_rate(rows).numerator, 1)

    def test_chance_level_uses_candidate_count(self):
        rows = [row("i1", "e1"), row("i2", "e1", candidates=[{"entity_id": "e1"}, {"entity_id": "e2"}])]
        self.assertAlmostEqual(m.chance_level(rows).value, (0.25 + 0.5) / 2)

    def test_paired_condition_difference_uses_common_items(self):
        rows = [row("i1", "e1", condition="full_mcq"), row("i1", "e2", condition="local_mcq"),
                row("i2", "e1", condition="full_mcq"), row("i3", "e1", condition="local_mcq")]
        result = m.paired_condition_difference(rows, "full_mcq", "local_mcq")
        self.assertEqual((result.value, result.denominator), (1.0, 1))


class PairMetrics(unittest.TestCase):
    def pair_rows(self):
        return [
            row("p1a", "e1", pair_id="p1", family_id="f1", version="early"), row("p1b", "e2", pair_id="p1", family_id="f1", version="late", designated_distractor_id="e2"),
            row("p2a", "e1", pair_id="p2", family_id="f1", version="early"), row("p2b", "e1", pair_id="p2", family_id="f1", version="late"),
            row("p3a", "e3", pair_id="p3", family_id="f2", version="early"), row("p3b", "e1", pair_id="p3", family_id="f2", version="late"),
            row("p4a", "e1", pair_id="p4", family_id="f2", version="early"),
        ]

    def test_pairs_drop_incomplete_and_count_transitions(self):
        pairs, dropped = m.build_pairs(self.pair_rows(), "early", "late")
        self.assertEqual(dropped, ["p4"])
        self.assertEqual(len(pairs), 3)
        self.assertEqual(m.pair_accuracy(pairs).numerator, 1)
        self.assertEqual(m.paired_harm(pairs).numerator, 1)
        self.assertEqual(m.paired_recovery(pairs).numerator, 1)
        self.assertEqual(m.pair_transition_counts(pairs), {"both_correct": 1, "correct_to_wrong": 1, "wrong_to_correct": 1, "both_wrong": 0})

    def test_missing_side_counts_as_wrong_not_dropped(self):
        rows = [row("a", "e1", pair_id="p", family_id="f", version="early"), row("b", None, status="missing", pair_id="p", family_id="f", version="late")]
        pairs, dropped = m.build_pairs(rows, "early", "late")
        self.assertEqual(dropped, [])
        self.assertEqual((pairs[0].c1, pairs[0].c2), (1, 0))

    def test_controlled_summary_reports_families_and_distractor(self):
        summary = m.controlled_summary(self.pair_rows(), "early", "late")
        self.assertEqual(summary["n_pairs"], 3)
        self.assertEqual(summary["n_families"], 2)
        self.assertEqual(summary["distractor_rate_by_version"]["late"]["numerator"], 1)


if __name__ == "__main__":
    unittest.main()
