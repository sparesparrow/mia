---
description: "Use when working on repo-wide Python code outside Android- and backend-specific instruction scopes, especially orchestration modules, root scripts, shared tests, and dependency files."
name: "Python Monorepo Guidance"
applyTo:
  - "*.py"
  - "orchestration/**/*.py"
  - "scripts/**/*.py"
  - "tests/**/*.py"
  - "tools/**/*.py"
  - "modules/**/*.py"
  - "services/**/*.py"
  - "requirements*.txt"
  - "orchestration/mcp/modules/**/requirements.txt"
---
# Python Monorepo Guidance

- Treat root `requirements*.txt` files as the repo-wide Python baseline. Use `requirements-dev.txt` for local validation, `requirements-ci.txt` when CI or low-resource environments need the smaller set, and per-module `requirements.txt` only when that module is intentionally deployable on its own.
- Match the root test and lint contract already defined in the repo:
  - `pytest tests/ -m "not hardware"`
  - `pytest -m integration`
  - `black . && isort . --profile black && flake8 . --max-line-length=120 --extend-ignore=E203,W503`
- Keep optional integrations optional. Many Python surfaces in `orchestration/mcp/modules/` and `scripts/` are written to survive missing audio, serial, Docker, BLE, or vendor SDK dependencies; prefer guarded imports and degraded behavior over hard startup failures.
- Preserve repo-wide response and lifecycle patterns where they already exist: structured `status` and `message` payloads, `initialize()` and `shutdown()` for MCP modules, and async-friendly service code.
- Minimize new `sys.path` hacks. Some legacy scripts patch import paths to stay runnable from the repo root; if you touch them, keep the entry point working, but prefer package-relative or module-local structure in new code.
- Put reusable logic in the owning shared area instead of copying helper code across scripts. In practice that usually means `orchestration/mcp/modules/shared/`, an existing package directory, or a local utility module next to the caller.
- When changing dependency files, audit the matching runtime or module entry point instead of assuming the root environment is the only consumer.
- Related docs: [requirements-dev.txt](../../requirements-dev.txt), [requirements-ci.txt](../../requirements-ci.txt), [pytest.ini](../../pytest.ini), [CLAUDE.md](../../CLAUDE.md), and [../copilot-instructions.md](../copilot-instructions.md).