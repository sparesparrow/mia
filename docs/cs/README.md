# MIA Universal - Inteligentní Osobní Asistent

## Přehled

MIA (Modular IoT Assistant) je distribuovaný řídicí systém navržený pro Raspberry Pi 4B jako hlavní výpočetní uzel, integrující Arduino/ESP32 mikrokontroléry pro ovládání hardwaru a Android smartphony pro vzdálené uživatelské rozhraní.

## Klíčové Funkce

- **Automobilová Telemetrie**: OBD-II diagnostika pro Citroën/PSA vozidla
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
# Klonování repozitáře
git clone https://github.com/sparesparrow/ai-servis.git
cd ai-servis

# Aktivace prostředí
source tools/env.sh

# Instalace závislostí
pip install -r requirements-dev.txt
pip install -r agents/requirements.txt

# Spuštění služeb
sudo systemctl start mia-broker
sudo systemctl start mia-citroen-bridge
```

## Dokumentace

- [Integrace Citroën](automotive/citroen-integrace.md)
- [Architektura systému](architecture/overview.md)
- [API Reference](api/overview.md)

## Podpora

- GitHub Issues: [ai-servis/issues](https://github.com/sparesparrow/ai-servis/issues)
- Dokumentace: [docs/](https://github.com/sparesparrow/ai-servis/tree/main/docs)
