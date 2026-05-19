## Raspberry Pi Gateway (Standalone)

> **Audience**: Ops engineers, deployment engineers

- Hardware: Raspberry Pi 4/5, 32GB+ SD/NVMe, 12V→5V buck, optional RTSP/UVC camera.
- OS: Raspberry Pi OS 64‑bit.

### Steps
1. Install Docker (and compose plugin):
```bash
cd edge-compat/pi-gateway/scripts
./install.sh
```

2. Configure VIN and camera stream:
```bash
cd edge-compat/pi-gateway
cp env.example .env
# edit VIN and ANPR_RTSP_URL
```

3. Start services:
```bash
docker compose up -d
docker compose ps
```

4. Verify MQTT discovery:
```bash
mosquitto_sub -h <pi-ip> -t 'vehicle/#' -v
```

### Services included
- `mqtt-broker` (Mosquitto) on 1883
- `mdns-advertiser` publishes `_mqtt._tcp` mDNS
- `camera-server` (RTSP Mediamtx) on 8554
- `lpr-engine` publishes `vehicle/events/{vin}/anpr`
- `health-publisher` publishes `system/health/{node}`
- `mqtt-bridge` optional mirror to remote broker
- `web-ui` serves `web/site` on 8080 (optional)

### Topics
Topics match the app and contracts: `vehicle/telemetry/{vin}/obd`, `vehicle/events/{vin}/anpr`, `vehicle/alerts/{vin}`.

### Smoke test
```bash
bash scripts/smoke.sh
```

For production: harden Mosquitto with password_file and TLS before deployment.
