# 0001. Record decisions as ADRs; keep the backlog in GitHub Issues

- Status: Accepted
- Date: 2026-09-25
- Requirements: all

## Context
Decisions, requirements, plans, ideas and to-dos were spread over `TODO.md`, `plan.md`,
per-app TODO files, `docs/plans`, `docs/superpowers`, a feature catalog and 21 GitHub
issues, with no IDs linking them. Nobody could tell which statements were decided,
which were wishes, and which were proven.

## Decision
- Requirements live in `spec/requirements/` with stable `REQ-<AREA>-NNN` IDs.
- Decisions live here as numbered ADRs.
- Open work of any kind (to-do, idea, validation task, test gap, missing ADR) is a GitHub
  issue that names the requirement it serves. There is no backlog file in the repo.

## Consequences
- A requirement, its decision and its open work can each be linked by ID.
- Planning documents no longer drift silently; when a plan is accepted its outcome becomes
  requirements and ADRs, and its open steps become issues.

## Sources
Repository reorganisation PR; issue #74 asked for this structure.
