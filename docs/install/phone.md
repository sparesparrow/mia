# Install – Phone Edition (BYOD)

## Požadavky
- Android 11+ telefon s USB‑C napájením v autě (PD/QC 18–30W)
- ESP32 OBD/CAN bridge + transceiver (SN65HVD230/TJA1050)
- Volitelně UVC zadní kamera (powered OTG hub)

## Kroky
1) Zapojení OBD a napájení: viz [Wiring & Power](../wiring.md)
2) Spusťte Android aplikaci, povolte oprávnění (BLE/Camera/Location/Notifications)
3) Spusťte foreground DrivingService (persistentní notifikace)
4) Spárujte ESP32 přes BLE (QR kód, pairing klíče)
5) Ověřte OBD data (fuel, RPM, speed, coolant), nastavte VIN
6) Zapněte ANPR (CameraX), otestujte notifikace a TTS

## Ověření
- V MQTT feedu vidíte `vehicle/telemetry/{vin}/obd`
- Při SPZ detekci se objeví `vehicle/events/{vin}/anpr`

## Bezpečnost
- Read‑only OBD, žádné zápisy do ECU
- Edge-only zpracování, retenční slider v aplikaci
