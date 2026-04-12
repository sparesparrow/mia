---
mode: agent
description: "RPi backend — FastAPI, ZeroMQ broker/workers, systemd services, hardware GPIO/serial integration"
---

# MIA RPi Backend Server Worker

You own `apps/rpi-backend/py-api/` and `apps/rpi-backend/cpp-audio/`. This is where MIA **lives** — the central nervous system.

## Boundaries

| Layer | Path | Tech |
|-------|------|------|
| REST/WS gateway | `py-api/api/main.py` | FastAPI :8000, WebSocket `/ws` |
| ZMQ broker | `shared/messaging/broker.py` | ROUTER-DEALER :5555 |
| ZMQ pub/sub | port 5556 | MCU telemetry fan-out |
| GPIO worker | `hardware/gpio_worker.py` | RPi.GPIO + simulation fallback |
| Serial bridge | `hardware/serial_bridge.py` | USB↔ZMQ for ESP32/Arduino |
| OBD worker | `services/obd_worker.py` | Digital Twin, virtual PTY |
| C++ audio | `cpp-audio/` | FFT, beat detection, hardware-server |
| Auth | `api/auth/` | API key middleware |

## Conventions

- Error responses: `{"status": "...", "message": "..."}` dicts — never raise HTTP exceptions in workers
- Workers register with broker on startup via DEALER socket
- All hardware imports wrapped in try-except with simulation fallback
- Systemd ordering: `mia-broker` → `mia-api` → workers
- Deployment target: `/opt/mia/` on RPi 4B
- Python 3.12, async-first, type-hinted

## Key Commands

```bash
pytest tests/ -m "not hardware"          # skip hardware tests
pytest tests/ -m integration             # integration suite
uvicorn api.main:app --host 0.0.0.0 --port 8000  # dev server
```

## When working here

1. Keep simulation fallbacks working — CI has no GPIO
2. Respect ZMQ message format: `{request_id, client_id, worker_type, command, data}`
3. Don't break service startup order
4. Match `{"status", "message"}` response shape in all workers
5. Reference `config/paths.json` for environment-dependent paths
