#!/bin/bash
# Production deploy on the Raspberry Pi (REQ-DEP-008). Run as root from the Pi's MIA source checkout, which is not
# the install directory, e.g.:
#
#   sudo ~/mia-src/tools/scripts/deploy-production-rpi.sh
#
# 1. brings the checkout to $MIA_DEPLOY_REF (default origin/main) with mia-update-checkout.sh, then runs the updated
#    copy of this script (a target whose copy predates that step is not run: this copy goes on, with a warning);
# 2. installs the BLE services (setup-ble-service.sh);
# 3. installs the code, the venv and the units into /opt/mia (deploy-raspberry-pi.sh);
# 4. enables mia-ble-obd and mia-ble-advertiser, and starts them (step 5 restarts every enabled unit);
# 5. restarts every enabled MIA unit, the broker first; an enabled unit that was stopped is started;
# 6. checks that the API answers and that the broker and every unit step 5 restarted are active without an automatic
#    restart after $MIA_DEPLOY_SETTLE_SECONDS, then records the deployed commit in $MIA_STATE_DIR/deployed.json.
#
# Environment:
#   MIA_DEPLOY_REF=<ref>         what to deploy (default origin/main; a tag or a commit works)
#   MIA_DEPLOY_SKIP_FETCH=1      deploy the checkout as it is: no fetch, no checkout
#   MIA_NO_RESTART=1             install only; leave the running services alone (nothing is verified or recorded)
#   MIA_DEPLOY_SETTLE_SECONDS=15 how long after the restart the units are judged; longer than any unit's RestartSec
#   MIA_SKIP_CLAUDE_TOOLING=1    do not update the Claude Code CLI and mcp-prompts (deploy-raspberry-pi.sh)

set -euo pipefail

# bash reads a script while it runs it, and step 1 may replace this file. The whole script is one { } group, which bash
# parses completely before it runs any of it, so this copy is safe to finish whatever the checkout wrote; the exit at
# the end keeps bash from reading on.
{

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${MIA_ENV_FILE:-/etc/mia/environment}"
STATE_DIR="${MIA_STATE_DIR:-/var/lib/mia}"
API_URL="${MIA_API_URL:-http://127.0.0.1:8000}"
DEPLOY_REF="${MIA_DEPLOY_REF:-origin/main}"
SETTLE_SECONDS="${MIA_DEPLOY_SETTLE_SECONDS:-15}"

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
        # Run the target's copy from the top, but only if it has this step. A copy from before it (a rollback past
        # #298) would pull origin main as root and restart nothing; this copy goes on instead.
        if [ -f "$SCRIPT_DIR/deploy-production-rpi.sh" ] \
            && grep -q MIA_DEPLOY_CHECKOUT_DONE "$SCRIPT_DIR/deploy-production-rpi.sh"; then
            exec env MIA_DEPLOY_CHECKOUT_DONE=1 bash "$SCRIPT_DIR/deploy-production-rpi.sh" "$@"
        fi
        log_warning "$DEPLOY_REF predates the safe deploy: its deploy-production-rpi.sh is missing or has no"
        log_warning "safe step 1. Continuing with the current copy; that commit's install scripts still run."
    else
        log_warning "Step 1: $PROJECT_ROOT is not a git checkout; deploying the files as they are"
    fi
fi

# What deployed.json records: the ref that step 1 checked out, or "checkout" for a tree deployed as it is.
if [ "${MIA_DEPLOY_SKIP_FETCH:-0}" = "1" ] || [ ! -d "$PROJECT_ROOT/.git" ]; then
    deployed_ref="checkout"
else
    deployed_ref="$DEPLOY_REF"
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

# Step 4: Enable BLE services. Step 5 then starts them with the other enabled units.
log_info "Step 4: Enabling BLE services (step 5 starts them)..."
systemctl enable mia-ble-obd || log_warning "Could not enable mia-ble-obd"
systemctl enable mia-ble-advertiser || log_warning "Could not enable mia-ble-advertiser"

# Step 5: restart every enabled MIA unit so the new code runs; the broker first (REQ-DEP-001). An enabled unit that
# was stopped is started. One-shot units (mia-selftest, mia-firstboot) run at boot and are not restarted.
services_ok=true
judged_units=()
if [ "${MIA_NO_RESTART:-0}" = "1" ]; then
    log_info "Step 5: MIA_NO_RESTART=1, leaving the running services alone"
else
    log_info "Step 5: Restarting services, broker first..."
    systemctl daemon-reload
    judged_units=(zmq-broker.service)
    if ! systemctl restart zmq-broker.service; then
        log_error "zmq-broker did not restart: journalctl -u zmq-broker -n 50"
        services_ok=false
    fi
    sleep 2
    restart_units=()
    if ! enabled_units="$(systemctl list-unit-files 'mia-*.service' --state=enabled --no-legend)"; then
        log_error "Could not list the enabled MIA units; none but the broker was restarted"
        services_ok=false
        enabled_units=""
    fi
    while read -r unit _; do
        [ -n "$unit" ] || continue
        [ "$(systemctl show -p Type --value "$unit")" = "oneshot" ] && continue
        restart_units+=("$unit")
    done <<< "$enabled_units"
    if [ ${#restart_units[@]} -gt 0 ]; then
        systemctl restart "${restart_units[@]}" || log_warning "Some units did not restart; see the check below"
        judged_units+=("${restart_units[@]}")
    fi
    restarted_at=$SECONDS
fi

# Step 6: verify
log_info "Step 6: Verifying..."

if [ "${MIA_NO_RESTART:-0}" != "1" ]; then
    api_key="$(grep -m1 '^MIA_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
    api_up=false
    for _ in $(seq 1 30); do
        # The header goes to curl on stdin: an argument would show the key to every user in ps.
        if printf 'X-API-Key: %s\n' "$api_key" | curl -fsS -o /dev/null -H @- "$API_URL/status" 2>/dev/null; then
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

    # Every long-running unit has Restart=always or on-failure with a RestartSec of up to 10 s, so a unit that
    # crashes on start shows as activating (auto-restart), not failed. After a wait longer than any RestartSec, a
    # healthy unit is active and has not been restarted automatically since step 5 (a manual restart resets
    # NRestarts).
    wait_left=$(( SETTLE_SECONDS - (SECONDS - restarted_at) ))
    [ "$wait_left" -gt 0 ] && sleep "$wait_left"
    for unit in "${judged_units[@]}"; do
        state="$(systemctl is-active "$unit" 2>/dev/null || true)"
        restarts="$(systemctl show -p NRestarts --value "$unit" 2>/dev/null || true)"
        if [ "$state" != "active" ] || [ "$restarts" != "0" ]; then
            log_error "$unit is ${state:-unknown}, ${restarts:-unknown} automatic restart(s) after ${SETTLE_SECONDS} s"
            log_error "  journalctl -u $unit -n 50"
            services_ok=false
        fi
    done
    # A unit this deploy did not restart (a one-shot such as mia-selftest that failed at boot) is reported only.
    while read -r unit _; do
        [ -n "$unit" ] || continue
        [[ " ${judged_units[*]} " == *" $unit "* ]] && continue
        log_warning "$unit has failed, but was not restarted by this deploy: journalctl -u $unit -n 50"
    done < <(systemctl list-units 'mia-*.service' 'zmq-broker.service' --state=failed --no-legend --plain || true)
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
    if [ "${MIA_NO_RESTART:-0}" = "1" ]; then
        log_success "Installed $sha ($deployed_ref) without a restart. Not verified, so $STATE_DIR/deployed.json"
        log_success "is unchanged; restart zmq-broker first, then the MIA units."
    else
        mkdir -p "$STATE_DIR"
        # json.dumps escapes whatever the ref holds; verified: the API answered and every restarted unit stayed up.
        python3 -c 'import json, sys; ref, sha, at = sys.argv[1:]
print(json.dumps({"ref": ref, "sha": sha, "deployed_at": at, "verified": True}))' \
            "$deployed_ref" "$sha" "$(date -Iseconds)" > "$STATE_DIR/deployed.json.tmp"
        mv "$STATE_DIR/deployed.json.tmp" "$STATE_DIR/deployed.json"
        log_success "Deployment completed: $sha ($deployed_ref), recorded in $STATE_DIR/deployed.json"
    fi
    systemctl list-units 'mia-*.service' 'zmq-broker.service' --no-pager --no-legend --plain | awk '{print "  " $1, $3, $4}'
else
    log_error "Deployment completed with errors. Please check service logs: journalctl -u 'mia-*' -n 100"
    exit 1
fi
exit 0
}
