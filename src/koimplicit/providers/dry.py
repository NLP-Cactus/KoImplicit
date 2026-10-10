"""네트워크를 쓰지 않는 adapter. 요청 본문 길이만 세고 응답은 missing으로 남긴다.

실행 기록 형식, 캐시, 순서 섞기, 요청 수를 실제 비용 없이 확인할 때 쓴다.
"""

from __future__ import annotations


class Adapter:
    def __init__(self, **options):
        self.options = options
        self.requests: list[dict] = []

    def complete(self, request: dict) -> dict:
        self.requests.append({"item_id": request["item_id"], "condition": request["condition"], "user_chars": len(request["user"])})
        return {"raw_text": None, "input_tokens": None, "output_tokens": None, "latency_ms": 0, "finish_reason": "dry_run"}
