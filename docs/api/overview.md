# API & Contracts Overview

Kontrakty mezi Pi, ESP32 a Android aplikací. Hlavní cesta vede přes Raspberry Pi
([ADR-0005](../spec/decisions/0005-raspberry-pi-edge-with-fastapi-gateway.md)); telefon bez Pi je omezený režim.

## Pi API (port 8000)
FastAPI brána je jediné HTTP/WebSocket rozhraní pro klienty. Když je na Pi nastavený `MIA_API_KEY`, každé volání
nese klíč v hlavičce `X-API-Key` ([ADR-0016](../spec/decisions/0016-android-reaches-the-pi-over-plain-http.md)).

- REST: `/status`, `/devices`, `/telemetry`, `/telemetry/cycle1`, `/command`, `/gpio/*`, `/led/*`, `/anpr/*`, `/features`
- WebSocket: `/ws`, `/ws/telemetry` (obálka `vehicle.telemetry` v1,
  [ADR-0009](../spec/decisions/0009-canonical-vehicle-telemetry-envelope.md)), `/ws/voice` (hlasová konzole,
  zapíná se `VOICE_CONSOLE=1`, [voice.md](../spec/interfaces/voice.md))
- Podrobný popis: [API Reference](mia-api-reference.md)

## Flow: vozidlo → Pi → telefon

```mermaid
sequenceDiagram
  participant CAN as CAN bus
  participant ESP as ESP32 (listen-only)
  participant PI as Raspberry Pi
  participant AND as Android

  CAN-->>ESP: rámce (jen příjem, TXD nezapojený)
  ESP->>PI: sériová linka
  PI->>PI: normalizace do obálky vehicle.telemetry v1
  AND->>PI: WebSocket /ws/telemetry + X-API-Key
  PI-->>AND: obálka (ignition, battery_voltage, engine_rpm, coolant_temp_c)
```

## MQTT
MQTT se používá jen na okrajích, kde ho zařízení nebo cizí systém potřebuje
([ADR-0003](../spec/decisions/0003-zeromq-control-plane-and-telemetry.md)). Jediný vnější kontrakt témat je
[topics.md](../spec/interfaces/topics.md) podle [ADR-0017](../spec/decisions/0017-mqtt-topic-namespace.md):

- `vehicle/telemetry/{vin}/obd` – fuel, rpm, speed, coolant, dtc[]
- `vehicle/events/{vin}/anpr` – plate_hash, confidence, snapshot_id
- `vehicle/alerts/{vin}` – severity, code, message

## Telefon bez Pi (omezený režim)
Bez Pi čte aplikace OBD sama přes BLE adaptér ve stylu ELM327, vyhodnocuje pravidla a publikuje na MQTT broker
v lokální síti. Toto **není** pasivní instalace: adaptér se na data aktivně ptá (viz
[instalace telefonu](../install/phone.md)).

```mermaid
sequenceDiagram
  participant OBD as OBD adaptér (BLE)
  participant AND as Android
  participant BRO as MQTT broker (LAN)

  AND->>OBD: dotazy na PID (ATZ, 010C, …)
  OBD-->>AND: odpovědi
  AND->>AND: pravidla (palivo, teplota)
  AND->>BRO: vehicle/telemetry/{vin}/obd, vehicle/alerts/{vin}
```

## Eventy
Příklady payloadů v [events.md](../spec/interfaces/events.md).

## BLE GATT
Služby a charakteristiky viz [ble-gatt.md](../spec/interfaces/ble-gatt.md). Aplikace dnes používá jen službu
Nordic UART.

## Konfigurace
Schéma konfigurace zařízení/aplikace: `schemas/json/config.schema.json`.
