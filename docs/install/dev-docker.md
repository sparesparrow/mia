## Dev Environment: Run Without a Raspberry Pi

This setup runs a local MQTT broker and two simulators:
- `dev-anpr-publisher`: emits fake ANPR events to `vehicle/events/{vin}/anpr`
- `obd-simulator`: emits OBD telemetry to `vehicle/telemetry/{vin}/obd`

### Requirements
- Docker with compose plugin

### Start
```bash
cd edge-compat/pi-gateway
VIN=DEVVIN docker compose -f docker-compose.dev.yml up -d --build
# or use helper scripts
bash scripts/dev-up.sh
```

### Observe topics
```bash
docker run --rm --network host eclipse-mosquitto:2 mosquitto_sub -t 'vehicle/#' -v
```

### Stop
```bash
docker compose -f docker-compose.dev.yml down -v
# or
bash scripts/dev-down.sh
```

This allows Android (or any client) to subscribe to the same topics on localhost:1883 during development.



