#!/bin/bash
# On-Pi install (REQ-DEP-008). Run on the Raspberry Pi, from a checkout of this repository, as root; it is
# step 3 of tools/scripts/deploy-production-rpi.sh.
#
# - copies what the systemd units and the code read into $INSTALL_DIR (default /opt/mia), mirroring the repo;
# - installs the Pi API's own requirements (apps/rpi-backend/py-api/requirements.txt) into $INSTALL_DIR/venv;
# - points /usr/local/bin/mia-python and MIA_PYTHON in /etc/mia/environment at that venv;
# - installs and enables the core units.
#
# Running it again is safe: the venv and $INSTALL_DIR/data are kept, nothing is deleted, and the environment file
# keeps every line it does not own, MIA_API_KEY included.
#
# The MIA_* overrides let tests/unit/infra/test_pi_install.py run it in a temporary directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

INSTALL_DIR="${MIA_INSTALL_DIR:-/opt/mia}"
SYSTEMD_DIR="${MIA_SYSTEMD_DIR:-/etc/systemd/system}"
ENV_FILE="${MIA_ENV_FILE:-/etc/mia/environment}"
PYTHON_WRAPPER="${MIA_PYTHON_WRAPPER:-/usr/local/bin/mia-python}"
BASE_PYTHON="${MIA_BASE_PYTHON:-python3}"
PY_REQUIREMENTS="${MIA_PY_REQUIREMENTS:-$PROJECT_ROOT/apps/rpi-backend/py-api/requirements.txt}"
SERVICE_USER="${MIA_USER:-mia}"
USE_SUDO="${MIA_USE_SUDO:-auto}"
VENV_DIR="$INSTALL_DIR/venv"

# What the units and the code read under $INSTALL_DIR: api/main.py and the voice codec load
# schemas/generated/python, the VAG and Citroen bridges run from orchestration/, mia-selftest runs infra/deploy/rpi.
INSTALL_PATHS=(
    apps/rpi-backend/py-api
    apps/rpi-backend/shared
    schemas/generated/python
    orchestration/mcp/modules
    infra/systemd
    infra/deploy/rpi
)

# The broker starts first; the units order themselves after it (REQ-DEP-001).
CORE_UNITS=(
    zmq-broker.service
    mia-api.service
    mia-gpio-worker.service
    mia-serial-bridge.service
    mia-obd-worker.service
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

run_privileged() {
    if [[ "$USE_SUDO" == "0" || "$USE_SUDO" == "false" || "$USE_SUDO" == "no" ]]; then
        "$@"
    elif [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        "$@"
    else
        if ! command -v sudo >/dev/null 2>&1; then
            echo -e "${RED}sudo is required for deployment actions${NC}" >&2
            exit 1
        fi
        sudo "$@"
    fi
}

install_system_packages() {
    echo "Installing system packages..."
    run_privileged env DEBIAN_FRONTEND=noninteractive apt-get update
    # python3-dev and build-essential: RPi.GPIO has no wheels and builds on the Pi.
    # python3-dbus and python3-gi: the BLE services; the venv sees them through --system-site-packages.
    # espeak-ng: the speech fallback when piper is missing.
    run_privileged env DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 \
        python3-venv \
        python3-dev \
        build-essential \
        python3-dbus \
        python3-gi \
        espeak-ng \
        mosquitto \
        mosquitto-clients
}

ensure_service_user() {
    local groups=() group joined
    for group in gpio dialout bluetooth audio i2c spi; do
        if getent group "$group" >/dev/null 2>&1; then
            groups+=("$group")
        fi
    done
    joined="$(IFS=,; echo "${groups[*]}")"

    if id "$SERVICE_USER" >/dev/null 2>&1; then
        if [[ -n "$joined" ]]; then
            run_privileged usermod -a -G "$joined" "$SERVICE_USER"
        fi
    elif [[ -n "$joined" ]]; then
        run_privileged useradd -r -m -s /usr/sbin/nologin -G "$joined" "$SERVICE_USER"
    else
        run_privileged useradd -r -m -s /usr/sbin/nologin "$SERVICE_USER"
    fi
}

install_code() {
    local path
    run_privileged mkdir -p "$INSTALL_DIR"
    if [[ "$(cd "$PROJECT_ROOT" && pwd -P)" == "$(cd "$INSTALL_DIR" && pwd -P)" ]]; then
        echo "The checkout is $INSTALL_DIR; nothing to copy."
    else
        echo "Copying the code to $INSTALL_DIR..."
        for path in "${INSTALL_PATHS[@]}"; do
            run_privileged mkdir -p "$INSTALL_DIR/$path"
            run_privileged cp -a "$PROJECT_ROOT/$path/." "$INSTALL_DIR/$path/"
        done
    fi
    # Piper voices and other run-time data (mia-tts reads $INSTALL_DIR/data/piper).
    run_privileged mkdir -p "$INSTALL_DIR/data"
    run_privileged chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/data"
}

install_python_packages() {
    if [[ ! -x "$VENV_DIR/bin/python" ]]; then
        echo "Creating $VENV_DIR..."
        run_privileged "$BASE_PYTHON" -m venv --system-site-packages "$VENV_DIR"
    fi
    echo "Installing $PY_REQUIREMENTS into $VENV_DIR..."
    run_privileged "$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -r "$PY_REQUIREMENTS"
}

point_units_at_venv() {
    local tmp
    echo "Pointing $PYTHON_WRAPPER and MIA_PYTHON at $VENV_DIR..."
    tmp="$(mktemp)"
    printf '#!/bin/bash\n# MIA Python: the venv tools/scripts/deploy-raspberry-pi.sh installs.\nexec "%s" "$@"\n' \
        "$VENV_DIR/bin/python" > "$tmp"
    run_privileged mkdir -p "$(dirname "$PYTHON_WRAPPER")"
    run_privileged install -m 755 "$tmp" "$PYTHON_WRAPPER"

    # Keep every line this script does not own. A PYTHONHOME left by ensure-bundled-cpython.sh would make the venv's
    # Python load that other interpreter's standard library, so it goes.
    : > "$tmp"
    if run_privileged test -f "$ENV_FILE"; then
        run_privileged cat "$ENV_FILE" | grep -v -e '^MIA_PYTHON=' -e '^PYTHONHOME=' > "$tmp" || true
    fi
    printf 'MIA_PYTHON=%s\n' "$VENV_DIR/bin/python" >> "$tmp"
    run_privileged mkdir -p "$(dirname "$ENV_FILE")"
    run_privileged install -m 600 "$tmp" "$ENV_FILE"
    rm -f "$tmp"
}

install_units() {
    local unit
    echo "Installing systemd units..."
    run_privileged mkdir -p "$SYSTEMD_DIR"
    for unit in "${CORE_UNITS[@]}"; do
        run_privileged cp "$PROJECT_ROOT/infra/systemd/$unit" "$SYSTEMD_DIR/"
        echo "  - Installed $unit"
    done
    run_privileged systemctl daemon-reload
    run_privileged systemctl enable "${CORE_UNITS[@]}"
}

echo "========================================"
echo "  MIA Raspberry Pi install"
echo "========================================"
echo ""

if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This script is designed for Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

install_system_packages
ensure_service_user
install_code
install_python_packages
point_units_at_venv
install_units

echo ""
echo -e "${GREEN}Install complete.${NC}"
echo ""
echo "Python: $VENV_DIR (run by the units through MIA_PYTHON, by hand through mia-python)"
echo "Units enabled: ${CORE_UNITS[*]}"
echo ""
echo "Set the API key in $ENV_FILE if you have not yet (docs/install/pi-gateway.md, step 2), then start the"
echo "broker first:"
echo "  sudo systemctl start zmq-broker"
echo "  sudo systemctl start mia-api mia-gpio-worker mia-serial-bridge mia-obd-worker"
echo ""
echo "Check:"
echo "  systemctl status zmq-broker mia-api"
echo "  curl -H \"X-API-Key: <key>\" http://localhost:8000/status"
echo "  sudo journalctl -u mia-api -f"
echo ""
