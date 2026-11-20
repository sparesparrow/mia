# 0022. Claude Code is the LLM dispatch backend; it supersedes claudepy-bridge

- Status: Accepted
- Date: 2026-11-20
- Requirements: REQ-ORCH-010, REQ-ORCH-011, REQ-ORCH-012, REQ-VOICE-029

## Context
`EnhancedOrchestrator.handle_enhanced_voice_command()` parses intents with a keyword matcher and, for anything it
can't map to a known `service_mapping` entry, calls `_route_enhanced_command` (`orchestration/mcp/modules/
core-orchestrator/enhanced_orchestrator.py:1176`). Today that unmatched-intent path has no real destination:
`claudepy-bridge` (`orchestration/mcp/modules/claudepy-bridge/`) is a documented seam for a multi-provider
(Anthropic → Kimi → Gemini) orchestrator via an external `claudepy` package, but it is not wired into
`_route_enhanced_command` and `claudepy` is not a dependency of this repo.

Separately, a standalone prototype this session (`~/.claude/quest-rc/`, not part of this repo) proved a working,
safety-gated design for exactly this kind of dispatch: a fixed-in-code per-agent tool allowlist, a lock serializing
`claude -p --resume` calls per session, and a read-back/audit log — running against a Meta Quest headset's voice
console talking to a dev PC. The Raspberry Pi already has Claude Code 2.1.329 installed and logged in to the same
account (verified: `ssh mia@mia claude auth status` → `loggedIn: true`, Pro plan), so it can run this natively,
with no dependency on the dev PC or on `claudepy`.

A single-provider (Anthropic-only, via the `claude` CLI already present) dispatch path is simpler, has no new
third-party dependency, and reuses a design already proven working end-to-end. This ADR picks it over finishing
the `claudepy` integration.

## Decision
- **`claude-agent-bridge` (`orchestration/mcp/modules/claude-agent-bridge/`) is the real, wired implementation of
  `_route_enhanced_command`'s LLM-dispatch fallback.** It supersedes `claudepy-bridge` for this purpose;
  `claudepy-bridge` is left in place (it may still be useful for genuine multi-provider fallback later) but is no
  longer the intended path for unmatched voice intents — a future ADR would be needed to reintroduce it.
- `ClaudeAgentBridge.dispatch(prompt, agent)` (`bridge.py`) shells out to `claude -p --agent <agent> --model haiku
  --session-id/--resume <per-agent uuid> --output-format json`, with `--allowedTools`/`--disallowedTools` set from
  a fixed-in-code `AGENTS` dict — never from the request, the transcript, or any data read at runtime. This mirrors
  the quest-rc prototype's safety model exactly (see that module's own history for why: an earlier attempt to let
  `--allowedTools` be empty-meaning-unrestricted was caught and fixed there first).
- Bridge state lives under the service user's XDG state directory (or the explicit
  `CLAUDE_AGENT_BRIDGE_STATE_DIR` override) with directory/file modes restricted to that user. The audit log records
  timestamps, agent, interaction ID, lengths and outcome only; it does not duplicate transcript or response text.
  Claude Code transcript cleanup is explicitly set to 30 days for each bridge session.
- `AGENTS["mia-car"]` is read-only: only exact `curl` GET commands to
  `http://localhost:8000/{telemetry,status,devices}`, with no path wildcards. The child CLI inherits the
  orchestrator's `MIA_API_KEY` for installations where the API requires authentication. Per ADR-0006
  (vehicle access is passive/read-only by default), it must never gain a write/control tool. The agent's own system
  prompt (`.claude/agents/mia-car.md`) repeats this as a second, independent line of defense, not a substitute for
  the tool-level restriction.
- `is_uplink_reachable()` does a 3 s `HEAD` to `api.anthropic.com` before every dispatch. Gated behind this check:
  on failure, `_route_enhanced_command` must fall back to its existing "no service available for intent" response
  rather than hang a voice turn on a dead uplink (phone hotspot dropped, no SIM data, etc.) — the car has no
  indefinite-wait budget while driving.
- Feature-gated behind `CLAUDE_AGENT_BRIDGE=1` (off by default, same convention as `VOICE_PHONE_MIC` in ADR-0021),
  so existing deployments are unaffected until explicitly enabled.
- This module can be deployed alongside the enhanced orchestrator on the Pi (car/offline context, agent `mia-car`)
  and can be imported by a future
  dev-PC-side service for the home context; the Quest-specific `/rc` page's own fixed adb actions and its
  `adb-quest`/`general-rc` agents stay in `~/.claude/quest-rc/` unchanged (not part of this repo, not read-only,
  intentionally different safety profile — it controls a headset, not a moving vehicle).

## Consequences
- One LLM dispatch path to maintain and reason about, not two half-wired ones.
- A misrecognized voice command in the car can, at most, trigger a read-only HTTP GET — it cannot move anything.
- No new third-party dependency (`claudepy` was never installed; this doesn't need it).
- This ADR is design plus a first module; the live Pi dispatch remains untested — see
  `spec/requirements/orchestration.yaml` and `voice.yaml`, not claimed here.

## Sources
`orchestration/mcp/modules/core-orchestrator/enhanced_orchestrator.py`, `orchestration/mcp/modules/claudepy-bridge/
mia_claudepy_bridge.py`, `orchestration/mcp/modules/claude-agent-bridge/bridge.py`, `.claude/agents/mia-car.md`,
ADR-0006, ADR-0010, ADR-0013, ADR-0020, ADR-0021.
