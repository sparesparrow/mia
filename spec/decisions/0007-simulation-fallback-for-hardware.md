# 0007. Hardware code must fall back to simulation

- Status: Accepted
- Date: 2026-09-25 (recording an existing decision)
- Requirements: REQ-NFR-001, REQ-HW-001, REQ-HW-003, REQ-HW-004, REQ-HW-006

## Context
CI and most development machines have no GPIO, serial MCU, CAN transceiver or camera.

## Decision
Every hardware-dependent component detects missing hardware and switches to a simulation
that produces realistic data, unless simulation is explicitly disabled.

## Consequences
- CI tests run the real code paths in simulation mode; they prove logic, not hardware.
  Hardware claims need `bench_tested` or stronger evidence (ADR-0010).
- Hardware-only tests are marked `hardware` and deselected in CI.

## Sources
`CLAUDE.md` conventions; `apps/rpi-backend/py-api/hardware/` simulation classes.
