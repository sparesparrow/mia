#!/bin/bash
# Production Deployment Script for Raspberry Pi
# Deploys complete system including BLE services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Please run as root (use sudo)"
    exit 1
fi

log_info "Starting production deployment for Raspberry Pi..."

# Step 1: Pull latest code
log_info "Step 1: Updating code from repository..."
cd "$PROJECT_ROOT"
if [ -d ".git" ]; then
    git pull origin main || log_warning "Could not pull from git (may be in detached state)"
else
    log_warning "Not a git repository, skipping git pull"
fi

# Step 2: Run BLE service setup
log_info "Step 2: Setting up BLE services..."
if [ -f "$PROJECT_ROOT/scripts/setup-ble-service.sh" ]; then
    bash "$PROJECT_ROOT/scripts/setup-ble-service.sh"
else
    log_error "BLE setup script not found!"
    exit 1
fi

# Step 3: Deploy main services
log_info "Step 3: Deploying main services..."
if [ -f "$PROJECT_ROOT/scripts/deploy-raspberry-pi.sh" ]; then
    bash "$PROJECT_ROOT/scripts/deploy-raspberry-pi.sh"
else
    log_warning "Main deployment script not found, skipping..."
fi

# Step 4: Enable and start BLE services
log_info "Step 4: Enabling BLE services..."
systemctl enable mia-ble-obd || log_warning "Could not enable mia-ble-obd"
systemctl enable mia-ble-advertiser || log_warning "Could not enable mia-ble-advertiser"

# Step 5: Start services
log_info "Step 5: Starting services..."
systemctl start mia-ble-obd || log_warning "Could not start mia-ble-obd"
systemctl start mia-ble-advertiser || log_warning "Could not start mia-ble-advertiser"

# Step 6: Verify services
log_info "Step 6: Verifying services..."
sleep 2

services_ok=true

if systemctl is-active --quiet mia-ble-obd; then
    log_success "mia-ble-obd service is running"
else
    log_error "mia-ble-obd service is not running"
    services_ok=false
fi

if systemctl is-active --quiet mia-ble-advertiser; then
    log_success "mia-ble-advertiser service is running"
else
    log_error "mia-ble-advertiser service is not running"
    services_ok=false
fi

# Step 7: Check Bluetooth status
log_info "Step 7: Checking Bluetooth status..."
if hciconfig &>/dev/null; then
    hci_status=$(hciconfig hci0 | grep -q "UP RUNNING" && echo "UP" || echo "DOWN")
    if [ "$hci_status" = "UP" ]; then
        log_success "Bluetooth adapter is UP"
    else
        log_warning "Bluetooth adapter is DOWN"
    fi
else
    log_warning "Bluetooth hardware not detected"
fi

# Summary
echo ""
log_info "=== Deployment Summary ==="
if [ "$services_ok" = true ]; then
    log_success "Deployment completed successfully!"
    echo ""
    log_info "Services status:"
    systemctl status mia-ble-obd --no-pager -l || true
    echo ""
    systemctl status mia-ble-advertiser --no-pager -l || true
    echo ""
    log_info "To view logs:"
    echo "  sudo journalctl -u mia-ble-obd -f"
    echo "  sudo journalctl -u mia-ble-advertiser -f"
else
    log_error "Deployment completed with errors. Please check service logs."
    exit 1
fi
