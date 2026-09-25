# 0006. Vehicle access is passive by default

- Status: Accepted
- Date: 2026-09-25 (recording an existing decision)
- Requirements: REQ-NFR-002, REQ-AUTO-006, REQ-AUTO-012

## Context
The prototype is a daily-driven Audi A4 Cabriolet 8H. A bug that transmits on a vehicle bus
or writes to an ECU can disable safety systems. A controller's listen-only mode is a register
that software can overwrite.

## Decision
- Default builds and installs only listen: the ESP32 listen-only build has no transmit path
  compiled in, and the VAG bridge keeps UDS disabled unless explicitly enabled.
- Coding, adaptation, security access, session escalation and all writes are out of scope.
- The car install also leaves the CAN transceiver TXD line physically disconnected;
  software evidence never replaces that.
- Active diagnostics, if ever added, are an isolated, explicitly armed mode with audit
  logging, and are not deployed on the daily-driver install.

## Consequences
- Tests prove the software half (no `twai_transmit` in the listen-only ELF; UDS off by
  default). The physical half needs a recorded evidence file in `spec/evidence/`.
- Features that need to transmit (OBD polling) exist only in the non-passive build.

## Sources
`TODO.md` "Audi/VAG read-only pilot" guardrails, `docs/automotive/audi-a4-8h-interface-integration.md`,
`apps/esp32/firmware-obd/components/ai_servis_obd/ai_servis_obd.c`, `infra/systemd/mia-vag-audi-bridge.service`.
