"""
Hardware Client for communicating with C++ Hardware Control Server

Provides TCP-based communication with the hardware-server executable
for GPIO control and hardware monitoring.
"""

import socket
import json
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GPIOConfig:
    """GPIO pin configuration"""
    pin: int
    direction: str  # "input" or "output"
    value: Optional[int] = None


@dataclass
class GPIOStatus:
    """GPIO pin status"""
    pin: int
    direction: str
    value: Optional[int] = None


class HardwareClient:
    """Client for communicating with C++ Hardware Control Server"""

    def __init__(self, host: str = "localhost", port: int = 8081):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to hardware server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to hardware server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to hardware server: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from hardware server"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            self.socket = None
        self.connected = False

    def _send_command(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send command to hardware server and receive response"""
        if not self.connected or not self.socket:
            logger.error("Not connected to hardware server")
            return None

        try:
            # Send command as JSON
            message = json.dumps(command) + "\n"
            self.socket.send(message.encode('utf-8'))

            # Receive response
            response_data = self.socket.recv(4096)
            if not response_data:
                logger.error("No response from hardware server")
                return None

            response = json.loads(response_data.decode('utf-8'))
            return response

        except Exception as e:
            logger.error(f"Error communicating with hardware server: {e}")
            return None

    def configure_gpio(self, pin: int, direction: str) -> bool:
        """Configure GPIO pin direction"""
        if direction not in ["input", "output"]:
            logger.error(f"Invalid direction: {direction}")
            return False

        command = {
            "command": "configure",
            "pin": pin,
            "direction": direction
        }

        response = self._send_command(command)
        if response and response.get("status") == "success":
            logger.info(f"Configured GPIO pin {pin} as {direction}")
            return True
        else:
            logger.error(f"Failed to configure GPIO pin {pin}")
            return False

    def set_gpio_value(self, pin: int, value: int) -> bool:
        """Set GPIO pin value (for output pins)"""
        if value not in [0, 1]:
            logger.error(f"Invalid GPIO value: {value}")
            return False

        command = {
            "command": "set",
            "pin": pin,
            "value": value
        }

        response = self._send_command(command)
        if response and response.get("status") == "success":
            logger.info(f"Set GPIO pin {pin} to {value}")
            return True
        else:
            logger.error(f"Failed to set GPIO pin {pin}")
            return False

    def get_gpio_value(self, pin: int) -> Optional[int]:
        """Get GPIO pin value"""
        command = {
            "command": "get",
            "pin": pin
        }

        response = self._send_command(command)
        if response and response.get("status") == "success":
            value = response.get("value")
            logger.info(f"GPIO pin {pin} value: {value}")
            return value
        else:
            logger.error(f"Failed to get GPIO pin {pin} value")
            return None

    def get_gpio_status(self) -> Optional[Dict[int, GPIOStatus]]:
        """Get status of all configured GPIO pins"""
        command = {"command": "status"}

        response = self._send_command(command)
        if response and response.get("status") == "success":
            pins = {}
            for pin_data in response.get("pins", []):
                pin = GPIOStatus(
                    pin=pin_data["pin"],
                    direction=pin_data["direction"],
                    value=pin_data.get("value")
                )
                pins[pin.pin] = pin
            return pins
        else:
            logger.error("Failed to get GPIO status")
            return None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()