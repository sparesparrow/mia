#!/bin/bash
# Demo script for Gonzo Web Monitor
# Shows the system in action with a shorter refresh interval for demonstration

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}🔥 GONZO MONITOR DEMO 🔥${NC}"
echo -e "${BLUE}========================${NC}"
echo ""
echo -e "${YELLOW}This demo will:${NC}"
echo "1. Start the web server on port 8080"
echo "2. Pull changes from git every 2 minutes (demo mode)"
echo "3. Rebuild web pages after each pull"
echo "4. Refresh browser automatically"
echo "5. Show real-time monitoring logs"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop the demo${NC}"
echo ""

# Wait for user confirmation
read -p "Start demo? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Demo cancelled"
    exit 0
fi

echo -e "${BLUE}🚀 Starting Gonzo Monitor Demo...${NC}"
echo ""

# Start the monitor with 2-minute refresh for demo
cd "$(dirname "$0")"
python3 monitor-gonzo.py --port 8080 --interval 120


