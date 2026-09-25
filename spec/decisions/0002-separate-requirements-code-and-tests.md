# 0002. Separate requirements, production code and tests at the top level

- Status: Accepted
- Date: 2026-09-25
- Requirements: REQ-NFR-004

## Context
The February 2026 restructure moved runtime code into `apps/`, `orchestration/` and
`infra/`, but 37 top-level directories remained, tests were split between `tests/` and
module folders (some never collected), and nothing tied code or tests to requirements.

## Decision
The top level has three kinds of content:

1. **Requirements and design:** `spec/` (requirements, ADRs, architecture, interfaces, evidence).
2. **Production code:** `apps/`, `orchestration/`, `schemas/`, `infra/`, `web/`, `agents/`
   and vendored `external/`.
3. **Tests and the test environment:** `tests/`. Android and C++ unit tests stay beside
   their Gradle and CMake builds because those tools require it.

`docs/` holds operator and user guides; `tools/` holds developer tooling.

## Consequences
- Every Python test runs from `tests/` and declares the requirements it covers.
- Moving code changes deployment paths (`/opt/mia/...`), so moves update systemd units,
  compose files and CI in the same change.

## Sources
`spec/architecture/README.md`; the reorganisation PR.
