#!/bin/bash
# AI-SERVIS Health Check Script

echo "Checking AI-SERVIS Universal services..."

services=(
  "ai-servis-core:8080"
  "ai-audio-assistant:8082"
  "ai-platform-linux:8083"
  "service-discovery:8090"
)

for service in "${services[@]}"; do
  if curl -f -s "http://$service/health" > /dev/null 2>&1; then
    echo "✅ $service - Healthy"
  else
    echo "❌ $service - Unhealthy"
  fi
done

echo "Health check complete."
