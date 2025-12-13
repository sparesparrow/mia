#!/usr/bin/env python3
"""
BLE Advertiser Service - Makes Raspberry Pi discoverable as OBD-II adapter
Uses BlueZ D-Bus API to advertise BLE service

This service:
- Advertises the device as "MIA OBD-II Adapter"
- Makes the device discoverable by Android BLE scanners
- Configures Bluetooth adapter for BLE peripheral mode
"""

import sys
import os
import logging
import time
import signal
from typing import Optional

try:
    import dbus
    import dbus.mainloop.glib
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    logging.warning("D-Bus libraries not available. Install with: apt-get install python3-dbus python3-gi")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service UUID for OBD-II adapter
OBD_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
DEVICE_NAME = "MIA OBD-II Adapter"


class BLEAdvertiser:
    """
    BLE Advertiser using BlueZ D-Bus API
    """
    
    def __init__(self, device_name: str = DEVICE_NAME):
        self.device_name = device_name
        self.bus = None
        self.adapter = None
        self.advertising_manager = None
        self.mainloop = None
        self.running = False
        
        if not DBUS_AVAILABLE:
            logger.error("D-Bus libraries not available. Cannot start BLE advertiser.")
            raise ImportError("D-Bus libraries required. Install with: apt-get install python3-dbus python3-gi")
    
    def start(self):
        """Start BLE advertising"""
        try:
            # Initialize D-Bus
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self.bus = dbus.SystemBus()
            
            # Get Bluetooth adapter
            adapter_path = self._get_adapter_path()
            if not adapter_path:
                logger.error("No Bluetooth adapter found")
                return False
            
            self.adapter = dbus.Interface(
                self.bus.get_object("org.bluez", adapter_path),
                "org.bluez.Adapter1"
            )
            
            # Get advertising manager
            try:
                self.advertising_manager = dbus.Interface(
                    self.bus.get_object("org.bluez", adapter_path),
                    "org.bluez.LEAdvertisingManager1"
                )
            except dbus.exceptions.DBusException as e:
                logger.error(f"LEAdvertisingManager not available: {e}")
                logger.info("Trying alternative method using hciconfig...")
                return self._start_legacy_advertising()
            
            # Register advertisement
            self._register_advertisement()
            
            # Start main loop
            self.mainloop = GLib.MainLoop()
            self.running = True
            
            logger.info(f"BLE advertising started for '{self.device_name}'")
            
            # Run main loop in background
            import threading
            loop_thread = threading.Thread(target=self.mainloop.run, daemon=True)
            loop_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start BLE advertiser: {e}")
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
    
    def _register_advertisement(self):
        """Register BLE advertisement"""
        try:
            # Create advertisement object path
            ad_path = "/org/bluez/mia/obd_advertisement"
            
            # Advertisement properties
            ad_properties = {
                "Type": "peripheral",
                "ServiceUUIDs": dbus.Array([OBD_SERVICE_UUID], signature='s'),
                "LocalName": self.device_name,
                "IncludeTxPower": dbus.Boolean(True)
            }
            
            # Register advertisement
            self.advertising_manager.RegisterAdvertisement(
                ad_path,
                ad_properties
            )
            
            logger.info("BLE advertisement registered")
            
        except Exception as e:
            logger.error(f"Error registering advertisement: {e}")
            logger.exception(e)
    
    def _start_legacy_advertising(self) -> bool:
        """Start advertising using legacy hciconfig method"""
        try:
            import subprocess
            
            # Set device name
            subprocess.run(
                ["hciconfig", "hci0", "name", self.device_name],
                check=True,
                capture_output=True
            )
            
            # Make discoverable
            subprocess.run(
                ["hciconfig", "hci0", "piscan"],
                check=True,
                capture_output=True
            )
            
            # Set class (OBD-II adapter)
            subprocess.run(
                ["hciconfig", "hci0", "class", "0x002540"],
                check=True,
                capture_output=True
            )
            
            logger.info(f"Legacy BLE advertising started for '{self.device_name}'")
            self.running = True
            return True
            
        except Exception as e:
            logger.error(f"Error starting legacy advertising: {e}")
            return False
    
    def stop(self):
        """Stop BLE advertising"""
        self.running = False
        
        if self.mainloop:
            self.mainloop.quit()
        
        if self.advertising_manager:
            try:
                self.advertising_manager.UnregisterAdvertisement("/org/bluez/mia/obd_advertisement")
            except Exception as e:
                logger.warning(f"Error unregistering advertisement: {e}")
        
        logger.info("BLE advertising stopped")


def main():
    """Main entry point"""
    advertiser = BLEAdvertiser()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        advertiser.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if advertiser.start():
            logger.info("BLE advertiser running. Press Ctrl+C to stop.")
            # Keep running
            while advertiser.running:
                time.sleep(1)
        else:
            logger.error("Failed to start BLE advertiser")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception(e)
        sys.exit(1)
    finally:
        advertiser.stop()


if __name__ == "__main__":
    main()
