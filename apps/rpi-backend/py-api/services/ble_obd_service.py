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

# Service UUIDs - Android app scans for SPP_UUID
SPP_SERVICE_UUID = "00001101-0000-1000-8000-00805F9B34FB"  # Serial Port Profile (what Android app expects)
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"  # Nordic UART Service (backup)
# Use SPP UUID as primary since Android app scans for it
SERVICE_UUID = SPP_SERVICE_UUID
# Characteristic UUIDs - Android app doesn't check specific UUIDs, only properties
# Using NUS characteristic UUIDs (standard BLE UART characteristics)
TX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # Write/Command
RX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Notify/Response
# Aliases for compatibility checks
NUS_TX_CHAR_UUID = TX_CHAR_UUID
NUS_RX_CHAR_UUID = RX_CHAR_UUID

# Device name advertised
DEVICE_NAME = "MIA OBD-II Adapter"


class GATTApplication(dbus.service.Object):
    """
    GATT Application that implements ObjectManager interface
    Following BlueZ canonical pattern from example-gatt-server
    """

    APPLICATION_PATH = "/org/bluez/mia/obd"

    def __init__(self, bus):
        self.path = self.APPLICATION_PATH
        self.bus = bus
        self.services = []
        # Create object directly on bus - BlueZ example pattern
        # The unique connection name will be used automatically
        dbus.service.Object.__init__(self, bus, self.path)

    @dbus.service.method("org.freedesktop.DBus.ObjectManager", out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        """Return all managed GATT objects - BlueZ calls this to discover services/characteristics"""
        response = {}
        logger.info(f"GetManagedObjects called by BlueZ (we have {len(self.services)} services)")
        
        for service in self.services:
            service_path = service.get_path()
            service_props = service.get_properties()
            response[service_path] = service_props
            logger.info(f"  Added service: {service_path} with UUID: {service.uuid}")
            
            for chrc in service.characteristics:
                chrc_path = chrc.get_path()
                chrc_props = chrc.get_properties()
                response[chrc_path] = chrc_props
                logger.info(f"    Added characteristic: {chrc_path} with UUID: {chrc.uuid}")
        
        logger.info(f"GetManagedObjects returning {len(response)} objects total")
        return response

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

    def __init__(self, bus, index, ob_service, service_uuid):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = service_uuid
        self.primary = True
        self.characteristics = []
        self.ob_service = ob_service  # Reference to parent BLEOBDService
        # Create object directly on bus (BlueZ example pattern)
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
    
    @dbus.service.method("org.freedesktop.DBus.Properties",
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        """Get all properties for an interface"""
        if interface != "org.bluez.GattService1":
            raise dbus.exceptions.DBusException(
                "org.freedesktop.DBus.Error.InvalidArgs",
                "Unknown interface: " + interface
            )
        return self.get_properties()["org.bluez.GattService1"]

    def get_properties(self):
        """Return properties in BlueZ format: interface name as key"""
        return {
            "org.bluez.GattService1": {
                "UUID": self.uuid,
                "Primary": self.primary,
                "Characteristics": dbus.Array(self.GetCharacteristics(), signature='o')
            }
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
        # Create object directly on bus (BlueZ example pattern)
        dbus.service.Object.__init__(self, bus, self.path)
    
    def matches_uuid(self, uuid_to_check):
        """Check if this characteristic matches a UUID"""
        return self.uuid.upper() == uuid_to_check.upper()

    @dbus.service.method("org.bluez.GattCharacteristic1", out_signature="as")
    def GetDescriptors(self):
        return [desc.get_path() for desc in self.descriptors]

    @dbus.service.method("org.bluez.GattCharacteristic1", out_signature="s")
    def GetUUID(self):
        return self.uuid

    @dbus.service.method("org.bluez.GattCharacteristic1", out_signature="o")
    def GetService(self):
        return self.service.get_path()
    
    @dbus.service.method("org.freedesktop.DBus.Properties",
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        """Get all properties for an interface"""
        if interface != "org.bluez.GattCharacteristic1":
            raise dbus.exceptions.DBusException(
                "org.freedesktop.DBus.Error.InvalidArgs",
                "Unknown interface: " + interface
            )
        return self.get_properties()["org.bluez.GattCharacteristic1"]

    @dbus.service.method("org.bluez.GattCharacteristic1", in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        logger.debug(f"ReadValue called on {self.uuid}")
        return self.value

    @dbus.service.method("org.bluez.GattCharacteristic1", in_signature="aya{sv}", out_signature="")
    def WriteValue(self, value, options):
        logger.debug(f"WriteValue called on {self.uuid} with: {bytes(value).decode('utf-8', errors='ignore')}")
        # Accept writes on TX characteristic (either SPP or NUS UUID)
        if self.matches_uuid(TX_CHAR_UUID) or self.matches_uuid(NUS_TX_CHAR_UUID):
            self.service.ob_service._on_command_received(bytes(value))

    @dbus.service.method("org.bluez.GattCharacteristic1", in_signature="", out_signature="")
    def StartNotify(self):
        # Accept notifications on RX characteristic (either SPP or NUS UUID)
        if self.matches_uuid(RX_CHAR_UUID) or self.matches_uuid(NUS_RX_CHAR_UUID):
            logger.debug("StartNotify called on RX characteristic")
            self.notifying = True

    @dbus.service.method("org.bluez.GattCharacteristic1", in_signature="", out_signature="")
    def StopNotify(self):
        # Accept stop notifications on RX characteristic (either SPP or NUS UUID)
        if self.matches_uuid(RX_CHAR_UUID) or self.matches_uuid(NUS_RX_CHAR_UUID):
            logger.debug("StopNotify called on RX characteristic")
            self.notifying = False

    @dbus.service.signal("org.freedesktop.DBus.Properties",
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        """Signal emitted when properties change"""
        pass

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        """Return properties in BlueZ format: interface name as key"""
        return {
            "org.bluez.GattCharacteristic1": {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
                "Descriptors": dbus.Array(self.GetDescriptors(), signature='o')
            }
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

            # Setup GATT service and characteristics FIRST
            # (Objects must exist before main loop starts for proper registration)
            self._setup_gatt_service()

            # Start main loop (needed for D-Bus service objects to expose interfaces)
            self.mainloop = GLib.MainLoop()
            self.running = True
            
            # Run main loop in background thread
            import threading
            loop_thread = threading.Thread(target=self.mainloop.run, daemon=True)
            loop_thread.start()
            
            # Wait a moment for main loop to start and objects to be registered
            time.sleep(1.0)

            # Register GATT application (after objects exist and main loop is running)
            self._register_gatt_application()

            logger.info(f"BLE GATT server started, advertising as '{self.device_name}'")

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

            # Create SPP service (what Android app expects)
            self.nus_service = NUSService(self.bus, 0, self, SERVICE_UUID)
            self.gatt_app.add_service(self.nus_service)

            # Create TX characteristic (write) - using SPP UUID
            self.tx_char = NUSCharacteristic(
                self.bus, 0, TX_CHAR_UUID,
                ["write", "write-without-response"], self.nus_service
            )
            self.nus_service.add_characteristic(self.tx_char)

            # Create RX characteristic (notify, read) - using SPP UUID
            self.rx_char = NUSCharacteristic(
                self.bus, 1, RX_CHAR_UUID,
                ["notify", "read"], self.nus_service
            )
            self.nus_service.add_characteristic(self.rx_char)

            logger.info(f"GATT service configured with UUID: {SERVICE_UUID}")
            logger.info(f"TX characteristic: {TX_CHAR_UUID}")
            logger.info(f"RX characteristic: {RX_CHAR_UUID}")

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
                        # Use BlueZ canonical PropertiesChanged signature: interface, changed, invalidated
                        self.rx_char.PropertiesChanged(
                            "org.bluez.GattCharacteristic1",
                            dbus.Dictionary({
                                "Value": self.rx_char.value
                            }, signature='sv'),
                            dbus.Array([], signature='s')
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
