# Zapojení ESP32 modulů do MIA

> **Pro koho**: ten, kdo pájí a montuje ESP32 desky do auta nebo na stůl
> **Stav**: návrh zapojení + revize stávajícího firmwaru. V autě zatím neodzkoušené.
> **Sourozenecký dokument**: [Zapojení MIA do Audi A4 Cabriolet 8H](zapojeni-audi-a4-8h.md) — tam je strana Raspberry Pi a vozu, tady je strana mikrokontroléru.

---

## 1. Co v repu reálně je

Tohle není přání, ale stav zdrojáků. Piny jsou vyčtené z kódu, ne z dokumentace:

| Modul | Cesta | Rozhraní | Piny / rychlost |
| --- | --- | --- | --- |
| OBD přes TWAI (ESP-IDF) | `apps/esp32/firmware-obd/components/ai_servis_obd/ai_servis_obd.c` | CAN (TWAI), MQTT | RX `GPIO16`, TX `GPIO17`, 500 kbit/s |
| Telemetrie po UART (ESP-IDF) | `apps/esp32/main/main.c` | UART0 → Pi, JSON po řádcích | LED `GPIO2`, tlačítko `GPIO0`, `ADC1_CH0` (= GPIO36), 115200 Bd |
| ELM327 emulátor (Arduino) | `firmware/esp32_obd/src/main.cpp` | 2× UART | `Serial` 38400 Bd (skener), `Serial2` 115200 Bd (Pi) |
| WiFi most (Arduino) | `apps/esp32/MIAWiFiBridge/MIAWiFiBridge.ino` | WiFi AP + TCP | TCP port 8888, SSID `MIA-Bridge` |
| Protokol MIA | `arduino/MIAProtocol/` | rámce po sériové lince | — |
| Protistrana na Pi | `apps/rpi-backend/py-api/hardware/serial_bridge.py` | UART → ZeroMQ `:5556` | výchozí `/dev/ttyUSB0`, 115200 Bd |

!!! warning "Sestavení v CI nepokrývá všechno"
    `apps/esp32/platformio.ini` má `src_dir = main`, takže CI job `esp32-build` překládá **jen `apps/esp32/main/`**.
    Projekt `apps/esp32/firmware-obd/` má vlastní CMake a do CI se nedostane — chyby v něm nikdo nezachytí (viz [kapitola 10](#10-nalezy-proti-firmwaru)).

---

## 2. Mapa pinů — co si můžeš dovolit

![Mapa rolí GPIO pinů ESP32 v MIA](../../automotive/images/esp32/esp32-pin-role-mapa.svg)

Tři pravidla, která tahle mapa shrnuje:

1. **GPIO6–GPIO11 nikdy.** Jsou drátem k flash paměti na modulu. Připojíš cokoliv → modul nenabootuje.
2. **Strapping piny čtou svůj stav při resetu.** `GPIO0` stažený k zemi v okamžiku resetu = modul jde do bootloaderu místo do aplikace. `GPIO12` tažený nahoru při resetu přepne napájení flash na 1,8 V a modul se nerozběhne.
3. **GPIO34–39 jsou jen vstupy** a nemají interní pull-up ani pull-down. Externí odpor je povinný, jinak vstup plave.

!!! danger "Tlačítko na GPIO0 je past, kterou si MIA nese ve firmwaru"
    `apps/esp32/main/main.c` používá `GPIO0` jako tlačítko s interním pull-upem. Funguje to, **dokud tlačítko nikdo nedrží při zapnutí zapalování.** Pak modul naběhne do bootloaderu a MIA ho nikdy neuvidí.
    V autě, kde se napájení objeví ve stejný okamžik, kdy může řidič držet tlačítko, to je reálný scénář.
    Řešení: přesuň tlačítko na volný pin (`GPIO4`, `GPIO13`, `GPIO27`…) a `GPIO0` nech být.

!!! warning "GPIO16/17 nejsou volné na každém modulu"
    TWAI je v repu na `GPIO16` a `GPIO17`. Na modulech **ESP32-WROVER** (ty s PSRAM) jsou tyhle dva piny obsazené právě tou PSRAM a ven nevedou.
    Na WROOM-32 (bez PSRAM) volné jsou. `platformio.ini` má `-DBOARD_HAS_PSRAM=0`, takže projekt s WROOM počítá — kup WROOM, nebo TWAI piny přemapuj.

---

## 3. Napájení

```mermaid
graph LR
  B["Palubní síť 12 V<br/>KL.30 přes pojistku"]
  M["Měnič 12 V → 5 V<br/>vstup 6–36 V, min. 1 A"]
  C["Bulk kondenzátor<br/>220–470 µF u modulu"]
  L["LDO na desce<br/>(AMS1117: 5 V → 3,3 V)"]
  E["ESP32<br/>špičky až ~500 mA"]
  B --> M --> C --> L --> E
```

| Veličina | Hodnota | Proč |
| --- | --- | --- |
| Vstup měniče | **6–36 V** | při startování motoru napětí padá hluboko pod 9 V; „12V nominal" modul ESP32 shodí |
| Výstup měniče | 5 V / ≥ 1 A | ESP32 bere ve špičkách při vysílání WiFi kolem 500 mA, měnič musí mít rezervu |
| Bulk kondenzátor | 220–470 µF co nejblíž modulu | pokrývá vysílací špičky, bez něj brownout uprostřed WiFi přenosu |
| Blokovací kondenzátor | 100 nF u pinu 3V3 | vysokofrekvenční šum |
| Pojistka | 1 A na odbočce | chrání kabel, ne modul |
| Průřez napájení | 0,5 mm² | proud je malý, mechanická pevnost velká |

!!! danger "Nikdy nenapájej desku z USB a z auta současně"
    Většina DevKit desek vede 5 V z USB a z pinu `VIN`/`5V` na stejný uzel, jen přes Schottkyho diodu (a spousta klonů ani to ne).
    Zapojené obojí = měnič z auta tlačí proud do USB portu notebooku. Při flashování **odpoj napájení z auta**.

!!! tip "3,3 V z Raspberry Pi jako napájení ESP32 nestačí"
    Pin 3V3 na Pi má rozpočet zhruba 250 mA pro celou lištu. ESP32 s WiFi si ve špičce řekne o dvojnásobek.
    Napájej ESP32 vlastní větví z 5 V a s Raspberry Pi spoj **jen zem a datové vodiče**.

---

## 4. CAN / TWAI

![Porovnání 3,3V a 5V CAN budiče připojeného k ESP32](../../automotive/images/esp32/can-budic-3v3-vs-5v.svg)

`docs/wiring.md` dosud uváděl „SN65HVD230/TJA1050" jako by šlo o alternativy. Nejdou:
**SN65HVD230 je 3,3V budič, TJA1050 je 5V budič a ESP32 není 5V tolerantní.**
TJA1050 se na ESP32 připojit dá, ale jen s převodníkem úrovní na vodiči RXD, nebo výměnou za typ s odděleným pinem VIO (TJA1051T/3).

### 4.1 Zapojení

| SN65HVD230 | ESP32 | Poznámka |
| --- | --- | --- |
| `VCC` | `3V3` | **ne 5 V** |
| `GND` | `GND` | společná zem, viz kap. 7 |
| `RXD` | `GPIO16` | budič → ESP32 |
| `TXD` | `GPIO17` | ESP32 → budič; pro pasivní odposlech **nezapojuj** |
| `Rs` | přes 10 kΩ na `GND` | normální rychlost; přímo na GND taky funguje |
| `CANH` / `CANL` | OBD piny 6 a 14 | kroucený pár |

### 4.2 Terminace — v autě ne, na stole ano

Tohle plete nejvíc lidí:

| Kde | Odpor 120 Ω | Proč |
| --- | --- | --- |
| V autě na OBD | **nepřidávej** | sběrnice je z výroby zakončená na obou koncích; třetí odpor sníží impedanci a rozhodí komunikaci |
| Na stole (ESP32 ↔ ESP32, ESP32 ↔ USB-CAN) | **2× 120 Ω, na každém konci jeden** | bez nich se nedomluví nic a budeš hledat chybu v kódu |

Většina modulů SN65HVD230 z tržiště má 120 Ω osazený napevno na desce. Před použitím v autě ho **vypájej nebo přeřízni propojku.**

### 4.3 Pasivní odposlech vs. aktivní dotazování

Jsou to dva různé režimy a firmware musí vědět, ve kterém je:

| Režim | Co dělá | Jak vynutit |
| --- | --- | --- |
| Pasivní odposlech | jen poslouchá, na sběrnici nic neposílá | `TWAI_MODE_LISTEN_ONLY` **a** vodič TXD fyzicky nezapojený |
| Aktivní OBD dotazy | posílá rámce na `0x7DF`, čte odpovědi z `0x7E8` | `TWAI_MODE_NORMAL`, TXD zapojený |

!!! warning "Softwarový přepínač sám o sobě není záruka"
    `TWAI_MODE_LISTEN_ONLY` je hodnota v konfiguračním registru — chyba v kódu ji přepíše.
    Když chceš mít jistotu, že se na sběrnici nic neobjeví, **nezapoj vodič TXD** mezi ESP32 a budičem. Budič pak nemá čím sběrnici rozkmitat, ať v softwaru nastaví kdokoli cokoli. Nastav oboje, ne jedno místo druhého.

---

## 5. UART k Raspberry Pi

Dvě cesty:

| | Zapojení | `serial_bridge.py` | Kdy |
| --- | --- | --- | --- |
| **A) USB** | USB kabel DevKit → Pi | funguje bez úprav (`/dev/ttyUSB0`) | vývoj, stůl |
| **B) GPIO UART** | 3 vodiče, viz níže | nutné přepnout na `/dev/serial0` | do auta — míň konektorů, míň bodů selhání |

Zapojení varianty B. Všimni si, že **TX vždy jde do RX** — linka se kříží:

```mermaid
graph LR
  ETX["ESP32 GPIO1<br/>TX"] --> PRX["Pi GPIO15<br/>RXD"]
  PTX["Pi GPIO14<br/>TXD"] --> ERX["ESP32 GPIO3<br/>RX"]
  EG["ESP32 GND"] --- PG["Pi GND"]
```

- **Křížení je povinné**: TX jde do RX, ne TX do TX.
- **Zem musí být společná**, jinak se linka chová náhodně.
- **Převodník úrovní tady nepotřebuješ**: ESP32 i Raspberry Pi mají 3,3V logiku. (Pozor: klasické Arduino Uno má 5V logiku a tam převodník nutný je.)
- Pro variantu B je potřeba v Pi vypnout sériovou konzoli, zapnout `enable_uart=1` a `serial_bridge.py` nasměrovat na `/dev/serial0` (výchozí je `/dev/ttyUSB0`, 115200 Bd).

!!! warning "UART0 sdílí piny s flashováním"
    `GPIO1`/`GPIO3` jsou zároveň programovací linka. Když na nich visí Raspberry Pi, může držet úrovně tak, že flashování přes USB selže.
    Při aktualizaci firmwaru dráty k Pi rozpoj, nebo používej OTA (`apps/esp32/MIAWiFiBridge` už ArduinoOTA obsahuje).

---

## 6. Vstupy a výstupy

### 6.1 Vstup z autoelektriky (12 V) — vždy přes optočlen

Stejné schéma jako pro Raspberry Pi v [sourozeneckém návodu](zapojeni-audi-a4-8h.md), jen cílové napětí je 3,3 V:

```
12V signál ──[ R1 2,2 kΩ / 0,25 W ]──┬── anoda PC817
                                      │
                                 D1 1N4148 (antiparalelně k LED)
                                      │
                       katoda PC817 ──┴── GND

Výstup PC817:
  kolektor ──┬── GPIO (např. GPIO27)
             │
        R2 10 kΩ pull-up
             │
            3V3          ← pozor: 3V3, ne 5V
  emitor ────── GND
  C1 100 nF mezi GPIO a GND
```

Logika je obrácená: signál aktivní → optočlen sepne → GPIO čte **LOG. 0**.

!!! danger "Na GPIO nesmí 12 V ani 5 V"
    Absolutní maximum na pinu ESP32 je přibližně 3,6 V. Odporový dělič z 12 V není dostatečná ochrana — při špičkách v palubní síti (load dump) dělič propustí násobky.
    Galvanické oddělení optočlenem je jediná varianta, která to přežije.

### 6.2 Výstup na zátěž — relé přes optočlen

- Optočlenem oddělená relé deska s 12V cívkou, řízená z GPIO.
- Ochranná dioda 1N4007 antiparalelně k cívce.
- Cívku napájej z vlastní jištěné větve, ne z 3,3 V modulu.
- **Klidový stav = rozepnuto.** Při resetu ESP32 jsou GPIO ve vysoké impedanci — zátěž musí sama od sebe zůstat vypnutá.
- Nic bezpečnostního: střecha, zamykání, vnější světla, palivo, chlazení.

---

## 7. Uzemnění, stínění, teplota

- **Jeden společný zemnící bod** pro měnič, ESP32, budič CAN i relé desku. Zem braná na dvou místech karoserie = zemní smyčka a šum na CAN i na audiu.
- CAN vždy **kroucený pár**, průřez 0,35–0,5 mm². Nevést podél zapalovacích kabelů ani vedení alternátoru.
- Anténa ESP32 nesmí ležet na plechu ani v kovové krabičce. Pokud je modul v krabici, vyveď anténu ven nebo použij variantu s U.FL konektorem.
- V kabinu v létě přes 60 °C. ESP32 je specifikované do 85 °C, ale levné LDO a elektrolyty na klonech ne — elektrolyty volte na 105 °C a modul nedávej na přímé slunce pod palubku.

---

## 8. Flashování a první boot

```bash
# PlatformIO (apps/esp32 — překládá jen main/)
cd apps/esp32
pio run -t upload
pio device monitor -b 115200

# ESP-IDF (apps/esp32/firmware-obd — vlastní projekt, mimo CI)
cd apps/esp32/firmware-obd
idf.py set-target esp32
idf.py build flash monitor
```

Když modul nenabootuje, projdi tohle pořadí:

1. Drží něco `GPIO0` u země? (tlačítko, Pi, odpor) → modul je v bootloaderu.
2. Je na `GPIO12` pull-up? → flash běží na špatném napětí.
3. Visí něco na `GPIO6`–`GPIO11`? → konflikt s flash pamětí.
4. Padá napájení při startu WiFi? → chybí bulk kondenzátor, hlaska `Brownout detector was triggered`.
5. Je připojené Raspberry Pi na `GPIO1`/`GPIO3`? → rozpoj a zkus znovu.

---

## 9. Kontrolní seznam před montáží do auta

- [ ] Modul je WROOM (ne WROVER), nebo jsou TWAI piny přemapované
- [ ] Tlačítko není na `GPIO0`
- [ ] Budič CAN je 3,3V typ, nebo je na RXD převodník úrovní
- [ ] Odpor 120 Ω na modulu budiče je pro provoz v autě odstraněný
- [ ] Pro pasivní odposlech je TXD fyzicky nezapojený
- [ ] Bulk kondenzátor 220–470 µF je osazený u modulu
- [ ] Vstupy z autoelektriky jdou přes optočlen, nikde není 12 V blízko GPIO
- [ ] Zem na jednom bodě, dotažená, očištěná od laku
- [ ] Při flashování odpojené napájení z auta
- [ ] Anténa není na plechu
- [ ] Relé v klidu rozepnutá, na nic bezpečnostního nepřipojená

---

## 10. Nálezy proti firmwaru {#10-nalezy-proti-firmwaru}

Při psaní tohohle návodu jsem porovnával dokumentaci se zdrojáky. Čtyři věci nesedí.
**Nic z toho zatím není opravené** — jsou to hlášení, ne provedené změny.

### N1 — OBD dotaz má rámec posunutý o bajt (nefunguje) {#n1}

`apps/esp32/firmware-obd/components/ai_servis_obd/ai_servis_obd.c:95`

```c
static const uint8_t obd_request_template[] = {
    0x7DF,  // CAN ID (broadcast)   ← 0x7DF se do uint8_t nevejde, uřízne se na 0xDF
    0x02,   // Data length
    0x01,   // Service mode 01
    0x00,   // PID (to be filled)
    ...
```

CAN identifikátor do datové části nepatří — nastavuje se zvlášť (což kód na řádku 206 i dělá).
Výsledkem je, že se odesílá `DF 02 01 <pid> 00 00 00 00`, zatímco správný jednorámcový OBD dotaz je `02 01 <pid> 55 55 55 55 55`.

První bajt je PCI: horní nibble `0` = jednoduchý rámec. Tady je `0xD`, což není platný typ rámce → **řídicí jednotka dotaz zahodí a nikdy neodpoví.**

Že jde o posun o jeden bajt, potvrzuje kontrola odpovědi na řádku 223: `message.data[2] == pid` odpovídá *správnému* rozložení (`03 41 <pid> …`), zatímco dotaz se plní na `data[3]`.

Navržená oprava:

```c
static const uint8_t obd_request_template[] = {
    0x02, 0x01, 0x00, 0x55, 0x55, 0x55, 0x55, 0x55
};
/* … */
message.data[2] = pid;   // bylo data[3]
```

### N2 — `twai_message_t` se nikdy neinicializuje {#n2}

`ai_servis_obd.c:203`

```c
twai_message_t message;
memcpy(&message.data, obd_request_template, sizeof(obd_request_template));
```

Vyplní se `data`, `identifier` a `data_length_code`, ale **příznaky ne**. `twai_message_t` má v sobě bitové pole (`extd`, `rtr`, `ss`, `self`, `dlc_non_comp`), které tímhle zůstane s náhodným obsahem ze zásobníku.
Podle toho, co na zásobníku zrovna leží, se rámec odešle jako 29bitový extended, jako RTR, nebo v režimu self-reception. Chování je nereprodukovatelné.

Oprava je jednoznaková: `twai_message_t message = {0};`

### N3 — dokumentace slibuje listen-only, firmware jede normal {#n3}

`docs/wiring.md` uvádí „Read‑only (listen‑only) při testování". `ai_servis_obd.c:124` instaluje ovladač napevno s `TWAI_MODE_NORMAL` a žádný build flag pro odposlechovou variantu neexistuje.

Aktivní dotazování na `0x7DF` je legitimní — dělá to každý OBD skener. Problém je, že **si mezi těmi dvěma režimy nelze vybrat** a dokument tvrdí něco jiného, než co se stane po nahrání firmwaru.
Návrh: přidat volbu do `Kconfig` (`CONFIG_MIA_TWAI_LISTEN_ONLY`) a ve výchozím stavu ji zapnout.

### N4 — zbytečná konfigurace TX pinu před instalací ovladače {#n4}

`ai_servis_obd.c:117–121` nastavuje `TWAI_TX_PIN` jako obyčejný výstup GPIO těsně před `twai_driver_install()`. Ovladač TWAI si pin směruje sám přes GPIO matici, takže tenhle blok nic nedělá.
Škodí až ve chvíli, kdy ho někdo při úpravách přesune **za** instalaci ovladače — pak přebije směrování a vysílání přestane fungovat. Navrhuju ho smazat.

!!! note "Proč to nechytila CI"
    `0x7DF` v inicializaci `uint8_t` je věc, na kterou GCC běžně upozorní (`-Woverflow`).
    Job `esp32-build` ale překládá jen `apps/esp32/main/` (kvůli `src_dir = main` v `platformio.ini`), takže `firmware-obd/` se nepřekládá vůbec a varování nemá kde vzniknout.

---

## 11. Materiál

| Položka | Poznámka |
| --- | --- |
| ESP32-WROOM-32 DevKit | ne WROVER, pokud chceš TWAI na GPIO16/17 |
| Modul budiče SN65HVD230 | 3,3V typ; zkontroluj a odstraň napevno osazený 120 Ω |
| Měnič 12 V → 5 V, vstup 6–36 V, ≥ 1 A | automotive, odolný load dump |
| Elektrolyt 220–470 µF / 16 V, 105 °C + keramika 100 nF | u modulu |
| Optočleny PC817, odpory 2,2 kΩ a 10 kΩ, diody 1N4148, kondenzátory 100 nF | vstupy |
| Optočlenem oddělená relé deska 12 V + diody 1N4007 | výstupy |
| Kroucený pár 0,35 mm² (CAN), 0,5 mm² (napájení, signály) | |
| USB-CAN adaptér nebo druhá ESP32 + 2× 120 Ω | stolní testování bez auta |
| Dutinky, kleště, smršťovací bužírky, textilní páska | žádné scotchloky |

---

## 12. Odkazy

**Oficiální dokumentace** (ověřeno, že odkazy fungují):

- [ESP-IDF — TWAI (CAN) driver](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/twai.html) — režimy, časování, `twai_message_t`
- [ESP-IDF — GPIO & RTC GPIO](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/gpio.html)
- [ESP-IDF — UART](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/uart.html)
- [ESP-IDF — ADC oneshot](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/adc_oneshot.html) — proč ADC2 při WiFi nejde
- [ESP-IDF — Application startup flow](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/startup.html) — co se děje se strapping piny při bootu
- [ESP-IDF — OTA aktualizace](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/ota.html)
- [ESP-IDF — Hardware reference](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/hw-reference/index.html)
- [ESP-IDF — Get Started](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html)
- [PlatformIO — platforma Espressif 32](https://docs.platformio.org/en/latest/platforms/espressif32.html)

**Datasheety** (ověřeno):

- [ESP32 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf) — absolutní maxima na pinech, strapping
- [ESP32-WROOM-32 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf) — odběr, doporučené zapojení napájení
- [TI SN65HVD230](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf) — 3,3V budič, funkce pinu `Rs`
- [NXP TJA1050](https://www.nxp.com/docs/en/data-sheet/TJA1050.pdf) — 5V budič, porovnej úrovně na `RXD` s maximy ESP32

**Linux / strana Raspberry Pi**:

- [SocketCAN v jádře Linuxu](https://www.kernel.org/doc/html/latest/networking/can.html) — `can0`, listen-only, `candump`
- [python-can](https://python-can.readthedocs.io/en/stable/) — čtení sběrnice z Pythonu

**Repozitáře** (kanonické projekty; přes firemní proxy je nešlo ověřit, ověř si je sám):

- `github.com/espressif/esp-idf` — příklady v `examples/peripherals/twai/`
- `github.com/espressif/arduino-esp32` — Arduino jádro pro ESP32
- `github.com/linux-can/can-utils` — `candump`, `cansend`, `cangen` pro stolní testy

**V tomhle repu**:

- [Zapojení MIA do Audi A4 Cabriolet 8H](zapojeni-audi-a4-8h.md) — strana vozu a Raspberry Pi
- [Wiring & Power (OBD-II/CAN)](../../wiring.md) — stručná verze zapojení OBD
- [Rozbor rozhraní vozu (anglicky)](../../automotive/audi-a4-8h-interface-integration.md)
