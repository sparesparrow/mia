#!/bin/bash
#
# Raspberry Pi Deployment Configuration
# Source this file to set deployment variables
#

export RPI_USER="mia"
export RPI_HOST="192.168.200.139"
export RPI_PORT="22"
export RPI_PATH="/home/mia/ai-servis"
export SSH_KEY=""  # Set to path of SSH key if needed, e.g., "~/.ssh/id_rsa"

# Usage:
#   source deploy/rpi-config.sh
#   ./scripts/deploy-raspberry-pi-remote.sh
