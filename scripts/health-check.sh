#!/bin/bash
# AI-SERVIS Health Check Script

set -euo pipefail

DEFAULT_SERVICES=(
  "ai-servis-core:8080"
  "ai-audio-assistant:8082"
  "ai-platform-linux:8083"
  "service-discovery:8090"
)

HEALTH_PATH="${MIA_HEALTH_PATH:-/health}"
CONNECT_TIMEOUT="${MIA_HEALTH_CONNECT_TIMEOUT:-2}"
MAX_TIME="${MIA_HEALTH_MAX_TIME:-5}"

echo "Checking AI-SERVIS Universal services..."

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for health checks" >&2
  exit 1
fi

if [[ "$#" -gt 0 ]]; then
  services=("$@")
else
  services=("${DEFAULT_SERVICES[@]}")
fi

status=0

for service in "${services[@]}"; do
  url="http://$service$HEALTH_PATH"
  if curl --fail --silent --show-error \
    --connect-timeout "$CONNECT_TIMEOUT" \
    --max-time "$MAX_TIME" \
    "$url" > /dev/null; then
    echo "✅ $service - Healthy"
  else
    echo "❌ $service - Unhealthy ($url)"
    status=1
  fi
done

if [[ "$status" -eq 0 ]]; then
  echo "Health check complete: all services healthy."
else
  echo "Health check complete: one or more services are unhealthy." >&2
fi

exit "$status"
