#!/bin/bash
# Unified Deployment Script for BLE OBD Service
# This script can be sent to RPi via scp and executed remotely
# Usage: scp scripts/deploy-ble-obd-service.sh mia@mia.local:/tmp/ && ssh mia@mia.local 'sudo bash /tmp/deploy-ble-obd-service.sh'

set -euo pipefail

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

log_info "Starting BLE OBD Service deployment..."

# Configuration
PROJECT_DIR="${MIA_INSTALL_DIR:-/opt/mia}"
SERVICES_DIR="$PROJECT_DIR/apps/rpi-backend/py-api/services"
SERVICE_USER="${MIA_USER:-mia}"
SERVICE_GROUP="${MIA_GROUP:-$SERVICE_USER}"
LOG_DIR="${MIA_LOG_DIR:-/var/log/mia}"
SYSTEMD_DIR="${MIA_SYSTEMD_DIR:-/etc/systemd/system}"

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    log_info "Creating service user $SERVICE_USER..."
    useradd -r -s /bin/bash -m -G bluetooth,dialout "$SERVICE_USER"
fi

# Create directories
log_info "Creating directories..."
mkdir -p "$SERVICES_DIR"
mkdir -p "$LOG_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$PROJECT_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"

# Install dependencies if needed
log_info "Checking dependencies..."
if ! python3 -c "import dbus" 2>/dev/null; then
    log_info "Installing python3-dbus..."
    apt-get update
    apt-get install -y python3-dbus python3-gi || log_warning "Could not install python3-dbus"
fi

if ! python3 -c "import zmq" 2>/dev/null; then
    log_info "Installing pyzmq..."
    python3 -m pip install pyzmq || python3 -m pip install --break-system-packages pyzmq || log_warning "Could not install pyzmq"
fi

# Extract and deploy BLE OBD service file
log_info "Deploying BLE OBD service Python script..."
cat > "$SERVICES_DIR/ble_obd_service.py" << 'ENDOFFILE'
#!/usr/bin/env python3
"""
BLE OBD Service - Raspberry Pi BLE Peripheral for OBD-II Communication
Acts as a BLE GATT server that Android app can connect to for OBD-II data

This service:
- Creates a BLE GATT server with Nordic UART Service (NUS) using BlueZ D-Bus API
- Accepts OBD-II commands from connected Android devices
- Forwards commands to OBD worker via ZeroMQ
- Returns OBD responses to Android device
"""

import sys
import os
import json
import logging
import time
import signal
from typing import Optional, Dict, List
from datetime import datetime

try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    logging.warning("D-Bus libraries not available. Install with: apt-get install python3-dbus python3-gi")

import zmq

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Nordic UART Service UUIDs (compatible with Android BLEManager)
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # Write/Command
NUS_RX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Notify/Response

# Device name advertised
DEVICE_NAME = "MIA OBD-II Adapter"


class GATTApplication(dbus.service.Object):
    """
    GATT Application that implements ObjectManager interface
    This is required by BlueZ to discover all GATT objects
    """

    APPLICATION_PATH = "/org/bluez/mia/obd"

    def __init__(self, bus):
        self.path = self.APPLICATION_PATH
        self.bus = bus
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    @dbus.service.method("org.freedesktop.DBus.ObjectManager", out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        """Return all managed GATT objects"""
        objects = {}
        
        # Add all services
        for service in self.services:
            service_path = service.get_path()
            objects[service_path] = {
                "org.bluez.GattService1": service.get_properties()
            }
            
            # Add all characteristics for each service
            for char in service.characteristics:
                char_path = char.get_path()
                objects[char_path] = {
                    "org.bluez.GattCharacteristic1": char.get_properties()
                }
        
        return objects

    def add_service(self, service):
        """Add a GATT service to this application"""
        self.services.append(service)

    def get_path(self):
        return dbus.ObjectPath(self.path)


class NUSService(dbus.service.Object):
    """
    Nordic UART Service implementation using BlueZ D-Bus API
    """

    PATH_BASE = "/org/bluez/mia/obd/service"

    def __init__(self, bus, index, ob_service):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = NUS_SERVICE_UUID
        self.primary = True
        self.characteristics = []
        self.ob_service = ob_service  # Reference to parent BLEOBDService
        dbus.service.Object.__init__(self, bus, self.path)

    @dbus.service.method("org.bluez.GattService1", out_signature="as")
    def GetCharacteristics(self):
        return [char.get_path() for char in self.characteristics]

    @dbus.service.method("org.bluez.GattService1", out_signature="b")
    def GetPrimary(self):
        return self.primary

    @dbus.service.method("org.bluez.GattService1", out_signature="s")
    def GetUUID(self):
        return self.uuid

    def get_properties(self):
        return {
            "UUID": self.uuid,
            "Primary": self.primary,
            "Characteristics": dbus.Array(self.GetCharacteristics(), signature='o')
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)


class NUSCharacteristic(dbus.service.Object):
    """
    GATT Characteristic implementation using BlueZ D-Bus API
    """

    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        self.notifying = False
        self.value = dbus.Array([], signature='y')
        dbus.service.Object.__init__(self, bus, self.path)

    @dbus.service.method("org.bluez.GattCharacteristic1", out_signature="as")
    def GetDescriptors(self):
        return [desc.get_path() for desc in self.descriptors]

    @dbus.service.method("org.bluez.GattCharacteristic1", out_signature="s")
    def GetUUID(self):
        return self.uuid

    @dbus.service.method("org.bluez.GattCharacteristic1", out_signature="s")
    def GetService(self):
        return self.service.get_path()

    @dbus.service.method("org.bluez.GattCharacteristic1", in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        logger.debug(f"ReadValue called on {self.uuid}")
        return self.value

    @dbus.service.method("org.bluez.GattCharacteristic1", in_signature="aya{sv}", out_signature="")
    def WriteValue(self, value, options):
        logger.debug(f"WriteValue called on {self.uuid} with: {bytes(value).decode('utf-8', errors='ignore')}")
        if self.uuid == NUS_TX_CHAR_UUID:
            self.service.ob_service._on_command_received(bytes(value))

    @dbus.service.method("org.bluez.GattCharacteristic1", in_signature="", out_signature="")
    def StartNotify(self):
        if self.uuid == NUS_RX_CHAR_UUID:
            logger.debug("StartNotify called on RX characteristic")
            self.notifying = True

    @dbus.service.method("org.bluez.GattCharacteristic1", in_signature="", out_signature="")
    def StopNotify(self):
        if self.uuid == NUS_RX_CHAR_UUID:
            logger.debug("StopNotify called on RX characteristic")
            self.notifying = False

    @dbus.service.signal("org.bluez.GattCharacteristic1", signature="a{sv}")
    def PropertiesChanged(self, changed_properties):
        pass

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            "UUID": self.uuid,
            "Service": self.service.get_path(),
            "Value": self.value,
            "Notifying": self.notifying,
            "Flags": self.flags,
            "Descriptors": dbus.Array(self.GetDescriptors(), signature='o')
        }


class BLEOBDService:
    """
    BLE GATT server that provides OBD-II interface using BlueZ D-Bus API
    """

    def __init__(self,
                 broker_url: str = "tcp://localhost:5555",
                 device_name: str = DEVICE_NAME):
        self.broker_url = broker_url
        self.device_name = device_name
        self.bus = None
        self.adapter = None
        self.gatt_manager = None
        self.mainloop = None
        self.context = zmq.Context()
        self.broker_socket = None
        self.running = False

        # D-Bus service objects
        self.gatt_app = None
        self.nus_service = None
        self.tx_char = None
        self.rx_char = None

        if not DBUS_AVAILABLE:
            logger.error("D-Bus libraries not available. Cannot start BLE service.")
            raise ImportError("D-Bus libraries required. Install with: apt-get install python3-dbus python3-gi")
    
    def start(self):
        """Start the BLE GATT server"""
        try:
            # Initialize D-Bus
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self.bus = dbus.SystemBus()

            # Connect to ZeroMQ broker
            self.broker_socket = self.context.socket(zmq.DEALER)
            import uuid
            worker_id = f"ble-obd-{uuid.uuid4()}"
            self.broker_socket.setsockopt_string(zmq.IDENTITY, worker_id)
            self.broker_socket.connect(self.broker_url)

            logger.info(f"Connected to ZeroMQ broker at {self.broker_url}")

            # Register with broker
            self._register_worker()

            # Get Bluetooth adapter
            adapter_path = self._get_adapter_path()
            if not adapter_path:
                logger.error("No Bluetooth adapter found")
                return False

            self.adapter = dbus.Interface(
                self.bus.get_object("org.bluez", adapter_path),
                "org.bluez.Adapter1"
            )

            # Get GATT manager
            try:
                self.gatt_manager = dbus.Interface(
                    self.bus.get_object("org.bluez", adapter_path),
                    "org.bluez.GattManager1"
                )
            except dbus.exceptions.DBusException as e:
                logger.error(f"GATT Manager not available: {e}")
                return False

            # Setup GATT service and characteristics
            self._setup_gatt_service()

            # Register GATT application
            self._register_gatt_application()

            # Start main loop
            self.mainloop = GLib.MainLoop()
            self.running = True

            logger.info(f"BLE GATT server started, advertising as '{self.device_name}'")

            # Run main loop in background
            import threading
            loop_thread = threading.Thread(target=self.mainloop.run, daemon=True)
            loop_thread.start()

            # Start response handler in a separate thread
            response_thread = threading.Thread(target=self._response_handler_thread, daemon=True)
            response_thread.start()

            return True

        except Exception as e:
            logger.error(f"Failed to start BLE service: {e}")
            logger.exception(e)
            return False
    
    def _get_adapter_path(self) -> Optional[str]:
        """Get the path of the first Bluetooth adapter"""
        try:
            manager = dbus.Interface(
                self.bus.get_object("org.bluez", "/"),
                "org.freedesktop.DBus.ObjectManager"
            )

            objects = manager.GetManagedObjects()
            for path, interfaces in objects.items():
                if "org.bluez.Adapter1" in interfaces:
                    return path

            return None
        except Exception as e:
            logger.error(f"Error getting adapter path: {e}")
            return None

    def _setup_gatt_service(self):
        """Setup GATT service and characteristics"""
        try:
            # Create GATT application
            self.gatt_app = GATTApplication(self.bus)

            # Create NUS service
            self.nus_service = NUSService(self.bus, 0, self)
            self.gatt_app.add_service(self.nus_service)

            # Create TX characteristic (write)
            self.tx_char = NUSCharacteristic(
                self.bus, 0, NUS_TX_CHAR_UUID,
                ["write", "write-without-response"], self.nus_service
            )
            self.nus_service.add_characteristic(self.tx_char)

            # Create RX characteristic (notify, read)
            self.rx_char = NUSCharacteristic(
                self.bus, 1, NUS_RX_CHAR_UUID,
                ["notify", "read"], self.nus_service
            )
            self.nus_service.add_characteristic(self.rx_char)

            logger.info("GATT service and characteristics configured")

        except Exception as e:
            logger.error(f"Error setting up GATT service: {e}")
            raise

    def _register_gatt_application(self):
        """Register the GATT application with BlueZ"""
        try:
            # Application object path
            app_path = self.gatt_app.get_path()

            # Register application
            self.gatt_manager.RegisterApplication(
                app_path,
                {},  # options
                reply_handler=self._register_application_reply,
                error_handler=self._register_application_error
            )

            logger.info(f"GATT application registered at {app_path}")

        except Exception as e:
            logger.error(f"Error registering GATT application: {e}")
            raise

    def _register_application_reply(self):
        """Callback for successful GATT application registration"""
        logger.info("GATT application registration successful")

    def _register_application_error(self, error):
        """Callback for GATT application registration error"""
        logger.error(f"GATT application registration failed: {error}")

    def _on_command_received(self, data: bytes):
        """Handle incoming OBD command from Android device"""
        try:
            command = data.decode('utf-8').strip()
            logger.debug(f"Received OBD command: {command}")

            # Forward command to OBD worker via ZeroMQ
            self._forward_command(command)

        except Exception as e:
            logger.error(f"Error handling command: {e}")

    def _forward_command(self, command: str):
        """Forward OBD command to OBD worker via ZeroMQ"""
        try:
            message = {
                "type": "OBD_COMMAND",
                "command": command,
                "timestamp": datetime.now().isoformat()
            }

            self.broker_socket.send_json(message)

            # Wait for response (with timeout)
            poller = zmq.Poller()
            poller.register(self.broker_socket, zmq.POLLIN)

            # Poll for response
            response_received = False
            timeout = 5000  # 5 seconds

            for _ in range(50):  # 50 * 100ms = 5 seconds
                socks = dict(poller.poll(100))
                if self.broker_socket in socks:
                    response = self.broker_socket.recv_json()
                    if response.get("type") == "OBD_RESPONSE":
                        self._send_response(response.get("response", ""))
                        response_received = True
                        break

                time.sleep(0.1)

            if not response_received:
                logger.warning(f"No response received for command: {command}")
                self._send_response("NO DATA")

        except Exception as e:
            logger.error(f"Error forwarding command: {e}")
            self._send_response("ERROR")

    def _send_response(self, response: str):
        """Send OBD response to connected Android device"""
        if not self.rx_char or not self.rx_char.notifying:
            logger.debug("RX characteristic not notifying, skipping response")
            return

        try:
            # Format response like ELM327 (with > prompt)
            formatted_response = f"{response}\r>"
            data = formatted_response.encode('utf-8')

            # Update characteristic value as D-Bus array
            self.rx_char.value = dbus.Array([dbus.Byte(b) for b in data], signature='y')

            # Emit PropertiesChanged signal to notify clients
            # This must be called from the main thread (GLib main loop)
            if self.mainloop:
                def emit_notification():
                    try:
                        self.rx_char.PropertiesChanged(
                            dbus.Dictionary({
                                "Value": self.rx_char.value
                            }, signature='sv')
                        )
                    except Exception as e:
                        logger.error(f"Error emitting PropertiesChanged: {e}")

                GLib.idle_add(emit_notification)

            logger.debug(f"Sent OBD response: {response}")

        except Exception as e:
            logger.error(f"Error sending response: {e}")

    def _response_handler_thread(self):
        """Handle responses from ZeroMQ broker (runs in separate thread)"""
        while self.running:
            try:
                # This would be used if we receive async responses
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in response handler: {e}")
                time.sleep(1)
    
    def _register_worker(self):
        """Register this worker with the ZeroMQ broker"""
        message = {
            "type": "WORKER_REGISTER",
            "worker_type": "BLE_OBD",
            "capabilities": ["OBD_COMMAND", "OBD_RESPONSE"],
            "timestamp": datetime.now().isoformat()
        }
        self.broker_socket.send_json(message)
        logger.info("Registered BLE OBD worker with broker")

    def stop(self):
        """Stop the BLE service"""
        self.running = False

        if self.mainloop:
            self.mainloop.quit()

        if self.gatt_manager and self.gatt_app:
            try:
                app_path = self.gatt_app.get_path()
                self.gatt_manager.UnregisterApplication(app_path)
            except Exception as e:
                logger.warning(f"Error unregistering GATT application: {e}")

        if self.broker_socket:
            self.broker_socket.close()

        self.context.term()
        logger.info("BLE OBD service stopped")


def main():
    """Main entry point"""
    service = BLEOBDService()

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if service.start():
            logger.info("BLE OBD service running. Press Ctrl+C to stop.")
            # Keep running
            while service.running:
                time.sleep(1)
        else:
            logger.error("Failed to start BLE OBD service")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception(e)
        sys.exit(1)
    finally:
        service.stop()


if __name__ == "__main__":
    main()
ENDOFFILE

chmod +x "$SERVICES_DIR/ble_obd_service.py"
chown "$SERVICE_USER:$SERVICE_GROUP" "$SERVICES_DIR/ble_obd_service.py"

# Deploy systemd service file
log_info "Deploying systemd service file..."
cat > "$SYSTEMD_DIR/mia-ble-obd.service" << ENDOFFILE
[Unit]
Description=MIA BLE OBD Service - BLE GATT Server for OBD-II Communication
After=network.target bluetooth.service zmq-broker.service
Requires=bluetooth.service
Wants=zmq-broker.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR/apps/rpi-backend/py-api
EnvironmentFile=-/etc/mia/environment
ExecStart=/bin/bash -c 'exec "$${MIA_PYTHON:-/usr/local/bin/mia-python}" services/ble_obd_service.py'
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH=$PROJECT_DIR/apps/rpi-backend/py-api

# Capabilities for Bluetooth
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN

[Install]
WantedBy=multi-user.target
ENDOFFILE

# Reload systemd
log_info "Reloading systemd daemon..."
systemctl daemon-reload

# Restart service
log_info "Restarting mia-ble-obd service..."
systemctl restart mia-ble-obd || log_warning "Could not restart service (may not be enabled yet)"

# Enable service
log_info "Enabling mia-ble-obd service..."
systemctl enable mia-ble-obd || log_warning "Could not enable service"

# Wait a moment for service to start
sleep 2

# Check service status
log_info "Checking service status..."
if systemctl is-active --quiet mia-ble-obd; then
    log_success "mia-ble-obd service is running"
    systemctl status mia-ble-obd --no-pager -l | head -20
else
    log_error "mia-ble-obd service is not running"
    log_info "Recent logs:"
    journalctl -u mia-ble-obd --no-pager -n 20 || true
    exit 1
fi

log_success "BLE OBD Service deployment completed!"
log_info "To view logs: sudo journalctl -u mia-ble-obd -f"
