#!/bin/bash
#
# Verify Arduino LED Strip Controller Upload
#

set -e

PORT=${1:-/dev/ttyUSB0}
BAUD=115200

echo "Verifying Arduino LED Strip Controller on $PORT..."
echo ""

# Check if port exists
if [ ! -e "$PORT" ]; then
    echo "Error: Port $PORT not found"
    exit 1
fi

# Test serial communication
echo "Sending status command..."
echo '{"command":"status"}' > "$PORT"

sleep 1

echo ""
echo "Reading response (if any)..."
timeout 2 cat < "$PORT" 2>&1 | head -10 || echo "No response received"

echo ""
echo "To properly test, use Python script:"
echo "  python modules/hardware-bridge/test_arduino_led.py $PORT"
echo ""
echo "Or use Arduino Serial Monitor:"
echo "  arduino-cli monitor -p $PORT -c baudrate=$BAUD"
