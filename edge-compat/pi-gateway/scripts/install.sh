#!/usr/bin/env bash
set -euo pipefail

# Install Docker & compose plugin
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
fi

# Avahi for mDNS at host level (optional; container already advertises)
sudo apt-get update -y
sudo apt-get install -y avahi-daemon

echo "Log out/in to refresh docker group if just installed."
echo "Then: cd edge-compat/pi-gateway && cp env.example .env && docker compose up -d && bash scripts/smoke.sh"


