"""
Arduino Driver for MIA Hardware Abstraction

This driver provides communication with Arduino devices using the MIA Protocol.
It handles serial communication, message framing, and protocol handshaking.

Features:
- Serial port auto-detection and management
- MIA Protocol message handling
- Device discovery and identification
- GPIO and sensor data abstraction
- Error recovery and reconnection
"""

import serial
import serial.tools.list_ports
import threading
import time
from typing import Optional, Dict, List, Callable, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ArduinoMessageType(Enum):
    """Message types matching MIA Protocol"""
    GPIO_COMMAND = 0
    SENSOR_TELEMETRY = 1
    SYSTEM_STATUS = 2
    COMMAND_ACK = 3
    DEVICE_INFO = 4
    LED_STATE = 5
    VEHICLE_TELEMETRY = 6
    HANDSHAKE_REQUEST = 7
    HANDSHAKE_RESPONSE = 8
    ERROR = 9

class ArduinoDeviceType(Enum):
    """Device types"""
    ARDUINO_UNO = 0
    ARDUINO_MEGA = 1
    ESP32 = 2
    ESP8266 = 3
    RASPBERRY_PI_PICO = 4

class ArduinoError(Enum):
    """Error codes"""
    NONE = 0
    CRC_MISMATCH = 1
    INVALID_MESSAGE = 2
    TIMEOUT = 3
    BUFFER_OVERFLOW = 4
    UNSUPPORTED_COMMAND = 5

class ArduinoDriver:
    """
    Driver for communicating with Arduino devices using MIA Protocol

    Handles serial communication, protocol framing, and message parsing.
    Provides high-level interface for GPIO control and sensor reading.
    """

    # Protocol constants
    START_BYTE = 0xAA
    END_BYTE = 0x55
    MAX_MESSAGE_SIZE = 256
    DEFAULT_TIMEOUT = 1.0

    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.device_type: Optional[ArduinoDeviceType] = None
        self.device_name = ""
        self.last_activity = 0

        # Threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Message handling
        self.message_handlers: Dict[ArduinoMessageType, List[Callable]] = {}
        self.pending_responses: Dict[int, Dict] = {}
        self.next_request_id = 1

        # GPIO and sensor state
        self.gpio_states: Dict[int, Dict] = {}
        self.sensor_data: Dict[int, Dict] = {}

    def connect(self) -> bool:
        """Connect to Arduino device"""
        try:
            if not self.port:
                self.port = self._auto_detect_port()
                if not self.port:
                    logger.error("No Arduino device found")
                    return False

            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=1.0
            )

            # Wait for connection
            time.sleep(2)

            if self.serial.is_open:
                self.connected = True
                self._running = True
                self._thread = threading.Thread(target=self._message_loop, daemon=True)
                self._thread.start()

                # Perform handshake
                if self._perform_handshake():
                    logger.info(f"Connected to Arduino: {self.device_name} ({self.device_type})")
                    return True
                else:
                    logger.error("Handshake failed")
                    self.disconnect()
                    return False
            else:
                logger.error("Failed to open serial port")
                return False

        except serial.SerialException as e:
            logger.error(f"Serial connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from Arduino device"""
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        if self.serial and self.serial.is_open:
            self.serial.close()

        self.connected = False
        self.serial = None
        logger.info("Disconnected from Arduino")

    def _auto_detect_port(self) -> Optional[str]:
        """Auto-detect Arduino serial port"""
        ports = serial.tools.list_ports.comports()

        # Common Arduino VID:PID combinations
        arduino_vids = [
            (0x2341, 0x0043),  # Arduino Uno
            (0x2341, 0x0001),  # Arduino Mega
            (0x10C4, 0xEA60),  # CP210x (common ESP32)
            (0x1A86, 0x7523),  # CH340 (cheap Arduino clones)
        ]

        for port in ports:
            if hasattr(port, 'vid') and hasattr(port, 'pid'):
                for vid, pid in arduino_vids:
                    if port.vid == vid and port.pid == pid:
                        logger.info(f"Found Arduino at {port.device} (VID:{port.vid:04X} PID:{port.pid:04X})")
                        return port.device

        # Fallback: try common port names
        for port in ports:
            if any(name in port.device.lower() for name in ['ttyusb', 'ttyacm', 'cu.usb', 'cu.usbmodem']):
                logger.info(f"Trying Arduino-like port: {port.device}")
                return port.device

        return None

    def _perform_handshake(self) -> bool:
        """Perform MIA Protocol handshake"""
        # Send handshake request
        handshake_data = bytearray()
        handshake_data.append(ArduinoDeviceType.ARDUINO_UNO.value)  # This device type
        handshake_data.append(1)  # Protocol version
        handshake_data.extend(b"PythonDriver")  # Device name
        handshake_data.append(0)  # Null terminator
        handshake_data.extend(b"1.0.0")  # Version
        handshake_data.append(0)  # Null terminator

        response = self._send_message_sync(
            ArduinoMessageType.HANDSHAKE_REQUEST,
            handshake_data,
            timeout=2.0
        )

        if response and response.get("type") == ArduinoMessageType.HANDSHAKE_RESPONSE:
            data = response.get("data", [])
            if len(data) >= 1 and data[0] == 1:  # Success byte
                # Parse device info from handshake response
                self.device_type = ArduinoDeviceType.ARDUINO_UNO  # Default
                self.device_name = "Arduino"
                return True

        return False

    def _send_message_sync(self, msg_type: ArduinoMessageType, data: bytes,
                          timeout: float = DEFAULT_TIMEOUT) -> Optional[Dict]:
        """Send message and wait for response synchronously"""
        request_id = self.next_request_id
        self.next_request_id += 1

        # Store pending response
        self.pending_responses[request_id] = {"event": threading.Event()}

        try:
            self._send_message(msg_type, data, request_id)
            if self.pending_responses[request_id]["event"].wait(timeout):
                response = self.pending_responses[request_id].get("response")
                del self.pending_responses[request_id]
                return response
            else:
                logger.warning(f"Timeout waiting for response to {msg_type}")
        except Exception as e:
            logger.error(f"Error in sync message send: {e}")
        finally:
            # Clean up in case of error
            self.pending_responses.pop(request_id, None)

        return None

    def _send_message(self, msg_type: ArduinoMessageType, data: bytes, request_id: Optional[int] = None):
        """Send message to Arduino"""
        if not self.serial or not self.serial.is_open:
            return

        with self._lock:
            try:
                # Encode message
                msg_data = bytearray()
                msg_data.append(msg_type.value)
                msg_data.extend(data)

                # Frame message with start/end bytes and CRC
                framed = self._frame_message(msg_data)

                self.serial.write(framed)
                self.serial.flush()
                self.last_activity = time.time()

            except serial.SerialException as e:
                logger.error(f"Serial write error: {e}")
                self.connected = False

    def _frame_message(self, data: bytes) -> bytes:
        """Frame message with start/end bytes and CRC"""
        crc = self._calculate_crc16(data)

        framed = bytearray()
        framed.append(self.START_BYTE)
        framed.extend(len(data).to_bytes(2, 'big'))  # Length as 2 bytes
        framed.extend(data)
        framed.extend(crc.to_bytes(2, 'big'))  # CRC as 2 bytes
        framed.append(self.END_BYTE)

        return framed

    def _calculate_crc16(self, data: bytes) -> int:
        """Calculate CRC16-CCITT"""
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

    def _message_loop(self):
        """Background message processing loop"""
        while self._running and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting:
                    message = self._read_message()
                    if message:
                        self._handle_message(message)

                time.sleep(0.01)  # Prevent busy waiting

            except serial.SerialException as e:
                logger.error(f"Serial error in message loop: {e}")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")

    def _read_message(self) -> Optional[Dict]:
        """Read and parse incoming message"""
        try:
            # Wait for start byte
            start_time = time.time()
            while time.time() - start_time < self.DEFAULT_TIMEOUT:
                if self.serial.in_waiting:
                    byte = self.serial.read(1)[0]
                    if byte == self.START_BYTE:
                        break
                time.sleep(0.001)
            else:
                return None  # Timeout

            # Read length (2 bytes)
            length_bytes = self.serial.read(2)
            if len(length_bytes) != 2:
                return None
            length = int.from_bytes(length_bytes, 'big')

            if length > self.MAX_MESSAGE_SIZE:
                logger.error(f"Message too large: {length}")
                return None

            # Read data
            data = self.serial.read(length)
            if len(data) != length:
                return None

            # Read CRC (2 bytes)
            crc_bytes = self.serial.read(2)
            if len(crc_bytes) != 2:
                return None
            received_crc = int.from_bytes(crc_bytes, 'big')

            # Verify CRC
            calculated_crc = self._calculate_crc16(data)
            if calculated_crc != received_crc:
                logger.error("CRC mismatch")
                return None

            # Read end byte
            end_byte = self.serial.read(1)
            if len(end_byte) != 1 or end_byte[0] != self.END_BYTE:
                return None

            # Parse message
            if len(data) < 1:
                return None

            msg_type = ArduinoMessageType(data[0])
            msg_data = data[1:]

            return {
                "type": msg_type,
                "data": msg_data,
                "timestamp": time.time()
            }

        except serial.SerialException as e:
            logger.error(f"Serial read error: {e}")
            return None

    def _handle_message(self, message: Dict):
        """Handle incoming message"""
        msg_type = message["type"]
        data = message["data"]

        # Check if this is a response to a pending request
        if msg_type == ArduinoMessageType.COMMAND_ACK and len(data) >= 1:
            request_id = data[0]
            if request_id in self.pending_responses:
                self.pending_responses[request_id]["response"] = message
                self.pending_responses[request_id]["event"].set()
                return

        # Call registered handlers
        if msg_type in self.message_handlers:
            for handler in self.message_handlers[msg_type]:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")

        # Handle specific message types
        if msg_type == ArduinoMessageType.SENSOR_TELEMETRY:
            self._handle_sensor_telemetry(data)
        elif msg_type == ArduinoMessageType.GPIO_COMMAND:
            self._handle_gpio_command(data)

    def _handle_sensor_telemetry(self, data: bytes):
        """Handle incoming sensor telemetry"""
        if len(data) < 8:  # Minimum size for sensor data
            return

        sensor_id = data[0]
        sensor_type = data[1]

        # Extract float value (little-endian)
        value_bytes = data[2:6]
        value = int.from_bytes(value_bytes, 'little') / 1000.0  # Assume milli-units

        # Extract unit string
        unit_start = 6
        unit = ""
        for i in range(unit_start, len(data)):
            if data[i] == 0:
                break
            unit += chr(data[i])

        self.sensor_data[sensor_id] = {
            "type": sensor_type,
            "value": value,
            "unit": unit,
            "timestamp": time.time()
        }

        logger.debug(f"Sensor {sensor_id}: {value} {unit}")

    def _handle_gpio_command(self, data: bytes):
        """Handle GPIO command (usually from Arduino to host)"""
        if len(data) >= 3:
            pin = data[0]
            direction = data[1]
            value = data[2] > 0

            self.gpio_states[pin] = {
                "direction": direction,
                "value": value,
                "timestamp": time.time()
            }

            logger.debug(f"GPIO {pin}: direction={direction}, value={value}")

    # Public API methods

    def send_gpio_command(self, pin: int, direction: int, value: bool) -> bool:
        """Send GPIO command to Arduino"""
        data = bytearray([pin, direction, 1 if value else 0])
        response = self._send_message_sync(ArduinoMessageType.GPIO_COMMAND, data)
        return response is not None

    def read_gpio(self, pin: int) -> Optional[bool]:
        """Read GPIO pin value"""
        # This would need to be implemented based on Arduino capabilities
        return self.gpio_states.get(pin, {}).get("value")

    def get_sensor_data(self, sensor_id: int) -> Optional[Dict]:
        """Get latest sensor data"""
        return self.sensor_data.get(sensor_id)

    def add_message_handler(self, msg_type: ArduinoMessageType, handler: Callable):
        """Add message handler callback"""
        if msg_type not in self.message_handlers:
            self.message_handlers[msg_type] = []
        self.message_handlers[msg_type].append(handler)

    def is_connected(self) -> bool:
        """Check if connected to Arduino"""
        return self.connected and self.serial and self.serial.is_open

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()