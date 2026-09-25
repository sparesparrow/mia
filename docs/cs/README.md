# MIA Universal - Inteligentní Osobní Asistent

> **Audience**: Czech-speaking users and contributors

## Přehled

MIA (Modular IoT Assistant) je distribuovaný řídicí systém navržený pro Raspberry Pi 4B jako hlavní výpočetní uzel, integrující Arduino/ESP32 mikrokontroléry pro ovládání hardwaru a Android smartphony pro vzdálené uživatelské rozhraní.

## Klíčové Funkce

- **Automobilóvá Telemetrie**: OBD-II diagnostika — primárně pro Audi A4 Cabriolet 8H (2004)
- **Chytrá Domácnost**: Ovládání GPIO, senzory, osvětlení
- **Hlasové Ovládání**: Integrace s AI asistenty
- **Vzdálený Přístup**: Android aplikace pro monitoring

## Rychlý Start

### Požadavky
- Raspberry Pi 4B (2GB+ RAM)
- Python 3.9+
- ELM327 OBD-II adaptér (volitelné)

### Instalace

```bash
# Klonovní repozitáře
git clone https://github.com/sparesparrow/mia.git
cd mia

# Instalace závislostí
pip install -r requirements-dev.txt

# Spuštění služeb
sudo systemctl start zmq-broker
sudo systemctl start mia-api
```

## Dokumentace

- [Zapojení MIA do Audi A4 Cabriolet 8H](automotive/zapojeni-audi-a4-8h.md) — praktický montážní návod
- [Zapojení ESP32 modulů do MIA](automotive/zapojeni-esp32-moduly.md) — mikrokontroléry, CAN budič, napájení
- [Integrace Audi A4 8H](../automotive/raspberry-pi-audi-integration.md)
- [Architektura systému](../../spec/architecture/README.md)
- [README](../../README.md)

## Podpora

- GitHub Issues: [mia/issues](https://github.com/sparesparrow/mia/issues)
- Dokumentace: [docs/](https://github.com/sparesparrow/mia/tree/main/docs)
