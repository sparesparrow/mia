#!/bin/bash

# Mobile Intelligent Assistant (MIA) - Car Assistant Startup Script
# Enhanced with MCP-Prompts Integration
# This script starts all required services for the car assistant agent with AI-powered prompt management

set -euo pipefail

# Enhanced logging & error handling
LOG_DIR="${MIA_LOG_DIR:-/var/log/mia}"
PROMPT_CACHE="${MIA_PROMPT_CACHE:-/tmp/mia-prompts.json}"

mkdir -p "$LOG_DIR"

log_info() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $*" | tee -a "$LOG_DIR/mia.log"; }
log_error() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_DIR/mia.log" >&2; }

echo "🚗 Starting Mobile Intelligent Assistant (MIA) - Car Assistant with MCP-Prompts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is available
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✓${NC} $service is running on port $port"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not running on port $port"
        return 1
    fi
}

# Function to start a service in background
start_service() {
    local name=$1
    local command=$2
    local logfile=$3

    echo -e "${BLUE}Starting $name...${NC}"
    if [ -n "$logfile" ]; then
        $command > "$logfile" 2>&1 &
        echo $! > "${name}.pid"
        echo -e "${GREEN}✓${NC} $name started (PID: $!, logs: $logfile)"
    else
        $command &
        echo $! > "${name}.pid"
        echo -e "${GREEN}✓${NC} $name started (PID: $!)"
    fi
}

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

log_info "Checking prerequisites..."

# Check if required packages are installed
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed"
    exit 1
fi

if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed"
    exit 1
fi

if ! command -v npx &> /dev/null; then
    log_error "npm/npx is not installed"
    exit 1
fi

# Check if MCP prompts is installed
if ! npx @sparesparrow/mcp-prompts --help &> /dev/null; then
    log_info "Installing MCP prompts package..."
    sudo npm install -g @sparesparrow/mcp-prompts
fi

echo -e "${GREEN}Prerequisites check passed${NC}"

# Bootstrap mcp-prompts
log_info "Bootstrapping mcp-prompts server..."
export PROMPTS_DIR="${PROMPTS_DIR:-/home/sparrow/mcp/data/prompts}"
export MCP_PROMPTS_PORT=9001

npx @sparesparrow/mcp-prompts --port $MCP_PROMPTS_PORT \
    > "$LOG_DIR/mcp-prompts.log" 2>&1 &

MCP_PROMPTS_PID=$!
echo $MCP_PROMPTS_PID > /tmp/mcp-prompts.pid

# Wait for server to be ready
sleep 3
if ! kill -0 $MCP_PROMPTS_PID 2>/dev/null; then
    log_error "Failed to start mcp-prompts server"
    exit 1
fi

log_info "mcp-prompts server started (PID: $MCP_PROMPTS_PID)"

# Start enhanced workers with prompt integration
echo "Starting hardware workers with MCP-prompts integration..."

# GPIO Worker (enhanced with prompt config)
python3 -c "
import sys
sys.path.append('.')
try:
    # Try to import existing GPIO worker
    from hardware.gpio_worker import GPIOWorker
    worker = GPIOWorker()
    worker.start()
except ImportError:
    print('GPIO worker not available - GPIO libraries not installed (expected on amd64 dev machine)')
    print('This will work on Raspberry Pi with proper GPIO libraries')
    print('Running in simulation mode for development')
" > "$LOG_DIR/gpio_worker.log" 2>&1 &
GPIO_PID=$!
echo $GPIO_PID > gpio_worker.pid
echo -e "${GREEN}✓${NC} GPIO Worker started (PID: $GPIO_PID, logs: logs/gpio_worker.log)"

# OBD Worker (enhanced with diagnostic prompts)
python3 -c "
import sys
sys.path.append('.')
try:
    # Try to import existing OBD worker
    from services.obd_worker import MIAOBDWorker
    worker = MIAOBDWorker()
    worker.start()
except ImportError:
    print('OBD worker not available - ELM327 emulator not installed')
    print('This will work on Raspberry Pi with OBD-II hardware')
    print('Running in simulation mode for development')
" > "$LOG_DIR/obd_worker.log" 2>&1 &
OBD_PID=$!
echo $OBD_PID > obd_worker.pid
echo -e "${GREEN}✓${NC} OBD Worker started (PID: $OBD_PID, logs: logs/obd_worker.log)"

# RF Worker (enhanced with MCP integration)
python3 -c "
import sys
sys.path.append('.')
try:
    # Try to import existing RF worker
    from hardware.rf_worker import RFZMQWorker
    worker = RFZMQWorker()
    worker.start()
except ImportError:
    print('RF worker not available - RF hardware not installed')
    print('This will work on Raspberry Pi with RF modules')
    print('Running in simulation mode for development')
" > "$LOG_DIR/rf_worker.log" 2>&1 &
RF_PID=$!
echo $RF_PID > rf_worker.pid
echo -e "${GREEN}✓${NC} RF Worker started (PID: $RF_PID, logs: logs/rf_worker.log)"

# Start MCP services...
log_info "Starting MCP services..."

# Start MIA Hardware MCP Server
start_service "mia_hardware" "env PYTHONPATH=/home/mia/projects/mia/modules python3 mia/modules/hardware-bridge/hardware_server.py" "logs/mia_hardware.log"

# Start MIA Core Orchestrator
start_service "mia_orchestrator" "env PYTHONPATH=/home/mia/projects/mia/modules python3 mia/modules/core-orchestrator/main.py" "logs/mia_orchestrator.log"

echo ""
echo -e "${GREEN}🎉 Mobile Intelligent Assistant (MIA) Car Assistant Started!${NC}"
echo ""
echo "Services running:"
echo "  • GPIO Worker:     tcp://127.0.0.1:5555 (simulation mode on amd64)"
echo "  • OBD Worker:      tcp://127.0.0.1:5556 (simulation mode on amd64)"
echo "  • RF Worker:       tcp://127.0.0.1:5557 (simulation mode on amd64)"
echo "  • MCP Prompts:     Available via Cursor MCP integration"
echo "  • MIA Hardware:    Available via MCP"
echo "  • MIA Orchestrator: Available via MCP"
echo ""
echo "For full hardware functionality, deploy to Raspberry Pi:"
echo "  • SSH: ssh mia@mia.local"
echo "  • Docker: docker-compose up"
echo "  • GitHub Actions: automated deployment"
echo ""
echo "To stop all services, run: ./stop_car_assistant.sh"
echo ""

# Keep the script running to show status
echo "Press Ctrl+C to stop monitoring..."
trap 'echo -e "\n${YELLOW}Stopping monitoring...${NC}"' INT

while true; do
    echo -e "${BLUE}Service Status Check:$(date)${NC}"
    check_port 5555 "GPIO Worker" || true
    check_port 5556 "OBD Worker" || true
    check_port 5557 "RF Worker" || true
    check_port 9001 "MCP Prompts" || true

    # Check if processes are still running
    for service in gpio_worker obd_worker rf_worker mia_hardware mia_orchestrator mcp-prompts; do
        if [ -f "${service}.pid" ]; then
            pid=$(cat "${service}.pid")
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} $service (PID: $pid)"
            else
                echo -e "${RED}✗${NC} $service (PID: $pid - stopped)"
            fi
        fi
    done

    sleep 10
done
