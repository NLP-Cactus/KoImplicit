"""Claude Code CLI adapter: `claude -p --output-format json`. 구독 로그인으로 동작한다(API 키 불필요).

- 프롬프트는 stdin으로 넘긴다. 도구는 모두 끄고(`--tools ""`) 한 턴만 돈다(`--max-turns 1`).
- request.system이 비어 있지 않으면 `--system-prompt`로 Claude Code 기본 시스템 프롬프트를 통째로 대체한다.
  비어 있으면 Claude Code의 기본(코딩 에이전트) 프롬프트가 붙는다. 어느 쪽이었는지 응답 메타에 남긴다.
- decoding: effort(`--effort`), timeout(초). temperature·max_tokens는 CLI가 받지 않으므로 무시하고 기록만 한다.
- 기록: modelUsage의 canonicalModel·토큰·CLI가 계산한 costUSD, session_id, claude --version.
- 로그인 안 됨·모델 거부 등은 PermanentError, 네트워크·시간 초과는 TransientError.
"""

from __future__ import annotations

import json
import time

from ..runner import PermanentError, TransientError
from ._cli import cli_version, find_executable, run_cli


def parse_claude_output(text: str) -> dict:
    """`--output-format json` 결과를 runner 응답 형식으로 바꾼다."""
    try:
        start = text.find("{")
        payload = json.loads(text[start:]) if start != -1 else None
    except json.JSONDecodeError:
        payload = None
    if not isinstance(payload, dict):
        raise TransientError(f"claude cli returned no json: {text[-200:]}")
    result = payload.get("result")
    if payload.get("is_error"):
        message = str(result or payload.get("terminal_reason") or "unknown error")
        if "not logged in" in message.lower() or "login" in message.lower():
            raise PermanentError(f"claude cli: {message}")
        if any(m in message.lower() for m in ("rate", "overloaded", "timeout", "network", "529", "503")):
            raise TransientError(f"claude cli: {message}")
        raise PermanentError(f"claude cli: {message}")
    usage = payload.get("usage") or {}
    model_usage = payload.get("modelUsage") or {}
    model = None
    cost = payload.get("total_cost_usd")
    input_tokens = output_tokens = None
    for name, u in model_usage.items():
        model = u.get("canonicalModel") or name
        input_tokens = (u.get("inputTokens") or 0) + (u.get("cacheReadInputTokens") or 0) + (u.get("cacheCreationInputTokens") or 0)
        output_tokens = u.get("outputTokens")
    if input_tokens is None:
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
    return {
        "raw_text": result if isinstance(result, str) else json.dumps(result, ensure_ascii=False),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "finish_reason": payload.get("stop_reason"),
        "model": model,
        "request_id": payload.get("session_id"),
        "cli_cost_usd": cost,
        "num_turns": payload.get("num_turns"),
    }


class Adapter:
    def __init__(self, executable: str = "claude", timeout: float = 300.0, extra_args: list[str] | None = None, **options):
        self.path = find_executable(executable)
        self.timeout = timeout
        self.extra_args = list(extra_args or [])
        self.options = options
        self.version = cli_version(self.path)
        self.seed_supported = False

    def build_args(self, request: dict) -> list[str]:
        decoding = dict(request.get("decoding") or {})
        args = [self.path, "-p", "--output-format", "json", "--max-turns", "1", "--tools", "", "--no-session-persistence"]
        model = request.get("model_id")
        if model and model != "unset":
            args += ["--model", model]
        if decoding.get("effort"):
            args += ["--effort", str(decoding["effort"])]
        if request.get("system"):
            args += ["--system-prompt", request["system"]]
        return args + self.extra_args

    def complete(self, request: dict) -> dict:
        args = self.build_args(request)
        started = time.perf_counter()
        stdout, stderr, _ = run_cli(args, request["user"], timeout=float((request.get("decoding") or {}).get("timeout", self.timeout)))
        out = parse_claude_output(stdout)
        out["latency_ms"] = int((time.perf_counter() - started) * 1000)
        out["cli_version"] = self.version
        out["system_prompt_mode"] = "replaced" if request.get("system") else "claude_code_default"
        return out
