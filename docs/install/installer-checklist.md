# Installer Checklist (OBD/CAN, Power, Cameras)

## Pre‑install
- Ověř kompatibilitu (EU CAN 11‑bit @ 500k)
- Zkontroluj přístup k OBD a trasu kabelů; připrav pojistku 0.5–1A
- Připrav PD/QC nabíječku a držák telefonu s ventilací

## Hardware
- OBD splitter + CAN transceiver (SN65HVD230/TJA1050) zapojen dle [Wiring](../wiring.md)
- Buck 12V→5V (3–5A) pevně uchycen, společná zem s OBD
- ESP32 upevněno (vibrace), UVC hub napájený (pokud kamera)

## Software
- Pairing přes BLE (QR), VIN nastaveno, telemetry 10Hz ověřena
- ANPR aktivní, notifikace a TTS test
- MQTT připojení a health pings viditelné

## Validace
- Jízda 10–15 min: stabilita připojení, alerty (fuel/temp)
- Export krátkých logů (DrivingService, BLE, ANPR)
- Předání zákazníkovi: UI tour, privacy/retence, podpora
