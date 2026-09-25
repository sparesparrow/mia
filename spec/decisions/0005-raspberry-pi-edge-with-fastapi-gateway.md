# 0005. Raspberry Pi 4B edge runtime with a FastAPI gateway on 8000

- Status: Accepted
- Date: 2026-09-25 (recording an existing decision)
- Requirements: REQ-NET-002, REQ-NET-003, REQ-AND-015, REQ-DEP-001

## Context
The system must run in the car without cloud connectivity, and the Android app and web
clients need one stable entry point.

## Decision
- A Raspberry Pi 4B is the primary runtime; services run as systemd units under `/opt/mia`.
- A FastAPI gateway on port 8000 is the only HTTP/WebSocket surface for clients; it talks to
  workers over ZeroMQ.

## Consequences
- The REST response shapes are a contract with the Android client and are tested as such.
- Anything a client needs must be exposed through the gateway, not by opening worker ports.

## Sources
`CLAUDE.md`, `spec/architecture/lean-architecture.md`, `apps/rpi-backend/py-api/api/main.py`,
`infra/systemd/mia-api.service`.
