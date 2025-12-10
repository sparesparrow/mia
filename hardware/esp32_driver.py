"""
ESP32 Driver for MIA Hardware Abstraction

This driver provides communication with ESP32 devices over WiFi or serial.
It handles TCP socket communication, device discovery, and protocol management.

Features:
- WiFi network discovery and connection
- TCP socket communication with ESP32 bridge
- Device management and health monitoring
- GPIO and sensor data abstraction
- Automatic reconnection and error recovery
"""

import socket
import threading
import time
import json
from typing import Optional, Dict, List, Callable, Any, Tuple
import logging
import ipaddress

logger = logging.getLogger(__name__)

class ESP32MessageType:
    """Message types for ESP32 communication"""
    REGISTER = 'R'
    DATA = 'D'
    HEARTBEAT = 'H'
    PING = 'P'
    PONG = 'O'
    ACK = 'A'
    LIST = 'L'
    WELCOME = 'W'

class ESP32Driver:
    """
    Driver for communicating with ESP32 WiFi bridge devices

    Handles TCP socket communication, device discovery, and message routing.
    Provides high-level interface for device management and data exchange.
    """

    def __init__(self, host: Optional[str] = None, port: int = 8888,
                 auto_discover: bool = True):
        self.host = host
        self.port = port
        self.auto_discover = auto_discover
        self.socket: Optional[socket.socket] = None
        self.connected = False

        # Threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Device management
        self.device_id: Optional[int] = None
        self.device_name = "PythonClient"
        self.connected_devices: Dict[int, Dict] = {}

        # Message handling
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.pending_responses: Dict[str, Dict] = {}

        # Network discovery
        self.discovered_bridges: List[Tuple[str, int]] = []

    def connect(self) -> bool:
        """Connect to ESP32 WiFi bridge"""
        try:
            if self.auto_discover and not self.host:
                self.host, self.port = self._discover_bridge()
                if not self.host:
                    logger.error("No ESP32 bridge found")
                    return False

            logger.info(f"Connecting to ESP32 bridge at {self.host}:{self.port}")

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))

            self.connected = True
            self._running = True
            self._thread = threading.Thread(target=self._message_loop, daemon=True)
            self._thread.start()

            # Register with bridge
            if self._register_device():
                logger.info(f"Connected to ESP32 bridge, device ID: {self.device_id}")
                return True
            else:
                logger.error("Device registration failed")
                self.disconnect()
                return False

        except socket.error as e:
            logger.error(f"Socket connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from ESP32 bridge"""
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        if self.socket:
            try:
                self.socket.close()
            except socket.error:
                pass

        self.connected = False
        self.socket = None
        self.device_id = None
        logger.info("Disconnected from ESP32 bridge")

    def _discover_bridge(self) -> Tuple[Optional[str], Optional[int]]:
        """Discover ESP32 bridge on network"""
        # Try common IP ranges and ports
        common_ports = [8888, 8080, 80]
        discovered = []

        # Try mDNS discovery (if available)
        try:
            import zeroconf
            zc = zeroconf.Zeroconf()
            service_info = zc.get_service_info("_mia-bridge._tcp.local.", "mia-bridge._tcp.local.")
            if service_info:
                ip = socket.inet_ntoa(service_info.addresses[0])
                port = service_info.port
                logger.info(f"Found ESP32 bridge via mDNS: {ip}:{port}")
                zc.close()
                return ip, port
            zc.close()
        except ImportError:
            logger.debug("zeroconf not available, skipping mDNS discovery")
        except Exception as e:
            logger.debug(f"mDNS discovery failed: {e}")

        # Fallback: try common IP addresses
        common_ips = [
            "192.168.1.100", "192.168.1.101", "192.168.1.200",  # Common ESP32 IPs
            "192.168.4.1",  # ESP32 AP default IP
            "10.0.0.100", "10.0.0.101"  # Other common ranges
        ]

        for ip in common_ips:
            for port in common_ports:
                try:
                    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_socket.settimeout(1.0)
                    result = test_socket.connect_ex((ip, port))
                    test_socket.close()

                    if result == 0:
                        logger.info(f"Found ESP32 bridge at {ip}:{port}")
                        discovered.append((ip, port))

                except socket.error:
                    pass

        if discovered:
            return discovered[0]  # Return first found

        logger.warning("No ESP32 bridge discovered")
        return None, None

    def _register_device(self) -> bool:
        """Register this device with the bridge"""
        name_bytes = self.device_name.encode('utf-8')
        message = bytearray([len(name_bytes)])  # Name length
        message.extend(name_bytes)  # Name data

        response = self._send_message_sync(ESP32MessageType.REGISTER, message, timeout=3.0)

        if response and response.get("type") == ESP32MessageType.ACK:
            data = response.get("data", [])
            if len(data) >= 1:
                self.device_id = data[0]
                return True

        return False

    def _send_message_sync(self, msg_type: str, data: bytes,
                          timeout: float = 2.0) -> Optional[Dict]:
        """Send message and wait for response synchronously"""
        # Create unique request ID
        request_id = f"{msg_type}_{int(time.time()*1000)}"

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

    def _send_message(self, msg_type: str, data: bytes, request_id: Optional[str] = None):
        """Send message to ESP32 bridge"""
        if not self.socket or not self.connected:
            return

        try:
            # Simple protocol: [type][length][data]
            message = bytearray()
            message.append(ord(msg_type))
            message.append(len(data))
            message.extend(data)

            with self._lock:
                self.socket.sendall(message)

        except socket.error as e:
            logger.error(f"Socket send error: {e}")
            self.connected = False

    def _message_loop(self):
        """Background message processing loop"""
        while self._running and self.socket and self.connected:
            try:
                # Check for incoming data
                ready = select.select([self.socket], [], [], 0.1)
                if ready[0]:
                    self._process_incoming_message()

            except socket.error as e:
                logger.error(f"Socket error in message loop: {e}")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")

    def _process_incoming_message(self):
        """Process incoming message from ESP32 bridge"""
        try:
            # Read message header (type + length)
            header = self.socket.recv(2)
            if len(header) != 2:
                return

            msg_type = chr(header[0])
            data_length = header[1]

            # Read message data
            data = b""
            if data_length > 0:
                data = self.socket.recv(data_length)
                if len(data) != data_length:
                    return

            message = {
                "type": msg_type,
                "data": data,
                "timestamp": time.time()
            }

            self._handle_message(message)

        except socket.error as e:
            logger.error(f"Socket receive error: {e}")
            self.connected = False

    def _handle_message(self, message: Dict):
        """Handle incoming message"""
        msg_type = message["type"]
        data = message["data"]

        # Handle specific message types
        if msg_type == ESP32MessageType.WELCOME:
            logger.info("Received welcome message from bridge")

        elif msg_type == ESP32MessageType.ACK:
            # Check if this is a response to a pending request
            if len(data) >= 1:
                # This would need more sophisticated request ID tracking
                pass

        elif msg_type == ESP32MessageType.DATA:
            # Forward data message to handlers
            self._call_handlers(msg_type, message)

        elif msg_type == ESP32MessageType.PONG:
            # Handle ping response
            logger.debug("Received pong from bridge")

        elif msg_type == ESP32MessageType.LIST:
            # Parse device list
            self._parse_device_list(data)

        else:
            logger.debug(f"Received unknown message type: {msg_type}")

        # Call registered handlers
        self._call_handlers(msg_type, message)

    def _call_handlers(self, msg_type: str, message: Dict):
        """Call registered message handlers"""
        if msg_type in self.message_handlers:
            for handler in self.message_handlers[msg_type]:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")

    def _parse_device_list(self, data: bytes):
        """Parse device list message"""
        if len(data) < 1:
            return

        device_count = data[0]
        offset = 1

        self.connected_devices.clear()

        for i in range(device_count):
            if offset + 2 >= len(data):
                break

            device_id = data[offset]
            name_length = data[offset + 1]
            offset += 2

            if offset + name_length > len(data):
                break

            name = data[offset:offset + name_length].decode('utf-8', errors='ignore')
            offset += name_length

            self.connected_devices[device_id] = {
                "name": name,
                "last_seen": time.time()
            }

        logger.info(f"Updated device list: {len(self.connected_devices)} devices")

    # Public API methods

    def send_data_to_device(self, target_device_id: int, data: bytes) -> bool:
        """Send data to specific device through bridge"""
        if not self.device_id:
            return False

        # Format: [target_id][data]
        message_data = bytearray([target_device_id])
        message_data.extend(data)

        self._send_message(ESP32MessageType.DATA, message_data)
        return True

    def broadcast_data(self, data: bytes) -> bool:
        """Broadcast data to all connected devices"""
        return self.send_data_to_device(255, data)  # 255 = broadcast

    def ping_bridge(self) -> bool:
        """Ping the bridge to check connectivity"""
        response = self._send_message_sync(ESP32MessageType.PING, b"", timeout=2.0)
        return response is not None

    def get_device_list(self) -> Dict[int, Dict]:
        """Get list of connected devices"""
        self._send_message(ESP32MessageType.LIST, b"")
        time.sleep(0.5)  # Give time for response
        return self.connected_devices.copy()

    def add_message_handler(self, msg_type: str, handler: Callable):
        """Add message handler callback"""
        if msg_type not in self.message_handlers:
            self.message_handlers[msg_type] = []
        self.message_handlers[msg_type].append(handler)

    def is_connected(self) -> bool:
        """Check if connected to ESP32 bridge"""
        return self.connected and self.socket is not None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

# Import select for cross-platform compatibility
try:
    import select
except ImportError:
    # Windows fallback
    import socket as select_socket
    select = None