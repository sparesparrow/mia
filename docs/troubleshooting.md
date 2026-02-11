# Troubleshooting (L1/L2/L3)

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
