#!/bin/bash
#
# Raspberry Pi Deployment Configuration
# Source this file to set deployment variables
#

is_sourced() {
	[[ "${BASH_SOURCE[0]}" != "$0" ]]
}

if ! is_sourced; then
	echo "This script must be sourced: source infra/deploy/rpi-config.sh" >&2
	exit 1
fi

export RPI_USER="mia"
export RPI_HOST="192.168.200.139"
export RPI_PORT="22"
export RPI_PATH="/opt/mia"
export SSH_KEY=""  # Set to path of SSH key if needed, e.g., "~/.ssh/id_rsa"

# Usage:
#   source deploy/rpi-config.sh
#   ./scripts/deploy-raspberry-pi-remote.sh
