#!/usr/bin/env python3
"""
LED Monitor Service - AI Service Status Monitor
Integrates LED strip controller with MIA ZeroMQ architecture

This service:
- Monitors health of all MIA services via ZeroMQ broker
- Connects to Arduino LED controller for visual feedback
- Provides real-time status visualization on 23-LED strip
- Subscribes to telemetry data for OBD visualization
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum

import zmq

# Import LED controller
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hardware.led_controller import AIServiceLEDController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service state enumeration"""
    UNKNOWN = "unknown"
    RUNNING = "running"
    WARNING = "warning"
    ERROR = "error"
    STOPPED = "stopped"


class LEDMonitorService:
    """
    LED Monitor Service that integrates LED strip with MIA services

    Responsibilities:
    - Monitor service health via ZeroMQ broker
    - Control LED strip for real-time status visualization
    - Subscribe to telemetry data for OBD visualization
    - Handle mode switching based on vehicle state
    """

    def __init__(self,
                 broker_url: str = "tcp://localhost:5555",
                 telemetry_url: str = "tcp://localhost:5556",
                 led_port: str = "/dev/ttyUSB0"):
        self.broker_url = broker_url
        self.telemetry_url = telemetry_url
        self.led_port = led_port

        self.context = zmq.Context()
        self.broker_socket: Optional[zmq.Socket] = None
        self.telemetry_socket: Optional[zmq.Socket] = None
        self.running = False

        # Service health tracking
        self.service_states: Dict[str, ServiceState] = {
            "api": ServiceState.UNKNOWN,
            "gpio": ServiceState.UNKNOWN,
            "serial": ServiceState.UNKNOWN,
            "obd": ServiceState.UNKNOWN,
            "mqtt": ServiceState.UNKNOWN,
            "camera": ServiceState.UNKNOWN,
        }

        # LED controller
        self.led_controller: Optional[AIServiceLEDController] = None

        # OBD data tracking
        self.last_obd_data = {
            "rpm": 0,
            "speed": 0,
            "temp": 0,
            "load": 0
        }

        # Mode and AI state tracking
        self.current_mode = "drive"
        self.ai_state = "idle"
        self.last_ai_state_time = 0

        # Intelligent mode switching
        self.vehicle_state = {
            "moving": False,
            "last_speed": 0,
            "last_speed_time": 0,
            "parked_duration": 0,
            "night_mode_active": False
        }

        # Health check timing
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds

        # Mode switching thresholds
        self.speed_threshold = 5  # km/h - consider moving above this
        self.parked_timeout = 300  # seconds - switch to parked after this time
        self.night_start_hour = 20  # 8 PM
        self.night_end_hour = 6    # 6 AM

    def start(self) -> bool:
        """Start the LED monitor service"""
        logger.info("Starting LED Monitor Service...")

        # Connect to LED controller
        try:
            self.led_controller = AIServiceLEDController(self.led_port)
            if not self.led_controller.connect():
                logger.error("Failed to connect to LED controller")
                return False
            logger.info(f"Connected to LED controller on {self.led_port}")
        except Exception as e:
            logger.error(f"Error connecting to LED controller: {e}")
            return False

        # Connect to ZeroMQ broker
        self.broker_socket = self.context.socket(zmq.DEALER)
        import uuid
        service_id = str(uuid.uuid4())
        self.broker_socket.setsockopt_string(zmq.IDENTITY, service_id)
        self.broker_socket.connect(self.broker_url)

        # Subscribe to telemetry
        self.telemetry_socket = self.context.socket(zmq.SUB)
        self.telemetry_socket.connect(self.telemetry_url)
        self.telemetry_socket.subscribe("mcu/telemetry")  # MCU telemetry
        self.telemetry_socket.subscribe("obd/telemetry")  # OBD telemetry

        self.running = True
        logger.info("LED Monitor Service started")
        logger.info(f"Connected to broker: {self.broker_url}")
        logger.info(f"Subscribed to telemetry: {self.telemetry_url}")

        # Register with broker
        self._register_service()

        # Start background threads
        telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        telemetry_thread.start()

        broker_thread = threading.Thread(target=self._broker_loop, daemon=True)
        broker_thread.start()

        health_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        health_thread.start()

        # Initialize LED state
        self._initialize_led_state()

        return True

    def stop(self):
        """Stop the LED monitor service"""
        self.running = False

        if self.broker_socket:
            self.broker_socket.close()
        if self.telemetry_socket:
            self.telemetry_socket.close()

        if self.led_controller:
            self.led_controller.disconnect()

        self.context.term()
        logger.info("LED Monitor Service stopped")

    def _register_service(self):
        """Register this service with the broker"""
        message = {
            "type": "WORKER_REGISTER",
            "worker_type": "LED_MONITOR",
            "capabilities": ["LED_STATUS", "LED_CONTROL"],
            "timestamp": datetime.now().isoformat()
        }
        self.broker_socket.send_json(message)
        logger.info("Registered LED Monitor service with broker")

    def _initialize_led_state(self):
        """Initialize LED strip to default state"""
        if not self.led_controller:
            return

        logger.info("Initializing LED strip state...")
        self.led_controller.clear_all()
        self.led_controller.set_mode_drive()

        # Set initial service states (assume running until proven otherwise)
        for service in self.service_states.keys():
            self.led_controller.service_running(service, priority=3)

    def _telemetry_loop(self):
        """Listen for telemetry data"""
        poller = zmq.Poller()
        poller.register(self.telemetry_socket, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(100))  # 100ms timeout

                if self.telemetry_socket in socks and socks[self.telemetry_socket] == zmq.POLLIN:
                    # Receive multipart: [topic][message]
                    parts = self.telemetry_socket.recv_multipart()
                    if len(parts) >= 2:
                        topic = parts[0].decode('utf-8')
                        message_data = parts[1]

                        if topic in ["mcu/telemetry", "obd/telemetry"]:
                            try:
                                data = json.loads(message_data.decode('utf-8'))
                                self._handle_telemetry(topic, data)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to decode telemetry JSON: {e}")

            except zmq.ZMQError as e:
                if self.running:
                    logger.error(f"ZMQ error in telemetry loop: {e}")
                break
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                time.sleep(0.1)

    def _handle_telemetry(self, topic: str, data: Dict[str, Any]):
        """Handle incoming telemetry data"""
        if topic == "mcu/telemetry":
            self._handle_mcu_telemetry(data)
        elif topic == "obd/telemetry":
            self._handle_obd_telemetry(data)

    def _handle_mcu_telemetry(self, data: Dict[str, Any]):
        """Handle MCU telemetry data"""
        # Update OBD data from MCU telemetry
        updated = False

        if 'pot1' in data:  # RPM from potentiometer
            rpm = max(800, min(4000, int(data['pot1'] * 4)))
            if rpm != self.last_obd_data["rpm"]:
                self.last_obd_data["rpm"] = rpm
                updated = True

        if 'pot2' in data:  # Speed from potentiometer
            speed = max(0, min(120, int(data['pot2'] / 8.5)))
            if speed != self.last_obd_data["speed"]:
                self.last_obd_data["speed"] = speed
                updated = True

        if 'throttle' in data:  # Throttle/load
            load = max(0, min(100, int(data['throttle'])))
            if load != self.last_obd_data["load"]:
                self.last_obd_data["load"] = load
                updated = True

        if 'coolant' in data:  # Temperature
            temp = max(-40, min(215, int(data['coolant'])))
            if temp != self.last_obd_data["temp"]:
                self.last_obd_data["temp"] = temp
                updated = True

        # Update LEDs if data changed
        if updated and self.led_controller:
            self._update_obd_leds()

        # Update intelligent mode switching
        self._update_vehicle_state(data)

    def _handle_obd_telemetry(self, data: Dict[str, Any]):
        """Handle OBD telemetry data"""
        updated = False

        if 'rpm' in data and data['rpm'] != self.last_obd_data["rpm"]:
            self.last_obd_data["rpm"] = int(data['rpm'])
            updated = True

        if 'speed' in data and data['speed'] != self.last_obd_data["speed"]:
            self.last_obd_data["speed"] = int(data['speed'])
            updated = True

        if 'coolant_temp' in data and data['coolant_temp'] != self.last_obd_data["temp"]:
            self.last_obd_data["temp"] = int(data['coolant_temp'])
            updated = True

        if 'load' in data and data['load'] != self.last_obd_data["load"]:
            self.last_obd_data["load"] = int(data['load'])
            updated = True

        # Update LEDs if data changed
        if updated and self.led_controller:
            self._update_obd_leds()

        # Update intelligent mode switching
        self._update_vehicle_state(data)
        """Handle OBD telemetry data"""
        updated = False

        if 'rpm' in data and data['rpm'] != self.last_obd_data["rpm"]:
            self.last_obd_data["rpm"] = int(data['rpm'])
            updated = True

        if 'speed' in data and data['speed'] != self.last_obd_data["speed"]:
            self.last_obd_data["speed"] = int(data['speed'])
            updated = True

        if 'coolant_temp' in data and data['coolant_temp'] != self.last_obd_data["temp"]:
            self.last_obd_data["temp"] = int(data['coolant_temp'])
            updated = True

        if 'load' in data and data['load'] != self.last_obd_data["load"]:
            self.last_obd_data["load"] = int(data['load'])
            updated = True

        # Update LEDs if data changed
        if updated and self.led_controller:
            self._update_obd_leds()

    def _update_obd_leds(self):
        """Update OBD visualization on LEDs"""
        if not self.led_controller:
            return

        # Only update OBD data in drive mode
        if self.current_mode == "drive":
            rpm = self.last_obd_data["rpm"]
            if rpm > 0:
                self.led_controller.obd_rpm(rpm)

    def _broker_loop(self):
        """Handle messages from ZeroMQ broker"""
        poller = zmq.Poller()
        poller.register(self.broker_socket, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(1000))  # 1 second timeout

                if self.broker_socket in socks and socks[self.broker_socket] == zmq.POLLIN:
                    message = self.broker_socket.recv_json()
                    self._handle_broker_message(message)

            except zmq.ZMQError as e:
                if self.running:
                    logger.error(f"ZMQ error in broker loop: {e}")
                break
            except Exception as e:
                logger.error(f"Error in broker loop: {e}")
                time.sleep(0.1)

    def _handle_broker_message(self, message: Dict[str, Any]):
        """Handle incoming message from broker"""
        message_type = message.get("type")
        request_id = message.get("request_id")

        try:
            if message_type == "LED_STATUS":
                self._handle_status_request(request_id)
            elif message_type == "LED_CONTROL":
                self._handle_control_request(message, request_id)
            # Listen for service status updates
            elif message_type in ["GPIO_STATUS_RESPONSE", "OBD_STATUS_RESPONSE"]:
                self._handle_service_status_update(message_type, message)
        except Exception as e:
            logger.error(f"Error handling {message_type}: {e}")
            self._send_error(request_id, str(e))

    def _handle_status_request(self, request_id: Optional[str]):
        """Handle LED status request"""
        status = {
            "type": "LED_STATUS_RESPONSE",
            "service_states": {k: v.value for k, v in self.service_states.items()},
            "obd_data": self.last_obd_data.copy(),
            "mode": self.current_mode,
            "ai_state": self.ai_state,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
        self.broker_socket.send_json(status)

    def _handle_control_request(self, message: Dict[str, Any], request_id: Optional[str]):
        """Handle LED control request"""
        command = message.get("command")

        if command == "set_ai_state":
            ai_state = message.get("ai_state", "idle")
            self._set_ai_state(ai_state)
        elif command == "set_mode":
            mode = message.get("mode", "drive")
            self._set_mode(mode)
        elif command == "emergency":
            action = message.get("action", "activate")
            if action == "activate":
                self.led_controller.emergency_activate()
            else:
                self.led_controller.emergency_deactivate()

        response = {
            "type": "LED_CONTROL_RESPONSE",
            "command": command,
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
        self.broker_socket.send_json(response)

    def _handle_service_status_update(self, message_type: str, message: Dict[str, Any]):
        """Handle service status updates from other services"""
        if message_type == "GPIO_STATUS_RESPONSE":
            # GPIO service is running
            self._update_service_state("gpio", ServiceState.RUNNING)
        elif message_type == "OBD_STATUS_RESPONSE":
            # OBD service is running
            self._update_service_state("obd", ServiceState.RUNNING)

    def _update_service_state(self, service_name: str, state: ServiceState):
        """Update service state and LED visualization"""
        if service_name not in self.service_states:
            return

        old_state = self.service_states[service_name]
        if old_state == state:
            return  # No change

        self.service_states[service_name] = state
        logger.info(f"Service {service_name} state changed: {old_state.value} -> {state.value}")

        # Update LED visualization
        if self.led_controller:
            if state == ServiceState.RUNNING:
                self.led_controller.service_running(service_name, priority=3)
            elif state == ServiceState.WARNING:
                self.led_controller.service_warning(service_name, priority=2)
            elif state == ServiceState.ERROR:
                self.led_controller.service_error(service_name, priority=1)
            elif state == ServiceState.STOPPED:
                self.led_controller.service_stopped(service_name)

    def _update_vehicle_state(self, data: Dict[str, Any]):
        """Update vehicle state for intelligent mode switching"""
        current_time = time.time()

        # Update speed-based movement detection
        speed = self.last_obd_data.get("speed", 0)
        if speed > self.speed_threshold:
            # Vehicle is moving
            if not self.vehicle_state["moving"]:
                logger.info("Vehicle movement detected")
                self.vehicle_state["moving"] = True
                self.vehicle_state["parked_duration"] = 0
                self._intelligent_mode_switch("drive")
        else:
            # Vehicle might be parked
            if self.vehicle_state["moving"]:
                self.vehicle_state["last_speed_time"] = current_time
                self.vehicle_state["moving"] = False
                logger.info("Vehicle stopped, monitoring for parking")

        # Check for prolonged parking
        if not self.vehicle_state["moving"]:
            parked_time = current_time - self.vehicle_state["last_speed_time"]
            if parked_time > self.parked_timeout and self.current_mode != "parked":
                logger.info(f"Vehicle parked for {parked_time:.0f}s, switching to parked mode")
                self._intelligent_mode_switch("parked")
                self.vehicle_state["parked_duration"] = parked_time

        # Night mode based on time
        current_hour = time.localtime().tm_hour
        should_be_night = (current_hour >= self.night_start_hour or current_hour < self.night_end_hour)

        if should_be_night and not self.vehicle_state["night_mode_active"]:
            logger.info("Night time detected, enabling night mode features")
            self.vehicle_state["night_mode_active"] = True
            if self.current_mode == "drive":
                self._intelligent_mode_switch("night")
        elif not should_be_night and self.vehicle_state["night_mode_active"]:
            logger.info("Day time detected, disabling night mode")
            self.vehicle_state["night_mode_active"] = False
            if self.current_mode == "night":
                self._intelligent_mode_switch("drive")

    def _intelligent_mode_switch(self, suggested_mode: str):
        """Intelligently switch modes based on context"""
        # Priority order for mode selection
        if suggested_mode == "parked":
            # Only switch to parked if no critical services are active
            critical_services = [s for s, state in self.service_states.items()
                               if state in [ServiceState.ERROR, ServiceState.WARNING]]
            if not critical_services:
                self._set_mode("parked")
            else:
                logger.info("Not switching to parked mode - critical services active")

        elif suggested_mode == "drive":
            # Always allow switching to drive mode
            self._set_mode("drive")

        elif suggested_mode == "night":
            # Night mode only when driving and it's actually night
            if self.vehicle_state["moving"] and self.vehicle_state["night_mode_active"]:
                self._set_mode("night")
            else:
                logger.debug("Night mode conditions not met")

        else:
            logger.warning(f"Unknown suggested mode: {suggested_mode}")

    def _health_monitor_loop(self):
        """Monitor service health by periodically checking status"""
        while self.running:
            current_time = time.time()

            if current_time - self.last_health_check >= self.health_check_interval:
                self._perform_health_checks()
                self.last_health_check = current_time

            time.sleep(5)  # Check every 5 seconds

    def _perform_health_checks(self):
        """Perform health checks on all services"""
        # This is a simplified health check - in a real system,
        # you might ping services or check their last activity

        # For now, assume services are running unless we get error indications
        # In a production system, this would involve actual health checks

        logger.debug("Performing service health checks...")

        # Reset unknown services to running (optimistic assumption)
        for service_name in self.service_states:
            if self.service_states[service_name] == ServiceState.UNKNOWN:
                self._update_service_state(service_name, ServiceState.RUNNING)

    def _set_ai_state(self, state: str):
        """Set AI state and update LEDs"""
        self.ai_state = state
        self.last_ai_state_time = time.time()

        if not self.led_controller:
            return

        if state == "listening":
            self.led_controller.ai_listening(priority=2)
        elif state == "speaking":
            self.led_controller.ai_speaking(priority=2)
        elif state == "thinking":
            self.led_controller.ai_thinking(priority=3)
        elif state == "recording":
            self.led_controller.ai_recording(priority=1)
        elif state == "error":
            self.led_controller.ai_error(priority=1)
        else:  # idle
            self.led_controller.ai_idle()

    def _set_mode(self, mode: str):
        """Set system mode and update LEDs"""
        if mode not in ["drive", "parked", "night", "service"]:
            logger.warning(f"Unknown mode: {mode}")
            return

        self.current_mode = mode
        logger.info(f"Mode changed to: {mode}")

        if not self.led_controller:
            return

        if mode == "drive":
            self.led_controller.set_mode_drive()
        elif mode == "parked":
            self.led_controller.set_mode_parked()
        elif mode == "night":
            self.led_controller.set_mode_night()
        elif mode == "service":
            self.led_controller.set_mode_service()

    def _send_error(self, request_id: Optional[str], error: str):
        """Send error response"""
        response = {
            "type": "ERROR",
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
        self.broker_socket.send_json(response)


def main():
    """Main entry point for LED Monitor Service"""
    import argparse

    parser = argparse.ArgumentParser(description="MIA LED Monitor Service")
    parser.add_argument(
        "--broker-url",
        type=str,
        default="tcp://localhost:5555",
        help="ZeroMQ broker URL (default: tcp://localhost:5555)"
    )
    parser.add_argument(
        "--telemetry-url",
        type=str,
        default="tcp://localhost:5556",
        help="Telemetry PUB URL (default: tcp://localhost:5556)"
    )
    parser.add_argument(
        "--led-port",
        type=str,
        default="/dev/ttyUSB0",
        help="LED controller serial port (default: /dev/ttyUSB0)"
    )

    args = parser.parse_args()

    service = LEDMonitorService(
        broker_url=args.broker_url,
        telemetry_url=args.telemetry_url,
        led_port=args.led_port
    )

    try:
        if service.start():
            logger.info("LED Monitor Service running. Press Ctrl+C to stop.")
            while service.running:
                time.sleep(1)
        else:
            logger.error("Failed to start LED Monitor Service")
    except KeyboardInterrupt:
        logger.info("Shutting down LED Monitor Service...")
        service.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception(e)
        service.stop()


if __name__ == "__main__":
    main()