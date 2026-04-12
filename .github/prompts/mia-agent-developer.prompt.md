---
mode: agent
description: "Agent & prompt developer — MCP modules, orchestration, prompt engineering, self-improvement loop"
---

# MIA Agent & Prompt Developer Worker

You own `orchestration/mcp/`, `.github/prompts/`, `.github/instructions/`, `.claude/`, and the MCP microservice ecosystem.

## MCP Module Inventory

| Module | Path | Purpose |
|--------|------|---------|
| Core Orchestrator | `modules/core-orchestrator/` | Command routing to MCP modules |
| Service Discovery | `modules/service-discovery/` | Registry + health checks |
| AI Audio Assistant | `modules/ai-audio-assistant/` | Whisper STT, ElevenLabs TTS, Spotify |
| AI Communications | `modules/ai-communications/` | Cross-service messaging |
| AI Platform Controllers | `modules/ai-platform-controllers/` | System command execution |
| AI Security | `modules/ai-security/` | Security scanning |
| Automotive Bridge | `modules/automotive-mcp-bridge/` | OBD-II interface |
| Citroën C4 Bridge | `modules/citroen-c4-bridge/` | PSA-specific vehicle bridge |
| Hardware Bridge | `modules/hardware-bridge/` | Hardware abstraction |
| Voice Learning | `modules/voice-learning/` | Adaptive voice commands |
| Security Scanner | `modules/security-scanner/` | Vulnerability detection |
| ClaudePy Bridge | `modules/claudepy-bridge/` | Python↔Claude integration |
| OBD Transport | `modules/obd-transport-agent/` | OBD transport layer |
| Messages MCP | `modules/messages_mcp/` | Message handling |
| Shared framework | `modules/shared/mcp_framework.py` | Base MCP lifecycle |

## MCP Module Lifecycle

```python
class MCPModule:
    async def initialize(self) -> None: ...   # setup connections
    async def shutdown(self) -> None: ...      # cleanup resources
    # Error responses: {"status": "...", "message": "..."}
```

## Prompt Locations

| Location | Purpose |
|----------|---------|
| `.github/prompts/` | VS Code Copilot prompt files |
| `.github/instructions/` | Copilot instruction files per domain |
| `.claude/agents.json` | Claude Code agent definitions |
| `.claude/skills/` | Reusable skill definitions |
| `orchestration/mcp/prompts/` | MCP-integrated prompt templates |

## When working here

1. MCP modules follow `initialize()`/`shutdown()` lifecycle — no constructor side effects
2. Shared framework in `modules/shared/` — don't duplicate into individual modules
3. Service discovery must register all modules with health check endpoints
4. Prompt files: `.prompt.md` for VS Code, `.json` for MCP prompts system
5. Instructions: one per domain (android, rpi-backend, schema-contracts)
6. Agent definitions in `.claude/agents.json` — orchestrator coordinates subagents
7. Self-improvement loop: capture successful patterns as new prompts via `create_prompt()`
