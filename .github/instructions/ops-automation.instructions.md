---
description: "Use when working on deployment automation, Docker Compose, systemd, GitHub workflows, pre-commit hooks, monitoring, bootstrap, or operational scripts under infra/, containers/, monitoring/, .github/workflows/, or scripts/."
name: "Ops Automation Guidance"
applyTo:
  - "infra/**"
  - "containers/**"
  - "monitoring/**"
  - ".github/workflows/**"
  - ".pre-commit-config.yaml"
  - "docker-compose*.yml"
  - "orchestrator-config.yaml"
  - "scripts/**"
  - "complete-bootstrap.py"
---
# Ops Automation Guidance

- Treat `infra/` as the canonical home for deployable runtime configuration. Many files under `scripts/` are wrappers or legacy helpers; change the canonical Compose, systemd, or deploy asset first and then update wrappers that depend on it.
- Preserve the Raspberry Pi deployment anchor points already used across the repo: `/opt/mia`, `infra/systemd/*.service`, and the bundled-Python flow in `scripts/ensure-bundled-cpython.sh`.
- Keep automation rerunnable and explicit about privilege boundaries. Shell scripts should fail fast, log what they changed, and accept host or path overrides through environment variables when the repo already does so.
- When changing service wiring, update all relevant operational surfaces together:
  - container startup under `infra/docker/`
  - systemd startup under `infra/systemd/`
  - CI and release wiring under `.github/workflows/`
  - remote and bootstrap flows under `scripts/`
- Preserve startup-order assumptions. Broker before API before workers is a deployment invariant, not just an implementation detail.
- Workflow and hook changes are part of the delivery path. Keep workflow triggers, repo paths, artifact names, and script entry points aligned with the real tree so CI does not silently drift from local automation.
- Monitoring changes are operational changes too. If ports, service names, or health endpoints move, audit the matching Prometheus, Grafana, Loki, smoke-test, and health-check assets in the same change.
- Useful validation:
  - `docker compose -f infra/docker/docker-compose.yml config`
  - `docker compose -f docker-compose.pi-simulation.yml config`
  - `pre-commit run --all-files`
  - `bash scripts/ensure-bundled-cpython.sh`
  - `python3 scripts/validate-mia-deployment.py`
- Related docs: [docs/PRODUCTION_DEPLOYMENT.md](../../docs/PRODUCTION_DEPLOYMENT.md), [docs/RASPBERRY_PI_SETUP.md](../../docs/RASPBERRY_PI_SETUP.md), [docs/ci-cd-setup.md](../../docs/ci-cd-setup.md), [docs/troubleshooting.md](../../docs/troubleshooting.md), and [../copilot-instructions.md](../copilot-instructions.md).