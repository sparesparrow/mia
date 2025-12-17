"""
Arduino Controller
Serial communication with Arduino devices.

This module provides serial communication capabilities for Arduino devices,
supporting the FlatBuffers-based message protocol defined in the Arduino sketches.
"""

import asyncio
import logging
import serial
import serial.tools.list_ports
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ArduinoStatus(Enum):
    """Arduino device status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ArduinoInfo:
    """Information about an Arduino device."""
    port: str
    board_type: str
    firmware_version: Optional[str] = None
    capabilities: List[str] = None
    last_seen: float = 0.0

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        self.last_seen = time.time()


class ArduinoController:
    """
    Arduino Controller for serial communication.

    Features:
    - Automatic Arduino detection and enumeration
    - Serial communication with FlatBuffers messages
    - Device health monitoring
    - Async operation support
    - Error handling and reconnection

    Usage:
        controller = ArduinoController()
        devices = await controller.discover_devices()
        arduino = devices[0]

        async with ArduinoController() as ctrl:
            await ctrl.connect_device(arduino.port)
            # Send commands, receive data
    """

    def __init__(self, baudrate: int = 115200, timeout: float = 1.0):
        """
        Initialize Arduino controller.

        Args:
            baudrate: Serial communication baud rate
            timeout: Serial read timeout in seconds
        """
        self.baudrate = baudrate
        self.timeout = timeout

        self.devices: Dict[str, ArduinoInfo] = {}
        self.connections: Dict[str, serial.Serial] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self):
        """Start the Arduino controller."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_devices())
        logger.info("Arduino controller started")

    async def stop(self):
        """Stop the Arduino controller."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for port, conn in self.connections.items():
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing Arduino connection on {port}: {e}")

        self.connections.clear()
        logger.info("Arduino controller stopped")

    async def discover_devices(self) -> List[ArduinoInfo]:
        """
        Discover available Arduino devices.

        Returns:
            List of discovered Arduino devices
        """
        devices = []

        try:
            # Get all serial ports
            ports = serial.tools.list_ports.comports()

            for port in ports:
                # Check if it's an Arduino (basic heuristics)
                if self._is_arduino_port(port):
                    arduino_info = ArduinoInfo(
                        port=port.device,
                        board_type=port.description or "Unknown Arduino",
                        capabilities=["gpio", "analog"]  # Basic capabilities
                    )
                    devices.append(arduino_info)
                    self.devices[port.device] = arduino_info

        except Exception as e:
            logger.error(f"Error discovering Arduino devices: {e}")

        logger.info(f"Discovered {len(devices)} Arduino devices")
        return devices

    def _is_arduino_port(self, port) -> bool:
        """
        Check if a serial port is likely an Arduino.

        Args:
            port: Serial port info from pyserial

        Returns:
            True if port appears to be an Arduino
        """
        # Basic heuristics for Arduino detection
        description = (port.description or "").lower()
        manufacturer = (port.manufacturer or "").lower()

        arduino_keywords = ["arduino", "uno", "mega", "nano", "leonardo", "micro"]
        return any(keyword in description or keyword in manufacturer for keyword in arduino_keywords)

    async def connect_device(self, port: str) -> bool:
        """
        Connect to an Arduino device.

        Args:
            port: Serial port path (e.g., "/dev/ttyACM0")

        Returns:
            True if connection successful
        """
        try:
            # Close existing connection if any
            if port in self.connections:
                self.connections[port].close()
                del self.connections[port]

            # Open new connection
            ser = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=1.0
            )

            # Test connection with a simple handshake
            success = await self._handshake_device(ser)
            if success:
                self.connections[port] = ser

                # Update device info
                if port in self.devices:
                    self.devices[port].last_seen = time.time()

                logger.info(f"Connected to Arduino on {port}")
                return True
            else:
                ser.close()
                logger.warning(f"Handshake failed for Arduino on {port}")
                return False

        except Exception as e:
            logger.error(f"Error connecting to Arduino on {port}: {e}")
            return False

    async def disconnect_device(self, port: str) -> bool:
        """
        Disconnect from an Arduino device.

        Args:
            port: Serial port path

        Returns:
            True if disconnection successful
        """
        if port in self.connections:
            try:
                self.connections[port].close()
                del self.connections[port]
                logger.info(f"Disconnected from Arduino on {port}")
                return True
            except Exception as e:
                logger.error(f"Error disconnecting Arduino on {port}: {e}")
                return False

        return False

    async def _handshake_device(self, ser: serial.Serial) -> bool:
        """
        Perform handshake with Arduino device.

        Args:
            ser: Serial connection

        Returns:
            True if handshake successful
        """
        try:
            # Send handshake command
            handshake_cmd = b"MIA_HANDSHAKE\n"
            ser.write(handshake_cmd)
            ser.flush()

            # Wait for response with timeout
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._readline_with_timeout, ser, 2.0
            )

            if response and b"MIA_READY" in response:
                return True

        except Exception as e:
            logger.debug(f"Handshake failed: {e}")

        return False

    def _readline_with_timeout(self, ser: serial.Serial, timeout: float) -> Optional[bytes]:
        """
        Read a line from serial with timeout.

        Args:
            ser: Serial connection
            timeout: Timeout in seconds

        Returns:
            Line data or None if timeout
        """
        start_time = time.time()
        buffer = b""

        while time.time() - start_time < timeout:
            if ser.in_waiting > 0:
                char = ser.read(1)
                if char == b"\n":
                    return buffer
                buffer += char
            else:
                time.sleep(0.01)  # Small delay to avoid busy waiting

        return None

    async def send_command(self, port: str, command: str, **kwargs) -> Optional[str]:
        """
        Send a command to an Arduino device.

        Args:
            port: Serial port path
            command: Command to send
            **kwargs: Additional command parameters

        Returns:
            Response string or None if failed
        """
        if port not in self.connections:
            logger.error(f"No connection to Arduino on {port}")
            return None

        try:
            ser = self.connections[port]

            # Format command
            cmd_str = f"{command}"
            if kwargs:
                params = ",".join(f"{k}:{v}" for k, v in kwargs.items())
                cmd_str += f" {params}"
            cmd_str += "\n"

            # Send command
            ser.write(cmd_str.encode())
            ser.flush()

            # Read response
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._readline_with_timeout, ser, 1.0
            )

            if response:
                return response.decode().strip()

        except Exception as e:
            logger.error(f"Error sending command to Arduino on {port}: {e}")

        return None

    async def get_device_info(self, port: str) -> Optional[ArduinoInfo]:
        """
        Get information about a connected Arduino device.

        Args:
            port: Serial port path

        Returns:
            Arduino info or None if not found
        """
        return self.devices.get(port)

    def get_connected_devices(self) -> List[str]:
        """Get list of connected device ports."""
        return list(self.connections.keys())

    def get_all_devices(self) -> List[ArduinoInfo]:
        """Get list of all discovered devices."""
        return list(self.devices.values())

    async def _monitor_devices(self):
        """Background task to monitor device connections."""
        while self._running:
            try:
                # Check connection health
                for port, ser in list(self.connections.items()):
                    try:
                        # Simple ping command
                        if ser.is_open:
                            ser.write(b"MIA_PING\n")
                            ser.flush()
                        else:
                            # Connection lost
                            logger.warning(f"Arduino connection lost on {port}")
                            del self.connections[port]

                    except Exception as e:
                        logger.warning(f"Arduino health check failed on {port}: {e}")
                        try:
                            ser.close()
                        except:
                            pass
                        del self.connections[port]

                # Update last seen times
                current_time = time.time()
                for device in self.devices.values():
                    if device.port in self.connections:
                        device.last_seen = current_time

            except Exception as e:
                logger.error(f"Error in device monitoring: {e}")

            await asyncio.sleep(10.0)  # Check every 10 seconds

    def get_device_status(self, port: str) -> ArduinoStatus:
        """
        Get the status of an Arduino device.

        Args:
            port: Serial port path

        Returns:
            Device status
        """
        if port in self.connections:
            return ArduinoStatus.CONNECTED
        elif port in self.devices:
            return ArduinoStatus.DISCONNECTED
        else:
            return ArduinoStatus.ERROR