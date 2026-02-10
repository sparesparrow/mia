# System Overview

## Komponenty
- Android app (hub): ANPR (CameraX), OBD (ELM327/ESP32-CAN), Voice, DVR-light
- ESP32 uzly: OBD/CAN bridge, IO (relé/LED/buzzer), volitelně S3-CAM snapshots
- Edge-compat (volitelné): Pi gateway (RTSP DVR, LPR offload, MQTT bridge)

## Datové toky
- BLE GATT: nízká latence telemetrie a příkazy (ESP32 ↔ Android)
- Wi‑Fi / Wi‑Fi Direct: video/OTA, MQTT over WS
- MQTT topics: `vehicle/telemetry/{vin}/obd`, `vehicle/events/{vin}/anpr`, `vehicle/alerts/{vin}`, `vehicle/cmd/{vin}/io`

## Privacy & Security
- Edge-only by default, retenční politika 24–72h, hashování SPZ (HMAC‑SHA256)
- Pairing QR + Ed25519; TLS pinning pro Wi‑Fi sessions

Více k protokolům a payloadům viz [API & Contracts](../api/overview.md).
