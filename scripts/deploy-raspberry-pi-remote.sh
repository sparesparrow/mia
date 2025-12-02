#!/bin/bash
#
# Remote Raspberry Pi Deployment Script
# Deploys AI-SERVIS components to Raspberry Pi via SSH
#

set -e

# Configuration
RPI_USER="${RPI_USER:-mia}"
RPI_HOST="${RPI_HOST:-192.168.200.139}"
RPI_PORT="${RPI_PORT:-22}"
RPI_PATH="${RPI_PATH:-/home/mia/ai-servis}"
SSH_KEY="${SSH_KEY:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AI-SERVIS Remote Raspberry Pi Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Target: ${GREEN}${RPI_USER}@${RPI_HOST}:${RPI_PORT}${NC}"
echo -e "Path: ${GREEN}${RPI_PATH}${NC}"
echo ""

# Build SSH command
SSH_CMD="ssh"
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="$SSH_CMD -i $SSH_KEY"
fi
SSH_CMD="$SSH_CMD -p $RPI_PORT ${RPI_USER}@${RPI_HOST}"

# Test SSH connection
echo -e "${YELLOW}Testing SSH connection...${NC}"
if ! $SSH_CMD "echo 'SSH connection successful'" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to ${RPI_USER}@${RPI_HOST}:${RPI_PORT}${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check SSH key is added: ssh-add ~/.ssh/id_rsa"
    echo "  2. Test connection: ssh ${RPI_USER}@${RPI_HOST}"
    echo "  3. Check SSH key path: export SSH_KEY=/path/to/key"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"
echo ""

# Create remote directory structure
echo -e "${YELLOW}Creating remote directory structure...${NC}"
$SSH_CMD "mkdir -p ${RPI_PATH}/{modules/hardware-bridge,arduino/led_strip_controller,scripts}"
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Deploy Python modules
echo -e "${YELLOW}Deploying Python modules...${NC}"
rsync -avz -e "ssh -p $RPI_PORT ${SSH_KEY:+-i $SSH_KEY}" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    modules/hardware-bridge/arduino_led_controller.py \
    modules/hardware-bridge/arduino_led_mcp.py \
    modules/hardware-bridge/test_arduino_led.py \
    ${RPI_USER}@${RPI_HOST}:${RPI_PATH}/modules/hardware-bridge/

echo -e "${GREEN}✓ Python modules deployed${NC}"
echo ""

# Deploy Arduino code (for reference/documentation)
echo -e "${YELLOW}Deploying Arduino code and documentation...${NC}"
rsync -avz -e "ssh -p $RPI_PORT ${SSH_KEY:+-i $SSH_KEY}" \
    arduino/led_strip_controller/ \
    ${RPI_USER}@${RPI_HOST}:${RPI_PATH}/arduino/led_strip_controller/
echo -e "${GREEN}✓ Arduino code deployed${NC}"
echo ""

# Deploy requirements
echo -e "${YELLOW}Deploying requirements...${NC}"
if [ -f modules/hardware-bridge/requirements.txt ]; then
    rsync -avz -e "ssh -p $RPI_PORT ${SSH_KEY:+-i $SSH_KEY}" \
        modules/hardware-bridge/requirements.txt \
        ${RPI_USER}@${RPI_HOST}:${RPI_PATH}/modules/hardware-bridge/
fi
echo -e "${GREEN}✓ Requirements deployed${NC}"
echo ""

# Install Python dependencies on remote
echo -e "${YELLOW}Installing Python dependencies on Raspberry Pi...${NC}"
$SSH_CMD "cd ${RPI_PATH} && \
    python3 -m pip install --user -r modules/hardware-bridge/requirements.txt 2>&1 | tail -5"
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create deployment info file
echo -e "${YELLOW}Creating deployment info...${NC}"
DEPLOY_INFO=$(cat <<EOF
Deployment Date: $(date)
Source Host: $(hostname)
Target: ${RPI_USER}@${RPI_HOST}:${RPI_PATH}
Arduino Port: /dev/ttyUSB0
EOF
)
echo "$DEPLOY_INFO" | $SSH_CMD "cat > ${RPI_PATH}/DEPLOYMENT_INFO.txt"
echo -e "${GREEN}✓ Deployment info created${NC}"
echo ""

# Test deployment
echo -e "${YELLOW}Testing deployment...${NC}"
$SSH_CMD "cd ${RPI_PATH} && \
    python3 -c 'import sys; sys.path.insert(0, \"modules/hardware-bridge\"); from arduino_led_controller import ArduinoLEDController; print(\"✓ Module imports successfully\")'" || {
    echo -e "${YELLOW}Warning: Module test failed, but deployment completed${NC}"
}
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps on Raspberry Pi:"
echo ""
echo "1. Connect Arduino to /dev/ttyUSB0"
echo "2. Test connection:"
echo "   cd ${RPI_PATH}"
echo "   python3 modules/hardware-bridge/test_arduino_led.py /dev/ttyUSB0"
echo ""
echo "3. Start MQTT bridge:"
echo "   python3 -m modules.hardware_bridge.arduino_led_controller /dev/ttyUSB0 localhost"
echo ""
echo "4. Start MCP server:"
echo "   python3 -m modules.hardware_bridge.arduino_led_mcp /dev/ttyUSB0 8084"
echo ""
