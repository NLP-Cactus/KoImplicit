"""Codex 교차검증(2026-10-10)에서 재현된 결함의 회귀 검사."""

import io
import json
import unittest
import urllib.error
from unittest import mock

from koimplicit.bootstrap import cluster_bootstrap, paired_item_difference
from koimplicit.normalize import map_qa_answer
from koimplicit.providers import anthropic as A
from koimplicit.runner import PermanentError, TransientError, call_with_retry
from koimplicit.schema import DialogueRecord, LabelRecord, Participant, Turn, derive, find_mentions, surface_forms_of


def _record(turns, parts, target_turn, predicate):
    return DialogueRecord(sample_id="r", dataset="controlled", scenario_id="R", participants=parts,
                          dialogue=[Turn(turn_index=i, speaker_id=s, text=t) for i, (s, t) in enumerate(turns, start=1)],
                          speaker_id=turns[target_turn - 1][0], target_turn=target_turn, target_predicate=predicate, creation_method="human_authored")


class MentionOverlap(unittest.TestCase):
    def test_longer_surface_form_wins(self):
        parts = [Participant(entity_id="P1", name="가"), Participant(entity_id="P2", name="나"),
                 Participant(entity_id="T1", name="형", aliases=["우리 형"], in_dialogue=False),
                 Participant(entity_id="T2", name="형수", aliases=["형수님"], in_dialogue=False)]
        forms = surface_forms_of(parts)
        self.assertEqual(find_mentions("형수님은 괜찮으셔? 우리 형은?", forms), [(0, "T2"), (11, "T1")])
        rec = _record([("P2", "형수님은 괜찮으셔?"), ("P1", "친정에 가 있기로 했대.")], parts, 2, "가 있기로 했대")
        d = derive(rec, LabelRecord(sample_id="r", gold_referent_id="T2", anchor_turn=1, anchor_referent_id="T2"))
        self.assertEqual((d.most_recent_mentioned_id, d.turn_distance, d.distractor_present), ("T2", 1, False))


class LabelBounds(unittest.TestCase):
    def test_anchor_turn_zero_rejected(self):
        with self.assertRaises(ValueError):
            LabelRecord(sample_id="r", anchor_turn=0, anchor_referent_id="P1")
        parts = [Participant(entity_id="P1", name="가"), Participant(entity_id="P2", name="나")]
        rec = _record([("P1", "문장 하나"), ("P2", "문장")], parts, 2, "문장")
        with self.assertRaises(ValueError):  # anchor가 목표 발화 이후
            derive(rec, LabelRecord(sample_id="r", gold_referent_id="P1", anchor_turn=2, anchor_referent_id="P1"))

    def test_no_gold_means_no_distractor_judgement(self):
        parts = [Participant(entity_id="P1", name="가"), Participant(entity_id="P2", name="나"), Participant(entity_id="T1", name="다", in_dialogue=False)]
        rec = _record([("P1", "다 왔어"), ("P2", "문장")], parts, 2, "문장")
        self.assertIsNone(derive(rec, LabelRecord(sample_id="r", gold_referent_id=None, ambiguity_status="ambiguous")).distractor_present)


class QaParsing(unittest.TestCase):
    roster = [{"entity_id": "E1", "label": "수아"}, {"entity_id": "E2", "label": "준호"}, {"entity_id": "E3", "label": "민수"}]

    def test_abstain_before_pronoun(self):
        self.assertEqual(map_qa_answer("제가 판단할 수 없습니다", self.roster, "수아", "준호")["parse_status"], "abstain")

    def test_addressee_by_label(self):
        self.assertEqual(map_qa_answer("청자", self.roster, "수아", "준호")["predicted_entity_id"], "E2")
        self.assertEqual(map_qa_answer("상대방", self.roster, "수아", None)["parse_status"], "unmapped")  # 청자 불명 → 임의 매핑 안 함
        self.assertEqual(map_qa_answer("화자", self.roster, "수아", None)["predicted_entity_id"], "E1")


class BootstrapDraws(unittest.TestCase):
    def test_duplicate_cluster_draws_are_kept(self):
        rows = []
        for cid, diff in (("c1", 1), ("c2", 0)):
            rows.append({"item_id": f"{cid}-i", "conversation_id": cid, "condition": "full_mcq", "parse_status": "ok", "gold_entity_id": "g", "predicted_entity_id": "g"})
            rows.append({"item_id": f"{cid}-i", "conversation_id": cid, "condition": "target_only_mcq", "parse_status": "ok", "gold_entity_id": "g", "predicted_entity_id": "g" if diff == 0 else "x"})
        stat = paired_item_difference("full_mcq", "target_only_mcq")
        # c1을 두 번, c2를 한 번 뽑은 재표집: 올바른 평균은 2/3
        resampled = [{**r, "_draw": k} for k, cid in enumerate(["c1", "c1", "c2"]) for r in rows if r["conversation_id"] == cid]
        self.assertAlmostEqual(stat(resampled), 2 / 3)
        out = cluster_bootstrap(rows, "conversation_id", stat, n_boot=50, seed=1)
        self.assertEqual(out["n_clusters"], 2)


class ProviderErrors(unittest.TestCase):
    request = {"model_id": "m", "user": "u", "decoding": {}}

    def test_incomplete_read_and_bad_json_are_transient(self):
        import http.client
        with mock.patch("urllib.request.urlopen", mock.Mock(side_effect=http.client.IncompleteRead(b""))):
            with self.assertRaises(TransientError):
                A.Adapter(api_key="k").complete(self.request)
        resp = mock.MagicMock()
        resp.read.return_value = b"<html>bad gateway</html>"
        resp.headers = {}
        resp.__enter__.return_value = resp
        with mock.patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(TransientError):
                A.Adapter(api_key="k").complete(self.request)

    def test_retry_after_is_honoured(self):
        err = urllib.error.HTTPError("u", 429, "m", {"retry-after": "3"}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", mock.Mock(side_effect=err)):
            with self.assertRaises(TransientError) as ctx:
                A.Adapter(api_key="k").complete(self.request)
        self.assertEqual(ctx.exception.retry_after, 3.0)
        waits = []

        class Flaky:
            calls = 0

            def complete(self, request):
                self.calls += 1
                if self.calls == 1:
                    raise TransientError("x", retry_after=5)
                return {"raw_text": "ok"}
        call_with_retry(Flaky(), {}, sleep=waits.append)
        self.assertEqual(waits, [5.0])

    def test_unexpected_structure_is_permanent(self):
        resp = mock.MagicMock()
        resp.read.return_value = json.dumps({"content": "not-a-list"}).encode()
        resp.headers = {}
        resp.__enter__.return_value = resp
        with mock.patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(PermanentError):
                A.Adapter(api_key="k").complete(self.request)


if __name__ == "__main__":
    unittest.main()
