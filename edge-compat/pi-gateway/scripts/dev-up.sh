#!/usr/bin/env bash
set -euo pipefail

docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml ps

echo "Dev stack running. Try:"
echo "  docker run --rm --network host eclipse-mosquitto:2 mosquitto_sub -t 'vehicle/#' -v"



