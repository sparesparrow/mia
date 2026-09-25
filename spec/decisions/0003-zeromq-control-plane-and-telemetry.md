# 0003. ZeroMQ control plane on 5555, telemetry PUB/SUB on 5556

- Status: Accepted
- Date: 2026-09-25 (recording an existing decision)
- Requirements: REQ-NET-001, REQ-HW-004, REQ-DEP-001

## Context
One vehicle, one Raspberry Pi, several Python workers, and an Android client. ROS2 was
rejected as too heavy for this scope (DDS overhead, weak Android support, Tier 3 on
Raspberry Pi OS). MQTT needs a broker process and adds latency for local IPC.

## Decision
- A ROUTER-DEALER broker on port 5555 routes requests between clients and workers.
- MCU telemetry fans out over PUB/SUB on port 5556.
- Vehicle telemetry from the vehicle bridges uses port 5557.
- MQTT is used only where a device or external system needs it.

## Consequences
- The broker must start before its dependants; systemd ordering enforces it and tests check it.
- Ports are part of the contract; changing one is an interface change.

## Sources
`spec/architecture/lean-architecture.md`, `spec/architecture/hybrid-messaging.md`,
`apps/rpi-backend/shared/messaging/broker.py`, `infra/systemd/zmq-broker.service`.
