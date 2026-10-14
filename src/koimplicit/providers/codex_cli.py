"""Codex CLI adapter: `codex exec --json`. ChatGPT 구독 로그인으로 동작한다(API 키 불필요).

- 프롬프트는 stdin(`-`)으로 넘긴다. 읽기 전용 샌드박스, 세션 미저장(`--ephemeral`), git 검사 생략.
- request.system이 있으면 프롬프트 앞에 붙인다(codex exec에는 시스템 프롬프트 옵션이 없다). Codex 자체의
  에이전트 시스템 프롬프트는 항상 붙으며 입력 토큰에 그 분량이 포함된다.
- decoding: reasoning_effort(`-c model_reasoning_effort=`), timeout(초). 그 밖의 키는 `-c key=value`로 전달한다.
- 기록: JSONL의 turn.completed usage, 마지막 agent_message, thread_id, codex --version. 모델명은 요청값을 기록한다
  (이벤트에 모델명이 없으므로 `-m`을 반드시 지정한다).
"""

from __future__ import annotations

import json
import time

from ..runner import PermanentError, TransientError
from ._cli import cli_version, find_executable, run_cli


def parse_codex_events(text: str) -> dict:
    """`--json` JSONL 이벤트를 runner 응답 형식으로 바꾼다. 마지막 agent_message가 답이다."""
    message, usage, thread_id, error = None, {}, None, None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "thread.started":
            thread_id = event.get("thread_id")
        elif kind == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message":
                message = item.get("text")
        elif kind == "turn.completed":
            usage = event.get("usage") or {}
        elif kind in ("error", "turn.failed"):
            error = event.get("message") or json.dumps(event, ensure_ascii=False)[:300]
    if error and message is None:
        if any(m in error.lower() for m in ("rate", "timeout", "network", "overloaded", "429", "503", "502")):
            raise TransientError(f"codex: {error}")
        raise PermanentError(f"codex: {error}")
    if message is None:
        raise TransientError(f"codex returned no agent_message: {text[-200:]}")
    return {
        "raw_text": message,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_read_input_tokens": usage.get("cached_input_tokens"),
        "reasoning_output_tokens": usage.get("reasoning_output_tokens"),
        "finish_reason": "turn.completed" if usage else None,
        "request_id": thread_id,
    }


class Adapter:
    def __init__(self, executable: str = "codex", timeout: float = 300.0, extra_args: list[str] | None = None, **options):
        self.path = find_executable(executable)
        self.timeout = timeout
        self.extra_args = list(extra_args or [])
        self.options = options
        self.version = cli_version(self.path)
        self.seed_supported = False

    def build_args(self, request: dict) -> list[str]:
        decoding = dict(request.get("decoding") or {})
        model = request.get("model_id")
        if not model or model == "unset":
            raise PermanentError("codex adapter needs an explicit model_id (-m)")
        args = [self.path, "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "-m", model]
        decoding.pop("timeout", None)
        if decoding.get("reasoning_effort"):
            args += ["-c", f"model_reasoning_effort={decoding.pop('reasoning_effort')}"]
        for key, value in decoding.items():
            args += ["-c", f"{key}={json.dumps(value) if not isinstance(value, str) else value}"]
        return args + self.extra_args + ["-"]

    def complete(self, request: dict) -> dict:
        args = self.build_args(request)
        prompt = request["user"]
        if request.get("system"):
            prompt = request["system"].rstrip() + "\n\n" + prompt
        started = time.perf_counter()
        stdout, stderr, _ = run_cli(args, prompt, timeout=float((request.get("decoding") or {}).get("timeout", self.timeout)))
        out = parse_codex_events(stdout)
        out["latency_ms"] = int((time.perf_counter() - started) * 1000)
        out["model"] = request.get("model_id")
        out["cli_version"] = self.version
        out["system_prompt_mode"] = "prepended_to_user" if request.get("system") else "codex_default_only"
        return out
