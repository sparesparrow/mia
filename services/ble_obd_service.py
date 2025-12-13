#!/usr/bin/env python3
"""
BLE OBD-II Service for Raspberry Pi
Provides Bluetooth LE peripheral that can be discovered by Android app
Implements OBD-II GATT services for automotive diagnostics
"""

import sys
import os
import json
import logging
import asyncio
import time
from typing import Dict, Optional, List
from datetime import datetime

# Try to import BLE libraries
try:
    from bleak import BleakServer, BleakGATTCharacteristic, BleakGATTService
    import bleak
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    logging.warning("Bleak not available. BLE service disabled.")

try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    logging.warning("ZeroMQ not available. Telemetry integration disabled.")

# OBD-II GATT Service UUIDs (custom)
OBD_SERVICE_UUID = "12345678-1234-5678-9012-123456789012"
RPM_CHARACTERISTIC_UUID = "12345678-1234-5678-9012-123456789013"
SPEED_CHARACTERISTIC_UUID = "12345678-1234-5678-9012-123456789014"
COOLANT_CHARACTERISTIC_UUID = "12345678-1234-5678-9012-123456789015"
COMMAND_CHARACTERISTIC_UUID = "12345678-1234-5678-9012-123456789016"
RESPONSE_CHARACTERISTIC_UUID = "12345678-1234-5678-9012-123456789017"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BLEOBDService:
    """
    BLE OBD-II Service that provides automotive diagnostics over Bluetooth LE
    """

    def __init__(self,
                 device_name: str = "MIA OBD-II Adapter",
                 zmq_pub_url: str = "tcp://localhost:5556",
                 zmq_broker_url: str = "tcp://localhost:5555"):
        self.device_name = device_name
        self.zmq_pub_url = zmq_pub_url
        self.zmq_broker_url = zmq_broker_url
        self.running = False

        # OBD-II data state
        self.obd_data = {
            "rpm": 850,
            "speed": 0,
            "coolant_temp": 85,
            "fuel_level": 75,
            "engine_load": 25
        }

        # BLE server and services
        self.server: Optional[BleakServer] = None
        self.obd_service: Optional[BleakGATTService] = None

        # Characteristics
        self.rpm_char: Optional[BleakGATTCharacteristic] = None
        self.speed_char: Optional[BleakGATTCharacteristic] = None
        self.coolant_char: Optional[BleakGATTCharacteristic] = None
        self.command_char: Optional[BleakGATTCharacteristic] = None
        self.response_char: Optional[BleakGATTCharacteristic] = None

        # ZeroMQ
        self.zmq_context: Optional[zmq.Context] = None
        self.zmq_pub_socket: Optional[zmq.Socket] = None
        self.zmq_broker_socket: Optional[zmq.Socket] = None

    async def setup_ble_services(self):
        """Setup BLE GATT services and characteristics"""
        if not BLEAK_AVAILABLE:
            logger.error("Bleak not available. Cannot setup BLE services.")
            return False

        try:
            # Create characteristics
            self.rpm_char = BleakGATTCharacteristic(
                RPM_CHARACTERISTIC_UUID,
                ["read", "notify"],
                "Engine RPM",
                value=self._encode_rpm(self.obd_data["rpm"])
            )

            self.speed_char = BleakGATTCharacteristic(
                SPEED_CHARACTERISTIC_UUID,
                ["read", "notify"],
                "Vehicle Speed",
                value=self._encode_speed(self.obd_data["speed"])
            )

            self.coolant_char = BleakGATTCharacteristic(
                COOLANT_CHARACTERISTIC_UUID,
                ["read", "notify"],
                "Coolant Temperature",
                value=self._encode_temp(self.obd_data["coolant_temp"])
            )

            self.command_char = BleakGATTCharacteristic(
                COMMAND_CHARACTERISTIC_UUID,
                ["write", "write-without-response"],
                "OBD Command",
                value=b""
            )

            self.response_char = BleakGATTCharacteristic(
                RESPONSE_CHARACTERISTIC_UUID,
                ["read", "notify"],
                "OBD Response",
                value=b""
            )

            # Create OBD service
            self.obd_service = BleakGATTService(
                OBD_SERVICE_UUID,
                [self.rpm_char, self.speed_char, self.coolant_char,
                 self.command_char, self.response_char],
                "OBD-II Diagnostics Service"
            )

            logger.info("BLE services setup complete")
            return True

        except Exception as e:
            logger.error(f"Failed to setup BLE services: {e}")
            return False

    def _encode_rpm(self, rpm: int) -> bytes:
        """Encode RPM value as 2 bytes (big endian)"""
        return rpm.to_bytes(2, byteorder='big')

    def _encode_speed(self, speed: int) -> bytes:
        """Encode speed value as 1 byte"""
        return speed.to_bytes(1, byteorder='big')

    def _encode_temp(self, temp: int) -> bytes:
        """Encode temperature value as 1 byte (offset by 40°C)"""
        return (temp + 40).to_bytes(1, byteorder='big')

    def _decode_command(self, command_bytes: bytes) -> str:
        """Decode command bytes to string"""
        return command_bytes.decode('utf-8', errors='ignore').strip()

    async def handle_command_write(self, characteristic: BleakGATTCharacteristic,
                                 value: bytes):
        """Handle OBD command writes"""
        try:
            command = self._decode_command(value)
            logger.info(f"Received OBD command: {command}")

            # Process command and generate response
            response = await self.process_obd_command(command)

            # Update response characteristic
            if self.response_char and self.server:
                await self.server.update_gatt_characteristic(
                    self.response_char, response.encode('utf-8')
                )

            logger.info(f"Sent OBD response: {response}")

        except Exception as e:
            logger.error(f"Error handling command: {e}")

    async def process_obd_command(self, command: str) -> str:
        """Process OBD-II command and return response"""
        cmd = command.upper().strip()

        if cmd == "ATZ":  # Reset
            return "ELM327 v1.5"
        elif cmd == "ATE0":  # Echo off
            return "OK"
        elif cmd == "ATL0":  # Linefeeds off
            return "OK"
        elif cmd == "ATSP0":  # Auto protocol
            return "OK"
        elif cmd == "010C":  # RPM
            rpm = self.obd_data["rpm"]
            return f"41 0C {rpm:04X}"
        elif cmd == "010D":  # Speed
            speed = self.obd_data["speed"]
            return f"41 0D {speed:02X}"
        elif cmd == "0105":  # Coolant temp
            temp = self.obd_data["coolant_temp"]
            return f"41 05 {(temp + 40):02X}"
        elif cmd.startswith("21"):  # Custom PSA commands
            return "21 01 00 00 00 00"  # Placeholder response
        else:
            return "NO DATA"  # Unknown command

    async def update_obd_data(self, data: Dict):
        """Update OBD data from telemetry"""
        updated = False

        if "rpm" in data and data["rpm"] != self.obd_data["rpm"]:
            self.obd_data["rpm"] = data["rpm"]
            if self.rpm_char and self.server:
                await self.server.update_gatt_characteristic(
                    self.rpm_char, self._encode_rpm(data["rpm"])
                )
            updated = True

        if "speed" in data and data["speed"] != self.obd_data["speed"]:
            self.obd_data["speed"] = data["speed"]
            if self.speed_char and self.server:
                await self.server.update_gatt_characteristic(
                    self.speed_char, self._encode_speed(data["speed"])
                )
            updated = True

        if "coolant_temp" in data and data["coolant_temp"] != self.obd_data["coolant_temp"]:
            self.obd_data["coolant_temp"] = data["coolant_temp"]
            if self.coolant_char and self.server:
                await self.server.update_gatt_characteristic(
                    self.coolant_char, self._encode_temp(data["coolant_temp"])
                )
            updated = True

        if updated:
            logger.debug(f"Updated OBD data: {self.obd_data}")

    async def setup_zeromq(self):
        """Setup ZeroMQ for telemetry integration"""
        if not ZMQ_AVAILABLE:
            logger.warning("ZeroMQ not available. Skipping telemetry integration.")
            return

        try:
            self.zmq_context = zmq.Context()

            # Subscribe to telemetry
            self.zmq_pub_socket = self.zmq_context.socket(zmq.SUB)
            self.zmq_pub_socket.connect(self.zmq_pub_url)
            self.zmq_pub_socket.subscribe(b"mcu/telemetry")

            # Register with broker
            self.zmq_broker_socket = self.zmq_context.socket(zmq.REQ)
            self.zmq_broker_socket.connect(self.zmq_broker_url)

            # Register service
            registration = {
                "service": "ble_obd_service",
                "type": "ble_peripheral",
                "capabilities": ["obd_ii", "gatt_server"],
                "status": "starting"
            }

            await asyncio.get_event_loop().run_in_executor(
                None, self.zmq_broker_socket.send_json, registration
            )

            logger.info("ZeroMQ setup complete")

        except Exception as e:
            logger.error(f"ZeroMQ setup failed: {e}")

    async def telemetry_listener(self):
        """Listen for telemetry updates"""
        if not self.zmq_pub_socket:
            return

        while self.running:
            try:
                # Non-blocking receive with timeout
                if await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.zmq_pub_socket.poll(1000) & zmq.POLLIN
                ):
                    topic, message = await asyncio.get_event_loop().run_in_executor(
                        None, self.zmq_pub_socket.recv_multipart
                    )

                    if topic == b"mcu/telemetry":
                        try:
                            data = json.loads(message.decode('utf-8'))
                            await self.update_obd_data(data)
                        except json.JSONDecodeError:
                            pass

            except Exception as e:
                logger.error(f"Telemetry listener error: {e}")
                await asyncio.sleep(1)

    async def simulate_obd_data(self):
        """Simulate changing OBD data for testing"""
        while self.running:
            # Simulate engine RPM changes
            self.obd_data["rpm"] = 800 + (int(time.time() * 50) % 2000)

            # Simulate speed changes (0-120 km/h)
            self.obd_data["speed"] = (int(time.time() * 10) % 120)

            # Simulate temperature changes
            self.obd_data["coolant_temp"] = 80 + (int(time.time() * 2) % 20)

            # Update BLE characteristics
            await self.update_obd_data(self.obd_data)

            await asyncio.sleep(0.1)  # Update 10 times per second

    async def start(self):
        """Start the BLE OBD service"""
        logger.info(f"Starting BLE OBD Service: {self.device_name}")

        self.running = True

        # Setup ZeroMQ
        await self.setup_zeromq()

        # Setup BLE services
        if not await self.setup_ble_services():
            logger.error("Failed to setup BLE services")
            return

        # Create BLE server
        if BLEAK_AVAILABLE:
            try:
                self.server = BleakServer(self.device_name)
                await self.server.add_gatt_service(self.obd_service)

                # Setup command handler
                if self.command_char:
                    await self.server.add_gatt_characteristic_handler(
                        self.command_char, self.handle_command_write
                    )

                logger.info(f"BLE server starting with device name: {self.device_name}")
                logger.info("OBD-II GATT Service UUID: " + OBD_SERVICE_UUID)

                # Start background tasks
                telemetry_task = asyncio.create_task(self.telemetry_listener())
                simulation_task = asyncio.create_task(self.simulate_obd_data())

                # Start BLE server
                await self.server.start()

                logger.info("BLE OBD service started successfully")
                logger.info("Android apps can now discover this device for OBD-II diagnostics")

                # Keep running until stopped
                while self.running:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Failed to start BLE server: {e}")
        else:
            logger.error("BLE libraries not available")

    async def stop(self):
        """Stop the BLE OBD service"""
        logger.info("Stopping BLE OBD service")
        self.running = False

        if self.server:
            await self.server.stop()

        if self.zmq_context:
            self.zmq_context.term()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="BLE OBD-II Service for Raspberry Pi")
    parser.add_argument("--name", default="MIA OBD-II Adapter",
                       help="BLE device name")
    parser.add_argument("--zmq-pub", default="tcp://localhost:5556",
                       help="ZeroMQ PUB socket URL")
    parser.add_argument("--zmq-broker", default="tcp://localhost:5555",
                       help="ZeroMQ broker URL")
    parser.add_argument("--simulate", action="store_true",
                       help="Enable OBD data simulation")

    args = parser.parse_args()

    service = BLEOBDService(
        device_name=args.name,
        zmq_pub_url=args.zmq_pub,
        zmq_broker_url=args.zmq_broker
    )

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await service.stop()


if __name__ == "__main__":
    # Check if running on Raspberry Pi
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip()
            if 'Raspberry Pi' not in model:
                logger.warning("This service is designed for Raspberry Pi")
    except FileNotFoundError:
        logger.warning("Cannot verify Raspberry Pi hardware")

    asyncio.run(main())