#!/usr/bin/env bash
# deploy-mia-rpi.sh — auto-discover RPi on LAN, sync code, bootstrap MIA services
# Usage: ./scripts/deploy-mia-rpi.sh [RPI_HOST] [RPI_USER]
# If RPI_HOST is omitted, scans LAN 192.168.200.0/24 for the RPi.
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
RPI_HOST="${1:-}"
RPI_USER="${2:-sparrow}"
RPI_PORT="${RPI_PORT:-22}"
INSTALL_DIR="/opt/mia"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SUBNET="${SUBNET:-192.168.200.0/24}"
SSH_KEY="${SSH_KEY:-}"   # optional explicit key path

# SSH options shared across all calls
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=6 -o BatchMode=yes"
[[ -n "$SSH_KEY" ]] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[info]${NC} $*"; }
ok()      { echo -e "${GREEN}[ ok ]${NC} $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC} $*"; }
die()     { echo -e "${RED}[fail]${NC} $*" >&2; exit 1; }

ssh_rpi() { ssh $SSH_OPTS -p "$RPI_PORT" "$RPI_USER@$RPI_HOST" "$@"; }
scp_rpi() { scp $SSH_OPTS -P "$RPI_PORT" "$@"; }

# ── 1. Discover ───────────────────────────────────────────────────────────────
discover_rpi() {
    info "Scanning $SUBNET for Raspberry Pi (ARM Linux + SSH open)..."
    local candidates
    candidates=$(nmap -p "$RPI_PORT" --open -n "$SUBNET" --min-rate 800 2>/dev/null \
        | awk '/Nmap scan report/{ip=$NF} /'"$RPI_PORT"'\/tcp.*open/{print ip}')

    for ip in $candidates; do
        [[ "$ip" == "$(hostname -I | awk '{print $1}')" ]] && continue  # skip self
        local uname
        uname=$(ssh $SSH_OPTS -p "$RPI_PORT" "$RPI_USER@$ip" 'uname -m' 2>/dev/null || true)
        if [[ "$uname" =~ ^(aarch64|armv[67]l) ]]; then
            ok "Found Raspberry Pi: $ip (arch: $uname)"
            echo "$ip"
            return 0
        fi
        # Also try 'mia' user on same IP
        uname=$(ssh $SSH_OPTS -p "$RPI_PORT" "mia@$ip" 'uname -m' 2>/dev/null || true)
        if [[ "$uname" =~ ^(aarch64|armv[67]l) ]]; then
            RPI_USER="mia"
            ok "Found Raspberry Pi: $ip as mia (arch: $uname)"
            echo "$ip"
            return 0
        fi
    done
    return 1
}

# ── 2. SSH key bootstrap (handles password auth via ssh-copy-id) ──────────────
push_ssh_key() {
    info "Ensuring SSH key is deployed to $RPI_USER@$RPI_HOST..."
    local pub_key
    if [[ -n "$SSH_KEY" ]]; then
        pub_key="${SSH_KEY}.pub"
    else
        pub_key=$(ls ~/.ssh/id_ed25519.pub ~/.ssh/id_rsa.pub 2>/dev/null | head -1)
    fi
    [[ -z "$pub_key" || ! -f "$pub_key" ]] && die "No SSH public key found. Run: ssh-keygen -t ed25519"

    if ssh $SSH_OPTS -p "$RPI_PORT" "$RPI_USER@$RPI_HOST" 'true' 2>/dev/null; then
        ok "SSH key already accepted — no password needed"
    else
        info "Deploying key via ssh-copy-id (you may be prompted for password)..."
        SSH_OPTS_PASS="${SSH_OPTS/-o BatchMode=yes/}"
        # shellcheck disable=SC2086
        ssh-copy-id $SSH_OPTS_PASS -p "$RPI_PORT" -i "$pub_key" "$RPI_USER@$RPI_HOST" || \
            die "ssh-copy-id failed — check credentials or connect the RPi to the network"
    fi
}

# ── 3. Sync code ──────────────────────────────────────────────────────────────
sync_code() {
    info "Syncing project → $RPI_USER@$RPI_HOST:$INSTALL_DIR ..."
    ssh_rpi "sudo mkdir -p $INSTALL_DIR && sudo chown $RPI_USER:$RPI_USER $INSTALL_DIR"
    rsync -avz --progress \
        --exclude='.git' \
        --exclude='.worktrees' \
        --exclude='.buildenv' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='site' \
        --exclude='exported-assets' \
        --exclude='.backups' \
        -e "ssh $SSH_OPTS -p $RPI_PORT" \
        "$REPO_DIR/" \
        "$RPI_USER@$RPI_HOST:$INSTALL_DIR/"
    ok "Code synced"
}

# ── 4. Remote bootstrap ───────────────────────────────────────────────────────
remote_bootstrap() {
    info "Bootstrapping MIA on $RPI_HOST ..."
    ssh_rpi bash -s << 'REMOTE'
set -euo pipefail
INSTALL_DIR="/opt/mia"
VENV="$INSTALL_DIR/venv"

echo "[remote] Installing system deps + arm64-native pydantic (no Rust needed)..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv libzmq3-dev git rsync curl net-tools \
    python3-pydantic python3-pydantic-core python3-aiohttp python3-yaml \
    python3-cryptography python3-jwt python3-psutil python3-serial \
    python3-zmq python3-flatbuffers python3-yaml \
    espeak-ng alsa-utils 2>&1 | tail -5

echo "[remote] Creating venv (--system-site-packages inherits arm64 pydantic)..."
sudo rm -rf "$VENV"
python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip

echo "[remote] Installing remaining Python requirements..."
"$VENV/bin/pip" install --quiet \
    websockets==12.0 fastapi==0.108.0 uvicorn==0.25.0 \
    python-dotenv==1.0.0 httpx==0.26.0 tenacity==8.2.3 \
    orjson==3.9.15 python-multipart argon2-cffi==25.1.0 \
    asyncio-mqtt==0.16.1 pyserial pyyaml \
    pytest pytest-asyncio pytest-cov pytest-mock 2>&1 | tail -3

echo "[remote] Installing voice pipeline dependencies (best-effort)..."
"$VENV/bin/pip" install --quiet \
    sounddevice faster-whisper piper-tts openwakeword 2>&1 | tail -3 || \
    echo "  (some voice deps unavailable on this arch — fallbacks will be used)"

echo "[remote] Patching systemd services to use venv..."
PYTHON_BIN="$VENV/bin/python3"
API_PARENT="$INSTALL_DIR/apps/rpi-backend/py-api"
BROKER="$INSTALL_DIR/apps/rpi-backend/shared/messaging/broker.py"
DEPLOY_USER="${SUDO_USER:-$USER}"
for svc in "$INSTALL_DIR"/infra/systemd/*.service; do
    svc_dest="/etc/systemd/system/$(basename $svc)"
    sudo cp "$svc" "$svc_dest"
    sudo sed -i "s|/usr/bin/python3|$PYTHON_BIN|g"        "$svc_dest"
    sudo sed -i "s|/home/mia/projects/mia|$INSTALL_DIR|g" "$svc_dest"
    sudo sed -i "s|User=mia|User=$DEPLOY_USER|g"           "$svc_dest"
    sudo sed -i "s|Group=mia|Group=$DEPLOY_USER|g"         "$svc_dest"
    sudo sed -i "/PYTHONHOME/d"                            "$svc_dest"  # prevents venv breakage
    # Add WatchdogSec if [Service] exists and WatchdogSec doesn't
    if grep -q '^\[Service\]' "$svc_dest" && ! grep -q 'WatchdogSec' "$svc_dest"; then
        sudo sed -i '/^\[Service\]/a WatchdogSec=30' "$svc_dest"
    fi
done
# API: fix WorkingDirectory (must be parent of api/ package) + module path
sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$API_PARENT|g" /etc/systemd/system/mia-api.service
sudo sed -i "s|ExecStart=.*uvicorn.*|ExecStart=$PYTHON_BIN -m uvicorn api.main:app --host 0.0.0.0 --port 8000|g" \
    /etc/systemd/system/mia-api.service
# Broker: set correct ExecStart path
[[ -f "$BROKER" ]] && \
    sudo sed -i "s|ExecStart=.*broker.py|ExecStart=$PYTHON_BIN $BROKER|g" /etc/systemd/system/zmq-broker.service

# Citroen bridge: use stable /dev/obd2 symlink from udev rules
if [[ -f /etc/systemd/system/mia-citroen-bridge.service ]]; then
    sudo sed -i "s|ELM_SERIAL_PORT=/dev/ttyUSB0|ELM_SERIAL_PORT=/dev/obd2|g" /etc/systemd/system/mia-citroen-bridge.service
    # Add device dependency so bridge only starts when OBD adapter is plugged in
    if ! grep -q 'BindsTo=dev-obd2.device' /etc/systemd/system/mia-citroen-bridge.service; then
        sudo sed -i '/^\[Unit\]/a BindsTo=dev-obd2.device\nAfter=dev-obd2.device' /etc/systemd/system/mia-citroen-bridge.service
    fi
fi

echo "[remote] Reloading systemd..."
sudo systemctl daemon-reload

echo "[remote] Installing boot self-test and watchdog..."
chmod +x "$INSTALL_DIR/infra/deploy/rpi/selftest.sh" 2>/dev/null || true
if [[ -f "$INSTALL_DIR/infra/deploy/rpi/watchdog.conf" ]]; then
    sudo cp "$INSTALL_DIR/infra/deploy/rpi/watchdog.conf" /etc/watchdog.conf
fi

echo "[remote] Creating persistent data directories..."
sudo mkdir -p /var/lib/mia /opt/mia/data
sudo chown "$DEPLOY_USER:$DEPLOY_USER" /var/lib/mia /opt/mia/data

echo "[remote] Installing udev rules for USB devices..."
if [[ -f "$INSTALL_DIR/infra/deploy/rpi/udev/99-mia-devices.rules" ]]; then
    sudo cp "$INSTALL_DIR/infra/deploy/rpi/udev/99-mia-devices.rules" /etc/udev/rules.d/
    sudo udevadm control --reload-rules 2>/dev/null || true
    sudo udevadm trigger 2>/dev/null || true
fi

echo "[remote] Deploying Avahi mDNS service..."
sudo mkdir -p /etc/avahi/services
if [[ -f "$INSTALL_DIR/infra/deploy/avahi-mia-api.service" ]]; then
    sudo cp "$INSTALL_DIR/infra/deploy/avahi-mia-api.service" /etc/avahi/services/mia-api.service
    sudo systemctl restart avahi-daemon 2>/dev/null || true
fi

echo "[remote] Enabling + starting core services..."
sudo systemctl enable zmq-broker mia-api mia-gpio-worker mia-selftest mia-power-monitor 2>/dev/null || true
sudo systemctl enable mia-serial-bridge mia-obd-worker 2>/dev/null || true
sudo systemctl enable mia-audio-capture mia-wake-word mia-stt mia-voice-router mia-tts 2>/dev/null || true
sudo systemctl restart zmq-broker && sleep 2
sudo systemctl restart mia-api mia-gpio-worker
sudo systemctl restart mia-serial-bridge 2>/dev/null || true
sudo systemctl restart mia-obd-worker 2>/dev/null || true
sudo systemctl restart mia-audio-capture mia-wake-word mia-stt mia-voice-router mia-tts 2>/dev/null || true
sudo systemctl restart mia-power-monitor 2>/dev/null || true

echo "[remote] Service status:"
sudo systemctl status zmq-broker mia-api --no-pager -l 2>&1 | tail -20
REMOTE
    ok "Remote bootstrap complete"
}

# ── 5. Smoke test ─────────────────────────────────────────────────────────────
smoke_test() {
    info "Smoke-testing API at http://$RPI_HOST:8000/status ..."
    local tries=0
    until ssh_rpi "curl -sf http://localhost:8000/status" >/dev/null 2>&1; do
        tries=$((tries + 1))
        [[ $tries -ge 10 ]] && { warn "API didn't respond after 30s — check logs: ssh $RPI_USER@$RPI_HOST 'journalctl -u mia-api -n 40'"; return; }
        sleep 3
    done
    ok "MIA API is up → http://$RPI_HOST:8000/status"

    # Check feature catalog
    local features
    features=$(ssh_rpi "curl -sf http://localhost:8000/features" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
    [[ "$features" -gt 0 ]] && ok "Feature catalog: $features features" || warn "Feature catalog not available"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo -e "\n${CYAN}══════════════════════════════════════${NC}"
    echo -e "${CYAN}  MIA Deploy → Raspberry Pi${NC}"
    echo -e "${CYAN}══════════════════════════════════════${NC}\n"

    # Resolve host
    if [[ -z "$RPI_HOST" ]]; then
        RPI_HOST=$(discover_rpi) || die "No Raspberry Pi found on $SUBNET. Is it powered on and connected?"
    else
        info "Using provided host: $RPI_HOST"
    fi

    push_ssh_key
    sync_code
    remote_bootstrap
    smoke_test

    echo -e "\n${GREEN}══════════════════════════════════════${NC}"
    echo -e "${GREEN}  MIA deployed to $RPI_HOST${NC}"
    echo -e "${GREEN}  API:      http://$RPI_HOST:8000${NC}"
    echo -e "${GREEN}  Features: http://$RPI_HOST:8000/features${NC}"
    echo -e "${GREEN}  OTA:      http://$RPI_HOST:8000/ota/status${NC}"
    echo -e "${GREEN}  Logs:     http://$RPI_HOST:8000/logs/services${NC}"
    echo -e "${GREEN}  Thermal:  http://$RPI_HOST:8000/health/thermal${NC}"
    echo -e "${GREEN}  WiFi AP:  sudo bash /opt/mia/infra/deploy/rpi/setup-wifi-ap.sh${NC}"
    echo -e "${GREEN}══════════════════════════════════════${NC}\n"
}

main "$@"
