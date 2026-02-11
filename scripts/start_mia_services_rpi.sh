#!/bin/bash
# MIA Universal Services Startup Script for Raspberry Pi

set -e

echo "Starting MIA Universal Services on Raspberry Pi..."

# Get the correct home directory
MIA_HOME="$HOME/mia-services"

# Set environment variables
export PYTHONPATH="$MIA_HOME:$PYTHONPATH"
export MIA_CONFIG_DIR="$MIA_HOME/config"

# Create log directory
mkdir -p "$MIA_HOME/logs"

# Function to start a service in background
start_service() {
    local service_name=$1
    local service_script=$2
    local log_file="$MIA_HOME/logs/${service_name}.log"

    echo "Starting $service_name..."
    nohup "$MIA_HOME/mia_env/bin/python" "$service_script" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$MIA_HOME/${service_name}.pid"
    echo "$service_name started (PID: $pid)"
}

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$MIA_HOME/${service_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $service_name (PID: $pid)..."
            kill "$pid"
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                echo "Force killing $service_name..."
                kill -9 "$pid"
            fi
        fi
        rm -f "$pid_file"
    fi
}

# Check command line arguments
case "${1:-start}" in
    start)
        echo "Starting all MIA services..."

        # Stop any existing services first
        "$0" stop

        # Start core orchestrator
        start_service "core-orchestrator" "$MIA_HOME/core-orchestrator/main.py"

        # Start hardware bridge
        start_service "hardware-bridge" "$MIA_HOME/hardware-bridge/mcp_bridge.py"

        # Start AI audio assistant
        start_service "ai-audio-assistant" "$MIA_HOME/ai-audio-assistant/main.py"

        echo "All MIA services started successfully!"
        echo "Check logs in $MIA_HOME/logs/"
        echo "Use '$0 status' to check service status"
        ;;

    stop)
        echo "Stopping all MIA services..."

        stop_service "core-orchestrator"
        stop_service "hardware-bridge"
        stop_service "ai-audio-assistant"

        echo "All MIA services stopped."
        ;;

    restart)
        echo "Restarting all MIA services..."
        "$0" stop
        sleep 2
        "$0" start
        ;;

    status)
        echo "MIA Services Status:"
        echo "==================="

        services=("core-orchestrator" "hardware-bridge" "ai-audio-assistant")

        for service in "${services[@]}"; do
            pid_file="$MIA_HOME/${service}.pid"
            if [ -f "$pid_file" ]; then
                pid=$(cat "$pid_file")
                if kill -0 "$pid" 2>/dev/null; then
                    echo "✅ $service: RUNNING (PID: $pid)"
                else
                    echo "❌ $service: DEAD (PID file exists but process not running)"
                fi
            else
                echo "❌ $service: NOT RUNNING"
            fi
        done

        echo ""
        echo "Recent logs:"
        for service in "${services[@]}"; do
            log_file="$MIA_HOME/logs/${service}.log"
            if [ -f "$log_file" ]; then
                echo "$service last 3 lines:"
                tail -3 "$log_file" | sed 's/^/  /'
                echo ""
            fi
        done
        ;;

    logs)
        service="${2:-core-orchestrator}"
        log_file="$MIA_HOME/logs/${service}.log"
        if [ -f "$log_file" ]; then
            echo "Logs for $service:"
            echo "=================="
            cat "$log_file"
        else
            echo "No log file found for $service"
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service]}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all MIA services"
        echo "  stop    - Stop all MIA services"
        echo "  restart - Restart all MIA services"
        echo "  status  - Show status of all services"
        echo "  logs [service] - Show logs for a specific service (default: core-orchestrator)"
        echo ""
        echo "Available services: core-orchestrator, hardware-bridge, ai-audio-assistant"
        exit 1
        ;;
esac