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
from typing import Optional

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


class ClaudeAgentBridge:
    """One instance per deployment (Pi, dev PC, ...). Holds per-agent session
    state so repeated calls continue the same conversation via --resume."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or (MODULE_DIR / "state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ask_log = self.state_dir / "ask_log.jsonl"
        self.lock = threading.Lock()

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

        return {"ok": ok, "result": result, "error": error}
