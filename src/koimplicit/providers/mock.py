"""결정적 mock adapter. API 키 없이 생성·평가 파이프라인 전체를 돌려 본다.

- 평가 요청(candidate_ids 있음): strategy에 따라 후보 하나를 고른다.
  hash(기본): payload 해시로 고정 선택. first/last: 후보 순서 기준.
- QA 요청(후보 없음): "화자"를 답한다.
- 생성 요청(task == "generate"): 시나리오 참여자 이름으로 자리표시 대화를 만든다.
  실제 한국어 대화가 아니며 파이프라인 형식 검증용이다.
"""

from __future__ import annotations

import hashlib
import json


class Adapter:
    def __init__(self, strategy: str = "hash", **options):
        if strategy not in ("hash", "first", "last"):
            raise ValueError(f"unknown mock strategy {strategy!r}")
        self.strategy = strategy
        self.options = options
        self.requests: list[dict] = []

    def complete(self, request: dict) -> dict:
        self.requests.append({"task": request.get("task"), "item_id": request.get("item_id"), "condition": request.get("condition")})
        if request.get("task") == "generate":
            raw = json.dumps(self._generate(request.get("scenario") or {}), ensure_ascii=False)
        else:
            ids = request.get("candidate_ids") or []
            if ids:
                if self.strategy == "first":
                    pick = ids[0]
                elif self.strategy == "last":
                    pick = ids[-1]
                else:
                    digest = hashlib.sha256(request.get("user", "").encode("utf-8")).hexdigest()
                    pick = ids[int(digest, 16) % len(ids)]
                raw = json.dumps({"entity_id": pick}, ensure_ascii=False)
            else:
                raw = "화자"
        user_len = len(request.get("user", ""))
        return {"raw_text": raw, "input_tokens": user_len // 2, "output_tokens": len(raw) // 2,
                "latency_ms": 0, "finish_reason": "mock", "model": "mock"}

    @staticmethod
    def _generate(scenario: dict) -> dict:
        names = [p["name"] for p in scenario.get("participants", []) if p.get("in_dialogue", True)] or ["A", "B"]
        n_turns = scenario.get("n_turns") or 4
        turns = [{"speaker": names[i % len(names)], "text": f"(mock 발화 {i + 1}) 자리표시 문장입니다."} for i in range(n_turns)]
        return {"turns": turns, "target_turn": n_turns, "target_predicate": "자리표시 문장입니다"}
