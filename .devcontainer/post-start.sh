#!/bin/bash
set -euo pipefail

echo "🌟 Starting AI-Servis development environment..."

# Check if services are already running
if docker-compose ps | grep -q "Up"; then
    echo "📊 Services already running"
else
    echo "🚀 Starting development services..."
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    
    # Run health check
    if [ -f "./scripts/health-check.sh" ]; then
        ./scripts/health-check.sh || echo "⚠️  Some services may not be fully ready yet"
    fi
fi

# Display useful information
echo ""
echo "🎯 Development Environment Ready!"
echo ""
echo "📍 Service Endpoints:"
echo "  - Core Orchestrator:    http://localhost:8080"
echo "  - Service Discovery:    http://localhost:8090"
echo "  - AI Audio Assistant:   http://localhost:8082"
echo "  - Platform Controller:  http://localhost:8083"
echo "  - Documentation:        http://localhost:8000"
echo "  - Grafana Dashboard:    http://localhost:3000"
echo "  - Prometheus Metrics:   http://localhost:9090"
echo ""
echo "🔌 Database Connections:"
echo "  - PostgreSQL:  localhost:5432 (aiservispdev/aiservislicdbdev)"
echo "  - Redis:       localhost:6379"
echo "  - MQTT:        localhost:1883"
echo ""
echo "🐛 Debug Ports:"
echo "  - Core:                 localhost:5678"
echo "  - Service Discovery:    localhost:5679"
echo "  - Audio Assistant:      localhost:5680"
echo "  - Platform Controller:  localhost:5681"