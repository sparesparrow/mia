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
- The instance lock serializes `claude -p` calls so concurrent requests can't race
  on the same agent's `--resume` session id.
- Calls are logged to a private `ask_log.jsonl` without transcript text.
"""

import json
import logging
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[4]

# Fixed in code — see bridge safety model above. `mia-car` is read-only per
# ADR-0006 (vehicle access is passive/read-only by default): it may only
# GET MIA's own local API, never run arbitrary Bash, never Write/Edit.
AGENTS = {
    "mia-car": (
        'Bash(curl -s -H "X-API-Key: $MIA_API_KEY" http://localhost:8000/telemetry),'
        'Bash(curl -s -H "X-API-Key: $MIA_API_KEY" http://localhost:8000/status),'
        'Bash(curl -s -H "X-API-Key: $MIA_API_KEY" http://localhost:8000/devices)'
    ),
    "general-rc": "",  # no tools at all — plain conversational fallback
}

ANTHROPIC_REACHABILITY_URL = "https://api.anthropic.com"
REACHABILITY_TIMEOUT_S = 3


class ClaudeAgentBridge:
    """One instance per deployment (Pi, dev PC, ...). Holds per-agent session
    state so repeated calls continue the same conversation via --resume."""

    def __init__(self, state_dir: Optional[Path] = None):
        if state_dir is None:
            state_root = Path(
                os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
            )
            state_dir = Path(
                os.environ.get(
                    "CLAUDE_AGENT_BRIDGE_STATE_DIR",
                    str(state_root / "mia" / "claude-agent-bridge"),
                ) or state_root / "mia" / "claude-agent-bridge"
            )
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state_dir, 0o700)
        self.ask_log = self.state_dir / "ask_log.jsonl"
        self.lock = threading.Lock()

    def _session_file(self, agent: str) -> Path:
        return self.state_dir / f"session_{agent}.txt"

    def _started_file(self, agent: str) -> Path:
        return self.state_dir / f".started_{agent}"

    def _session_id_for(self, agent: str) -> str:
        f = self._session_file(agent)
        if not f.exists():
            self._write_private(f, str(uuid.uuid4()))
        return f.read_text().strip()

    def is_uplink_reachable(self) -> bool:
        """Cheap reachability check before dispatching — never hang a voice
        turn on a dead uplink (phone hotspot dropped, no SIM data, etc.)."""
        try:
            req = urllib.request.Request(ANTHROPIC_REACHABILITY_URL, method="HEAD")
            with urllib.request.urlopen(req, timeout=REACHABILITY_TIMEOUT_S):
                pass
            return True
        except urllib.error.HTTPError:
            # A 4xx/5xx response still proves that the host is reachable. The
            # endpoint need not serve a successful response to a bare HEAD.
            return True
        except Exception:
            return False

    @staticmethod
    def _write_private(path: Path, contents: str, *, append: bool = False) -> None:
        flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else os.O_TRUNC)
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "a" if append else "w", encoding="utf-8") as stream:
            stream.write(contents)
        os.chmod(path, 0o600)

    def _append_audit_entry(self, entry: dict) -> None:
        self._write_private(self.ask_log, json.dumps(entry) + "\n", append=True)

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

        # Keep transcript text out of MIA's audit log. The CLI owns its
        # resumable session history; this log records only interaction metadata.
        entry = {
            "ts": time.time(),
            "interaction_id": str(uuid.uuid4()),
            "agent": agent,
            "prompt_chars": len(prompt),
        }
        with self.lock:
            allowed_tools = AGENTS[agent]
            sid = self._session_id_for(agent)
            started_file = self._started_file(agent)
            started = started_file.exists()

            cmd = [
                "claude",
                "-p",
                prompt,
                "--agent",
                agent,
                "--model",
                model,
                "--max-turns",
                str(max_turns),
                "--output-format",
                "json",
                "--settings",
                json.dumps({"cleanupPeriodDays": 30}),
            ]
            if allowed_tools:
                cmd += ["--allowedTools", allowed_tools]
            else:
                cmd += ["--disallowedTools", "Bash Write Edit NotebookEdit WebFetch Agent"]
            cmd += ["--resume", sid] if started else ["--session-id", sid]

            try:
                p = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=PROJECT_ROOT,
                )
                if not started and p.returncode == 0:
                    self._write_private(started_file, "1")
                try:
                    data = json.loads(p.stdout)
                    result = str(data.get("result", ""))
                except (TypeError, ValueError):
                    result = p.stdout.strip() or p.stderr.strip()
                entry["result_chars"] = len(result)
                entry["returncode"] = p.returncode
                ok = p.returncode == 0
                error = None if ok else (p.stderr.strip() or "non-zero exit")
            except subprocess.TimeoutExpired:
                result, ok, error = "", False, "timeout"
                entry["error"] = error
            except OSError as exc:
                result, ok, error = "", False, f"claude CLI unavailable: {exc}"
                entry["error"] = "claude CLI unavailable"

            try:
                self._append_audit_entry(entry)
            except OSError:
                logger.exception("Could not append the Claude Agent Bridge audit record")

        return {"ok": ok, "result": result, "error": error}
