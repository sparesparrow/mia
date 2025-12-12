# Integrace Citroën OBD-II

## Požadavky na Hardware

### ELM327 Adaptér
- **Doporučeno**: OBDLink SX (USB), Vgate iCar Pro (Bluetooth)
- **Rozpočtová varianta**: ELM327 v1.5 (pozor na klony v2.1)

### Podporovaná Vozidla
| Model | Roky | Motor | Poznámky |
|-------|------|-------|----------|
| Citroën C4 Picasso | 2006-2013 | 1.6 HDi, 2.0 HDi | Plná podpora DPF |
| Citroën C5 | 2008-2017 | 1.6-2.2 HDi | Monitoring Eolys |
| Peugeot 308/508 | 2007-2018 | 1.6-2.0 HDi | Standardní PIDs |

## Instalace

### 1. Připojení Adaptéru
```bash
# Ověření detekce
ls -l /dev/ttyUSB*

# Přidání uživatele do skupiny
sudo usermod -a -G dialout $USER
```

### 2. Nasazení Služby
```bash
sudo cp rpi/services/mia-citroen-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mia-citroen-bridge
sudo systemctl start mia-citroen-bridge
```

### 3. Ověření Funkčnosti
```bash
# Kontrola stavu
sudo systemctl status mia-citroen-bridge

# Sledování logů
journalctl -u mia-citroen-bridge -f
```

## Testovací Režim (Mock)
```bash
ELM_MOCK=1 python3 agents/citroen_bridge.py
```

## Řešení Problémů

### Žádná Odpověď od ELM327
1. Zkontrolujte přenosovou rychlost (9600, 38400, 115200)
2. Ověřte sériový port: `screen /dev/ttyUSB0 38400`
3. Zadejte `ATZ` pro reset

### Bezpečnostní Upozornění
- ⚠️ **NIKDY** nepoužívejte `force_regen` při stání
- ⚠️ Neprovádějte testy déle než 30 minut
- ⚠️ Sledujte teplotu chladicí kapaliny (max 105°C)
