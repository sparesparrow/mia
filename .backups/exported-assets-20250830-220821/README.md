# MIA: Modulární Car AI Server

Kompletní řešení pro autoservisy kombinující ANPR, OBD diagnostiku, hlasového AI asistenta a fleet management v jednom modulárním systému.

## 🏗️ Architektura

```
ai-servis/
├── android/           # Android aplikace (hlavní hub)
├── esp32/            # ESP32 firmware (OBD, IO, kamera)
├── edge-compat/      # Pi gateway (volitelné)
├── web/              # Web prezentace a konfigurátor
├── contracts/        # API specifikace a protokoly
├── docs/             # Dokumentace
└── ci/               # CI/CD pipeline
```

## 🚀 Rychlý Start

### Požadavky
- Android Studio Arctic Fox+
- ESP-IDF v5.0+
- Docker (pro edge-compat)
- Node.js 18+ (pro web)

### Instalace

```bash
# Klonování repozitáře
git clone https://github.com/sparesparrow/mia.git
cd mia

# Android aplikace
cd android
./gradlew assembleDebug

# ESP32 firmware
cd ../esp32/firmware-obd
idf.py build

# Web aplikace
cd ../web/site
npm install
npm run dev
```

## 📚 Dokumentace

- Procházejte dokumenty v `docs/` nebo spusťte lokální web:

```bash
# v kořeni repozitáře
pip install mkdocs mkdocs-mermaid2-plugin
mkdocs serve
# otevřete http://127.0.0.1:8000
```

- Vstupní stránky:
  - `docs/index.md` (přehled)
  - `docs/install/phone.md`, `docs/install/hybrid.md`, `docs/install/pro.md`, `docs/install/pi-gateway.md`
  - `docs/wiring.md`, `docs/api/overview.md`, `docs/troubleshooting.md`
  - Diagramy a Mermaid: `docs/architecture/diagrams.md`

## 📱 Varianty Nasazení

### Phone Edition (BYOD)
- **Hardware**: ESP32 OBD + UVC kamera
- **Software**: Android aplikace
- **Cena**: 22.000 - 38.000 Kč
- **Instalace**: 1.5-3 hodiny

### Hybrid Edition (Phone + DVR)
- **Hardware**: ESP32 + Pi + kamery
- **Software**: Android + Pi gateway
- **Cena**: 48.000 - 89.000 Kč
- **Instalace**: 3-5 hodin

### Pro Edition (Vehicle PC)
- **Hardware**: Dedikovaný mini-PC + multi-kamera
- **Software**: Kompletní stack
- **Cena**: 89.000 - 143.000 Kč
- **Instalace**: 4-6 hodin

## 🔧 Technické Specifikace

### Android Aplikace
- **Min. API**: 24 (Android 7.0)
- **Cíl API**: 34 (Android 14)
- **Jazyk**: Kotlin
- **Architektura**: MVVM + Clean Architecture

### ESP32 Firmware
- **Framework**: ESP-IDF v5.0
- **Jazyk**: C/C++
- **Protokoly**: TWAI (CAN), BLE, Wi-Fi
- **OTA**: Podporováno

### Komunikace
- **BLE**: GATT služby pro telemetrii
- **MQTT**: Event-driven messaging
- **Wi-Fi Direct**: Vysokorychlostní přenos
- **mDNS**: Service discovery

## 📊 Implementační Plán

### Fáze 0 - Iniciační příprava ✅
- [x] Monorepo struktura
- [x] Contracts v1.0
- [x] CI/CD pipeline
- [ ] Build artefakty

### Fáze 1 - Analýza a návrh
- [ ] Workshopy s autoservisem
- [ ] LPR stack výběr
- [ ] OBD strategie
- [ ] UX návrh

### Fáze 2 - Quick Wins / MVP
- [ ] Android MVP
- [ ] ESP32 OBD bridge
- [ ] Web UI
- [ ] První testy

## 🔒 Bezpečnost a Soukromí

- **Edge-only zpracování**: Data zůstávají v autě
- **SPZ hashování**: HMAC-SHA256 s pepper
- **Retenční politika**: 24-72h, konfigurovatelné
- **GDPR compliance**: Opt-in, transparentnost
- **Read-only OBD**: Žádné zápisy do ECU

## 📈 Business Value

- **70-93% úspora** oproti tradičním ANPR systémům
- **Rychlá instalace** 2-4 hodiny vs. 1-2 týdny
- **Modulární design** - postupné rozšiřování
- **Český support** - Brno-sever lokalizace

## 🤝 Přispívání

1. Fork repozitáře
2. Vytvořte feature branch (`git checkout -b feature/amazing-feature`)
3. Commit změny (`git commit -m 'Add amazing feature'`)
4. Push do branch (`git push origin feature/amazing-feature`)
5. Otevřete Pull Request

## 📄 Licence

Tento projekt je licencován pod MIT licencí - viz [LICENSE](LICENSE) soubor pro detaily.

## 📞 Kontakt

- **Web**: https://ai-servis.cz
- **Email**: info@ai-servis.cz
- **Telefon**: +420 777 888 999
- **Adresa**: Brno-sever, Česká republika

---

**MIA** - První modulární AI Car Server v ČR 🚗✨

