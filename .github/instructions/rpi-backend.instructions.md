---
description: "Use when working on the Raspberry Pi backend, FastAPI routes, ZeroMQ broker or workers, hardware integrations, or systemd service wiring under apps/rpi-backend."
name: "RPi Backend Guidance"
applyTo:
  - "apps/rpi-backend/py-api/**"
  - "apps/rpi-backend/shared/**"
  - "infra/systemd/*.service"
---
# RPi Backend Guidance

- Keep the runtime boundary clear: FastAPI lives in `apps/rpi-backend/py-api/`, while broker and shared messaging code live in `apps/rpi-backend/shared/`. Avoid pushing broker or worker concerns into route handlers.
- Preserve the current ZeroMQ topology. The ROUTER/DEALER broker is the control plane on port 5555, and telemetry uses a separate PUB/SUB path. When changing ports, topics, or message types, audit API code, workers, deployment assets, and systemd units together.
- Startup order matters. [infra/systemd/mia-api.service](../../infra/systemd/mia-api.service) depends on [infra/systemd/zmq-broker.service](../../infra/systemd/zmq-broker.service), and workers depend on the broker being available first. Do not rename services or change ports without checking the whole chain.
- Preserve graceful fallback behavior for hardware code. Follow the existing pattern in [apps/rpi-backend/py-api/hardware/gpio_worker.py](../../apps/rpi-backend/py-api/hardware/gpio_worker.py): try `RPi.GPIO`, then `gpiozero`, then run in simulation mode instead of crashing on non-RPi machines.
- Keep worker lifecycle behavior intact. Workers register with `WORKER_REGISTER`, use `request_id` for correlation, and clean up sockets and contexts on shutdown. New workers should follow the same `start()`/`stop()` and registration pattern.
- Prefer optional imports with warnings over hard startup failures for integrations that are not always present. [apps/rpi-backend/py-api/api/main.py](../../apps/rpi-backend/py-api/api/main.py) already follows this pattern for auth, registry, and FlatBuffers decoding.
- Match the repo's existing service response style where applicable: structured payloads with `status` and `message` keys are common in Python service layers.
- Be careful with telemetry wiring changes. The repo currently contains multiple port references for subscriber and publisher paths, so verify the active code path and environment configuration before changing message flow behavior.
- Prefer non-hardware validation by default: `pytest tests/ -m "not hardware"` and `black . && isort . --profile black && flake8 . --max-line-length=120 --extend-ignore=E203,W503`. Use hardware-specific tests only when the change actually needs a Pi or attached device.
- When touching deployment or runtime wiring, validate with the existing operational surfaces: `curl http://localhost:8000/status`, `sudo systemctl status zmq-broker mia-api mia-gpio-worker mia-serial-bridge mia-obd-worker`, and the troubleshooting/deployment docs.
- Related docs: [apps/rpi-backend/py-api/README.md](../../apps/rpi-backend/py-api/README.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), [CLAUDE.md](../../CLAUDE.md), [docs/PRODUCTION_DEPLOYMENT.md](../../docs/PRODUCTION_DEPLOYMENT.md), [docs/RASPBERRY_PI_SETUP.md](../../docs/RASPBERRY_PI_SETUP.md), [docs/troubleshooting.md](../../docs/troubleshooting.md), and [../copilot-instructions.md](../copilot-instructions.md).