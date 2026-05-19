# Raspberry Pi and Audi Integration

> **Audience**: Vehicle integrators, backend developers working on OBD-II

This document explains how MIA integrates an Audi vehicle through a Raspberry Pi gateway, what is already implemented in the repository, and where the current limits are.

## Primary Prototype Vehicle

**Audi A4 B3 Cabriolet (2004)** — this is the primary development and validation target for all automotive work in MIA.

Key characteristics:
- VAG platform with KWP2000 / early CAN-based UDS diagnostics
- CAN bus at 500 kbps, simpler topology than modern MQB/MLB (no central gateway module)
- Common engine variants: 1.8T (AMB/BFB), 2.4 V6 (BDV), 3.0 V6 (ASN/BBJ)
- Standard OBD-II PIDs fully supported
- Read-only UDS diagnostics achievable without complex gateway negotiation

## Integration Goal

For Audi support, the Raspberry Pi is the edge runtime that sits between the vehicle bus and the rest of MIA. Its job is to:

- collect transport data from an OBD-II interface or transport agent
- normalize safe read-only telemetry into MIA runtime surfaces
- expose vehicle state to orchestration, API, WebSocket, and Android consumers
- keep hardware-specific concerns on the Pi instead of pushing them into UI clients

The current Audi strategy is intentionally conservative: generic OBD where possible, passive ingestion first, and optional read-only UDS only after the transport path is stable.

## Why Audi Needs a Different Path

Audi vehicles fit under the wider VAG family, so the integration model is different from a simple SAE J1979-only adapter.

- Generic OBD PIDs cover baseline signals such as RPM, speed, coolant temperature, and fuel level.
- Deeper Audi diagnostics usually move into UDS over CAN and depend on module-specific identifiers.
- The 2004 A4 B3 Cabriolet has a simpler CAN topology than newer VAG platforms — no central gateway module blocking diagnostic access, which makes it a good prototype target.
- Many cheap ELM327 clones are good enough for standard PIDs but unreliable for sustained UDS work.
- Operations such as coding, adaptation, security access, routine control, and ECU resets should stay out of scope for MIA unless there is a dedicated safety and validation program.

That is why the repository currently treats Audi as a read-only integration problem, not a vehicle-coding platform.

## Recommended Starter Platform

The primary validation target is **Audi A4 B3 Cabriolet (2004)**.

Reasons:

- simpler CAN bus topology makes initial integration straightforward
- no central gateway module to negotiate (unlike MQB/MLB Evo platforms)
- standard OBD-II and basic VAG UDS diagnostics are accessible with common adapters
- realistic overlap with the generic telemetry already present in MIA
- available as the physical development vehicle

Future expansion targets (after A4 B3 is stable):
- Audi A3 8V on MQB (2015–2019) — widespread platform with strong community tooling
- Other VAG family vehicles sharing common diagnostic protocols

## Raspberry Pi Runtime Topology

| Component | Role in Audi integration |
| --- | --- |
| `apps/rpi-backend/shared/messaging/broker.py` | ZeroMQ ROUTER/DEALER control plane on port `5555` |
| ZeroMQ PUB/SUB telemetry path | vehicle and MCU telemetry fan-out on port `5556` |
| `apps/rpi-backend/py-api/api/main.py` | FastAPI boundary for HTTP and WebSocket consumers |
| `orchestration/mcp/modules/automotive-mcp-bridge/main.py` | command routing and vehicle-aware orchestration |
| `orchestration/mcp/modules/vag-audi-bridge/main.py` | read-only Audi/VAG telemetry and diagnostic scaffold |
| `hardware/serial_bridge.py` or other transport source | injects raw or normalized telemetry into the Pi runtime |

## Current Repository Status

The repository already contains a first-pass Audi path.

### Default Safety Posture

- passive monitoring enabled
- UDS polling disabled
- allowlisted read services limited to `0x19` and `0x22`
- default identifier hint limited to `F190` for VIN
- extended session disabled
- security access disabled
- write services disabled

### Audi Intents Already Routed

- `audi_vehicle_status`
- `audi_read_vin`
- `audi_read_dtc`
- `audi_read_identifiers`
- `audi_diagnostics`

## Recommended Validation Sequence

### 1. Bench Validation Without a Car

```bash
/bin/python3.13 -m unittest tests.test_vag_audi_bridge tests.test_automotive_mcp_bridge_vag
```

### 2. Raspberry Pi Runtime Validation

```bash
sudo systemctl status zmq-broker mia-api mia-serial-bridge mia-obd-worker
curl http://localhost:8000/status
```

### 3. In-Vehicle Passive Monitoring (Audi A4 B3 Cabriolet)

- Start with ignition on and passive telemetry only
- Verify speed, RPM, coolant, fuel, and voltage are stable
- Confirm no write, session, or security operations are attempted

### 4. Controlled Read-Only UDS Trial

- Enable UDS polling explicitly
- Start with VIN DID `F190`
- Add DTC summary reads through `0x19`

## Practical Next Step

The next useful engineering step is wiring a real Pi transport source into the VAG Audi bridge in read-only mode, validating VIN and DTC access on the Audi A4 B3 Cabriolet prototype, and only then widening the identifier set or expanding to newer VAG platforms.
