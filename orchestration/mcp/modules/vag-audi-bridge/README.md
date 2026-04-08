# VAG Audi Bridge

Read-only bridge scaffold for Audi and VAG diagnostics inside MIA.

## Scope

- Passive telemetry ingestion from an existing transport stream
- Optional read-only UDS DID and DTC access
- No coding, adaptations, ECU reset, routine control, security access, or write services

## Safe Defaults

- Passive monitoring is enabled
- UDS polling is disabled
- Extended sessions are disabled
- Security access is disabled
- Write operations are disabled
- The only default DID hint is `F190` for VIN, and it is not queried unless UDS polling is explicitly enabled

## Capability Reporting

- Status surfaces expose a coarse `capability_class`: `unknown`, `generic_pid_only`, or `uds_read_only`
- Read-only UDS requests are gated by both runtime policy and transport capability class
- Adapter facts such as transport kind, protocol hint, last PID success, and last UDS success are reported additively for clients

## First Validation Target

Initial platform focus is Audi A3 8V on MQB, approximately model years 2015 to 2019.

## Current Constraints

- This module is wired into `automotive-mcp-bridge` when the bridge is available and enabled
- No companion legacy agent is added under `orchestration/mia-agents/agents/`
- No schema changes are required for the scaffold
- Live Audi-specific UDS transport is still not connected

## Intended Next Step

After transport and capability wiring are stabilized, this bridge can move from scaffolded read-only status surfaces to verified Pi-backed VIN, DTC, and DID reads on a known-good target vehicle.