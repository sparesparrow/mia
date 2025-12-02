#!/bin/bash
#
# Upload Arduino LED Strip Controller to Arduino Uno
#
# Requirements:
# - Arduino CLI installed (arduino-cli)
# - Arduino Uno connected via USB
# - Required libraries: FastLED, ArduinoJson
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKETCH_FILE="${SCRIPT_DIR}/led_strip_controller.ino"
BOARD="arduino:avr:uno"
FQBN="arduino:avr:uno"

echo -e "${GREEN}Arduino LED Strip Controller Upload Script${NC}"
echo "=========================================="

# Check if arduino-cli is installed
if ! command -v arduino-cli &> /dev/null; then
    echo -e "${RED}Error: arduino-cli is not installed${NC}"
    echo ""
    echo "Install arduino-cli:"
    echo "  curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh"
    echo "  sudo mv bin/arduino-cli /usr/local/bin/"
    echo ""
    echo "Or use Arduino IDE instead:"
    echo "  1. Open led_strip_controller.ino in Arduino IDE"
    echo "  2. Select Tools → Board → Arduino Uno"
    echo "  3. Select Tools → Port → [Your Arduino Port]"
    echo "  4. Click Upload"
    exit 1
fi

# Check if sketch file exists
if [ ! -f "$SKETCH_FILE" ]; then
    echo -e "${RED}Error: Sketch file not found: $SKETCH_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Initializing Arduino CLI...${NC}"
arduino-cli core update-index
arduino-cli core install arduino:avr

echo -e "${YELLOW}Step 2: Installing required libraries...${NC}"
arduino-cli lib install "FastLED"
arduino-cli lib install "ArduinoJson"

echo -e "${YELLOW}Step 3: Detecting Arduino board...${NC}"
PORT=$(arduino-cli board list | grep -i "arduino\|uno\|usb" | head -1 | awk '{print $1}')

if [ -z "$PORT" ]; then
    echo -e "${RED}Error: No Arduino board detected${NC}"
    echo ""
    echo "Please:"
    echo "  1. Connect Arduino Uno via USB"
    echo "  2. Check connection: arduino-cli board list"
    exit 1
fi

echo -e "${GREEN}Found Arduino on port: $PORT${NC}"

echo -e "${YELLOW}Step 4: Compiling sketch...${NC}"
arduino-cli compile --fqbn "$FQBN" "$SCRIPT_DIR"

if [ $? -ne 0 ]; then
    echo -e "${RED}Compilation failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Compilation successful!${NC}"

echo -e "${YELLOW}Step 5: Uploading to Arduino...${NC}"
arduino-cli upload -p "$PORT" --fqbn "$FQBN" "$SCRIPT_DIR"

if [ $? -ne 0 ]; then
    echo -e "${RED}Upload failed!${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check USB connection"
    echo "  2. Verify correct port: arduino-cli board list"
    echo "  3. Try pressing reset button on Arduino"
    echo "  4. Check permissions: sudo chmod 666 $PORT"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Upload successful!${NC}"
echo ""
echo "Next steps:"
echo "  1. Open serial monitor: arduino-cli monitor -p $PORT -c baudrate=115200"
echo "  2. Test connection: python modules/hardware-bridge/test_arduino_led.py $PORT"
echo ""
