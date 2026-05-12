# Troubleshooting (L1/L2/L3)

## Docker / Compose

- Canonical Compose files live in `infra/docker/`; use `docker compose -f infra/docker/docker-compose.dev.yml config` to validate the dev stack before starting it.
- The root-level `docker-compose.pi-simulation.yml` keeps only the runnable broker/state services enabled by default. Add `--profile legacy-sim` only if you also maintain the older simulator images.
- If `docker compose build` fails while pulling base images with a `gpg: public key decryption failed` or Docker credential timeout, fix the local Docker credential helper first and retry the build.

## ZeroMQ Broker and Service Health

The ZeroMQ broker must be running before any dependent service starts. To verify:

```bash
# Check broker status
sudo systemctl status zmq-broker

# Check core service chain
sudo systemctl status zmq-broker mia-api mia-serial-bridge mia-obd-worker

# Verify broker is listening on port 5555
ss -tlnp | grep 5555

# Verify telemetry PUB/SUB on port 5556
ss -tlnp | grep 5556

# Quick API health check
curl -s http://localhost:8000/status
```

If the broker is not running, all dependent services will fail to connect. Restart in order:

```bash
sudo systemctl restart zmq-broker
sleep 2
sudo systemctl restart mia-api mia-gpio-worker mia-serial-bridge
sleep 2
sudo systemctl restart mia-obd-worker
```

## L1 – Basic Verification

- **Power**: Check PD/QC adapter, cables, and fuse
- **ESP32**: Visible via BLE? RSSI should be > −80 dBm
- **OBD data**: Arriving? Check fuel/RPM in dashboard
- **Camera**: Image feed and ANPR enabled?

## L2 – Network and Messaging

- **MQTT broker**: Running? Check reconnect logs
- **Wi‑Fi Direct / SoftAP**: Throughput verified
- **mDNS discovery**: Android ↔ Pi resolution working

## L3 – Diagnostics and Logs

- Export application logs (BLE, ANPR, OBD services)
- ESP32: serial line, bitrate/filters, watchdog
- Pi gateway: RTSP ingest, disk space, health checks

```bash
# View all MIA service logs
sudo journalctl -u "mia-*" --since "1 hour ago"

# Follow a specific service
sudo journalctl -u mia-serial-bridge -f

# Check for errors across all services
sudo journalctl -u "mia-*" -p err --since "1 hour ago"
```

If the problem persists, open an issue with logs and device versions.
