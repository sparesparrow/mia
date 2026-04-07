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

## First Validation Target

Initial platform focus is Audi A3 8V on MQB, approximately model years 2015 to 2019.

## First-Pass Constraints

- This module is intentionally standalone and is not wired into `automotive-mcp-bridge` yet
- No companion legacy agent is added under `orchestration/mia-agents/agents/`
- No schema changes are required for the scaffold

## Intended Next Step

After transport and capability wiring are stabilized, this bridge can be integrated as a sibling profile next to the existing Citroen-specific bridge.