import json
import tempfile
import unittest
from pathlib import Path

from koimplicit import runner
from koimplicit.baselines import fit_majority_role, majority_role_prior, most_recent_entity_oracle, most_recent_explicit_np
from koimplicit.providers import get_adapter

PROMPT = {"version": "test_v0", "slots": list(runner.PROMPT_SLOTS),
          "template": "{dialogue}|{target_utterance}|{target_marker}|{target_speaker_label}|{candidates}|{output_schema}"}
CONFIG = {"model_id": "unset", "model_label": "model_a", "decoding": {"temperature": 0}, "output_schema": "{}", "seed": 1}


def item(item_id="i1", **extra):
    base = {"item_id": item_id, "conversation_id": "c1", "split": "development",
            "full_text": "A: 문장1\nB: 문장2", "local_text": "B: 문장2", "target_marker": {"form": "문장2", "begin": 3, "end": 6},
            "target_speaker_label": "B", "candidates": [{"entity_id": "A", "label": "A", "role": "addressee"}, {"entity_id": "B", "label": "B", "role": "speaker"}, {"entity_id": "T1", "label": "name1", "role": "third_party", "aliases": ["name1"]}],
            "gold_entity_id": "B"}
    base.update(extra)
    return base


class FlakyAdapter:
    def __init__(self, fail_times=0, permanent=False):
        self.fail_times, self.permanent, self.calls = fail_times, permanent, 0

    def complete(self, request):
        self.calls += 1
        if self.permanent:
            raise runner.PermanentError("401")
        if self.calls <= self.fail_times:
            raise runner.TransientError("timeout")
        return {"raw_text": "B", "input_tokens": 10, "output_tokens": 1, "latency_ms": 5, "finish_reason": "stop"}


class RequestBuilding(unittest.TestCase):
    def test_build_request_rejects_gold(self):
        with self.assertRaises(ValueError):
            runner.build_request(item(), "full_mcq", PROMPT, CONFIG)

    def test_conditions_select_text_and_candidates(self):
        clean = runner.strip_gold(item())
        full = runner.build_request(clean, "full_mcq", PROMPT, CONFIG)
        local = runner.build_request(clean, "local_mcq", PROMPT, CONFIG)
        qa = runner.build_request(clean, "full_qa_subset", PROMPT, CONFIG)
        self.assertIn("A: 문장1", full["user"])
        self.assertNotIn("A: 문장1", local["user"])
        self.assertIn("T1: name1", full["user"])
        self.assertNotIn("T1: name1", qa["user"])
        self.assertNotIn("role", full["user"])

    def test_payload_hash_stable_and_sensitive(self):
        clean = runner.strip_gold(item())
        a = runner.payload_hash(runner.build_request(clean, "full_mcq", PROMPT, CONFIG))
        b = runner.payload_hash(runner.build_request(clean, "full_mcq", PROMPT, CONFIG))
        c = runner.payload_hash(runner.build_request(clean, "local_mcq", PROMPT, CONFIG))
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_unapproved_prompt_cannot_render(self):
        with self.assertRaises(runner.PromptNotApproved):
            runner.render_prompt({"version": "v", "slots": ["dialogue"], "template": ""}, {"dialogue": "x"})

    def test_prompt_validation_reports_slot_mismatch(self):
        problems = runner.validate_prompt({"version": "v", "slots": ["dialogue"], "template": "{dialogue} {other}"})
        self.assertEqual(len(problems), 1)
        self.assertEqual(runner.validate_prompt(PROMPT), [])

    def test_repository_prompt_files_load(self):
        from koimplicit.generate import GENERATE_SLOTS
        root = Path(__file__).resolve().parents[1] / "prompts"
        for path in root.glob("*.json"):
            slots = GENERATE_SLOTS if path.name.startswith("generate") else runner.PROMPT_SLOTS
            prompt = runner.load_prompt(path, allowed_slots=slots)
            self.assertTrue(prompt["template"].strip(), f"{path.name} template is empty")
            self.assertEqual(runner.validate_prompt(prompt), [], path.name)
            self.assertNotIn("role", prompt["template"].lower())

    def test_target_only_condition_uses_local_text(self):
        clean = runner.strip_gold(item())
        req = runner.build_request(clean, "target_only_mcq", PROMPT, CONFIG)
        self.assertNotIn("A: 문장1", req["user"])
        self.assertEqual(req["candidate_ids"], ["A", "B", "T1"])
        self.assertEqual(runner.build_request(clean, "full_qa", PROMPT, CONFIG)["candidate_ids"], [])


class Retry(unittest.TestCase):
    def test_transient_retried_twice_then_missing(self):
        adapter = FlakyAdapter(fail_times=2)
        response, retries, error = runner.call_with_retry(adapter, {}, sleep=lambda s: None)
        self.assertEqual((retries, error), (2, None))
        self.assertEqual(response["raw_text"], "B")
        adapter = FlakyAdapter(fail_times=3)
        response, retries, error = runner.call_with_retry(adapter, {}, sleep=lambda s: None)
        self.assertIsNone(response)
        self.assertEqual(retries, 2)
        self.assertEqual(adapter.calls, 3)

    def test_permanent_not_retried(self):
        adapter = FlakyAdapter(permanent=True)
        response, retries, error = runner.call_with_retry(adapter, {}, sleep=lambda s: None)
        self.assertIsNone(response)
        self.assertEqual((retries, adapter.calls), (0, 1))


class RunRecords(unittest.TestCase):
    def test_run_writes_records_and_uses_cache(self):
        items = [item("i1"), item("i2", gold_entity_id="A", local_text="B: 문장3", full_text="A: 문장1\nB: 문장3")]
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            adapter = FlakyAdapter()
            summary = runner.run_items(items, ["full_mcq", "local_mcq"], adapter, PROMPT, CONFIG, run_dir, seed=1, sleep=lambda s: None)
            self.assertEqual(summary["ok"], 4)
            self.assertEqual(adapter.calls, 4)
            config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["prompt_version"], "test_v0")
            responses = [json.loads(l) for l in (run_dir / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(responses), 4)
            self.assertTrue(all("gold_entity_id" not in r for r in responses))
            again = runner.run_items(items, ["full_mcq", "local_mcq"], adapter, PROMPT, CONFIG, run_dir, seed=1, sleep=lambda s: None)
            self.assertEqual(again["cached"], 4)
            self.assertEqual(adapter.calls, 4)

    def test_dry_provider_records_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = get_adapter("dry")
            summary = runner.run_items([item()], ["full_mcq"], adapter, PROMPT, CONFIG, Path(tmp) / "run", sleep=lambda s: None)
            self.assertEqual(summary["missing"], 1)
            self.assertEqual(adapter.requests[0]["item_id"], "i1")


class Baselines(unittest.TestCase):
    def test_majority_role_prior_fixed_on_development(self):
        dev = [{"gold_entity_id": "B", "entity_roles": {"B": "speaker", "A": "addressee"}} for _ in range(3)]
        dev.append({"gold_entity_id": "A", "entity_roles": {"B": "speaker", "A": "addressee"}})
        fitted = fit_majority_role(dev)
        self.assertEqual(fitted["majority_role"], "speaker")
        self.assertEqual(majority_role_prior(item(), fitted)["predicted_entity_id"], "B")
        third = fit_majority_role([{"gold_entity_id": "T1", "entity_roles": {"T1": "third_party"}}])
        self.assertEqual(majority_role_prior(item(full_text="A: name1 문장"), third)["predicted_entity_id"], "T1")

    def test_most_recent_np_and_oracle(self):
        self.assertEqual(most_recent_explicit_np(item(full_text="A: name1 문장"))["predicted_entity_id"], "T1")
        self.assertEqual(most_recent_explicit_np(item())["parse_status"], "unmapped")
        oracle_item = item(mentions=[{"position": 0, "entity_id": "A"}, {"position": 5, "entity_id": "T1"}, {"position": 9, "entity_id": "B"}], target_position=7)
        self.assertEqual(most_recent_entity_oracle(oracle_item)["predicted_entity_id"], "T1")


if __name__ == "__main__":
    unittest.main()
