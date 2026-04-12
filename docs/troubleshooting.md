# Troubleshooting (L1/L2/L3)

## Docker / Compose
- Canonical Compose files live in `infra/docker/`; use `docker compose -f infra/docker/docker-compose.dev.yml config` to validate the dev stack before starting it.
- The root-level `docker-compose.pi-simulation.yml` keeps only the runnable broker/state services enabled by default. Add `--profile legacy-sim` only if you also maintain the older simulator images.
- If `docker compose build` fails while pulling base images with a `gpg: public key decryption failed` or Docker credential timeout, fix the local Docker credential helper first and retry the build.

## L1 – Základní ověření
- Napájení: PD/QC adaptér, kabely, pojistka
- ESP32 viditelné v BLE? RSSI > −80 dBm
- OBD data přichází? fuel/rpm v dashboardu
- Kamera obraz/ANPR povoleno?

## L2 – Síť a messaging
- MQTT broker běží? reconnect logy
- Wi‑Fi Direct/SoftAP throughput ověřen
- mDNS discovery (Android ↔ Pi) funkční

## L3 – Diagnostika a logy
- Export logů z aplikace (DrivingService, BLE, ANPR)
- ESP32: seriová linka, bitrate/filtry, watchdog
- Pi gateway: RTSP ingest, disk prostor, healthchecks

Pokud problém přetrvá, založte issue s logy a verzemi zařízení.
