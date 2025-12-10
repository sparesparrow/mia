"""
AI Service LED Controller - Python Interface for Arduino LED Strip Monitor
Provides high-level interface for controlling the 23-LED WS2812B AI service monitor.
"""

import serial
import json
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AIServiceLEDController:
    """
    Python controller for Arduino AI Service LED Monitor

    Features:
    - AI communication state visualization (listening, speaking, etc.)
    - Service health monitoring (API, GPIO, Serial, OBD, MQTT, Camera)
    - OBD data visualization (RPM, speed, temperature, load)
    - Mode switching (drive, parked, night, service)
    - Emergency override controls
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baud_rate: int = 115200, timeout: float = 1.0):
        """
        Initialize the LED controller

        Args:
            port: Serial port path (default: /dev/ttyUSB0, use "mock" for testing)
            baud_rate: Serial baud rate (default: 115200)
            timeout: Serial timeout in seconds (default: 1.0)
        """
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.mock_mode = port == "mock"

    def connect(self) -> bool:
        """
        Connect to the Arduino via serial

        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.mock_mode:
            self.connected = True
            logger.info("Connected to mock LED controller")
            return True

        try:
            self.serial = serial.Serial(
                self.port,
                self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self.connected = True
            logger.info(f"Connected to Arduino LED controller on {self.port}")

            # Wait for Arduino to initialize
            time.sleep(2)

            # Test connection
            response = self._send_command({"cmd": "status"})
            if response and response.get("status") == "ok":
                logger.info("Arduino LED controller ready")
                return True
            else:
                logger.error("Arduino did not respond to status request")
                return False

        except serial.SerialException as e:
            logger.error(f"Failed to connect to Arduino: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from the Arduino"""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
        logger.info("Disconnected from Arduino LED controller")

    def _send_command(self, cmd_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send a JSON command to the Arduino

        Args:
            cmd_dict: Command dictionary to send

        Returns:
            Optional response dictionary, or None if error
        """
        if not self.connected:
            logger.error("Not connected to Arduino")
            return None

        if self.mock_mode:
            # Mock responses for testing
            cmd = cmd_dict.get("cmd", "")
            response = {
                "status": "ok",
                "message": f"Mock command '{cmd}' processed",
                "brightness": 128,
                "mode": "drive",
                "emergency_override": False,
                "num_leds": 23
            }

            if cmd == "ai_state":
                response.update({"status": "ai_state_set", "message": f"AI state set to: {cmd_dict.get('state', 'none')}"})
            elif cmd == "service_status":
                response.update({"status": "service_status_set", "message": f"Service {cmd_dict.get('service', 'unknown')} status set"})
            elif cmd == "obd_data":
                response.update({"status": "obd_data_set", "message": f"OBD data set: {cmd_dict.get('value', 0)}"})
            elif cmd == "set_mode":
                response.update({"status": "mode_set", "message": f"Mode set to: {cmd_dict.get('mode', 'drive')}"})
            elif cmd == "emergency":
                action = cmd_dict.get("action", "activate")
                response.update({"status": f"emergency_{action}", "message": f"Emergency {action}d"})
            elif cmd == "clear":
                response.update({"status": "cleared", "message": "All LEDs cleared"})
            elif cmd == "set_brightness":
                response.update({"status": "brightness_set", "message": f"Brightness set to {cmd_dict.get('brightness', 128)}"})

            # Simulate serial delay
            time.sleep(0.05)
            return response

        try:
            # Convert command to JSON string
            json_str = json.dumps(cmd_dict) + '\n'

            # Send command
            self.serial.write(json_str.encode('utf-8'))
            self.serial.flush()

            # Read response (with timeout)
            if self.serial.in_waiting > 0:
                response_line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if response_line:
                    try:
                        return json.loads(response_line)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON response: {response_line} ({e})")
                        return None

            # Small delay for Arduino processing
            time.sleep(0.05)
            return None

        except serial.SerialException as e:
            logger.error(f"Serial communication error: {e}")
            self.connected = False
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending command: {e}")
            return None

    # AI State Methods

    def ai_listening(self, priority: int = 1) -> bool:
        """
        Set AI to listening state (Knight Rider blue pattern)

        Args:
            priority: Animation priority (0-4, 0=highest)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "ai_state",
            "state": "listening",
            "priority": priority
        })
        return response is not None and response.get("status") == "ai_state_set"

    def ai_speaking(self, priority: int = 1) -> bool:
        """
        Set AI to speaking state (green wave pattern)

        Args:
            priority: Animation priority (0-4, 0=highest)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "ai_state",
            "state": "speaking",
            "priority": priority
        })
        return response is not None and response.get("status") == "ai_state_set"

    def ai_thinking(self, priority: int = 2) -> bool:
        """
        Set AI to thinking state (purple pulse pattern)

        Args:
            priority: Animation priority (0-4, 0=highest)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "ai_state",
            "state": "thinking",
            "priority": priority
        })
        return response is not None and response.get("status") == "ai_state_set"

    def ai_recording(self, priority: int = 0) -> bool:
        """
        Set AI to recording state (red Knight Rider pattern)

        Args:
            priority: Animation priority (0-4, 0=highest)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "ai_state",
            "state": "recording",
            "priority": priority
        })
        return response is not None and response.get("status") == "ai_state_set"

    def ai_error(self, priority: int = 0) -> bool:
        """
        Set AI to error state (red flash pattern)

        Args:
            priority: Animation priority (0-4, 0=highest)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "ai_state",
            "state": "error",
            "priority": priority
        })
        return response is not None and response.get("status") == "ai_state_set"

    def ai_idle(self) -> bool:
        """
        Clear AI state (turn off AI animations)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "ai_state",
            "state": "none",
            "priority": 4
        })
        return response is not None and response.get("status") == "ai_state_set"

    # Service Status Methods

    def service_running(self, service_name: str, priority: int = 2) -> bool:
        """
        Set service status to running (green pulse)

        Args:
            service_name: Service name (api, gpio, serial, obd, mqtt, camera)
            priority: Animation priority (0-4, 0=highest)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "service_status",
            "service": service_name,
            "status": "running",
            "priority": priority
        })
        return response is not None and response.get("status") == "service_status_set"

    def service_warning(self, service_name: str, priority: int = 1) -> bool:
        """
        Set service status to warning (yellow pulse)

        Args:
            service_name: Service name (api, gpio, serial, obd, mqtt, camera)
            priority: Animation priority (0-4, 0=highest)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "service_status",
            "service": service_name,
            "status": "warning",
            "priority": priority
        })
        return response is not None and response.get("status") == "service_status_set"

    def service_error(self, service_name: str, priority: int = 0) -> bool:
        """
        Set service status to error (red flash)

        Args:
            service_name: Service name (api, gpio, serial, obd, mqtt, camera)
            priority: Animation priority (0-4, 0=highest)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "service_status",
            "service": service_name,
            "status": "error",
            "priority": priority
        })
        return response is not None and response.get("status") == "service_status_set"

    def service_stopped(self, service_name: str) -> bool:
        """
        Set service status to stopped (LED off)

        Args:
            service_name: Service name (api, gpio, serial, obd, mqtt, camera)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "service_status",
            "service": service_name,
            "status": "stopped",
            "priority": 4
        })
        return response is not None and response.get("status") == "service_status_set"

    # OBD Data Methods

    def obd_rpm(self, rpm: int, max_rpm: int = 8000) -> bool:
        """
        Display RPM as bargraph in AI zone

        Args:
            rpm: Current RPM value
            max_rpm: Maximum RPM for scaling (default: 8000)

        Returns:
            bool: True if command sent successfully
        """
        percentage = min(100, int((rpm / max_rpm) * 100))
        response = self._send_command({
            "cmd": "obd_data",
            "type": "rpm",
            "value": percentage
        })
        return response is not None and response.get("status") == "obd_data_set"

    def obd_speed(self, speed: int, max_speed: int = 200) -> bool:
        """
        Display speed as bargraph in AI zone

        Args:
            speed: Current speed in km/h or mph
            max_speed: Maximum speed for scaling (default: 200)

        Returns:
            bool: True if command sent successfully
        """
        percentage = min(100, int((speed / max_speed) * 100))
        response = self._send_command({
            "cmd": "obd_data",
            "type": "speed",
            "value": percentage
        })
        return response is not None and response.get("status") == "obd_data_set"

    def obd_temperature(self, temp: int, max_temp: int = 120) -> bool:
        """
        Display temperature as bargraph in AI zone

        Args:
            temp: Current temperature in Celsius
            max_temp: Maximum temperature for scaling (default: 120°C)

        Returns:
            bool: True if command sent successfully
        """
        percentage = min(100, int((temp / max_temp) * 100))
        response = self._send_command({
            "cmd": "obd_data",
            "type": "temp",
            "value": percentage
        })
        return response is not None and response.get("status") == "obd_data_set"

    def obd_load(self, load: int) -> bool:
        """
        Display engine load as bargraph in AI zone

        Args:
            load: Current engine load percentage (0-100)

        Returns:
            bool: True if command sent successfully
        """
        percentage = min(100, load)
        response = self._send_command({
            "cmd": "obd_data",
            "type": "load",
            "value": percentage
        })
        return response is not None and response.get("status") == "obd_data_set"

    # Mode Control Methods

    def set_mode_drive(self) -> bool:
        """
        Set mode to drive (normal brightness)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "set_mode",
            "mode": "drive"
        })
        return response is not None and response.get("status") == "mode_set"

    def set_mode_parked(self) -> bool:
        """
        Set mode to parked (dimmed brightness)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "set_mode",
            "mode": "parked"
        })
        return response is not None and response.get("status") == "mode_set"

    def set_mode_night(self) -> bool:
        """
        Set mode to night (very dim brightness)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "set_mode",
            "mode": "night"
        })
        return response is not None and response.get("status") == "mode_set"

    def set_mode_service(self) -> bool:
        """
        Set mode to service (normal brightness, diagnostic mode)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "set_mode",
            "mode": "service"
        })
        return response is not None and response.get("status") == "mode_set"

    # Emergency Control

    def emergency_activate(self) -> bool:
        """
        Activate emergency override (all LEDs red, full brightness)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "emergency",
            "action": "activate"
        })
        return response is not None and response.get("status") == "emergency_activate"

    def emergency_deactivate(self) -> bool:
        """
        Deactivate emergency override (restore normal operation)

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({
            "cmd": "emergency",
            "action": "deactivate"
        })
        return response is not None and response.get("status") == "emergency_deactivate"

    # Utility Methods

    def clear_all(self) -> bool:
        """
        Clear all LEDs

        Returns:
            bool: True if command sent successfully
        """
        response = self._send_command({"cmd": "clear"})
        return response is not None and response.get("status") == "cleared"

    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current status from Arduino

        Returns:
            Status dictionary or None if error
        """
        return self._send_command({"cmd": "status"})

    def set_brightness(self, brightness: int) -> bool:
        """
        Set global brightness (0-255)

        Args:
            brightness: Brightness level (0-255)

        Returns:
            bool: True if command sent successfully
        """
        brightness = max(0, min(255, brightness))
        response = self._send_command({
            "cmd": "set_brightness",
            "brightness": brightness
        })
        return response is not None and response.get("status") == "brightness_set"


# Convenience functions for common operations

def create_controller(port: str = "/dev/ttyUSB0") -> AIServiceLEDController:
    """
    Create and connect to an LED controller

    Args:
        port: Serial port path

    Returns:
        Connected AIServiceLEDController instance
    """
    controller = AIServiceLEDController(port)
    if controller.connect():
        return controller
    else:
        raise ConnectionError(f"Failed to connect to Arduino on {port}")


# Example usage and demo
if __name__ == "__main__":
    # Demo script
    logging.basicConfig(level=logging.INFO)

    try:
        controller = create_controller()

        print("AI Service LED Controller Demo")
        print("==============================")

        # AI state demo
        print("1. AI Listening (Knight Rider blue)")
        controller.ai_listening()
        time.sleep(3)

        print("2. AI Speaking (green wave)")
        controller.ai_speaking()
        time.sleep(3)

        print("3. AI Thinking (purple pulse)")
        controller.ai_thinking()
        time.sleep(3)

        # Service status demo
        print("4. Service Error (red flash)")
        controller.service_error("obd")
        time.sleep(3)

        print("5. Service Running (green pulse)")
        controller.service_running("api")
        time.sleep(3)

        # OBD demo
        print("6. RPM Bargraph")
        for rpm in [1000, 2000, 3500, 5000, 6500, 8000]:
            controller.obd_rpm(rpm)
            time.sleep(0.5)

        # Mode demo
        print("7. Night Mode (dim)")
        controller.set_mode_night()
        time.sleep(2)

        print("8. Drive Mode (normal)")
        controller.set_mode_drive()
        time.sleep(2)

        # Clear and disconnect
        print("9. Clearing all animations")
        controller.clear_all()
        time.sleep(1)

        controller.disconnect()
        print("Demo complete!")

    except ConnectionError as e:
        print(f"Connection failed: {e}")
    except KeyboardInterrupt:
        print("Demo interrupted")
    except Exception as e:
        print(f"Error: {e}")