"""Claude Agent Bridge: in-process `claude -p` dispatch for MIA's voice pipeline.

See spec/decisions/0022-claude-agent-dispatch.md. Ports the agent-allowlist
and gated-execution design proven in a standalone prototype
(`~/.claude/quest-rc/relay_server.py`, a Quest-headset voice console) into
MIA's orchestrator as the real `_route_enhanced_command` LLM-dispatch path.

Safety model (do not weaken without a new ADR):
- `AGENTS` is a fixed-in-code allowlist of {agent_name: allowed_tools}. Never
  accept an agent name or tool string from a request/transcript/intent —
  only from this module's own constant.
- An agent with no tools gets `--disallowedTools` naming the risky
  categories explicitly (`--restricted` also disables custom-agent loading,
  which breaks `--agent <name>` — do not use it here).
- `ASK_LOCK` serializes `claude -p` calls so concurrent requests can't race
  on the same agent's `--resume` session id.
- Every call is logged to `ask_log.jsonl` as an audit trail.
- `on_handoff`, if given, hears "orchestrator -> executor" before a dispatch and
  "executor -> orchestrator" after it, for the Pi's web console (ADR-0029,
  REQ-WEB-007). It only reports; a failing callback never changes a dispatch.
"""

import json
import os
import re
import subprocess
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Callable, Optional

MODULE_DIR = Path(__file__).parent

# Fixed in code — see bridge safety model above. `mia-car` is read-only per
# ADR-0006 (vehicle access is passive/read-only by default): it may only
# GET MIA's own local API, never run arbitrary Bash, never Write/Edit.
AGENTS = {
    "mia-car": "Bash(curl -s http://localhost:8000/telemetry*),"
               "Bash(curl -s http://localhost:8000/status*),"
               "Bash(curl -s http://localhost:8000/devices*)",
    "general-rc": "",  # no tools at all — plain conversational fallback
}

ANTHROPIC_REACHABILITY_URL = "https://api.anthropic.com"
REACHABILITY_TIMEOUT_S = 3

# (from_role, to_role, task, summary) -> None
HandoffCallback = Callable[[str, str, str, str], None]
HANDOFF_TEXT_MAX = 140
CONSOLE_URL = "http://127.0.0.1:8000"
CONSOLE_TIMEOUT_S = 2


def console_reporter(base_url: Optional[str] = None, api_key: Optional[str] = None) -> HandoffCallback:
    """A callback that posts each handoff to the web console's `POST /console/agents/events`.

    The post runs on a daemon thread with a short timeout, so a slow or missing API never delays a voice
    turn. The key comes from `MIA_API_KEY` unless given; the console needs the write scope.
    """
    url = (base_url or os.environ.get("MIA_CONSOLE_URL", CONSOLE_URL)).rstrip("/") + "/console/agents/events"
    key = api_key if api_key is not None else os.environ.get("MIA_API_KEY", "")

    def post(from_role: str, to_role: str, task: str, summary: str) -> None:
        body = json.dumps({"from_role": from_role, "to_role": to_role, "task": task, "summary": summary})
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = key
        request = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers, method="POST")

        def send() -> None:
            try:
                urllib.request.urlopen(request, timeout=CONSOLE_TIMEOUT_S).close()
            except Exception:  # noqa: BLE001 - the console is optional; a lost handoff is only a lost line
                pass

        threading.Thread(target=send, name="mia-handoff-report", daemon=True).start()

    return post


def _short(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= HANDOFF_TEXT_MAX else text[: HANDOFF_TEXT_MAX - 1] + "…"


class ClaudeAgentBridge:
    """One instance per deployment (Pi, dev PC, ...). Holds per-agent session
    state so repeated calls continue the same conversation via --resume."""

    def __init__(self, state_dir: Optional[Path] = None, on_handoff: Optional[HandoffCallback] = None):
        self.state_dir = state_dir or (MODULE_DIR / "state")
        self.on_handoff = on_handoff
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ask_log = self.state_dir / "ask_log.jsonl"
        self.lock = threading.Lock()

    def _handoff(self, from_role: str, to_role: str, task: str, summary: str) -> None:
        if self.on_handoff is None:
            return
        try:
            self.on_handoff(from_role, to_role, task, _short(summary))
        except Exception:  # noqa: BLE001 - reporting must never change a dispatch
            pass

    def _session_file(self, agent: str) -> Path:
        return self.state_dir / f"session_{agent}.txt"

    def _started_file(self, agent: str) -> Path:
        return self.state_dir / f".started_{agent}"

    def _session_id_for(self, agent: str) -> str:
        f = self._session_file(agent)
        if not f.exists():
            f.write_text(str(uuid.uuid4()))
        return f.read_text().strip()

    def is_uplink_reachable(self) -> bool:
        """Cheap reachability check before dispatching — never hang a voice
        turn on a dead uplink (phone hotspot dropped, no SIM data, etc.)."""
        try:
            req = urllib.request.Request(ANTHROPIC_REACHABILITY_URL, method="HEAD")
            urllib.request.urlopen(req, timeout=REACHABILITY_TIMEOUT_S)
            return True
        except Exception:
            return False

    def dispatch(self, prompt: str, agent: str, model: str = "haiku",
                 max_turns: int = 6, timeout: int = 120) -> dict:
        """Run one `claude -p` turn against `agent`. Returns
        {"ok": bool, "result": str, "error": str|None}. Never raises for a
        reachability/timeout/subprocess failure — the caller (voice pipeline)
        must always get a spoken-back answer, including "I'm offline"."""
        if agent not in AGENTS:
            return {"ok": False, "result": "", "error": f"unknown agent '{agent}'"}
        if not prompt.strip():
            return {"ok": False, "result": "", "error": "empty prompt"}
        if not self.is_uplink_reachable():
            return {"ok": False, "result": "", "error": "uplink unreachable"}

        allowed_tools = AGENTS[agent]
        sid = self._session_id_for(agent)
        started_file = self._started_file(agent)
        started = started_file.exists()

        cmd = ["claude", "-p", prompt, "--agent", agent, "--model", model,
               "--max-turns", str(max_turns), "--output-format", "json"]
        if allowed_tools:
            cmd += ["--allowedTools", allowed_tools]
        else:
            cmd += ["--disallowedTools", "Bash Write Edit NotebookEdit WebFetch Agent"]
        cmd += ["--resume", sid] if started else ["--session-id", sid]

        entry = {"ts": time.time(), "agent": agent, "prompt": prompt}
        self._handoff("orchestrator", "executor", agent, prompt)
        try:
            with self.lock:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if not started and p.returncode == 0:
                    started_file.write_text("1")
            try:
                data = json.loads(p.stdout)
                result = data.get("result", "")
            except Exception:
                result = p.stdout.strip() or p.stderr.strip()
            entry["result"] = result
            entry["returncode"] = p.returncode
            ok = p.returncode == 0
            error = None if ok else (p.stderr.strip() or "non-zero exit")
        except subprocess.TimeoutExpired:
            result, ok, error = "", False, "timeout"
            entry["result"], entry["error"] = result, error

        with self.ask_log.open("a") as f:
            f.write(json.dumps(entry) + "\n")

        self._handoff("executor", "orchestrator", agent, result if ok else f"failed: {error}")

        return {"ok": ok, "result": result, "error": error}
