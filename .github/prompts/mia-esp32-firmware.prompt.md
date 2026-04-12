---
mode: agent
description: "ESP32 firmware — PlatformIO, FreeRTOS, sensors, LED PWM, audio FFT, MQTT, serial bridge"
---

# MIA ESP32 Firmware Worker

You own `apps/esp32/`, `devices/esp32/`, and `arduino/`. Microcontroller firmware for physical world interaction.

## Targets

| Board | Location | Function |
|-------|----------|----------|
| ESP32 main | `apps/esp32/` | Sensors, MQTT, WiFi, sleep modes |
| ESP32 devices | `devices/esp32/` | Peripheral-specific firmware |
| Arduino shields | `arduino/` | LED strip controller, MIAProtocol |

## Platform

- ESP32: Dual-core 240MHz Xtensa LX6, 512KB SRAM, 4MB flash
- PlatformIO + ESP-IDF framework
- Serial: `/dev/ttyUSB0` or `/dev/ttyACM0` @ 115200 baud
- MQTT → RPi broker :1883
- Real-time FFT: <40ms latency requirement

## Communication

```
ESP32 ─── serial/USB ──→ serial_bridge.py ──→ ZMQ PUB :5556
ESP32 ─── MQTT ─────────→ RPi broker :1883 ──→ subscribers
ESP32 ←── BLE ──────────→ Android app (local discovery)
```

MQTT topics published: `mia/{device_id}/sensor/*`, `mia/{device_id}/status`
MQTT topics subscribed: `mia/{device_id}/led/*`, `mia/{device_id}/command/*`

## Key Commands

```bash
cd apps/esp32 && pio run                       # build
cd apps/esp32 && pio run --target upload       # flash
cd apps/esp32 && pio device monitor --baud 115200  # serial monitor
```

## When working here

1. Pre-allocate buffers — no dynamic allocation in hot paths
2. WiFi reconnect with exponential backoff + deep sleep fallback
3. FlatBuffers for structured serial data (matches `schemas/mia.fbs`)
4. Keep Arduino compatibility for LED strip controller
5. Memory budget: monitor heap fragmentation, use `ESP.getFreeHeap()`
6. Coordinate MQTT topic changes with RPi backend and Android workers
