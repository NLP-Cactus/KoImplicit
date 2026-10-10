"""Anthropic Messages API adapter (표준 라이브러리 urllib).

- 키: 환경 변수 ANTHROPIC_API_KEY. 로그·기록에 출력하지 않는다.
- decoding 설정: max_tokens, effort(output_config.effort), thinking, extra_body(그대로 병합).
  Claude 5 계열은 temperature/top_p를 받지 않으므로 사용자가 명시한 경우에만 보낸다.
- seed 미지원. 재현성은 payload 캐시와 결정적 프롬프트로 확보한다.
- 408/409/429/5xx와 연결 오류는 TransientError, 그 외 4xx는 PermanentError.
- stop_reason == refusal이면 raw_text를 빈 문자열로 두고 finish_reason에 남긴다.
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request

from ..runner import PermanentError, TransientError

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
RETRYABLE = {408, 409, 429}


class Adapter:
    def __init__(self, api_key: str | None = None, timeout: float = 120.0, api_url: str = API_URL, **options):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise PermanentError("ANTHROPIC_API_KEY is not set")
        self.timeout = timeout
        self.api_url = api_url
        self.options = options
        self.seed_supported = False

    def build_body(self, request: dict) -> dict:
        decoding = dict(request.get("decoding") or {})
        body = {
            "model": request["model_id"],
            "max_tokens": int(decoding.pop("max_tokens", 1024)),
            "messages": [{"role": "user", "content": request["user"]}],
        }
        if request.get("system"):
            body["system"] = request["system"]
        effort = decoding.pop("effort", None)
        if effort:
            body["output_config"] = {"effort": effort}
        thinking = decoding.pop("thinking", None)
        if thinking:
            body["thinking"] = thinking
        for key in ("temperature", "top_p", "top_k", "stop_sequences"):
            if key in decoding:
                body[key] = decoding.pop(key)
        body.update(decoding.pop("extra_body", {}) or {})
        return body

    def complete(self, request: dict) -> dict:
        body = self.build_body(request)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        http = urllib.request.Request(self.api_url, data=data, method="POST", headers={
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        })
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(http, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                request_id = resp.headers.get("request-id")
        except urllib.error.HTTPError as error:
            text = error.read().decode("utf-8", errors="replace")[:300]
            if error.code in RETRYABLE or error.code >= 500:
                raise TransientError(f"HTTP {error.code}: {text}") from None
            raise PermanentError(f"HTTP {error.code}: {text}") from None
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as error:
            raise TransientError(f"connection: {error}") from None
        latency = int((time.perf_counter() - started) * 1000)
        text = "".join(block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text")
        stop = payload.get("stop_reason")
        usage = payload.get("usage") or {}
        return {
            "raw_text": "" if stop == "refusal" else text,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
            "latency_ms": latency,
            "finish_reason": stop,
            "model": payload.get("model"),
            "request_id": request_id,
            "stop_details": payload.get("stop_details"),
        }
