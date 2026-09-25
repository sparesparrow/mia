# Architecture decision records

Each file records one decision: what was decided, why, and what it costs. A decision
that changes gets a new record that supersedes the old one; old records are not edited
beyond their status line.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-record-decisions-and-keep-the-backlog-in-issues.md) | Record decisions as ADRs; keep the backlog in GitHub Issues | Accepted |
| [0002](0002-separate-requirements-code-and-tests.md) | Separate requirements, production code and tests at the top level | Accepted |
| [0003](0003-zeromq-control-plane-and-telemetry.md) | ZeroMQ control plane on 5555, telemetry PUB/SUB on 5556 | Accepted |
| [0004](0004-flatbuffers-wire-format.md) | FlatBuffers wire format with committed bindings | Accepted |
| [0005](0005-raspberry-pi-edge-with-fastapi-gateway.md) | Raspberry Pi 4B edge runtime with a FastAPI gateway on 8000 | Accepted |
| [0006](0006-passive-vehicle-access-by-default.md) | Vehicle access is passive by default | Accepted |
| [0007](0007-simulation-fallback-for-hardware.md) | Hardware code must fall back to simulation | Accepted |
| [0008](0008-audi-a4-8h-primary-citroen-secondary.md) | Audi A4 Cabriolet 8H is the primary vehicle; Citroën C4 is secondary on 5557 | Accepted |
| [0009](0009-canonical-vehicle-telemetry-envelope.md) | Canonical vehicle telemetry envelope v1 | Accepted |
| [0010](0010-evidence-based-requirement-status.md) | Requirement status is evidence-based | Accepted |

## Template

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD
- Requirements: REQ-...

## Context
Why a decision is needed and what constrains it.

## Decision
What we do.

## Consequences
What gets easier, what gets harder, what we now must keep true.

## Sources
Where the decision is evidenced (code, docs, commits).
```
