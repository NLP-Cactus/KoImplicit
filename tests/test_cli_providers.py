"""구독 CLI adapter(claude_cli, codex_cli)의 인자 구성과 출력 파싱. 실제 CLI를 실행하지 않는다."""

import json
import unittest
from unittest import mock

from koimplicit.providers import claude_cli, codex_cli
from koimplicit.runner import PermanentError, TransientError

CLAUDE_OK = json.dumps({"type": "result", "is_error": False, "result": '```json\n{"entity_id": "E1"}\n```\n설명', "stop_reason": "end_turn",
                        "session_id": "s1", "total_cost_usd": 0.0013, "num_turns": 1,
                        "usage": {"input_tokens": 2, "output_tokens": 163},
                        "modelUsage": {"claude-haiku-5-5": {"inputTokens": 2, "outputTokens": 163, "cacheReadInputTokens": 3148, "cacheCreationInputTokens": 5951, "canonicalModel": "claude-haiku-5-5"}}})
CLAUDE_LOGIN = json.dumps({"type": "result", "is_error": True, "result": "Not logged in · Please run /login", "usage": {}, "modelUsage": {}})
CODEX_OK = "\n".join([
    "Reading additional input from stdin...",
    json.dumps({"type": "thread.started", "thread_id": "t1"}),
    json.dumps({"type": "turn.started"}),
    json.dumps({"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": '{"entity_id":"E1"}'}}),
    json.dumps({"type": "turn.completed", "usage": {"input_tokens": 17714, "cached_input_tokens": 12544, "output_tokens": 11, "reasoning_output_tokens": 0}}),
])


class ClaudeCli(unittest.TestCase):
    def test_parse_ok(self):
        out = claude_cli.parse_claude_output(CLAUDE_OK)
        self.assertIn('"entity_id": "E1"', out["raw_text"])
        self.assertEqual((out["model"], out["output_tokens"], out["input_tokens"]), ("claude-haiku-5-5", 163, 2 + 3148 + 5951))
        self.assertEqual(out["cli_cost_usd"], 0.0013)

    def test_parse_errors(self):
        with self.assertRaises(PermanentError):
            claude_cli.parse_claude_output(CLAUDE_LOGIN)
        with self.assertRaises(TransientError):
            claude_cli.parse_claude_output("garbage without json")

    def test_build_args(self):
        with mock.patch("koimplicit.providers.claude_cli.find_executable", return_value="claude.CMD"), \
             mock.patch("koimplicit.providers.claude_cli.cli_version", return_value="2.1.296"):
            adapter = claude_cli.Adapter()
        args = adapter.build_args({"model_id": "claude-haiku-5-5", "system": "sys", "user": "u", "decoding": {"effort": "low", "timeout": 10}})
        self.assertEqual(args[:2], ["claude.CMD", "-p"])
        self.assertIn("--max-turns", args)
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertEqual(args[args.index("--model") + 1], "claude-haiku-5-5")
        self.assertEqual(args[args.index("--system-prompt") + 1], "sys")
        self.assertEqual(args[args.index("--effort") + 1], "low")
        self.assertNotIn("--system-prompt", adapter.build_args({"model_id": "m", "user": "u"}))

    def test_complete_uses_stdin_and_records_mode(self):
        with mock.patch("koimplicit.providers.claude_cli.find_executable", return_value="claude.CMD"), \
             mock.patch("koimplicit.providers.claude_cli.cli_version", return_value="2.1.296"), \
             mock.patch("koimplicit.providers.claude_cli.run_cli", return_value=(CLAUDE_OK, "", 0)) as run:
            out = claude_cli.Adapter().complete({"model_id": "claude-haiku-5-5", "system": "", "user": "질문", "decoding": {}})
        self.assertEqual(run.call_args.args[1], "질문")
        self.assertEqual(out["system_prompt_mode"], "claude_code_default")
        self.assertEqual(out["cli_version"], "2.1.296")


class CodexCli(unittest.TestCase):
    def test_parse_ok(self):
        out = codex_cli.parse_codex_events(CODEX_OK)
        self.assertEqual(out["raw_text"], '{"entity_id":"E1"}')
        self.assertEqual((out["input_tokens"], out["output_tokens"], out["cache_read_input_tokens"], out["request_id"]), (17714, 11, 12544, "t1"))

    def test_parse_errors(self):
        with self.assertRaises(TransientError):
            codex_cli.parse_codex_events(json.dumps({"type": "thread.started", "thread_id": "t"}))
        with self.assertRaises(PermanentError):
            codex_cli.parse_codex_events(json.dumps({"type": "error", "message": "invalid model"}))
        with self.assertRaises(TransientError):
            codex_cli.parse_codex_events(json.dumps({"type": "error", "message": "rate limit exceeded"}))

    def test_build_args_and_prompt(self):
        with mock.patch("koimplicit.providers.codex_cli.find_executable", return_value="codex.CMD"), \
             mock.patch("koimplicit.providers.codex_cli.cli_version", return_value="codex-cli 0.160.0"):
            adapter = codex_cli.Adapter()
        args = adapter.build_args({"model_id": "gpt-6.1-sol", "user": "u", "decoding": {"reasoning_effort": "low", "timeout": 5}})
        self.assertEqual(args[-1], "-")
        self.assertEqual(args[args.index("-m") + 1], "gpt-6.1-sol")
        self.assertIn("model_reasoning_effort=low", args)
        self.assertIn("read-only", args)
        with self.assertRaises(PermanentError):
            adapter.build_args({"model_id": "unset", "user": "u"})
        with mock.patch("koimplicit.providers.codex_cli.run_cli", return_value=(CODEX_OK, "", 0)) as run:
            out = adapter.complete({"model_id": "gpt-6.1-sol", "system": "규칙", "user": "질문", "decoding": {}})
        self.assertTrue(run.call_args.args[1].startswith("규칙\n\n질문"))
        self.assertEqual((out["model"], out["system_prompt_mode"]), ("gpt-6.1-sol", "prepended_to_user"))


class CliCommon(unittest.TestCase):
    def test_run_cli_classifies_exit_codes(self):
        from koimplicit.providers._cli import run_cli
        import subprocess
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, b"", b"ECONNRESET while calling api")):
            with self.assertRaises(TransientError):
                run_cli(["x"], "p", timeout=1)
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 2, b"", b"unknown flag")):
            with self.assertRaises(PermanentError):
                run_cli(["x"], "p", timeout=1)
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)):
            with self.assertRaises(TransientError):
                run_cli(["x"], "p", timeout=1)


if __name__ == "__main__":
    unittest.main()
