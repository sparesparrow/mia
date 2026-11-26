#!/bin/bash
# Production deploy on the Raspberry Pi (REQ-DEP-008). Run as root from the Pi's MIA source checkout, which is not
# the install directory, e.g.:
#
#   sudo ~/mia-src/tools/scripts/deploy-production-rpi.sh
#
# 1. brings the checkout to $MIA_DEPLOY_REF (default origin/main) with mia-update-checkout.sh, then runs the updated
#    copy of this script;
# 2. installs the BLE services (setup-ble-service.sh);
# 3. installs the code, the venv and the units into /opt/mia (deploy-raspberry-pi.sh);
# 4. enables the BLE units;
# 5. restarts every enabled MIA unit, the broker first;
# 6. checks that the API answers and no MIA unit failed, and records the deployed commit in $MIA_STATE_DIR/deployed.json.
#
# Environment:
#   MIA_DEPLOY_REF=<ref>         what to deploy (default origin/main; a tag or a commit works)
#   MIA_DEPLOY_SKIP_FETCH=1      deploy the checkout as it is: no fetch, no checkout
#   MIA_NO_RESTART=1             install only; leave the running services alone
#   MIA_SKIP_CLAUDE_TOOLING=1    do not update the Claude Code CLI and mcp-prompts (deploy-raspberry-pi.sh)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${MIA_ENV_FILE:-/etc/mia/environment}"
STATE_DIR="${MIA_STATE_DIR:-/var/lib/mia}"
API_URL="${MIA_API_URL:-http://127.0.0.1:8000}"
DEPLOY_REF="${MIA_DEPLOY_REF:-origin/main}"

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

# Step 1: bring the checkout to the deploy ref, then continue with the updated copy of this script.
if [ "${MIA_DEPLOY_CHECKOUT_DONE:-0}" != "1" ]; then
    if [ "${MIA_DEPLOY_SKIP_FETCH:-0}" = "1" ]; then
        log_info "Step 1: MIA_DEPLOY_SKIP_FETCH=1, deploying the checkout as it is"
    elif [ -d "$PROJECT_ROOT/.git" ]; then
        log_info "Step 1: Bringing $PROJECT_ROOT to $DEPLOY_REF..."
        # A failed fetch or local changes stop the deploy: deploying stale code under a success message is worse.
        bash "$SCRIPT_DIR/mia-update-checkout.sh" "$PROJECT_ROOT" "$DEPLOY_REF" >/dev/null
        # bash reads a script as it runs; the checkout may have replaced this file, so run the new copy from the top.
        exec env MIA_DEPLOY_CHECKOUT_DONE=1 bash "$SCRIPT_DIR/deploy-production-rpi.sh" "$@"
    else
        log_warning "Step 1: $PROJECT_ROOT is not a git checkout; deploying the files as they are"
    fi
fi

log_info "Deploying $(git -C "$PROJECT_ROOT" -c safe.directory="$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'an unversioned tree')"

# Step 2: Run BLE service setup
log_info "Step 2: Setting up BLE services..."
if [ -f "$PROJECT_ROOT/tools/scripts/setup-ble-service.sh" ]; then
    bash "$PROJECT_ROOT/tools/scripts/setup-ble-service.sh"
else
    log_error "BLE setup script not found!"
    exit 1
fi

# Step 3: Deploy main services
log_info "Step 3: Installing code, venv and units..."
bash "$PROJECT_ROOT/tools/scripts/deploy-raspberry-pi.sh"

# Step 4: Enable BLE services
log_info "Step 4: Enabling BLE services..."
systemctl enable mia-ble-obd || log_warning "Could not enable mia-ble-obd"
systemctl enable mia-ble-advertiser || log_warning "Could not enable mia-ble-advertiser"

# Step 5: restart every enabled MIA unit so the new code runs; the broker first (REQ-DEP-001).
# One-shot units (mia-selftest, mia-firstboot) run at boot and are not restarted.
if [ "${MIA_NO_RESTART:-0}" = "1" ]; then
    log_info "Step 5: MIA_NO_RESTART=1, leaving the running services alone"
else
    log_info "Step 5: Restarting services, broker first..."
    systemctl daemon-reload
    systemctl restart zmq-broker.service
    sleep 2
    restart_units=()
    while read -r unit _; do
        [ -n "$unit" ] || continue
        [ "$(systemctl show -p Type --value "$unit")" = "oneshot" ] && continue
        restart_units+=("$unit")
    done < <(systemctl list-unit-files 'mia-*.service' --state=enabled --no-legend)
    if [ ${#restart_units[@]} -gt 0 ]; then
        systemctl restart "${restart_units[@]}" || log_warning "Some units did not restart; see the check below"
    fi
fi

# Step 6: verify
log_info "Step 6: Verifying..."
services_ok=true

if [ "${MIA_NO_RESTART:-0}" != "1" ]; then
    api_key="$(grep -m1 '^MIA_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
    api_up=false
    for _ in $(seq 1 30); do
        if curl -fsS -o /dev/null -H "X-API-Key: $api_key" "$API_URL/status" 2>/dev/null; then
            api_up=true
            break
        fi
        sleep 2
    done
    if [ "$api_up" = true ]; then
        log_success "API answers at $API_URL/status"
    else
        log_error "API did not answer at $API_URL/status within 60 s: journalctl -u mia-api -n 50"
        services_ok=false
    fi

    sleep 5  # a unit that crashes on start shows as failed or activating after a few seconds
    failed="$(systemctl list-units 'mia-*.service' 'zmq-broker.service' --state=failed --no-legend --plain | awk '{print $1}')"
    if [ -n "$failed" ]; then
        log_error "Failed units: $(echo "$failed" | tr '\n' ' ')"
        services_ok=false
    fi
fi

if command -v hciconfig &>/dev/null && hciconfig hci0 &>/dev/null; then
    if hciconfig hci0 | grep -q "UP RUNNING"; then
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
    sha="$(git -C "$PROJECT_ROOT" -c safe.directory="$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
    mkdir -p "$STATE_DIR"
    printf '{"ref":"%s","sha":"%s","deployed_at":"%s"}\n' "$DEPLOY_REF" "$sha" "$(date -Iseconds)" \
        > "$STATE_DIR/deployed.json"
    log_success "Deployment completed: $sha ($DEPLOY_REF), recorded in $STATE_DIR/deployed.json"
    systemctl list-units 'mia-*.service' 'zmq-broker.service' --no-pager --no-legend --plain | awk '{print "  " $1, $3, $4}'
else
    log_error "Deployment completed with errors. Please check service logs: journalctl -u 'mia-*' -n 100"
    exit 1
fi
