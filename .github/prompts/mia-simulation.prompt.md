---
mode: agent
description: "Simulation, emulation, HIL, mocks — Docker Pi sim, GPIO stubs, OBD emulator, test doubles"
---

# MIA Simulation & Testing Environment Worker

You own the simulation layer that makes development possible without physical hardware.

## Simulation Assets

| System | Mechanism | Config |
|--------|-----------|--------|
| RPi GPIO | `GPIO_SIMULATION=true` env var + try-except RPi.GPIO | `gpio_worker.py` fallback |
| Pi full stack | Docker containers | `docker-compose.pi-simulation.yml` |
| OBD-II Digital Twin | Potentiometer MCU → ELM327 emulator → virtual PTY | `obd_worker.py` |
| GPIO web sim | Browser-based GPIO simulator | `containers/gpio-simulator/` |
| Pi simulation | Full Pi environment in Docker | `containers/pi-simulation/` |
| MQTT | Mosquitto container | `containers/mosquitto/` |
| Metrics | Prometheus + AlertManager containers | `containers/prometheus/`, `containers/alertmanager/` |
| Database | PostgreSQL container | `containers/postgres/` |

## Docker Dev Stack

```bash
docker compose -f infra/docker/docker-compose.dev.yml up    # dev mode
docker compose -f docker-compose.pi-simulation.yml up        # full Pi sim
```

## Mock Patterns

- **GPIO**: `MockHardwareWorker` in tests — simulates pin read/write
- **Serial**: Mock serial port for ESP32 bridge testing
- **OBD**: Virtual PTY that responds to OBD-II PIDs with mapped potentiometer data
- **MQTT**: In-process broker for integration tests
- **Sensors**: Random data generators matching `SensorTelemetry` schema

## Environment Variables

```bash
GPIO_SIMULATION=true     # Force GPIO simulation mode
PI_SIMULATION=true       # Docker Pi simulation flag
MIA_ENV=development      # Skip hardware init
```

## When working here

1. Every hardware worker must have a simulation path — CI depends on it
2. Mock class naming: prefix `Mock` or `Test` (e.g., `MockHardwareWorker`)
3. Docker containers must be self-contained — no host hardware deps
4. OBD Digital Twin must respond to real diagnostic tool queries
5. Test markers: `@pytest.mark.hardware` for real HW, skip in CI with `-m "not hardware"`
6. Pi simulation docker-compose shares volumes for live code reload
