#!/bin/bash
#
# Upload Arduino LED Strip Controller to Arduino Uno
#
# Requirements:
# - Arduino CLI installed (arduino-cli)
# - Arduino Uno connected via USB
# - Required libraries: FastLED, ArduinoJson
#
# Usage:
#   ./upload.sh                 # Auto-detect Arduino port
#   ./upload.sh /dev/ttyUSB1    # Specify port manually
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Allow port override via command line argument
if [ ! -z "$1" ]; then
    PORT="$1"
    echo -e "${BLUE}Using specified port: $PORT${NC}"
    
    # Verify specified port exists
    if [ ! -e "$PORT" ]; then
        echo -e "${RED}Error: Specified port $PORT does not exist${NC}"
        echo ""
        echo "Available ports:"
        arduino-cli board list
        exit 1
    fi
else
    # Auto-detect Arduino port
    PORTS=$(arduino-cli board list | grep -E "/dev/tty(USB|ACM)" | awk '{print $1}')
    
    if [ -z "$PORTS" ]; then
        echo -e "${RED}Error: No Arduino board detected${NC}"
        echo ""
        echo "Please:"
        echo "  1. Connect Arduino Uno via USB"
        echo "  2. Check connection: arduino-cli board list"
        echo "  3. Check permissions: sudo chmod 666 /dev/ttyUSB*"
        exit 1
    fi
    
    PORT_COUNT=$(echo "$PORTS" | wc -l)
    
    if [ "$PORT_COUNT" -eq 1 ]; then
        # Only one port found - use it
        PORT="$PORTS"
        echo -e "${GREEN}Found single device on port: $PORT${NC}"
    else
        # Multiple ports found - need to identify the Arduino
        echo -e "${BLUE}Multiple serial devices detected:${NC}"
        echo "$PORTS"
        echo ""
        echo -e "${YELLOW}Testing ports to identify Arduino...${NC}"
        
        PORT=""
        for P in $PORTS; do
            echo -n "Testing $P ... "
            
            # Kill any existing processes using this port
            sudo fuser -k "$P" 2>/dev/null || true
            sleep 0.2
            
            # Test if device is quiet (Arduino) or noisy (ESP8266/etc)
            timeout 0.5s cat "$P" 2>/dev/null > /tmp/port_test_$$ &
            sleep 0.6
            BYTES=$(wc -c < /tmp/port_test_$$ 2>/dev/null || echo 0)
            rm -f /tmp/port_test_$$
            
            # Arduino Uno should be relatively quiet when idle
            # ESP8266 devices constantly spam boot messages
            if [ "$BYTES" -lt 50 ]; then
                PORT="$P"
                echo -e "${GREEN}quiet ($BYTES bytes) - likely Arduino ✓${NC}"
                break
            else
                echo -e "${YELLOW}noisy ($BYTES bytes) - likely ESP8266/other${NC}"
            fi
        done
        
        # Fallback to last port if auto-detection failed
        if [ -z "$PORT" ]; then
            PORT=$(echo "$PORTS" | tail -1)
            echo ""
            echo -e "${YELLOW}Warning: Could not auto-detect Arduino${NC}"
            echo -e "${YELLOW}Using fallback port: $PORT${NC}"
            echo ""
            echo "If upload fails, specify port manually:"
            echo "  $0 /dev/ttyUSB0"
            echo "  $0 /dev/ttyUSB1"
            echo ""
        fi
    fi
fi

echo -e "${GREEN}Using Arduino on port: $PORT${NC}"

# Kill any process that might be using the port
echo -e "${YELLOW}Ensuring port is available...${NC}"
sudo fuser -k "$PORT" 2>/dev/null || true
sleep 0.5

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
    echo "  3. Try manual port: $0 /dev/ttyUSB0 or $0 /dev/ttyUSB1"
    echo "  4. Press reset button on Arduino before uploading"
    echo "  5. Check permissions: sudo chmod 666 $PORT"
    echo ""
    echo "If multiple USB serial devices are connected:"
    echo "  - $PORT might not be the Arduino"
    echo "  - Try specifying the other port manually"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Upload successful!${NC}"
echo ""
echo "Next steps:"
echo -e "${BLUE}  1. Test serial monitor:${NC}"
echo "     arduino-cli monitor -p $PORT -c baudrate=115200"
echo ""
echo -e "${BLUE}  2. Test LED controller:${NC}"
echo "     python modules/hardware-bridge/test_arduino_led.py $PORT"
echo ""
echo -e "${BLUE}  3. Run verify script:${NC}"
echo "     ./verify_upload.sh $PORT"
echo ""
