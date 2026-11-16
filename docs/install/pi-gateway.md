# Raspberry Pi install (supported)

> **Audience**: Ops engineers, deployment engineers

The Raspberry Pi 4B is MIA's primary runtime ([ADR-0005](../spec/decisions/0005-raspberry-pi-edge-with-fastapi-gateway.md)).
Services run as systemd units from `/opt/mia`; clients reach only the FastAPI gateway on port 8000.
Background and troubleshooting: [Production deployment](../PRODUCTION_DEPLOYMENT.md).

- Hardware: Raspberry Pi 4B, 32 GB+ SD or NVMe, 12 V → 5 V buck converter.
- OS: Raspberry Pi OS 64-bit.
- Vehicle side: the ESP32 runs the default (listen-only) firmware and the CAN transceiver's `TXD` line stays
  disconnected ([ADR-0006](../spec/decisions/0006-passive-vehicle-access-by-default.md),
  [installer checklist](installer-checklist.md)).

## Steps

1. Deploy from a checkout of this repository on the Pi:
   ```bash
   sudo ./tools/scripts/deploy-production-rpi.sh
   ```
   The script:
   - copies the code to `/opt/mia`;
   - installs the API's requirements (`apps/rpi-backend/py-api/requirements.txt`) into the venv
     `/opt/mia/venv`, never into the system Python;
   - points `/usr/local/bin/mia-python` and `MIA_PYTHON` in `/etc/mia/environment` at that venv;
   - installs and enables the systemd units from `infra/systemd/`.

   It works with the Python of Raspberry Pi OS Bookworm (3.11) and Trixie (3.13). Running it again updates the
   code and keeps the venv and the API key.

2. Set an API key. The units read `/etc/mia/environment`; these commands replace only the `MIA_API_KEY` line and
   keep the `MIA_PYTHON` line the deploy wrote:
   ```bash
   sudo mkdir -p /etc/mia && sudo touch /etc/mia/environment && sudo chmod 600 /etc/mia/environment
   sudo sed -i '/^MIA_API_KEY=/d' /etc/mia/environment
   python3 -c "import secrets; print('MIA_API_KEY=mia_api_' + secrets.token_hex(16))" | sudo tee -a /etc/mia/environment
   ```

3. Start the broker first, then the API and the workers:
   ```bash
   sudo systemctl start zmq-broker
   sudo systemctl start mia-api mia-gpio-worker mia-serial-bridge mia-obd-worker
   systemctl status zmq-broker mia-api
   ```

4. Check the API with the key:
   ```bash
   curl -H "X-API-Key: <key from /etc/mia/environment>" http://<pi-ip>:8000/status
   ```

5. On the phone, open Settings in the MIA app and enter the Pi's address and the same key
   ([ADR-0016](../spec/decisions/0016-android-reaches-the-pi-over-plain-http.md)). The Cycle 1 card on the
   Dashboard then shows the Pi's telemetry.

## Not covered here

`infra/edge/pi-gateway` is an older Docker stack (Mosquitto, mDNS advertiser and simulators) from before
the systemd runtime. It is not covered by the requirements registry and is not how the car install runs; it is
still used by [Dev without a Pi](dev-docker.md).
