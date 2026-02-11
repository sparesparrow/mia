# API & Contracts Overview

Tento projekt používá konzistentní kontrakty napříč Android/ESP32/Pi.

## MQTT Topics (výběr)
- `vehicle/telemetry/{vin}/obd` – fuel, rpm, speed, coolant, dtc[]
- `vehicle/events/{vin}/anpr` – plate_hash, confidence, snapshot_id
- `vehicle/alerts/{vin}` – severity, code, message
- `vehicle/cmd/{vin}/io` – relé/LED/buzzer

Detailní popis viz `contracts/topics.md`.

## Flow: Telemetry → Alert → Command

```mermaid
sequenceDiagram
  participant ESP as ESP32
  participant AND as Android
  participant BRO as MQTT Broker
  participant IO as IO Node

  ESP->>AND: BLE Telemetry Notify (CBOR)
  AND->>BRO: Publish vehicle/telemetry/{vin}/obd
  AND->>AND: Evaluate rules (fuel_low,temp_high)
  AND->>BRO: Publish vehicle/alerts/{vin}
  AND->>BRO: Publish vehicle/cmd/{vin}/io {"buzzer":"short"}
  BRO-->>IO: Deliver IO command
```

## Eventy
Příklady payloadů v `contracts/events.md`.

## BLE GATT
Služby/charakteristiky a OTA viz `contracts/ble-gatt.md`.

## Konfigurace
Schéma konfigurace zařízení/aplikace: `contracts/config.schema.json`.
