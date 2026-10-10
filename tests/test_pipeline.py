"""검증·변형·payload·벤치마크·기준선·생성·주석을 Pilot v0와 mock provider로 끝까지 돌린다. 네트워크 없음."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from koimplicit import annotation as A
from koimplicit.baselines import current_addressee, current_speaker, most_recent_entity
from koimplicit.benchmark import estimate_cost, join_gold, load_model_config, run_baselines, run_benchmark
from koimplicit.generate import generate_drafts, load_generation_prompt
from koimplicit.metrics import benchmark_summary, confusion_matrix, distractor_error_rate, pair_consistency
from koimplicit.payload import build_payload, to_gold, to_item
from koimplicit.providers import get_adapter
from koimplicit.runner import GOLD_KEYS, load_prompt
from koimplicit.scenarios import load_scenarios
from koimplicit.schema import load_dataset
from koimplicit.validate import check_duplicates, check_leakage, validate_samples
from koimplicit.variations import pair_manifest

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "pilot_v0"
SCENARIOS = ROOT / "datasets" / "scenarios" / "pilot_v0.jsonl"
PROMPT = ROOT / "prompts" / "mcq_v1.json"


class PilotDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = load_dataset(DATASET)
        cls.scenarios = load_scenarios(SCENARIOS)

    def test_pilot_validates_without_errors(self):
        report = validate_samples(self.samples, self.scenarios, PROMPT)
        self.assertEqual(report["n_errors"], 0, [i for i in report["issues"] if i["level"] == "error"])
        self.assertEqual(report["n_samples"], 20)
        roles = report["balance"]["by_role"]
        self.assertTrue(all(roles.get(r, 0) > 0 for r in ("speaker", "addressee", "third_party")))
        self.assertEqual(set(report["balance"]["by_referent_changed"]) >= {"True", "False"}, True)
        self.assertTrue({"True", "False"} <= set(report["balance"]["by_distractor_present"]))
        self.assertEqual(report["balance"]["by_distractor_present"].get("None", 0), 1)  # gold 없는 S03-novocative
        self.assertEqual(report["balance"]["by_annotation_status"], {"candidate": 20})

    def test_every_sample_flagged_for_human_review(self):
        report = validate_samples(self.samples, self.scenarios, PROMPT)
        flagged = {i["sample_id"] for i in report["issues"] if i["code"] == "HUMAN_REVIEW"}
        self.assertEqual(flagged, {s.sample_id for s in self.samples})

    def test_pairs_report_unclaimed_differences(self):
        manifest = pair_manifest(self.samples)
        self.assertEqual(manifest["problems"], [])
        by_id = {p["pair_id"]: p for p in manifest["pairs"]}
        self.assertTrue(by_id["S01:base~distractor"]["is_single_variable_pair"])
        self.assertTrue(by_id["S01:distractor~shift"]["observed_gold_change"])
        self.assertFalse(by_id["S02:base~speaker"]["is_single_variable_pair"])  # 구조를 바꿔야 해 compound
        self.assertFalse(by_id["S03:base~novocative"]["evaluable"])

    def test_duplicate_detection(self):
        twin = self.samples[0].model_copy(deep=True)
        twin.record.sample_id = twin.label.sample_id = "dup"
        self.assertTrue(any(i["code"] == "DUPLICATE_SAMPLE" for i in check_duplicates([self.samples[0], twin])))


class Payload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = load_dataset(DATASET)

    def test_item_has_no_gold_and_ends_at_target(self):
        for s in self.samples:
            item = to_item(s, seed=1)
            self.assertFalse(any(k in item for k in GOLD_KEYS))
            self.assertEqual(item["full_text"].count("\n") + 1, s.record.target_turn)
            self.assertNotIn("role", json.dumps(item, ensure_ascii=False))
        self.assertEqual(check_leakage(self.samples, PROMPT), [])

    def test_neutral_ids_fixed_within_family(self):
        from koimplicit.payload import neutral_id_map
        by_id = {s.sample_id: s for s in self.samples}
        a, b = neutral_id_map(by_id["S01-base"], 3), neutral_id_map(by_id["S01-shift"], 3)
        self.assertEqual(a, b)
        self.assertNotEqual(a, neutral_id_map(by_id["S01-base"], 4))
        item = to_item(by_id["S01-base"], 3)
        self.assertEqual([c["entity_id"] for c in item["candidates"]], ["E1", "E2", "E3", "E4"])
        self.assertNotIn("P1", json.dumps(item, ensure_ascii=False))
        gold = to_gold(by_id["S01-base"], 3)
        self.assertEqual(gold["id_map"][gold["gold_entity_id"]], "T1")

    def test_build_payload_skips_unreviewed_and_ambiguous(self):
        items, gold, skipped = build_payload(self.samples)
        self.assertEqual(items, [])
        items, gold, skipped = build_payload(self.samples, include_unreviewed=True)
        self.assertEqual(len(items), 19)
        self.assertEqual(len(skipped), 1)
        self.assertEqual({g["item_id"] for g in gold}, {i["item_id"] for i in items})
        self.assertIn("entity_roles", gold[0])


class Benchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = load_dataset(DATASET)
        cls.items, cls.gold, _ = build_payload(cls.samples, include_unreviewed=True)
        cls.prompt = load_prompt(PROMPT)

    def test_mock_benchmark_end_to_end(self):
        model = load_model_config(ROOT / "configs" / "models.json", "mock")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):  # 검수 전 표본은 명시적 허용 없이는 평가하지 않는다
                run_benchmark(self.items, self.gold, ["full_mcq"], get_adapter("mock"), self.prompt, model, Path(tmp), seed=1, sleep=lambda s: None)
            with self.assertRaises(ValueError):
                run_benchmark(self.items, self.gold, ["full_mcq", "typo"], get_adapter("mock"), self.prompt, model, Path(tmp), seed=1, sleep=lambda s: None, allow_unreviewed=True)
            report = run_benchmark(self.items, self.gold, ["full_mcq", "target_only_mcq"], get_adapter("mock"), self.prompt, model, Path(tmp), seed=1, sleep=lambda s: None, allow_unreviewed=True)
            self.assertEqual(report["run"]["ok"], 38)
            self.assertTrue(report["contains_unreviewed"])
            m = report["metrics"]["by_model_condition"]["mock|full_mcq"]
            self.assertEqual(m["overall_accuracy"]["denominator"], 19)
            self.assertIn("third_party", m["by_referent_type"])
            self.assertIn("role_confusion", m)
            self.assertIn("mock", report["metrics"]["context_benefit"])
            self.assertTrue((Path(tmp) / "per_sample.csv").exists())
            with (Path(tmp) / "per_sample.csv").open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 38)
            config = json.loads((Path(tmp) / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["prompt_version"], "mcq_v1")
            # 재실행은 캐시만 쓰고 채점 행·pair 분모가 그대로여야 한다
            again = run_benchmark(self.items, self.gold, ["full_mcq", "target_only_mcq"], get_adapter("mock"), self.prompt, model, Path(tmp), seed=1, sleep=lambda s: None, allow_unreviewed=True)
            self.assertEqual(again["run"]["cached"], 38)
            m2 = again["metrics"]["by_model_condition"]["mock|full_mcq"]
            self.assertEqual((m2["n_rows"], m2["pair_consistency"]["n_pairs"]), (m["n_rows"], m["pair_consistency"]["n_pairs"]))
            self.assertEqual(m2["overall_accuracy"], m["overall_accuracy"])
            # 다른 설정으로 같은 run_dir 재사용은 거부
            with self.assertRaises(ValueError):
                run_benchmark(self.items, self.gold, ["full_mcq"], get_adapter("mock"), self.prompt, {**model, "model_id": "other"}, Path(tmp), seed=1, sleep=lambda s: None, allow_unreviewed=True)

    def test_mock_is_deterministic_and_hides_gold(self):
        adapter = get_adapter("mock")
        from koimplicit.runner import build_request
        req = build_request(self.items[0], "full_mcq", self.prompt, {"model_id": "m", "output_schema": "{}"})
        self.assertEqual(req["output_schema"], "{}")
        self.assertNotIn("gold", json.dumps(req, ensure_ascii=False).lower())
        self.assertEqual(adapter.complete(req)["raw_text"], adapter.complete(req)["raw_text"])

    def test_metrics_helpers(self):
        gold = {g["item_id"]: g for g in self.gold}
        base_gold, dis_gold = gold["S01-base"]["gold_entity_id"], gold["S01-distractor"]["designated_distractor_id"]
        pid = "S01:base~distractor"
        rows = join_gold([
            {"item_id": "S01-base", "condition": "c", "model_label": "m", "predicted_entity_id": base_gold, "parse_status": "ok", "pair_ids": [pid], "pair_id": pid, "version": "base"},
            {"item_id": "S01-distractor", "condition": "c", "model_label": "m", "predicted_entity_id": dis_gold, "parse_status": "ok", "pair_ids": [pid], "pair_id": pid, "version": "distractor"},
        ], [gold["S01-base"], gold["S01-distractor"]])
        pc = pair_consistency(rows)
        self.assertEqual(pc["transitions"], {"both_correct": 0, "base_correct_only": 1, "variant_correct_only": 0, "both_wrong": 0})
        self.assertEqual(pc["paired_harm"]["numerator"], 1)
        self.assertEqual(distractor_error_rate(rows).as_dict(), {"value": 1.0, "numerator": 1, "denominator": 1})
        self.assertEqual(confusion_matrix(rows)["third_party"], {"third_party": 2})
        with self.assertRaises(ValueError):
            join_gold(rows, [])
        self.assertEqual(estimate_cost(rows, {"input": 1.0, "output": 2.0})["estimated_cost_usd"], 0.0)
        summary = benchmark_summary(rows)
        self.assertEqual(summary["by_model_condition"]["m|c"]["overall_accuracy"]["numerator"], 1)

    def test_baselines(self):
        by_id = {i["item_id"]: i for i in self.items}
        gold = {g["item_id"]: g for g in self.gold}

        def orig(item_id, neutral):
            return gold[item_id]["id_map"][neutral]
        self.assertEqual(orig("S01-distractor", most_recent_entity(by_id["S01-distractor"])["predicted_entity_id"]), "T2")
        self.assertEqual(orig("S01-base", most_recent_entity(by_id["S01-base"])["predicted_entity_id"]), "T1")
        self.assertEqual(orig("N03-01", most_recent_entity(by_id["N03-01"])["predicted_entity_id"]), "T2")  # 형수님 > 형
        self.assertEqual(orig("S02-speaker", current_speaker(by_id["S02-speaker"])["predicted_entity_id"]), "P1")
        self.assertEqual(orig("S02-addressee", current_addressee(by_id["S02-addressee"])["predicted_entity_id"]), "P2")
        self.assertEqual(orig("N02-01", current_addressee(by_id["N02-01"])["predicted_entity_id"]), "P3")  # 직전 화자
        out = run_baselines(self.items, self.gold)
        self.assertEqual(set(out), {"most_recent_entity", "current_speaker", "current_addressee"})
        self.assertEqual(out["current_speaker"]["metrics"]["by_model_condition"]["current_speaker|baseline"]["overall_accuracy"]["denominator"], 19)


class Generation(unittest.TestCase):
    def test_mock_generation_writes_candidates(self):
        scenarios = [s for s in load_scenarios(SCENARIOS) if s.scenario_id in ("S01", "N01")]
        prompt = load_generation_prompt(ROOT / "prompts" / "generate_v1.json")
        with tempfile.TemporaryDirectory() as tmp:
            summary = generate_drafts(scenarios, get_adapter("mock"), prompt, {"model_id": "mock", "provider": "mock"}, Path(tmp), sleep=lambda s: None)
            self.assertEqual(summary["ok"], 4)
            samples = load_dataset(Path(tmp))
            self.assertTrue(all(s.label.annotation_status == "candidate" and s.label.ambiguity_status == "unreviewed" for s in samples))
            self.assertTrue(all(s.record.creation_method == "llm_generated_api" for s in samples))
            shift = next(s for s in samples if s.sample_id == "S01-shift")
            self.assertEqual(shift.record.pair_ids, ["S01:distractor~shift"])
            self.assertIsNone(shift.label.distractor_id)
            log = (Path(tmp) / "generation_log.jsonl").read_text(encoding="utf-8")
            self.assertIn("payload_hash", log)


class Annotation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = load_dataset(DATASET)

    def test_sheets_hide_gold_and_shuffle(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = A.make_sheets(self.samples, ["a", "b"], Path(tmp), seed=1)
            text = Path(paths[0]).read_text(encoding="utf-8-sig")
            self.assertNotIn("gold", text)
            self.assertNotIn("anchor", text)
            self.assertNotIn("근거", text)
            for s in self.samples:
                self.assertNotIn(s.sample_id, text)  # 의도가 드러나는 sample_id 숨김
            rows_a = A.load_sheet(paths[0])
            rows_b = A.load_sheet(paths[1])
            self.assertNotEqual([r["sample_id"] for r in rows_a], [r["sample_id"] for r in rows_b])

    def _rows(self, overrides_b):
        rows = []
        for name, overrides in (("a", {}), ("b", overrides_b)):
            for s in self.samples:
                gold = s.label.gold_referent_id
                row = {"annotator": name, "sample_id": s.sample_id, "naturalness_1to5": "4", "referent_id": gold or "",
                       "addressee_id": "", "context_sufficient": "yes", "ambiguity": "unambiguous" if gold else "ambiguous", "notes": ""}
                row.update(overrides.get(s.sample_id, {}))
                rows.append(row)
        return rows

    def test_agreement_and_adjudication(self):
        rows = self._rows({"S07-plain": {"referent_id": "P2"}, "S04-distractor": {"referent_id": "", "ambiguity": "uncertain"}})
        report = A.agreement(rows)["by_condition"]["full"]["pairs"]["a~b"]
        self.assertAlmostEqual(report["fields"]["referent_id"]["percent_agreement"], 17 / 18)
        self.assertEqual(sorted(report["disagreements"]), ["S04-distractor", "S07-plain"])
        self.assertIsNone(report["fields"]["context_sufficient"]["cohen_kappa"])  # 단일 범주 → 정의되지 않음
        decisions = {"S07-plain": {"decision": "reject", "final_ambiguity": "ambiguous"},
                     "S04-distractor": {"decision": "accept", "final_referent_id": "T2"}}
        labels, summary = A.adjudicate(self.samples, rows, decisions)
        by_id = {l.sample_id: l for l in labels}
        self.assertEqual(summary["accepted_unanimous"], 17)
        self.assertEqual(by_id["S07-plain"].annotation_status, "rejected")
        self.assertIsNone(by_id["S07-plain"].gold_referent_id)
        self.assertEqual(by_id["S04-distractor"].annotation_status, "accepted")
        self.assertEqual(by_id["S03-novocative"].annotation_status, "rejected")  # 전원 모호 → 제외
        self.assertEqual(len(by_id["S01-base"].validation_metadata["annotator_votes"]), 2)
        self.assertIn("addressee_id", by_id["S01-base"].validation_metadata["annotator_votes"][0])
        self.assertIn("determinable", report["fields"])

    def test_adjudication_reflects_addressee_and_rejects_bad_sheets(self):
        rows = self._rows({})
        for r in rows:  # 두 검수자 모두 S03-vocative의 청자를 P2로 판정(작성자 P3과 다름)
            if r["sample_id"] == "S03-vocative":
                r["addressee_id"] = "P2"
        labels, _ = A.adjudicate(self.samples, rows, {})
        lab = {l.sample_id: l for l in labels}["S03-vocative"]
        self.assertEqual(lab.addressee_id, "P2")
        self.assertIn("addressee_id", lab.validation_metadata["author_values_overridden"])
        self.assertEqual(lab.anchor_turn, 4)  # anchor는 작성자 값 유지
        with self.assertRaises(ValueError):  # 같은 검수자 중복 행
            A.adjudicate(self.samples, rows + [rows[0]], {})
        with self.assertRaises(ValueError):  # 후보 밖 ID
            A.adjudicate(self.samples, self._rows({"S01-base": {"referent_id": "INVALID"}}), {})
        same = [dict(r, annotator="a") for r in self._rows({}) if r["annotator"] == "a"]
        same += [dict(r, annotator="a", condition="local") for r in self._rows({}) if r["annotator"] == "a"]
        labels, summary = A.adjudicate(self.samples, same, {})  # 서로 다른 검수자 1명 → in_review
        self.assertEqual(summary, {"in_review": 20})

    def test_local_sheets_and_context_need(self):
        with tempfile.TemporaryDirectory() as tmp:
            full = A.make_sheets(self.samples, ["a"], Path(tmp), seed=1, condition="full")
            local = A.make_sheets(self.samples, ["a"], Path(tmp), seed=1, condition="local")
            text = Path(local[0]).read_text(encoding="utf-8-sig")
            self.assertNotIn("S01-base", text)  # sample_id 숨김
            self.assertIn("review_id", text)
            rows_full, rows_local = A.load_sheet(full[0]), A.load_sheet(local[0])
            self.assertEqual({r["condition"] for r in rows_full}, {"full"})
            self.assertEqual({r["condition"] for r in rows_local}, {"local"})
            self.assertEqual({r["sample_id"] for r in rows_local}, {s.sample_id for s in self.samples})
        self.assertEqual(A.classify_context_need("T1", [{"referent_id": "T1", "ambiguity": "unambiguous"}, {"referent_id": "T1", "ambiguity": "unambiguous"}]), "locally_recoverable")
        self.assertEqual(A.classify_context_need("T1", [{"referent_id": "", "ambiguity": "ambiguous"}, {"referent_id": "", "ambiguity": "uncertain"}]), "discourse_dependent")
        self.assertEqual(A.classify_context_need("T1", [{"referent_id": "P1", "ambiguity": "unambiguous"}, {"referent_id": "", "ambiguity": "ambiguous"}]), "conflict")
        self.assertIsNone(A.classify_context_need(None, [{"referent_id": "T1", "ambiguity": "unambiguous"}]))

    def test_single_annotator_stays_in_review(self):
        rows = [r for r in self._rows({}) if r["annotator"] == "a"]
        labels, summary = A.adjudicate(self.samples, rows, {})
        self.assertEqual(summary, {"in_review": 20})

    def test_payload_check_on_written_files(self):
        from koimplicit.benchmark import load_model_config
        from koimplicit.validate import check_payload
        items, gold, _ = build_payload(self.samples, include_unreviewed=True)
        model = load_model_config(ROOT / "configs" / "models.json", "mock")
        self.assertEqual(check_payload(items, gold, model, PROMPT, ROOT / "prompts" / "qa_v1.json"), [])
        leaky = [{**items[0], "gold_entity_id": "E1"}] + items[1:]
        self.assertTrue(any(i["code"] == "ITEM_FORBIDDEN_KEY" for i in check_payload(leaky, gold, model, PROMPT)))
        leaky = [{**items[0], "candidates": items[0]["candidates"] + [{"entity_id": "P1", "label": "x"}]}] + items[1:]
        self.assertTrue(any(i["code"] == "ITEM_ORIGINAL_ID" for i in check_payload(leaky, gold, model, PROMPT)))


if __name__ == "__main__":
    unittest.main()
