#!/usr/bin/env python3
"""
Simple BLE Advertiser for Raspberry Pi
Advertises the Raspberry Pi as a BLE device that can be discovered by Android apps
"""

import subprocess
import time
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleBLEAdvertiser:
    """Simple BLE advertiser using bluetoothctl"""

    def __init__(self, device_name: str = "MIA OBD-II Adapter"):
        self.device_name = device_name
        self.running = False

    def run_bluetoothctl_command(self, command: str) -> bool:
        """Run a single bluetoothctl command"""
        try:
            # Run bluetoothctl with the command
            process = subprocess.Popen(
                ['bluetoothctl'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Send the command
            stdout, stderr = process.communicate(input=command + '\n', timeout=10)

            logger.debug(f"bluetoothctl command '{command}' result: {process.returncode}")
            if stdout:
                logger.debug(f"stdout: {stdout.strip()}")
            if stderr:
                logger.debug(f"stderr: {stderr.strip()}")

            return process.returncode == 0

        except Exception as e:
            logger.error(f"Failed to run bluetoothctl command '{command}': {e}")
            return False

    def start_advertising(self):
        """Start BLE advertising"""
        logger.info(f"Starting BLE advertising as '{self.device_name}'")

        # Commands to set up BLE advertising
        commands = [
            "power on",
            "discoverable on",
            "pairable on",
            f"name {self.device_name}",
            "advertise on"
        ]

        success = True
        for cmd in commands:
            if not self.run_bluetoothctl_command(cmd):
                logger.warning(f"Command '{cmd}' failed")
                success = False
            else:
                logger.debug(f"Command '{cmd}' succeeded")
                time.sleep(1)  # Small delay between commands

        if success:
            logger.info("BLE advertising started successfully")
            return True
        else:
            logger.error("Failed to start BLE advertising")
            return False

    def check_advertising_status(self):
        """Check if advertising is active"""
        try:
            result = subprocess.run(
                ["bluetoothctl", "show"],
                capture_output=True, text=True, timeout=10
            )

            advertising_active = "Discoverable: yes" in result.stdout
            powered_on = "Powered: yes" in result.stdout

            logger.info(f"Bluetooth powered: {powered_on}, discoverable: {advertising_active}")
            return powered_on and advertising_active

        except Exception as e:
            logger.error(f"Failed to check advertising status: {e}")
            return False

    def stop_advertising(self):
        """Stop BLE advertising"""
        logger.info("Stopping BLE advertising")

        commands = [
            "advertise off",
            "discoverable off",
            "pairable off"
        ]

        self.run_bluetoothctl_command(commands)
        logger.info("BLE advertising stopped")

    def run(self):
        """Main run loop"""
        self.running = True
        logger.info("Simple BLE Advertiser starting...")

        try:
            # Start advertising
            if not self.start_advertising():
                logger.error("Failed to start advertising")
                return

            # Keep advertising active
            while self.running:
                time.sleep(10)  # Check every 10 seconds

                if not self.check_advertising_status():
                    logger.warning("Advertising status check failed, restarting...")
                    self.start_advertising()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop_advertising()

def main():
    """Main entry point"""
    advertiser = SimpleBLEAdvertiser()
    advertiser.run()

if __name__ == "__main__":
    main()