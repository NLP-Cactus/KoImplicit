import unittest

from koimplicit.bootstrap import cluster_bootstrap, condition_difference, paired_item_difference, percentile
from koimplicit.metrics import entity_accuracy


def row(item, cluster, correct, condition="full_mcq"):
    return {"item_id": item, "conversation_id": cluster, "condition": condition, "model_label": "m",
            "gold_entity_id": "e1", "predicted_entity_id": "e1" if correct else "e2", "parse_status": "ok"}


class Bootstrap(unittest.TestCase):
    def test_single_cluster_ci_equals_point(self):
        rows = [row("i1", "c1", True), row("i2", "c1", False)]
        result = cluster_bootstrap(rows, "conversation_id", entity_accuracy, n_boot=50, seed=1)
        self.assertEqual((result["point"], result["ci_low"], result["ci_high"]), (0.5, 0.5, 0.5))
        self.assertEqual(result["n_clusters"], 1)

    def test_same_seed_same_result_and_ci_contains_point(self):
        rows = [row(f"i{i}", f"c{i % 5}", i % 3 == 0) for i in range(30)]
        a = cluster_bootstrap(rows, "conversation_id", entity_accuracy, n_boot=200, seed=7)
        b = cluster_bootstrap(rows, "conversation_id", entity_accuracy, n_boot=200, seed=7)
        self.assertEqual(a, b)
        self.assertLessEqual(a["ci_low"], a["point"])
        self.assertGreaterEqual(a["ci_high"], a["point"])
        self.assertEqual(a["n_clusters"], 5)

    def test_condition_difference_in_same_resample(self):
        rows = []
        for i in range(10):
            rows.append(row(f"i{i}", f"c{i % 2}", True, "full_mcq"))
            rows.append(row(f"i{i}", f"c{i % 2}", False, "local_mcq"))
        stat = condition_difference(entity_accuracy, "full_mcq", "local_mcq")
        result = cluster_bootstrap(rows, "conversation_id", stat, n_boot=100, seed=3)
        self.assertEqual((result["point"], result["ci_low"], result["ci_high"]), (1.0, 1.0, 1.0))
        paired = cluster_bootstrap(rows, "conversation_id", paired_item_difference("full_mcq", "local_mcq"), n_boot=100, seed=3)
        self.assertEqual(paired["point"], 1.0)

    def test_undefined_resamples_are_counted(self):
        rows = [row("i1", "c1", True, "full_mcq"), row("i2", "c2", True, "local_mcq")]
        stat = condition_difference(entity_accuracy, "full_mcq", "local_mcq")
        result = cluster_bootstrap(rows, "conversation_id", stat, n_boot=100, seed=0)
        self.assertGreater(result["n_undefined"], 0)

    def test_missing_cluster_key_raises(self):
        with self.assertRaises(KeyError):
            cluster_bootstrap([{"item_id": "x"}], "conversation_id", entity_accuracy, n_boot=1)

    def test_percentile_interpolates(self):
        self.assertEqual(percentile([0.0, 1.0], 0.5), 0.5)
        self.assertEqual(percentile([3.0], 0.975), 3.0)


if __name__ == "__main__":
    unittest.main()
