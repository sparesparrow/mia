"""Tests for the Claude Agent Bridge (ADR-0022).

The module directory is hyphenated, so it's loaded by path like the
existing claudepy-bridge test.
"""

import importlib.util
import json
import os
import sys

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


def test_mia_car_agent_is_read_only_by_tool_allowlist():
    """REQ-VOICE-029 / ADR-0006: the car agent may only read MIA's own API."""
    allowed = AGENTS["mia-car"]
    assert "curl -s http://localhost:8000/" in allowed
    for risky in ("Write", "Edit", "rm ", "POST", "PUT", "DELETE"):
        assert risky not in allowed


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


# ── Handoffs for the Pi's web console (ADR-0029, REQ-WEB-007) ─────────────


class _Done:
    def __init__(self, returncode=0, stdout='{"result": "coolant 89 C"}', stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _reachable_bridge(tmp_path, monkeypatch, on_handoff, completed=None):
    bridge = ClaudeAgentBridge(state_dir=tmp_path, on_handoff=on_handoff)
    monkeypatch.setattr(bridge, "is_uplink_reachable", lambda: True)
    monkeypatch.setattr(_bridge_module.subprocess, "run", lambda cmd, **kw: completed or _Done())
    return bridge


@pytest.mark.req("REQ-WEB-007")
def test_a_dispatch_is_reported_as_two_handoffs(tmp_path, monkeypatch):
    seen = []
    bridge = _reachable_bridge(tmp_path, monkeypatch, lambda *a: seen.append(a))
    result = bridge.dispatch("what is the coolant   temperature\n" + "x" * 300, agent="mia-car")
    assert result["ok"] is True
    (out_from, out_to, out_task, out_text), back = seen
    assert (out_from, out_to, out_task) == ("orchestrator", "executor", "mia-car")
    assert out_text.startswith("what is the coolant temperature x") and len(out_text) == 140
    assert back == ("executor", "orchestrator", "mia-car", "coolant 89 C")


@pytest.mark.req("REQ-WEB-007")
def test_a_failed_dispatch_is_reported_as_failed(tmp_path, monkeypatch):
    seen = []
    bridge = _reachable_bridge(tmp_path, monkeypatch, lambda *a: seen.append(a), _Done(1, "", "boom"))
    assert bridge.dispatch("status", agent="mia-car")["ok"] is False
    assert seen[-1] == ("executor", "orchestrator", "mia-car", "failed: boom")


@pytest.mark.req("REQ-WEB-007")
def test_nothing_is_reported_when_nothing_is_dispatched(tmp_path, monkeypatch):
    seen = []
    bridge = ClaudeAgentBridge(state_dir=tmp_path, on_handoff=lambda *a: seen.append(a))
    monkeypatch.setattr(bridge, "is_uplink_reachable", lambda: False)
    bridge.dispatch("status", agent="mia-car")
    bridge.dispatch("status", agent="not-an-agent")
    assert seen == []


@pytest.mark.req("REQ-WEB-007")
def test_a_failing_report_never_changes_the_dispatch(tmp_path, monkeypatch):
    def broken(*args):
        raise RuntimeError("console down")

    bridge = _reachable_bridge(tmp_path, monkeypatch, broken)
    assert bridge.dispatch("status", agent="mia-car") == {"ok": True, "result": "coolant 89 C", "error": None}


@pytest.mark.req("REQ-WEB-007")
def test_the_console_reporter_posts_the_handoff_with_the_key(monkeypatch):
    import threading

    sent = {}
    done = threading.Event()

    class _Response:
        def close(self):
            pass

    def fake_urlopen(request, timeout):
        sent.update(url=request.full_url, body=json.loads(request.data), key=request.get_header("X-api-key"),
                    method=request.get_method(), timeout=timeout)
        done.set()
        return _Response()

    monkeypatch.setattr(_bridge_module.urllib.request, "urlopen", fake_urlopen)
    report = _bridge_module.console_reporter("http://127.0.0.1:8000/", api_key="k")
    report("orchestrator", "executor", "mia-car", "status")
    assert done.wait(5)
    assert sent["url"] == "http://127.0.0.1:8000/console/agents/events" and sent["method"] == "POST"
    assert sent["body"] == {"from_role": "orchestrator", "to_role": "executor", "task": "mia-car", "summary": "status"}
    assert sent["key"] == "k" and sent["timeout"] == _bridge_module.CONSOLE_TIMEOUT_S


@pytest.mark.req("REQ-WEB-007")
def test_the_console_reporter_swallows_a_missing_console(monkeypatch):
    import threading

    tried = threading.Event()

    def refused(request, timeout):
        tried.set()
        raise OSError("connection refused")

    monkeypatch.setattr(_bridge_module.urllib.request, "urlopen", refused)
    _bridge_module.console_reporter("http://127.0.0.1:9", api_key="")("executor", "orchestrator", "mia-car", "x")
    assert tried.wait(5)
