#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Checking containers"
docker compose ps

echo "[2/4] Waiting for MQTT broker..."
sleep 2

echo "[3/4] Subscribing to test topic in background"
docker run --rm --network host eclipse-mosquitto:2 mosquitto_sub -t "system/health/#" -C 1 -v &
SUB_PID=$!

echo "[4/4] Publishing test message"
docker run --rm --network host eclipse-mosquitto:2 mosquitto_pub -t "system/health/smoke" -m '{"ok":true}' -q 1

wait $SUB_PID || true
echo "Smoke test completed: check above output shows system/health/smoke"


