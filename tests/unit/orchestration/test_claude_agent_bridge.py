"""Tests for the Claude Agent Bridge (ADR-0022).

The module directory is hyphenated, so it's loaded by path like the
existing claudepy-bridge test.
"""

import importlib.util
import os
import sys
import stat
import urllib.error

import pytest

pytestmark = pytest.mark.req("REQ-ORCH-010", "REQ-ORCH-012", "REQ-VOICE-029")

_BRIDGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "..",
    "orchestration",
    "mcp",
    "modules",
    "claude-agent-bridge",
    "bridge.py",
)
_spec = importlib.util.spec_from_file_location("claude_agent_bridge", _BRIDGE_PATH)
_bridge_module = importlib.util.module_from_spec(_spec)
sys.modules["claude_agent_bridge"] = _bridge_module
assert _spec.loader is not None
_spec.loader.exec_module(_bridge_module)

ClaudeAgentBridge = _bridge_module.ClaudeAgentBridge
AGENTS = _bridge_module.AGENTS


def test_unknown_agent_rejected(tmp_path):
    bridge = ClaudeAgentBridge(state_dir=tmp_path)
    result = bridge.dispatch("do something", agent="not-a-real-agent")
    assert result["ok"] is False
    assert "unknown agent" in result["error"]


def test_empty_prompt_rejected(tmp_path):
    bridge = ClaudeAgentBridge(state_dir=tmp_path)
    result = bridge.dispatch("  ", agent="mia-car")
    assert result["ok"] is False
    assert "empty prompt" in result["error"]


def test_unreachable_uplink_skips_dispatch_without_hanging(tmp_path, monkeypatch):
    """REQ-ORCH-012: never block a voice turn on a dead uplink."""
    bridge = ClaudeAgentBridge(state_dir=tmp_path)
    monkeypatch.setattr(bridge, "is_uplink_reachable", lambda: False)

    called = {"subprocess": False}

    def fake_run(*args, **kwargs):
        called["subprocess"] = True
        raise AssertionError("subprocess.run must not be called when uplink is unreachable")

    monkeypatch.setattr(_bridge_module.subprocess, "run", fake_run)

    result = bridge.dispatch("what is my speed", agent="mia-car")
    assert result["ok"] is False
    assert result["error"] == "uplink unreachable"
    assert called["subprocess"] is False


def test_http_error_still_counts_as_reachable(tmp_path, monkeypatch):
    bridge = ClaudeAgentBridge(state_dir=tmp_path)

    def reject_head(*args, **kwargs):
        raise urllib.error.HTTPError(
            "https://api.anthropic.com", 404, "not found", {}, None
        )

    monkeypatch.setattr(_bridge_module.urllib.request, "urlopen", reject_head)

    assert bridge.is_uplink_reachable() is True


def test_mia_car_agent_is_read_only_by_tool_allowlist():
    """REQ-VOICE-029 / ADR-0006: the car agent may only read MIA's own API."""
    allowed = AGENTS["mia-car"]
    assert 'curl -s -H "X-API-Key: $MIA_API_KEY"' in allowed
    for risky in ("Write", "Edit", "rm ", "POST", "PUT", "DELETE"):
        assert risky not in allowed
    assert "*" not in allowed


def test_no_tool_agent_gets_disallowed_tools_not_omitted(tmp_path, monkeypatch):
    """Regression guard: an agent with allowed_tools == "" must get an explicit
    --disallowedTools, not have --allowedTools silently omitted (which means
    *unrestricted*, not *zero tools* — this exact bug was caught and fixed in
    the quest-rc prototype this module was ported from)."""
    bridge = ClaudeAgentBridge(state_dir=tmp_path)
    monkeypatch.setattr(bridge, "is_uplink_reachable", lambda: True)

    captured_cmd = {}

    class FakeCompletedProcess:
        returncode = 0
        stdout = '{"result": "ok"}'
        stderr = ""

    def fake_run(cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return FakeCompletedProcess()

    monkeypatch.setattr(_bridge_module.subprocess, "run", fake_run)

    assert AGENTS["general-rc"] == ""
    bridge.dispatch("hello", agent="general-rc")

    cmd = captured_cmd["cmd"]
    assert "--allowedTools" not in cmd
    assert "--disallowedTools" in cmd
    idx = cmd.index("--disallowedTools")
    assert "Bash" in cmd[idx + 1]


def test_audit_log_is_private_and_does_not_store_transcript(tmp_path, monkeypatch):
    bridge = ClaudeAgentBridge(state_dir=tmp_path / "state")
    monkeypatch.setattr(bridge, "is_uplink_reachable", lambda: True)
    invocation = {}

    class FakeCompletedProcess:
        returncode = 0
        stdout = '{"result": "Private reply"}'
        stderr = ""

    def fake_run(command, **kwargs):
        invocation["command"] = command
        invocation["kwargs"] = kwargs
        return FakeCompletedProcess()

    monkeypatch.setattr(_bridge_module.subprocess, "run", fake_run)

    result = bridge.dispatch("Private spoken request", agent="mia-car")

    assert result["ok"] is True
    audit_text = bridge.ask_log.read_text()
    assert "Private spoken request" not in audit_text
    assert "Private reply" not in audit_text
    assert stat.S_IMODE(bridge.state_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(bridge.ask_log.stat().st_mode) == 0o600
    command = invocation["command"]
    settings_index = command.index("--settings")
    assert command[settings_index + 1] == '{"cleanupPeriodDays": 30}'
    assert invocation["kwargs"]["cwd"] == _bridge_module.PROJECT_ROOT
