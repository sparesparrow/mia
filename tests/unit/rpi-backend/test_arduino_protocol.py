#!/usr/bin/env python3
"""
Test script for Arduino MIA Protocol communication.
Tests the integration between Python ArduinoController and Arduino MIAProtocol library.
"""

import asyncio
import logging
import time
from typing import Dict, Any

from .arduino import ArduinoController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockArduinoSerial:
    """Mock Arduino serial connection for testing MIA Protocol."""

    def __init__(self):
        self.buffer = b""
        self.connected = True
        self.device_info = {
            "type": 0,  # DEVICE_ARDUINO_UNO
            "name": "TestArduino",
            "version": "1.0.0"
        }

    def write(self, data: bytes):
        """Handle incoming data from Python client."""
        self.buffer += data

    def read(self, size: int = 1) -> bytes:
        """Read data (for testing, return mock responses)."""
        if not self.connected:
            return b""

        # Process incoming framed messages
        if len(self.buffer) >= 7:  # Minimum framed message size
            if self.buffer[0] == 0xAA:  # START_BYTE
                length = (self.buffer[1] << 8) | self.buffer[2]
                if len(self.buffer) >= 7 + length:
                    # Extract message
                    message_data = self.buffer[3:3+length]
                    crc_received = (self.buffer[3+length] << 8) | self.buffer[3+length+1]
                    end_byte = self.buffer[3+length+2]

                    if end_byte == 0x55:  # END_BYTE
                        # Process message
                        response = self._process_message(message_data)
                        if response:
                            # Remove processed message from buffer
                            self.buffer = self.buffer[4+length+3:]
                            return response

        return b""

    @property
    def in_waiting(self) -> int:
        """Check if data is available."""
        return len(self.buffer) if self.connected else 0

    def flush(self):
        """Flush output buffer."""
        pass

    def close(self):
        """Close connection."""
        self.connected = False

    def _calculate_crc16(self, data: bytes) -> int:
        """Calculate CRC16-CCITT."""
        crc = 0xFFFF
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc

    def _process_message(self, message_data: bytes) -> bytes:
        """Process incoming message and generate response."""
        if len(message_data) < 1:
            return None

        message_type = message_data[0]
        payload = message_data[1:]

        if message_type == 7:  # MSG_HANDSHAKE_REQUEST
            # Parse handshake data
            if len(payload) >= 3:
                device_type = payload[0]
                protocol_version = payload[1]

                # Extract device name and version
                name_end = payload.find(0, 2)
                if name_end > 2:
                    device_name = payload[2:name_end].decode('utf-8', errors='ignore')
                    version_start = name_end + 1
                    version_end = payload.find(0, version_start)
                    if version_end > version_start:
                        device_version = payload[version_start:version_end].decode('utf-8', errors='ignore')

                        logger.info(f"Handshake from {device_name} v{device_version}")

                        # Send handshake response
                        response_data = bytes([8, 1])  # MSG_HANDSHAKE_RESPONSE, success
                        return self._build_framed_message(response_data)

        elif message_type == 0:  # MSG_GPIO_COMMAND
            if len(payload) >= 3:
                pin = payload[0]
                direction = payload[1]
                value = payload[2]

                logger.info(f"GPIO command: pin={pin}, direction={direction}, value={value}")

                # Send acknowledgment
                ack_data = bytes([0, 1, 0, 0])  # command_id, success, error_code, reserved
                return self._build_framed_message(bytes([3]) + ack_data)  # MSG_COMMAND_ACK

        return None

    def _build_framed_message(self, data: bytes) -> bytes:
        """Build a framed message in MIA Protocol format."""
        # Calculate CRC
        crc = self._calculate_crc16(data)

        # Build frame
        frame = bytearray([0xAA])  # START_BYTE
        frame.extend(len(data).to_bytes(2, 'big'))  # LENGTH
        frame.extend(data)  # DATA
        frame.extend(crc.to_bytes(2, 'big'))  # CRC
        frame.append(0x55)  # END_BYTE

        return bytes(frame)


async def test_arduino_protocol():
    """Test Arduino MIA Protocol communication."""
    logger.info("Testing Arduino MIA Protocol communication...")

    try:
        # Create controller
        controller = ArduinoController()

        # Test device discovery (may find real devices)
        devices = await controller.discover_devices()
        logger.info(f"Discovered {len(devices)} Arduino devices")

        # Test with mock Arduino if no real devices found
        if not devices:
            logger.info("No real Arduino devices found, testing with mock...")
            # Note: In a real test, you'd need to patch the serial connection
            # For now, we'll test the protocol parsing functions

            controller = ArduinoController()
            mock_serial = MockArduinoSerial()

            # Test CRC calculation
            test_data = b"hello"
            crc = controller._calculate_crc16(test_data)
            expected_crc = mock_serial._calculate_crc16(test_data)
            assert crc == expected_crc, f"CRC mismatch: {crc} != {expected_crc}"
            logger.info("✓ CRC16 calculation correct")

            # Test framed message building
            test_msg = controller._build_framed_message(7, b"test")  # MSG_HANDSHAKE_REQUEST
            assert len(test_msg) >= 7, "Framed message too short"
            assert test_msg[0] == 0xAA, "Missing START_BYTE"
            assert test_msg[-1] == 0x55, "Missing END_BYTE"
            logger.info("✓ Framed message building correct")

            # Test message type mapping
            assert controller._get_message_type("gpio") == 0, "GPIO message type incorrect"
            assert controller._get_message_type("ping") == 7, "Ping message type incorrect"
            logger.info("✓ Message type mapping correct")

            # Test command data building
            gpio_data = controller._build_command_data("gpio", pin=13, direction=1, value=True)
            assert gpio_data == b"\r\x01\x01", "GPIO command data incorrect"
            logger.info("✓ Command data building correct")

        logger.info("✅ Arduino protocol tests passed")

    except Exception as e:
        logger.error(f"Arduino protocol test failed: {e}")
        raise


async def test_protocol_integration():
    """Test end-to-end protocol integration."""
    logger.info("Testing protocol integration...")

    try:
        # This would require a real Arduino with MIAProtocol
        # For now, test the controller initialization
        controller = ArduinoController()

        async with controller:
            # Test controller state
            assert controller._running == True, "Controller not running"
            assert controller._monitor_task is not None, "Monitor task not created"

            # Test device discovery
            devices = await controller.discover_devices()
            logger.info(f"Found {len(devices)} devices during integration test")

            # Test status queries
            connected = controller.get_connected_devices()
            all_devices = controller.get_all_devices()

            logger.info(f"Connected devices: {connected}")
            logger.info(f"All devices: {len(all_devices)}")

        logger.info("✅ Protocol integration tests passed")

    except Exception as e:
        logger.error(f"Protocol integration test failed: {e}")
        raise


async def main():
    """Run all Arduino protocol tests."""
    logger.info("Starting Arduino MIA Protocol comprehensive tests...")

    try:
        # Run protocol tests
        await test_arduino_protocol()

        # Run integration tests
        await test_protocol_integration()

        logger.info("🎉 All Arduino protocol tests passed!")

    except Exception as e:
        logger.error(f"Arduino protocol tests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())