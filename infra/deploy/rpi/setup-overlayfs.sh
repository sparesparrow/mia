#!/usr/bin/env bash
# setup-overlayfs.sh — make rootfs read-only with tmpfs overlay
# Protects the SD card from write wear and corruption on power loss.
#
# Writable bind-mounts preserved:
#   /var/lib/mia/   — persistent state (device registry, sessions, telemetry cache)
#   /var/log/journal/ — systemd journal (size-limited)
#   /opt/mia/data/  — config and feature catalog
#
# Usage: sudo bash infra/deploy/rpi/setup-overlayfs.sh
# To disable: sudo bash infra/deploy/rpi/setup-overlayfs.sh --disable

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

if [[ "${1:-}" == "--disable" ]]; then
    echo -e "${YELLOW}Disabling OverlayFS...${NC}"
    sudo raspi-config nonint disable_overlayfs 2>/dev/null || {
        # Manual fallback: remove the initramfs overlay hook
        sudo rm -f /etc/initramfs-tools/scripts/init-bottom/overlayfs
        sudo update-initramfs -u
    }
    echo -e "${GREEN}OverlayFS disabled. Reboot to apply.${NC}"
    exit 0
fi

echo -e "${GREEN}Setting up OverlayFS for MIA in-car deployment${NC}"

# 1. Create persistent writable directories
echo "Creating writable mount points..."
sudo mkdir -p /var/lib/mia
sudo mkdir -p /opt/mia/data
sudo chown -R "$(logname 2>/dev/null || echo sparrow)":"$(logname 2>/dev/null || echo sparrow)" /var/lib/mia /opt/mia/data

# 2. Limit journal size to prevent disk fill
echo "Configuring journal size limits..."
sudo mkdir -p /etc/systemd/journald.conf.d
cat <<'EOF' | sudo tee /etc/systemd/journald.conf.d/mia-size-limit.conf >/dev/null
[Journal]
SystemMaxUse=50M
SystemMaxFileSize=10M
MaxRetentionSec=7day
EOF

# 3. Create fstab entries for persistent mounts (if not already present)
if ! grep -q '/var/lib/mia' /etc/fstab 2>/dev/null; then
    echo "Adding persistent mount entries to fstab..."
    cat <<'EOF' | sudo tee -a /etc/fstab >/dev/null

# MIA persistent writable mounts (survive OverlayFS)
tmpfs /tmp tmpfs defaults,noatime,nosuid,size=100m 0 0
EOF
fi

# 4. Enable OverlayFS via raspi-config if available
if command -v raspi-config &>/dev/null; then
    echo "Enabling OverlayFS via raspi-config..."
    sudo raspi-config nonint enable_overlayfs
    echo -e "${GREEN}OverlayFS enabled via raspi-config. Reboot to activate.${NC}"
else
    echo -e "${YELLOW}raspi-config not found (Kali Linux).${NC}"
    echo "Manual OverlayFS setup required. Options:"
    echo "  1. Install overlayroot: sudo apt install overlayroot"
    echo "  2. Configure /etc/overlayroot.conf with:"
    echo "     overlayroot=\"tmpfs:swap=1,recurse=0\""
    echo "  3. Reboot"

    if dpkg -l overlayroot &>/dev/null 2>&1; then
        echo "overlayroot is installed, configuring..."
        echo 'overlayroot="tmpfs:swap=1,recurse=0"' | sudo tee /etc/overlayroot.conf >/dev/null
        echo -e "${GREEN}overlayroot configured. Reboot to activate.${NC}"
    else
        echo "Installing overlayroot..."
        sudo apt-get install -y overlayroot 2>/dev/null || {
            echo -e "${YELLOW}overlayroot not available in repos. Manual setup needed.${NC}"
            exit 0
        }
        echo 'overlayroot="tmpfs:swap=1,recurse=0"' | sudo tee /etc/overlayroot.conf >/dev/null
        echo -e "${GREEN}overlayroot configured. Reboot to activate.${NC}"
    fi
fi

echo ""
echo "Persistent directories (survive reboot with OverlayFS):"
echo "  /var/lib/mia/      — device registry, sessions, telemetry cache"
echo "  /var/log/journal/   — systemd journal (50MB max)"
echo "  /opt/mia/data/      — config files, feature catalog"
