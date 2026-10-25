# System Overview

Krátký přehled toho, z čeho se MIA skládá a kudy tečou data. Podrobnosti jsou v [README architektury](README.md),
rozhodnutí v [ADR](../decisions/README.md).

## Komponenty
- **Raspberry Pi 4B (hlavní uzel, [ADR-0005](../decisions/0005-raspberry-pi-edge-with-fastapi-gateway.md))**:
  služby pod systemd v `/opt/mia`. FastAPI brána na portu 8000 je jediné HTTP/WebSocket rozhraní pro klienty.
  Za ní běží ZeroMQ: broker ROUTER-DEALER na 5555, telemetrie z MCU (PUB/SUB) na 5556 a telemetrie vozidla
  na 5557 ([ADR-0003](../decisions/0003-zeromq-control-plane-and-telemetry.md)). Dále hlasové služby, OBD worker
  a mosty pro Audi A4 8H a Citroën C4 ([ADR-0008](../decisions/0008-audi-a4-8h-primary-citroen-secondary.md)).
- **ESP32 uzly**: pasivní odposlech sběrnice CAN ([ADR-0006](../decisions/0006-passive-vehicle-access-by-default.md)).
  Výchozí build firmwaru nemá vysílací cestu (`twai_transmit`) a v autě zůstává vodič `TXD` budiče fyzicky
  nezapojený. Build s vysíláním (`-DMIA_ALLOW_TX=1` v adresáři `build-tx`) do auta nepatří.
- **Android aplikace (společník)**: dashboard s telemetrií Cycle 1 z Pi, čtení SPZ kamerou telefonu, hlasová
  konzole, nastavení adresy Pi a API klíče. Bez Pi umí omezený režim (BLE OBD, čtení SPZ, hlasová upozornění),
  viz [instalace telefonu](../../docs/install/phone.md).

## Datové toky
- Vozidlo → ESP32 (listen-only) → sériová linka → Pi (ZeroMQ) → FastAPI (`/ws/telemetry`, REST) → Android.
  Telemetrie vozidla má jednotnou obálku `vehicle.telemetry` v1
  ([ADR-0009](../decisions/0009-canonical-vehicle-telemetry-envelope.md)).
- Android → Pi: REST a WebSocket na portu 8000, klíč v hlavičce `X-API-Key`
  ([ADR-0016](../decisions/0016-android-reaches-the-pi-over-plain-http.md)).
- MQTT jen na okrajích, kde ho zařízení nebo cizí systém potřebuje (ADR-0003). Jmenný prostor témat určuje
  [ADR-0017](../decisions/0017-mqtt-topic-namespace.md) a [topics.md](../interfaces/topics.md).
- Hlas: pro hlasovou konzoli a zpětnou vazbu FlatBuffers obálka a abstraktní kanál
  ([ADR-0013](../decisions/0013-message-envelope-and-abstract-channel.md), [voice.md](../interfaces/voice.md)).

## Soukromí a bezpečnost
- Zpracování zůstává v autě (edge-only). SPZ se v aplikaci ukládají jen jako HMAC-SHA256 otisk
  (`apps/android/app/src/main/java/cz/mia/app/core/security/PlateIdentity.kt`). Klíč má každá instalace vlastní,
  32 náhodných bajtů mimo zálohy; mimo tento telefon otisk nic neznamená
  ([ADR-0018](../decisions/0018-per-install-plate-key-and-black-book.md)).
- Černá kniha (SPZ, na které má aplikace upozornit) a upozornění na auto, které se opakovaně objevuje, zůstávají
  v telefonu: oznámení a hlas, nic přes MQTT.
- Retence záznamů v aplikaci je nastavitelná, výchozí 2 dny, a platí i v režimu inkognito. Černá kniha retenci
  nepodléhá; položky maže uživatel.
- Spojení telefon ↔ Pi je prostý HTTP s API klíčem v hlavičce `X-API-Key` (ADR-0016). TLS na Pi zatím není
  (issue #139), párování přes QR ani připínání certifikátů neexistuje.
- Hlasová data zůstávají na Pi s omezenou retencí ([ADR-0014](../decisions/0014-voice-data-and-privacy.md)).

Více k protokolům a payloadům viz [API & Contracts](../../docs/api/overview.md).
