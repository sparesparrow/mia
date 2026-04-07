#!/usr/bin/env bash
# setup-wifi-ap.sh — configure RPi as a WiFi access point for in-car use
#
# Creates "MIA-Car" WiFi network at 192.168.4.0/24.
# Android phones connect to this and discover the API via mDNS.
#
# Usage: sudo bash infra/deploy/rpi/setup-wifi-ap.sh
# To disable: sudo bash infra/deploy/rpi/setup-wifi-ap.sh --disable

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

if [[ "${1:-}" == "--disable" ]]; then
    echo -e "${YELLOW}Disabling WiFi AP mode...${NC}"
    sudo systemctl stop hostapd dnsmasq 2>/dev/null || true
    sudo systemctl disable hostapd 2>/dev/null || true
    sudo rm -f /etc/dnsmasq.d/mia.conf
    # Restore dynamic wlan0
    if [[ -f /etc/network/interfaces.d/wlan0-ap.bak ]]; then
        sudo rm -f /etc/network/interfaces.d/wlan0-ap
    fi
    sudo ip addr flush dev wlan0 2>/dev/null || true
    sudo systemctl restart networking 2>/dev/null || true
    echo -e "${GREEN}WiFi AP disabled. wlan0 returned to client mode.${NC}"
    exit 0
fi

echo -e "${CYAN}══════════════════════════════════════${NC}"
echo -e "${CYAN}  MIA WiFi Access Point Setup${NC}"
echo -e "${CYAN}══════════════════════════════════════${NC}"

# 1. Install required packages
echo "Installing hostapd + dnsmasq..."
sudo apt-get update -qq
sudo apt-get install -y -qq hostapd dnsmasq avahi-daemon 2>&1 | tail -3

# 2. Stop services during configuration
sudo systemctl stop hostapd dnsmasq 2>/dev/null || true

# 3. Configure static IP for wlan0
echo "Configuring wlan0 static IP (192.168.4.1)..."
# Use dhcpcd if available (Raspbian), otherwise direct interface config
if [[ -f /etc/dhcpcd.conf ]]; then
    if ! grep -q 'interface wlan0' /etc/dhcpcd.conf 2>/dev/null; then
        cat <<'EOF' | sudo tee -a /etc/dhcpcd.conf >/dev/null

# MIA WiFi AP — static IP for wlan0
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF
    fi
else
    # Kali Linux / direct config
    cat <<'EOF' | sudo tee /etc/network/interfaces.d/wlan0-ap >/dev/null
# MIA WiFi AP
auto wlan0
iface wlan0 inet static
    address 192.168.4.1
    netmask 255.255.255.0
EOF
fi

# 4. Deploy hostapd config
echo "Deploying hostapd configuration..."
sudo cp "$SCRIPT_DIR/hostapd.conf" /etc/hostapd/hostapd.conf
# Point hostapd to the config
if [[ -f /etc/default/hostapd ]]; then
    sudo sed -i 's|^#\?DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd
fi

# 5. Deploy dnsmasq config
echo "Deploying dnsmasq configuration..."
sudo cp "$SCRIPT_DIR/dnsmasq-mia.conf" /etc/dnsmasq.d/mia.conf

# 6. Unmask and enable hostapd (often masked by default)
sudo systemctl unmask hostapd 2>/dev/null || true
sudo rfkill unblock wlan 2>/dev/null || true

# 7. Deploy Avahi mDNS service for _mia-api._tcp
echo "Deploying Avahi mDNS service..."
AVAHI_SVC="$(dirname "$SCRIPT_DIR")/deploy/avahi-mia-api.service"
if [[ ! -f "$AVAHI_SVC" ]]; then
    AVAHI_SVC="$(dirname "$SCRIPT_DIR")/../deploy/avahi-mia-api.service"
fi
# Try the repo path
if [[ -f "$AVAHI_SVC" ]]; then
    sudo cp "$AVAHI_SVC" /etc/avahi/services/mia-api.service
elif [[ -f /opt/mia/infra/deploy/avahi-mia-api.service ]]; then
    sudo cp /opt/mia/infra/deploy/avahi-mia-api.service /etc/avahi/services/mia-api.service
fi
sudo systemctl restart avahi-daemon 2>/dev/null || true

# 8. Set wlan0 IP now (before reboot)
sudo ip addr flush dev wlan0 2>/dev/null || true
sudo ip addr add 192.168.4.1/24 dev wlan0 2>/dev/null || true
sudo ip link set wlan0 up 2>/dev/null || true

# 9. Start services
echo "Starting hostapd + dnsmasq..."
sudo systemctl enable hostapd dnsmasq
sudo systemctl start dnsmasq
sudo systemctl start hostapd

echo ""
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  WiFi AP configured!${NC}"
echo -e "${GREEN}  SSID: MIA-Car${NC}"
echo -e "${GREEN}  Password: mia-car-2026${NC}"
echo -e "${GREEN}  RPi IP: 192.168.4.1${NC}"
echo -e "${GREEN}  DHCP range: 192.168.4.10-50${NC}"
echo -e "${GREEN}  mDNS: _mia-api._tcp${NC}"
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo ""
echo "Android phones can now:"
echo "  1. Connect to 'MIA-Car' WiFi"
echo "  2. App discovers API via mDNS at http://192.168.4.1:8000"
echo "  3. Or browse to http://mia:8000"
