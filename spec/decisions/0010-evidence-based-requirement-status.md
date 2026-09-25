# 0010. Requirement status is evidence-based

- Status: Accepted
- Date: 2026-09-25
- Requirements: REQ-NFR-004

## Context
The old feature catalog marked features TESTED or DEPLOYED without saying by what. Several
were deployed as systemd units but had no test, and none had been validated on the car.
A green CI run proves logic, not hardware.

## Decision
Each requirement carries one evidence state:

| State | Needs |
|---|---|
| `planned` / `blocked` | nothing |
| `implemented_untested` | code in `implemented_in` |
| `implemented_and_ci_tested` | at least one linked automated test, all passing in CI |
| `simulation_tested` | as above, against a replay or simulator |
| `bench_tested` | as above, plus a record in `spec/evidence/<REQ-ID>/` |
| `hardware_tested` | as above, on the target hardware |
| `vehicle_installed` | as above, installed in the vehicle |

CI can never promote a requirement beyond `simulation_tested`; the stronger states need a
recorded evidence file (date, setup, capture, result). The traceability check enforces both.

## Consequences
- Claims shrink to what is proven; untested code is visible as `implemented_untested`.
- Every PR states Claim, Proof, Not proven, Safety and Next owner.

## Sources
Project review of 2026-09-24 (evidence states and handoff rule); `tools/ci/traceability.py`.
