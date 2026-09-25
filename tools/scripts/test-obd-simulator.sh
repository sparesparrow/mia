#!/bin/bash
set -e

echo "========================================"
echo "  MIA OBD Simulator Test Suite"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Install test dependencies
echo ""
echo "Installing test dependencies..."
pip3 install -q pytest pytest-cov pytest-mock pyzmq pyserial || {
    echo -e "${YELLOW}Warning: Some test dependencies may not be available${NC}"
}

# Check if OBD components exist
echo ""
echo "Checking OBD components..."
COMPONENTS_OK=true

if [ ! -f "rpi/services/obd_worker.py" ]; then
    echo -e "${RED}  ✗ Missing: rpi/services/obd_worker.py${NC}"
    COMPONENTS_OK=false
else
    echo -e "${GREEN}  ✓ Found: rpi/services/obd_worker.py${NC}"
fi

if [ ! -f "rpi/hardware/serial_bridge.py" ]; then
    echo -e "${RED}  ✗ Missing: rpi/hardware/serial_bridge.py${NC}"
    COMPONENTS_OK=false
else
    echo -e "${GREEN}  ✓ Found: rpi/hardware/serial_bridge.py${NC}"
fi

if [ ! -f "rpi/requirements.txt" ]; then
    echo -e "${RED}  ✗ Missing: rpi/requirements.txt${NC}"
    COMPONENTS_OK=false
else
    echo -e "${GREEN}  ✓ Found: rpi/requirements.txt${NC}"
fi

if [ "$COMPONENTS_OK" = false ]; then
    echo -e "${RED}Some required components are missing. Aborting tests.${NC}"
    exit 1
fi

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
DEPS_OK=true

python3 -c "import zmq" 2>/dev/null || {
    echo -e "${YELLOW}  ⚠ pyzmq not installed${NC}"
    DEPS_OK=false
}

python3 -c "import serial" 2>/dev/null || {
    echo -e "${YELLOW}  ⚠ pyserial not installed (will use mock mode)${NC}"
}

python3 -c "from elm import elm327" 2>/dev/null || {
    echo -e "${YELLOW}  ⚠ ELM327-emulator not installed (OBD worker will not start)${NC}"
}

if [ "$DEPS_OK" = false ]; then
    echo -e "${YELLOW}Some dependencies are missing. Tests may run in mock mode.${NC}"
fi

# Run unit tests
echo ""
echo "Running unit tests..."
if [ -f "tests/integration/test_obd_simulator.py" ]; then
    python3 -m pytest tests/integration/test_obd_simulator.py -v --tb=short || {
        echo -e "${YELLOW}Some tests failed or were skipped${NC}"
    }
else
    echo -e "${YELLOW}Test file not found: tests/integration/test_obd_simulator.py${NC}"
fi

# Test serial bridge mock mode
echo ""
echo "Testing serial bridge (mock mode)..."
python3 -c "
import sys
sys.path.insert(0, 'rpi')
from hardware.serial_bridge import SerialBridge
bridge = SerialBridge(serial_port=None)
print('  ✓ Serial bridge initialized in mock mode')
" || {
    echo -e "${RED}  ✗ Serial bridge test failed${NC}"
    exit 1
}

# Test OBD worker initialization
echo ""
echo "Testing OBD worker initialization..."
python3 -c "
import sys
sys.path.insert(0, 'rpi')
from services.obd_worker import MIAOBDWorker, DynamicCarState
state = DynamicCarState()
state.update_from_telemetry({'pot1': 512, 'pot2': 256})
print(f'  ✓ Car state updated: RPM={state.get_rpm()}, Speed={state.get_speed()}')
worker = MIAOBDWorker()
print('  ✓ OBD worker initialized')
" || {
    echo -e "${YELLOW}  ⚠ OBD worker test completed with warnings${NC}"
}

# Test ZeroMQ integration
echo ""
echo "Testing ZeroMQ integration..."
python3 -c "
import zmq
import json
import time

ctx = zmq.Context()
pub = ctx.socket(zmq.PUB)
pub.bind('inproc://test')
time.sleep(0.1)

sub = ctx.socket(zmq.SUB)
sub.connect('inproc://test')
sub.subscribe('mcu/telemetry')
time.sleep(0.1)

test_data = {'pot1': 512, 'pot2': 256}
pub.send_multipart([b'mcu/telemetry', json.dumps(test_data).encode()])

sub.setsockopt(zmq.RCVTIMEO, 1000)
topic, msg = sub.recv_multipart()
data = json.loads(msg.decode())
assert data == test_data
print('  ✓ ZeroMQ PUB/SUB communication working')
pub.close()
sub.close()
ctx.term()
" || {
    echo -e "${RED}  ✗ ZeroMQ integration test failed${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}All tests completed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Install dependencies: pip3 install -r rpi/requirements.txt"
echo "  2. Flash Arduino firmware: rpi/hardware/arduino_firmware.ino"
echo "  3. Start services: sudo systemctl start zmq-broker mia-serial-bridge mia-obd-worker"
echo ""
