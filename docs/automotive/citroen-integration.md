# Citroën OBD-II Integration Guide

## Overview
This guide covers integration of Citroën/PSA vehicles with the MIA platform using an ELM327 OBD-II adapter.

## Hardware Requirements
- **ELM327 Adapter**: USB or Bluetooth (USB recommended for reliability)
  - Verified: OBDLink SX, Vgate iCar Pro
  - Budget option: Generic ELM327 v1.5 (not v2.1 clones)
- **Raspberry Pi**: 4B with 2GB+ RAM
- **Serial Connection**: USB-to-OBD cable or Bluetooth pairing

## Supported Vehicles
| Model | Years | Engine | Notes |
|-------|-------|--------|-------|
| Citroën C4 Picasso | 2006-2013 | 1.6 HDi, 2.0 HDi | Full DPF support |
| Citroën C5 | 2008-2017 | 1.6 HDi, 2.0 HDi, 2.2 HDi | Eolys monitoring |
| Peugeot 308 | 2007-2013 | 1.6 HDi | Standard PIDs |
| Peugeot 508 | 2011-2018 | 1.6 HDi, 2.0 HDi | Full support |

## Installation

### 1. Install Dependencies
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-serial
pip3 install --break-system-packages pyzmq flatbuffers
```

### 2. Configure Serial Port
```bash
# Check ELM327 is detected
ls -l /dev/ttyUSB*

# Add user to dialout group
sudo usermod -a -G dialout mia

# Set port permissions (if needed)
sudo chmod 666 /dev/ttyUSB0
```

### 3. Deploy Service
```bash
sudo cp rpi/services/mia-citroen-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mia-citroen-bridge
sudo systemctl start mia-citroen-bridge
```

## Configuration

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `ELM_SERIAL_PORT` | `/dev/ttyUSB0` | Serial port path |
| `ELM_BAUD_RATE` | `38400` | Baud rate (9600, 38400, 115200) |
| `ZMQ_PUB_PORT` | `5557` | ZMQ publisher port |
| `ELM_MOCK` | `0` | Set to `1` for mock mode |

### Mock Mode Testing
```bash
# Run without hardware for testing
ELM_MOCK=1 python3 agents/citroen_bridge.py
```

## Standard OBD-II PIDs
| PID | Name | Formula | Unit |
|-----|------|---------|------|
| 010C | Engine RPM | (A*256+B)/4 | RPM |
| 010D | Vehicle Speed | A | km/h |
| 0105 | Coolant Temp | A-40 | °C |
| 0111 | Throttle Position | A*100/255 | % |
| 012F | Fuel Level | A*100/255 | % |

## PSA-Specific PIDs (Mode 21)
| PID | Name | Notes |
|-----|------|-------|
| 2101 | DPF Soot Mass | Model-specific formula |
| 2102 | Oil Temperature | A-40 (°C) |
| 2103 | Eolys Level | Percentage + liters |

## Troubleshooting

### No Response from ELM327
1. Check baud rate: Try 9600, 38400, 115200
2. Verify serial port: `ls -l /dev/ttyUSB*`
3. Test manually: `screen /dev/ttyUSB0 38400` then type `ATZ`

### Incorrect PID Values
- Some PIDs are model-specific
- Consult PSA documentation for your vehicle
- Use DiagBox/Lexia for reference values

### CAN Bus Errors
- Reduce polling frequency
- Check vehicle ignition is ON
- Verify protocol: `ATSP0` for auto-detect
