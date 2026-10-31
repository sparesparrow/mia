# MIA Documentation

MIA je systém do auta: Raspberry Pi 4B v autě sbírá telemetrii z vozidla, řídí hlasového asistenta a nabízí
REST/WebSocket API; Android aplikace je jeho společník. Tento web shrnuje instalaci, architekturu, kontrakty a podporu.

## Pro koho / For you
- Vývojáři / Developers: [start here](for/developers.md)
- Automechanici a montáž / Mechanics & installers: [start here](for/mechanics.md)
- Testeři / Testers: [start here](for/testers.md)
- Zákazníci, partneři a média / Customers, partners and press: [hlavní web / main site](https://sparesparrow.github.io/mia/)

## Jak MIA funguje
- **Raspberry Pi 4B je hlavní uzel** ([ADR-0005](spec/decisions/0005-raspberry-pi-edge-with-fastapi-gateway.md)):
  služby běží pod systemd v `/opt/mia`, klienti mluví jen s FastAPI bránou na portu 8000.
- **ESP32 čte sběrnici CAN jen pasivně** ([ADR-0006](spec/decisions/0006-passive-vehicle-access-by-default.md)):
  výchozí firmware nemá vysílací cestu a v autě zůstává vodič `TXD` budiče fyzicky nezapojený.
- **Android aplikace je společník** ([ADR-0016](spec/decisions/0016-android-reaches-the-pi-over-plain-http.md)):
  dashboard, čtení SPZ, hlasová konzole. K Pi se připojuje přes HTTP/WebSocket s API klíčem zadaným v Nastavení.

## Instalace
- Raspberry Pi v autě (podporovaná cesta): [instalace](install/pi-gateway.md)
- Telefon bez Pi (omezený režim): [instalace](install/phone.md)
- Vývoj bez Pi: [instalace](install/dev-docker.md)

## Architektura
- Přehled komponent a datových toků: [System Overview](spec/architecture/overview.md)
- Rozhodnutí: [ADR index](spec/decisions/README.md); požadavky a jejich ověření: [How MIA is specified](spec/README.md)

## Dráty a napájení
- OBD-II/CAN a napájení 12V→5V: [Wiring & Power](wiring.md)
- Piny GPIO Raspberry Pi 4B, zapalování, relé, ochranný allowlist (návrh, neověřeno na hardwaru): [GPIO pin map](hardware/gpio-pin-map.md)

## API & Contracts
- REST, WebSocket, MQTT topics, BLE GATT: [API & Contracts](api/overview.md)

## Podpora
- Postup řešení problémů (L1/L2/L3): [Troubleshooting](troubleshooting.md)
