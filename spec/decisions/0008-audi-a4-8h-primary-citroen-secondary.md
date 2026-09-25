# 0008. Audi A4 Cabriolet 8H is the primary vehicle; Citroën C4 is secondary on 5557

- Status: Accepted
- Date: 2026-09-25 (recording an existing decision)
- Requirements: REQ-AUTO-005, REQ-AUTO-006

## Context
The project started on a Citroën C4 (PSA) and moved to a 2004 Audi A4 Cabriolet, body 8H
(not B3, which has no CAN). On the 8H the instrument cluster is the diagnostic gateway,
so comfort-bus signals are not readable at the OBD port.

## Decision
- The Audi A4 Cabriolet 8H is the primary prototype; new automotive work targets it first.
- The Citroën C4 bridge is maintained but secondary, and publishes vehicle telemetry on 5557,
  never on the MCU channel 5556.

## Consequences
- Signals are mapped per bus and per physical tap, with confidence recorded in
  `apps/rpi-backend/config/vehicles/audi_a4_8h_cabriolet.yaml`.
- The next target (A3 8V MQB) waits until the A4 8H path is stable.

## Sources
`CLAUDE.md`, `docs/automotive/audi-a4-8h-interface-integration.md`, commit fcbdfd2.
