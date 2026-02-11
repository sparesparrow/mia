#!/bin/bash
# Gonzo Web Monitor Launcher
# Starts the monitoring system for the journalists/gonzo variant

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${PURPLE}🔥 GONZO WEB MONITOR LAUNCHER 🔥${NC}"
echo -e "${CYAN}================================${NC}"

# Check if we're in the right directory
if [ ! -f "$SCRIPT_DIR/monitor-gonzo.py" ]; then
    echo -e "${RED}❌ Error: monitor-gonzo.py not found in $SCRIPT_DIR${NC}"
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python 3 is required but not installed${NC}"
    exit 1
fi

# Check if we're in a git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

# Check if we're on the right branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "feature/journalists-audio-autoplay" ]; then
    echo -e "${YELLOW}⚠️  Warning: Not on feature/journalists-audio-autoplay branch (currently on: $CURRENT_BRANCH)${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Aborted${NC}"
        exit 1
    fi
fi

# Parse command line arguments
PORT=8080
INTERVAL=600
NO_BROWSER=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --no-browser)
            NO_BROWSER=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT        Port to serve on (default: 8080)"
            echo "  --interval SECONDS Refresh interval in seconds (default: 600 = 10 minutes)"
            echo "  --no-browser       Do not open browser automatically"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Start with defaults (port 8080, 10min interval)"
            echo "  $0 --port 3000               # Start on port 3000"
            echo "  $0 --interval 300            # Refresh every 5 minutes"
            echo "  $0 --no-browser              # Start server without opening browser"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Display configuration
echo -e "${BLUE}📋 Configuration:${NC}"
echo -e "  Port: ${GREEN}$PORT${NC}"
echo -e "  Refresh Interval: ${GREEN}$INTERVAL seconds${NC}"
echo -e "  Open Browser: ${GREEN}$([ "$NO_BROWSER" = true ] && echo "No" || echo "Yes")${NC}"
echo -e "  Project Root: ${GREEN}$PROJECT_ROOT${NC}"
echo -e "  Web Directory: ${GREEN}$SCRIPT_DIR${NC}"
echo ""

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Warning: Port $PORT is already in use${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Aborted${NC}"
        exit 1
    fi
fi

# Install Python dependencies if needed
echo -e "${BLUE}🔧 Checking Python dependencies...${NC}"
if ! python3 -c "import urllib.request, json, threading, logging" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Some Python modules may be missing, but continuing...${NC}"
fi

# Make sure the Python script is executable
chmod +x "$SCRIPT_DIR/monitor-gonzo.py"

# Change to web directory
cd "$SCRIPT_DIR"

# Start the monitor
echo -e "${GREEN}🚀 Starting Gonzo Monitor...${NC}"
echo ""

if [ "$NO_BROWSER" = true ]; then
    python3 monitor-gonzo.py --port "$PORT" --interval "$INTERVAL" --no-browser
else
    python3 monitor-gonzo.py --port "$PORT" --interval "$INTERVAL"
fi


