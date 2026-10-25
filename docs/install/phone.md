# Telefon bez Pi (omezený režim)

Hlavní instalace MIA běží na Raspberry Pi ([instalace Pi](pi-gateway.md),
[ADR-0005](../spec/decisions/0005-raspberry-pi-edge-with-fastapi-gateway.md)). Bez Pi umí Android aplikace jen část:

| Funguje bez Pi | Potřebuje Pi |
|---|---|
| čtení SPZ kamerou telefonu (ukládá se jen otisk) | telemetrie Cycle 1 z pasivního odposlechu CAN |
| hlasová upozornění z pravidel (palivo, teplota) | hlasová konzole a hlasový asistent |
| OBD přes BLE adaptér (viz bezpečnost níže) | kontrola dálniční známky (eDálnice) |
| | Audi/VAG most, ovládání LED |

!!! danger "Bezpečnost: tento režim není pasivní"
    BLE OBD v aplikaci se na data aktivně ptá: `OBDManager` posílá adaptéru ve stylu ELM327 příkazy `ATZ`,
    `010C` a další a adaptér je vysílá do sběrnice. Pasivní instalace podle
    [ADR-0006](../spec/decisions/0006-passive-vehicle-access-by-default.md) do denně používaného auta je
    Pi + ESP32 s výchozím (listen-only) firmwarem a fyzicky nezapojeným vodičem `TXD` budiče.
    Tento režim používej jen na testovacím voze.

## Požadavky
- Android telefon s USB‑C napájením v autě (PD/QC 18–30W)
- BLE OBD adaptér kompatibilní s ELM327 (nebo ESP32 s firmwarem emulátoru ELM327)

## Kroky
1) Zapojení OBD a napájení: viz [Wiring & Power](../wiring.md)
2) Spusťte Android aplikaci, povolte oprávnění (BLE/Camera/Location/Notifications)
3) Spusťte foreground DrivingService (persistentní notifikace)
4) Spárujte adaptér na záložce OBD (běžné BLE párování)
5) Ověřte OBD data (fuel, RPM, speed, coolant), nastavte VIN
6) Zapněte čtení SPZ na záložce Camera, otestujte notifikace a hlas

## Ověření
- Na dashboardu se mění hodnoty z adaptéru
- Je-li v síti MQTT broker (najde ho mDNS), objeví se `vehicle/telemetry/{vin}/obd` a při SPZ
  `vehicle/events/{vin}/anpr` ([topics.md](../spec/interfaces/topics.md))

## Soukromí
- Zpracování zůstává v telefonu; SPZ se ukládají jen jako otisk
- Retence se nastavuje v Nastavení (výchozí 2 dny)
