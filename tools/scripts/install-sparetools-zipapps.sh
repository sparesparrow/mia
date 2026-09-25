#!/bin/bash
# mia/scripts/install-sparetools-zipapps.sh

REPO="sparesparrow/sparetools"
INSTALL_DIR="$HOME/.local/bin"

# Install bootstrap tool
TOOL="sparetools-bootstrap"
DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | \
  grep "browser_download_url.*$TOOL\.pyz" | \
  cut -d '"' -f 4)

if [ -n "$DOWNLOAD_URL" ]; then
  echo "Installing $TOOL..."
  wget -q "$DOWNLOAD_URL" -O "/tmp/$TOOL.pyz" || curl -L "$DOWNLOAD_URL" -o "/tmp/$TOOL.pyz"
  chmod +x "/tmp/$TOOL.pyz"
  mkdir -p "$INSTALL_DIR"
  mv "/tmp/$TOOL.pyz" "$INSTALL_DIR/$TOOL"
  echo "✅ Installed $TOOL to $INSTALL_DIR"
fi

# Install validation tools
for tool in sparetools-validate-tier1 sparetools-validate-tier2; do
  DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | \
    grep "browser_download_url.*$tool\.pyz" | \
    cut -d '"' -f 4)
  
  if [ -n "$DOWNLOAD_URL" ]; then
    echo "Installing $tool..."
    wget -q "$DOWNLOAD_URL" -O "/tmp/$tool.pyz" || curl -L "$DOWNLOAD_URL" -o "/tmp/$tool.pyz"
    chmod +x "/tmp/$tool.pyz"
    mv "/tmp/$tool.pyz" "$INSTALL_DIR/$tool"
    echo "✅ Installed $tool"
  fi
done