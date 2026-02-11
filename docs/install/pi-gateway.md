## Raspberry Pi Gateway (Standalone)

- Hardware: Raspberry Pi 4/5, 32GB+ SD/NVMe, 12V→5V buck, optional RTSP/UVC camera.
- OS: Raspberry Pi OS 64‑bit.

### Steps
1) Install Docker (and compose plugin):
```bash
cd /home/sparrow/projects/ai-servis/edge-compat/pi-gateway/scripts
./install.sh
```

2) Configure VIN and camera stream:
```bash
cd /home/sparrow/projects/ai-servis/edge-compat/pi-gateway
cp env.example .env
# edit VIN and ANPR_RTSP_URL (and REMOTE_URL if mirroring)
```

3) Start services:
```bash
docker compose up -d
docker compose ps
```

4) Verify MQTT discovery:
- Android app discovers `_mqtt._tcp` via mDNS and connects automatically.
- Or test from another client:
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

### Android support (optional)
- If present, the Android app auto-discovers and can publish/subscribe.
- If absent, Pi runs standalone: ANPR, MQTT, and health continue operating.

### Notes
- Topics match the app and contracts: `vehicle/telemetry/{vin}/obd`, `vehicle/events/{vin}/anpr`, `vehicle/alerts/{vin}`.
- Harden Mosquitto for production (password_file, TLS) before deployment. For TLS/auth:
```bash
# Create passwords
mkdir -p services/mosquitto/passwords services/mosquitto/certs
docker run --rm -v $(pwd)/services/mosquitto/passwords:/mosquitto/passwords eclipse-mosquitto:2 \
  mosquitto_passwd -b /mosquitto/passwords/credentials user1 strongpassword

# Place certs (ca.crt, server.crt, server.key) into services/mosquitto/certs

# Start secure compose variant
docker compose -f docker-compose.yml -f docker-compose.secure.yml up -d
```

### Smoke test
After the stack is up, run a quick pub/sub check and verify health:
```bash
# From pi-gateway directory
bash scripts/smoke.sh
```

If Android doesn’t auto-discover the broker, ensure mDNS is allowed on your network and the `mdns-advertiser` container runs in host network mode.


