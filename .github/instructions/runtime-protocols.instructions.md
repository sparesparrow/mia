---
description: "Use when changing runtime message flow between services, including ZeroMQ envelopes, MQTT topics, WebSocket payloads, REST handoffs, or MCP transport surfaces."
name: "Runtime Protocol Guidance"
applyTo:
  - "contracts/topics.md"
  - "contracts/events.md"
  - "apps/rpi-backend/shared/messaging/**"
  - "apps/rpi-backend/py-api/api/**/*.py"
  - "orchestration/mcp/modules/shared/mcp_framework.py"
  - "orchestration/mcp/modules/**/main.py"
  - "orchestrator-config.yaml"
  - "web/voice-chat.html"
  - "web/voice-chat.js"
---
# Runtime Protocol Guidance

- Use this guidance for runtime envelopes, ports, topics, routes, and handshakes. Use the schema-contracts guidance when a FlatBuffers schema, generated binding, or other serialized payload definition changes.
- Preserve the current runtime split:
  - `apps/rpi-backend/shared/messaging/broker.py` handles control-plane routing over ROUTER/DEALER on port `5555`.
  - Telemetry fan-out is PUB/SUB, with most active code and docs expecting `5556`.
  - Browser and mobile realtime entry still comes through FastAPI `/ws`.
  - MCP JSON-RPC transport helpers live in `orchestration/mcp/modules/shared/mcp_framework.py`.
- Keep correlation fields stable where they already exist: `request_id`, `client_id`, `worker_type`, `command`, and `data`. Worker registration still uses `WORKER_REGISTER`, so protocol changes must keep registration and reply routing compatible.
- When changing MQTT or event naming, update `contracts/topics.md`, `contracts/events.md`, and every publisher or subscriber in the same change. Topic drift is a runtime bug, not a docs-only issue.
- Validate existing port references before "standardizing" them. This repo already contains mixed telemetry-port assumptions, so check active code, config, and deployment assets together instead of updating one constant in isolation.
- Keep WebSocket and HTTP clients aligned with the backend boundary. If `/ws`, `/status`, `/devices`, or command payloads change, audit matching use in `web/` and orchestration modules instead of assuming the server is the only consumer.
- Prefer additive protocol evolution. If you must rename a field, route, or topic, either ship a compatibility path or update all touched consumers in one change.
- Useful validation:
  - `curl http://localhost:8000/status`
  - `pytest tests/ -m "not hardware"`
  - `bash scripts/system-tests.sh` for changes that span multiple services
- Related docs: [contracts/topics.md](../../contracts/topics.md), [contracts/events.md](../../contracts/events.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), [README.md](../../README.md), and [../copilot-instructions.md](../copilot-instructions.md).