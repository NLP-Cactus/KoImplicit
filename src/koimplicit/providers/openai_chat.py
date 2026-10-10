"""OpenAI Chat Completions adapter (표준 라이브러리 urllib).

- 키: 환경 변수 OPENAI_API_KEY.
- decoding: temperature, seed, max_tokens, extra_body. seed는 best-effort 재현성이며
  응답의 system_fingerprint를 기록한다.
- model_id는 configs/models.json에서 사용자가 지정한다. 기본값을 두지 않는다.
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request

from ..runner import PermanentError, TransientError

API_URL = "https://api.openai.com/v1/chat/completions"
RETRYABLE = {408, 409, 429}


class Adapter:
    def __init__(self, api_key: str | None = None, timeout: float = 120.0, api_url: str = API_URL, **options):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise PermanentError("OPENAI_API_KEY is not set")
        self.timeout = timeout
        self.api_url = api_url
        self.options = options
        self.seed_supported = True

    def build_body(self, request: dict) -> dict:
        decoding = dict(request.get("decoding") or {})
        messages = []
        if request.get("system"):
            messages.append({"role": "system", "content": request["system"]})
        messages.append({"role": "user", "content": request["user"]})
        body = {"model": request["model_id"], "messages": messages}
        if request.get("seed") is not None:
            body["seed"] = request["seed"]
        for key in ("temperature", "top_p", "max_tokens", "seed", "response_format"):
            if key in decoding:
                body[key] = decoding.pop(key)
        body.update(decoding.pop("extra_body", {}) or {})
        return body

    def complete(self, request: dict) -> dict:
        if not request.get("model_id") or request["model_id"] == "unset":
            raise PermanentError("openai model_id is not configured")
        data = json.dumps(self.build_body(request), ensure_ascii=False).encode("utf-8")
        http = urllib.request.Request(self.api_url, data=data, method="POST", headers={
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        })
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(http, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                request_id = resp.headers.get("x-request-id")
        except urllib.error.HTTPError as error:
            text = error.read().decode("utf-8", errors="replace")[:300]
            if error.code in RETRYABLE or error.code >= 500:
                raise TransientError(f"HTTP {error.code}: {text}") from None
            raise PermanentError(f"HTTP {error.code}: {text}") from None
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as error:
            raise TransientError(f"connection: {error}") from None
        latency = int((time.perf_counter() - started) * 1000)
        choice = (payload.get("choices") or [{}])[0]
        usage = payload.get("usage") or {}
        return {
            "raw_text": (choice.get("message") or {}).get("content"),
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "latency_ms": latency,
            "finish_reason": choice.get("finish_reason"),
            "model": payload.get("model"),
            "request_id": request_id,
            "system_fingerprint": payload.get("system_fingerprint"),
        }
