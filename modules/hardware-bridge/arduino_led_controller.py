"""
Arduino LED Strip Controller

Python module for controlling Arduino Uno LED strip via Serial communication.
Integrates with the AI-SERVIS hardware bridge for MQTT/MCP communication.

Hardware:
- Arduino Uno connected via USB (ttyUSB0)
- WS2812B LED strip with 23 programmable 5V LEDs
"""

import serial
import json
import logging
import time
from typing import Optional, Dict, Any, Tuple
from threading import Lock
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class ArduinoLEDController:
    """Controller for Arduino LED strip via Serial communication"""

    def __init__(self, serial_port: str = "/dev/ttyUSB0", baud_rate: int = 115200,
                 timeout: float = 1.0):
        """
        Initialize Arduino LED controller
        
        Args:
            serial_port: Serial port path (e.g., /dev/ttyUSB0)
            baud_rate: Serial baud rate (default: 115200)
            timeout: Serial timeout in seconds
        """
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.lock = Lock()
        self.connected = False

    def connect(self) -> bool:
        """Connect to Arduino via Serial"""
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            # Wait for Arduino to initialize
            time.sleep(2)
            self.connected = True
            logger.info(f"Connected to Arduino LED controller on {self.serial_port}")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to Arduino: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Arduino: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from Arduino"""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception as e:
                logger.error(f"Error closing serial connection: {e}")
            self.serial_conn = None
        self.connected = False

    def _send_command(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send command to Arduino and receive response"""
        if not self.connected or not self.serial_conn:
            logger.error("Not connected to Arduino")
            return None

        with self.lock:
            try:
                # Send command as JSON
                json_command = json.dumps(command) + "\n"
                self.serial_conn.write(json_command.encode('utf-8'))
                self.serial_conn.flush()

                # Read response
                response_line = self.serial_conn.readline()
                if response_line:
                    response_str = response_line.decode('utf-8').strip()
                    try:
                        response = json.loads(response_str)
                        return response
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Arduino response: {e}, response: {response_str}")
                        return None
                else:
                    logger.warning("No response from Arduino")
                    return None

            except serial.SerialTimeoutException:
                logger.error("Serial write timeout")
                return None
            except Exception as e:
                logger.error(f"Error communicating with Arduino: {e}")
                return None

    def set_color(self, r: int, g: int, b: int) -> bool:
        """
        Set all LEDs to a specific color
        
        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
        
        Returns:
            True if successful, False otherwise
        """
        command = {
            "command": "set_color",
            "r": r,
            "g": g,
            "b": b
        }
        response = self._send_command(command)
        return response is not None and response.get("status") != "error"

    def set_brightness(self, brightness: int) -> bool:
        """
        Set LED strip brightness
        
        Args:
            brightness: Brightness value (0-255)
        
        Returns:
            True if successful, False otherwise
        """
        command = {
            "command": "set_brightness",
            "brightness": brightness
        }
        response = self._send_command(command)
        return response is not None and response.get("status") != "error"

    def set_led(self, led_index: int, r: int, g: int, b: int) -> bool:
        """
        Set a specific LED to a color
        
        Args:
            led_index: LED index (0-22)
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
        
        Returns:
            True if successful, False otherwise
        """
        command = {
            "command": "set_led",
            "led": led_index,
            "r": r,
            "g": g,
            "b": b
        }
        response = self._send_command(command)
        return response is not None and response.get("status") != "error"

    def start_animation(self, animation: str, **kwargs) -> bool:
        """
        Start an animation
        
        Args:
            animation: Animation type (blink, fade, rainbow, chase)
            **kwargs: Animation-specific parameters (speed, color, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        command = {
            "command": "animation",
            "animation": animation,
            **kwargs
        }
        response = self._send_command(command)
        return response is not None and response.get("status") != "error"

    def start_rainbow(self, speed: int = 10) -> bool:
        """
        Start rainbow animation
        
        Args:
            speed: Animation speed (milliseconds between updates)
        
        Returns:
            True if successful, False otherwise
        """
        command = {
            "command": "rainbow",
            "speed": speed
        }
        response = self._send_command(command)
        return response is not None and response.get("status") != "error"

    def start_chase(self, r: int = 255, g: int = 0, b: int = 0, speed: int = 100) -> bool:
        """
        Start chase animation
        
        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
            speed: Animation speed (milliseconds between updates)
        
        Returns:
            True if successful, False otherwise
        """
        command = {
            "command": "chase",
            "r": r,
            "g": g,
            "b": b,
            "speed": speed
        }
        response = self._send_command(command)
        return response is not None and response.get("status") != "error"

    def clear(self) -> bool:
        """
        Clear all LEDs (turn off)
        
        Returns:
            True if successful, False otherwise
        """
        command = {"command": "clear"}
        response = self._send_command(command)
        return response is not None and response.get("status") != "error"

    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current status from Arduino
        
        Returns:
            Status dictionary or None if failed
        """
        command = {"command": "status"}
        response = self._send_command(command)
        return response

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class ArduinoLEDMQTTBridge:
    """MQTT bridge for Arduino LED controller"""

    def __init__(self, serial_port: str = "/dev/ttyUSB0", 
                 mqtt_broker: str = "localhost", mqtt_port: int = 1883,
                 mqtt_topic_prefix: str = "hardware/arduino/led"):
        """
        Initialize MQTT bridge for Arduino LED controller
        
        Args:
            serial_port: Serial port path
            mqtt_broker: MQTT broker hostname
            mqtt_port: MQTT broker port
            mqtt_topic_prefix: MQTT topic prefix for LED commands
        """
        self.led_controller = ArduinoLEDController(serial_port)
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self.mqtt_client: Optional[mqtt.Client] = None

    def connect_mqtt(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def disconnect_mqtt(self):
        """Disconnect from MQTT broker"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connect callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to LED control topics
            client.subscribe(f"{self.mqtt_topic_prefix}/set_color")
            client.subscribe(f"{self.mqtt_topic_prefix}/set_brightness")
            client.subscribe(f"{self.mqtt_topic_prefix}/set_led")
            client.subscribe(f"{self.mqtt_topic_prefix}/animation")
            client.subscribe(f"{self.mqtt_topic_prefix}/rainbow")
            client.subscribe(f"{self.mqtt_topic_prefix}/chase")
            client.subscribe(f"{self.mqtt_topic_prefix}/clear")
            client.subscribe(f"{self.mqtt_topic_prefix}/status")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())

            logger.info(f"Received MQTT message on {topic}: {payload}")

            # Handle different commands
            if topic.endswith("/set_color"):
                r = payload.get("r", 255)
                g = payload.get("g", 255)
                b = payload.get("b", 255)
                success = self.led_controller.set_color(r, g, b)
                self._publish_response("set_color", success, payload)

            elif topic.endswith("/set_brightness"):
                brightness = payload.get("brightness", 128)
                success = self.led_controller.set_brightness(brightness)
                self._publish_response("set_brightness", success, payload)

            elif topic.endswith("/set_led"):
                led_index = payload.get("led", 0)
                r = payload.get("r", 255)
                g = payload.get("g", 255)
                b = payload.get("b", 255)
                success = self.led_controller.set_led(led_index, r, g, b)
                self._publish_response("set_led", success, payload)

            elif topic.endswith("/animation"):
                animation = payload.get("animation", "blink")
                speed = payload.get("speed", 500)
                success = self.led_controller.start_animation(animation, speed=speed)
                self._publish_response("animation", success, payload)

            elif topic.endswith("/rainbow"):
                speed = payload.get("speed", 10)
                success = self.led_controller.start_rainbow(speed)
                self._publish_response("rainbow", success, payload)

            elif topic.endswith("/chase"):
                r = payload.get("r", 255)
                g = payload.get("g", 0)
                b = payload.get("b", 0)
                speed = payload.get("speed", 100)
                success = self.led_controller.start_chase(r, g, b, speed)
                self._publish_response("chase", success, payload)

            elif topic.endswith("/clear"):
                success = self.led_controller.clear()
                self._publish_response("clear", success, payload)

            elif topic.endswith("/status"):
                status = self.led_controller.get_status()
                if status:
                    self.mqtt_client.publish(
                        f"{self.mqtt_topic_prefix}/response/status",
                        json.dumps(status)
                    )

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _publish_response(self, command: str, success: bool, original_payload: Dict[str, Any]):
        """Publish command response to MQTT"""
        response = {
            "command": command,
            "success": success,
            "payload": original_payload,
            "timestamp": time.time()
        }
        self.mqtt_client.publish(
            f"{self.mqtt_topic_prefix}/response/{command}",
            json.dumps(response)
        )

    def run(self):
        """Run the MQTT bridge"""
        # Connect to Arduino
        if not self.led_controller.connect():
            raise RuntimeError("Failed to connect to Arduino")

        # Connect to MQTT
        if not self.connect_mqtt():
            raise RuntimeError("Failed to connect to MQTT broker")

        try:
            # Keep running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Arduino LED MQTT Bridge shutting down")
        finally:
            self.disconnect_mqtt()
            self.led_controller.disconnect()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get serial port from command line or use default
    serial_port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    mqtt_broker = sys.argv[2] if len(sys.argv) > 2 else "localhost"

    bridge = ArduinoLEDMQTTBridge(serial_port=serial_port, mqtt_broker=mqtt_broker)
    bridge.run()
