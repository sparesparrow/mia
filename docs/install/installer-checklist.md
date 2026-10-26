# Installer Checklist (OBD/CAN, Power, Cameras)

!!! warning "Pasivní přístup k vozidlu (ADR-0006)"
    - Na ESP32 nahraj **výchozí** build firmwaru (`idf.py build`). Ten nemá vysílací cestu. Nikdy do auta
      nenahrávej image z adresáře `build-tx` (`-DMIA_ALLOW_TX=1`).
    - Vodič `TXD` mezi ESP32 a CAN budičem **nezapojuj**. Režim listen-only je registr, který může chyba
      v softwaru přepsat; přerušený vodič ne.
    - Viz [ADR-0006](../spec/decisions/0006-passive-vehicle-access-by-default.md) a
      [zapojení ESP32](../cs/automotive/zapojeni-esp32-moduly.md).

## Pre‑install
- Ověř kompatibilitu (EU CAN 11‑bit @ 500k)
- Zkontroluj přístup k OBD a trasu kabelů; připrav pojistku 0.5–1A
- Připrav PD/QC nabíječku a držák telefonu s ventilací

## Hardware
- OBD splitter + CAN transceiver (SN65HVD230/TJA1050) zapojen dle [Wiring](../wiring.md), `TXD` nezapojený
- Buck 12V→5V (3–5A) pevně uchycen, společná zem s OBD
- ESP32 upevněno (vibrace), UVC hub napájený (pokud kamera)

## Software
- Pi: služby běží (`systemctl status zmq-broker mia-api`), `/status` odpovídá, viz [instalace Pi](pi-gateway.md)
- Telefon: v Nastavení zadaná adresa Pi a API klíč; na dashboardu karta Cycle 1 ukazuje hodnoty
- Čtení SPZ aktivní, notifikace a hlasový test

## Validace
- Jízda 10–15 min: stabilita připojení, hodnoty na kartě Cycle 1
- Export krátkých logů (DrivingService, ANPR)
- Předání zákazníkovi: UI tour, privacy/retence, podpora
- Výsledek zapiš jako záznam v `spec/evidence/<REQ-ID>/` ([ADR-0010](../spec/decisions/0010-evidence-based-requirement-status.md))
