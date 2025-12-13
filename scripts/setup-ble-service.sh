#!/bin/bash
set -e

echo "========================================"
echo "  Setting up BLE OBD Service on RPi"
echo "========================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "This script must be run on a Raspberry Pi"
    exit 1
fi

# Install BLE dependencies
echo "Installing BLE dependencies..."
sudo apt-get update
sudo apt-get install -y \
    bluetooth \
    bluez \
    python3-bluez \
    libbluetooth-dev

# Install Python BLE libraries
echo "Installing Python BLE libraries..."
sudo apt-get install -y python3-bleak

# Create MIA user if it doesn't exist
if ! id -u mia >/dev/null 2>&1; then
    echo "Creating MIA user..."
    sudo useradd -m -s /bin/bash mia
    sudo usermod -a -G bluetooth,dialout,gpio mia
fi

# Create working directory
echo "Setting up MIA working directory..."
sudo mkdir -p /home/mia/ai-servis
sudo chown -R mia:mia /home/mia/ai-servis

# Copy service files
if [ -d "rpi" ]; then
    echo "Copying service files..."
    sudo cp -r rpi/* /home/mia/ai-servis/
    sudo chown -R mia:mia /home/mia/ai-servis
fi

# Install systemd service
echo "Installing BLE OBD service..."
sudo cp rpi/services/mia-ble-obd.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable Bluetooth
echo "Enabling Bluetooth..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Enable BLE service
echo "Enabling BLE OBD service..."
sudo systemctl enable mia-ble-obd

echo ""
echo "BLE OBD service setup complete!"
echo ""
echo "To start the service:"
echo "  sudo systemctl start mia-ble-obd"
echo ""
echo "To check status:"
echo "  sudo systemctl status mia-ble-obd"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u mia-ble-obd -f"
echo ""
echo "The Android app should now be able to discover 'MIA OBD-II Adapter' via Bluetooth LE"