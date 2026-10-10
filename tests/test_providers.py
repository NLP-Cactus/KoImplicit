"""실제 provider adapter의 요청 본문 구성과 오류 분류. 네트워크를 쓰지 않는다."""

import io
import json
import unittest
import urllib.error
from unittest import mock

from koimplicit.providers import anthropic as A
from koimplicit.providers import get_adapter
from koimplicit.providers import openai_chat as O
from koimplicit.runner import PermanentError, TransientError

REQUEST = {"model_id": "claude-opus-5-5", "system": "sys", "user": "질문", "decoding": {"max_tokens": 64, "effort": "low"}, "seed": 7}


class AnthropicAdapter(unittest.TestCase):
    def test_requires_key(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(PermanentError):
                A.Adapter()

    def test_body_shape(self):
        body = A.Adapter(api_key="k").build_body(REQUEST)
        self.assertEqual(body["model"], "claude-opus-5-5")
        self.assertEqual(body["max_tokens"], 64)
        self.assertEqual(body["output_config"], {"effort": "low"})
        self.assertEqual(body["messages"], [{"role": "user", "content": "질문"}])
        self.assertEqual(body["system"], "sys")
        self.assertNotIn("temperature", body)
        self.assertNotIn("seed", body)

    def _fake_response(self, payload):
        resp = mock.MagicMock()
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.headers = {"request-id": "req_1"}
        resp.__enter__.return_value = resp
        return resp

    def test_parses_text_and_usage(self):
        payload = {"content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": '{"entity_id": "P1"}'}],
                   "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 3}, "model": "claude-opus-5-5"}
        with mock.patch("urllib.request.urlopen", return_value=self._fake_response(payload)):
            out = A.Adapter(api_key="k").complete(REQUEST)
        self.assertEqual(out["raw_text"], '{"entity_id": "P1"}')
        self.assertEqual((out["input_tokens"], out["output_tokens"], out["request_id"]), (10, 3, "req_1"))

    def test_refusal_gives_empty_text(self):
        payload = {"content": [], "stop_reason": "refusal", "usage": {}, "stop_details": {"category": "x"}}
        with mock.patch("urllib.request.urlopen", return_value=self._fake_response(payload)):
            out = A.Adapter(api_key="k").complete(REQUEST)
        self.assertEqual((out["raw_text"], out["finish_reason"]), ("", "refusal"))

    def test_error_classification(self):
        def raise_http(code):
            return mock.Mock(side_effect=urllib.error.HTTPError("u", code, "m", {}, io.BytesIO(b"{}")))
        with mock.patch("urllib.request.urlopen", raise_http(529)):
            with self.assertRaises(TransientError):
                A.Adapter(api_key="k").complete(REQUEST)
        with mock.patch("urllib.request.urlopen", raise_http(429)):
            with self.assertRaises(TransientError):
                A.Adapter(api_key="k").complete(REQUEST)
        with mock.patch("urllib.request.urlopen", raise_http(400)):
            with self.assertRaises(PermanentError):
                A.Adapter(api_key="k").complete(REQUEST)
        with mock.patch("urllib.request.urlopen", mock.Mock(side_effect=urllib.error.URLError("down"))):
            with self.assertRaises(TransientError):
                A.Adapter(api_key="k").complete(REQUEST)


class OpenAIAdapter(unittest.TestCase):
    def test_body_and_unset_model(self):
        body = O.Adapter(api_key="k").build_body({**REQUEST, "model_id": "gpt-x", "decoding": {"temperature": 0, "max_tokens": 32}})
        self.assertEqual(body["messages"][0], {"role": "system", "content": "sys"})
        self.assertEqual((body["temperature"], body["max_tokens"], body["seed"]), (0, 32, 7))
        with self.assertRaises(PermanentError):
            O.Adapter(api_key="k").complete({**REQUEST, "model_id": "unset"})


class Registry(unittest.TestCase):
    def test_known_and_unknown(self):
        self.assertEqual(type(get_adapter("mock", strategy="first")).__name__, "Adapter")
        with self.assertRaises(KeyError):
            get_adapter("nope")
        with self.assertRaises(ValueError):
            get_adapter("mock", strategy="weird")


if __name__ == "__main__":
    unittest.main()
