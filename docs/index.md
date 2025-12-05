# MIA Documentation

MIA je modulární Car AI systém kombinující ANPR, OBD diagnostiku, hlasového asistenta a volitelný DVR gateway. Tento web shrnuje instalaci, architekturu, kontrakty a podporu.

## Rychlý přehled
- Phone Edition: Android jako hub + ESP32 OBD/IO. Viz [instalace](install/phone.md).
- Hybrid Edition: Telefon + mikro DVR/Pi. Viz [instalace](install/hybrid.md).
- Pro Edition: Vehicle PC/Pi5. Viz [instalace](install/pro.md).
 - Pi Gateway (Standalone): Raspberry Pi hostuje systém; Android volitelný. Viz [instalace](install/pi-gateway.md).

## Architektura
- Přehled komponent a datových toků: [System Overview](architecture/overview.md)
- Komunikace: BLE GATT, MQTT topics, mDNS

## Dráty a napájení
- OBD-II/CAN a napájení 12V→5V: [Wiring & Power](wiring.md)

## API & Contracts
- Events, MQTT topics, BLE GATT, config schema: [API & Contracts](api/overview.md)

## Podpora
- Postup řešení problémů (L1/L2/L3): [Troubleshooting](troubleshooting.md)
