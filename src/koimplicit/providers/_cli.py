"""CLI 기반 provider의 공통 부분. 프롬프트는 stdin으로 넘기고 출력은 UTF-8 bytes로 받는다.

구독 CLI(Claude Code, Codex)를 모델 호출에 쓰는 것은 개발·pilot 점검용이다. 에이전트용 시스템 프롬프트·도구가
붙을 수 있고 디코딩 설정을 통제하기 어려우며 CLI가 자동 갱신되므로, 정식 평가는 API provider로 한다.
"""

from __future__ import annotations

import shutil
import subprocess

from ..runner import PermanentError, TransientError

TRANSIENT_MARKERS = ("timeout", "timed out", "rate limit", "429", "overloaded", "529", "503", "502", "ECONNRESET", "ENOTFOUND", "network", "connection")


def find_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise PermanentError(f"{name} CLI not found on PATH")
    return path


def cli_version(path: str) -> str | None:
    try:
        out = subprocess.run([path, "--version"], capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        return (out.stdout or out.stderr).decode("utf-8", errors="replace").strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def run_cli(args: list[str], prompt: str, timeout: float, cwd: str | None = None) -> tuple[str, str, int]:
    """(stdout, stderr, returncode). 실행 실패·타임아웃은 TransientError, 그 밖의 0이 아닌 종료는 메시지로 분류한다."""
    try:
        proc = subprocess.run(args, input=prompt.encode("utf-8"), capture_output=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        raise TransientError(f"cli timeout after {timeout}s") from None
    except OSError as error:
        raise PermanentError(f"cannot run cli: {error}") from None
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        text = (stderr or stdout)[-400:]
        if any(m.lower() in text.lower() for m in TRANSIENT_MARKERS):
            raise TransientError(f"cli exit {proc.returncode}: {text}")
        raise PermanentError(f"cli exit {proc.returncode}: {text}")
    return stdout, stderr, proc.returncode
