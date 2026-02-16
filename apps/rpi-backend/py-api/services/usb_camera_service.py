"""
USB Camera Service - Video Streaming Coordination
Implements video streaming service for MIA system

This service coordinates between the USB camera driver and the broader MIA system:
- Manages camera discovery and enumeration
- Handles video stream lifecycle (start/stop/status)
- Coordinates with video streaming server for data routing
- Provides camera diagnostics and health monitoring
- Handles camera hotplug/unplug events
"""
import sys
import os
import json
import logging
import threading
import time
import subprocess
from typing import Dict, Optional, List
from datetime import datetime
import zmq

# Try to import MQTT client for streaming coordination
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logging.warning("MQTT client not available. Camera service will use ZeroMQ only.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class USBCameraService:
    """
    USB Camera Service for coordinating video streaming operations
    """

    def __init__(self, broker_url: str = "tcp://localhost:5555",
                 mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.broker_url = broker_url
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port

        # ZeroMQ setup
        self.context = zmq.Context()
        self.socket = None
        self.running = False

        # MQTT client for coordination
        self.mqtt_client = None

        # Camera and stream management
        self.available_cameras: Dict[str, Dict] = {}
        self.active_streams: Dict[str, Dict] = {}
        self.camera_health: Dict[str, Dict] = {}

        # Driver process management
        self.driver_process = None
        self.driver_monitor_thread = None

        # Health monitoring
        self.health_check_interval = 30  # seconds
        self.last_health_check = 0

    def _init_mqtt(self):
        """Initialize MQTT client for coordination"""
        if not MQTT_AVAILABLE:
            return

        try:
            self.mqtt_client = mqtt.Client(client_id=f"usb_camera_service_{id(self)}")
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.subscribe("mia/camera/#")
            self.mqtt_client.loop_start()
            logger.info(f"MQTT client connected to {self.mqtt_broker}:{self.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to initialize MQTT client: {e}")
            self.mqtt_client = None

    def _on_mqtt_message(self, client, userdata, message):
        """Handle incoming MQTT messages"""
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')

            logger.debug(f"MQTT message: {topic} -> {payload}")

            # Handle camera status updates
            if topic.startswith("mia/camera/") and topic.endswith("/status"):
                camera_id = topic.split("/")[2]
                status_data = json.loads(payload)
                self._update_camera_status(camera_id, status_data)

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _update_camera_status(self, camera_id: str, status_data: Dict):
        """Update camera status from MQTT messages"""
        self.camera_health[camera_id] = {
            **status_data,
            "last_update": time.time(),
            "timestamp": datetime.now().isoformat()
        }

        # Update available cameras if this is a new camera
        if camera_id not in self.available_cameras:
            self.available_cameras[camera_id] = {
                "camera_id": camera_id,
                "status": "detected",
                "last_seen": time.time(),
                "capabilities": status_data.get("capabilities", {})
            }
            logger.info(f"New camera detected: {camera_id}")

    def _start_camera_driver(self) -> bool:
        """Start the USB camera driver process"""
        try:
            driver_path = os.path.join(os.path.dirname(__file__), "..", "..", "hardware", "usb_camera_driver.py")

            if not os.path.exists(driver_path):
                logger.error(f"Camera driver not found at {driver_path}")
                return False

            # Start driver as subprocess
            env = os.environ.copy()
            env["PYTHONPATH"] = "/home/mia/projects/mia"  # Adjust path as needed

            self.driver_process = subprocess.Popen(
                [sys.executable, driver_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=os.path.dirname(driver_path)
            )

            logger.info(f"Started camera driver process (PID: {self.driver_process.pid})")

            # Start driver monitor thread
            self.driver_monitor_thread = threading.Thread(target=self._monitor_driver_process)
            self.driver_monitor_thread.daemon = True
            self.driver_monitor_thread.start()

            return True

        except Exception as e:
            logger.error(f"Failed to start camera driver: {e}")
            return False

    def _monitor_driver_process(self):
        """Monitor the camera driver process and restart if necessary"""
        while self.running:
            if self.driver_process:
                return_code = self.driver_process.poll()
                if return_code is not None:
                    logger.warning(f"Camera driver process exited with code {return_code}")

                    # Read any error output
                    if self.driver_process.stderr:
                        error_output = self.driver_process.stderr.read().decode('utf-8')
                        if error_output:
                            logger.error(f"Driver stderr: {error_output}")

                    # Attempt restart after delay
                    if self.running:
                        logger.info("Attempting to restart camera driver...")
                        time.sleep(5)
                        self._start_camera_driver()
                else:
                    # Process is still running
                    time.sleep(1)
            else:
                time.sleep(1)

    def _stop_camera_driver(self):
        """Stop the camera driver process"""
        if self.driver_process:
            try:
                self.driver_process.terminate()
                self.driver_process.wait(timeout=10)
                logger.info("Camera driver process terminated")
            except subprocess.TimeoutExpired:
                logger.warning("Camera driver process didn't terminate gracefully, killing...")
                self.driver_process.kill()
            except Exception as e:
                logger.error(f"Error stopping camera driver: {e}")

        self.driver_process = None

    def _perform_health_check(self):
        """Perform periodic health checks on cameras and streams"""
        current_time = time.time()

        if current_time - self.last_health_check < self.health_check_interval:
            return

        self.last_health_check = current_time

        # Check camera health
        for camera_id, camera_info in self.available_cameras.items():
            if current_time - camera_info.get("last_seen", 0) > 60:  # 1 minute timeout
                logger.warning(f"Camera {camera_id} appears offline")
                camera_info["status"] = "offline"

        # Check stream health
        for session_id, stream_info in self.active_streams.items():
            if current_time - stream_info.get("last_frame_time", 0) > 10:  # 10 second timeout
                logger.warning(f"Stream {session_id} appears stalled")

                # Send stream status check request
                self._request_stream_status(session_id)

        # Publish health summary via MQTT
        if self.mqtt_client and MQTT_AVAILABLE:
            health_summary = {
                "service": "usb_camera_service",
                "status": "healthy",
                "cameras": len(self.available_cameras),
                "active_streams": len(self.active_streams),
                "timestamp": datetime.now().isoformat()
            }

            self.mqtt_client.publish("mia/camera/service/health", json.dumps(health_summary), qos=1)

    def _request_stream_status(self, session_id: str):
        """Request status update for a specific stream"""
        request = {
            "type": "VIDEO_STREAM_STATUS",
            "session_id": session_id,
            "request_id": f"health_check_{int(time.time())}",
            "timestamp": datetime.now().isoformat()
        }

        if self.socket:
            self.socket.send_json(request)

    def start(self):
        """Start the USB camera service"""
        self.socket = self.context.socket(zmq.DEALER)
        service_id = f"usb_camera_service_{id(self)}"
        self.socket.setsockopt_string(zmq.IDENTITY, service_id)
        self.socket.connect(self.broker_url)

        self.running = True
        logger.info(f"USB Camera Service started, connected to {self.broker_url}")

        # Initialize MQTT
        self._init_mqtt()

        # Start camera driver
        if not self._start_camera_driver():
            logger.error("Failed to start camera driver, service may not function properly")

        # Register with broker
        self._register_service()

        # Start message processing loop
        self._message_loop()

        return True

    def stop(self):
        """Stop the USB camera service"""
        self.running = False

        # Stop all active streams
        for session_id in list(self.active_streams.keys()):
            self._stop_stream(session_id)

        # Stop camera driver
        self._stop_camera_driver()

        # Stop MQTT client
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

        # Close ZeroMQ socket
        if self.socket:
            self.socket.close()
        self.context.term()

        logger.info("USB Camera Service stopped")

    def _register_service(self):
        """Register this service with the broker"""
        capabilities = [
            "VIDEO_STREAM_START", "VIDEO_STREAM_STOP", "VIDEO_STREAM_STATUS",
            "CAMERA_LIST", "CAMERA_CAPABILITIES", "CAMERA_HEALTH"
        ]

        message = {
            "type": "SERVICE_REGISTER",
            "service_type": "USB_CAMERA",
            "capabilities": capabilities,
            "service_id": "usb_camera_service",
            "timestamp": datetime.now().isoformat()
        }
        self.socket.send_json(message)

    def _message_loop(self):
        """Main message processing loop"""
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(1000))  # 1 second timeout

                if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                    message_parts = self.socket.recv_multipart()

                    if len(message_parts) >= 1:
                        try:
                            message = json.loads(message_parts[0].decode('utf-8'))
                            message_type = message.get("type", "UNKNOWN")
                            self._handle_message(message_type, message)
                        except json.JSONDecodeError:
                            logger.error("Failed to parse JSON message")

                # Perform periodic health checks
                self._perform_health_check()

            except zmq.ZMQError as e:
                if self.running:
                    logger.error(f"ZMQ error: {e}")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                time.sleep(0.1)

    def _handle_message(self, message_type: str, message: Dict):
        """Handle incoming message"""
        try:
            if message_type == "VIDEO_STREAM_START":
                self._handle_stream_start(message)
            elif message_type == "VIDEO_STREAM_STOP":
                self._handle_stream_stop(message)
            elif message_type == "VIDEO_STREAM_STATUS":
                self._handle_stream_status(message)
            elif message_type == "CAMERA_LIST":
                self._handle_camera_list(message)
            elif message_type == "CAMERA_CAPABILITIES":
                self._handle_camera_capabilities(message)
            elif message_type == "CAMERA_HEALTH":
                self._handle_camera_health(message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling {message_type}: {e}")
            self._send_error_response(message, str(e))

    def _handle_stream_start(self, message: Dict):
        """Handle video stream start request"""
        session_id = message.get("session_id")
        camera_id = message.get("camera_id")
        config = message.get("config", {})

        if not session_id or not camera_id:
            self._send_error_response(message, "Missing session_id or camera_id")
            return

        # Forward request to camera driver
        driver_request = {
            "type": "VIDEO_STREAM_START",
            "session_id": session_id,
            "camera_id": camera_id,
            "config": config,
            "request_id": message.get("request_id"),
            "timestamp": datetime.now().isoformat()
        }

        # Send to driver (could be via ZeroMQ routing or direct communication)
        # For now, assume driver is registered as a worker
        self.socket.send_json(driver_request)

        # Track the stream locally
        self.active_streams[session_id] = {
            "camera_id": camera_id,
            "config": config,
            "start_time": time.time(),
            "last_frame_time": 0,
            "status": "starting"
        }

        logger.info(f"Requested stream start: {session_id} for camera {camera_id}")

    def _handle_stream_stop(self, message: Dict):
        """Handle video stream stop request"""
        session_id = message.get("session_id")
        reason = message.get("reason", "user_request")

        if not session_id:
            self._send_error_response(message, "Missing session_id")
            return

        # Forward request to camera driver
        driver_request = {
            "type": "VIDEO_STREAM_STOP",
            "session_id": session_id,
            "reason": reason,
            "request_id": message.get("request_id"),
            "timestamp": datetime.now().isoformat()
        }

        self.socket.send_json(driver_request)
        self._stop_stream(session_id)

        logger.info(f"Requested stream stop: {session_id} ({reason})")

    def _stop_stream(self, session_id: str):
        """Stop tracking a stream locally"""
        if session_id in self.active_streams:
            del self.active_streams[session_id]

    def _handle_stream_status(self, message: Dict):
        """Handle stream status request"""
        session_id = message.get("session_id")

        if session_id and session_id in self.active_streams:
            stream_info = self.active_streams[session_id]

            # Update last frame time if we have recent activity
            if "last_frame_time" in stream_info:
                stream_info["last_frame_time"] = time.time()

            status_response = {
                "type": "VIDEO_STREAM_STATUS_RESPONSE",
                "session_id": session_id,
                "status": stream_info.get("status", "unknown"),
                "frames_sent": stream_info.get("frames_sent", 0),
                "bytes_sent": stream_info.get("bytes_sent", 0),
                "avg_fps": stream_info.get("avg_fps", 0.0),
                "uptime": time.time() - stream_info.get("start_time", time.time()),
                "error_message": stream_info.get("error_message", ""),
                "request_id": message.get("request_id"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            status_response = {
                "type": "VIDEO_STREAM_STATUS_RESPONSE",
                "session_id": session_id or "unknown",
                "status": "not_found",
                "error_message": "Stream not found",
                "request_id": message.get("request_id"),
                "timestamp": datetime.now().isoformat()
            }

        self.socket.send_json(status_response)

    def _handle_camera_list(self, message: Dict):
        """Handle camera list request"""
        camera_list = []
        for camera_id, camera_info in self.available_cameras.items():
            camera_list.append({
                "camera_id": camera_id,
                "name": camera_info.get("name", camera_id),
                "status": camera_info.get("status", "unknown"),
                "capabilities": camera_info.get("capabilities", {}),
                "last_seen": datetime.fromtimestamp(camera_info.get("last_seen", 0)).isoformat()
            })

        response = {
            "type": "CAMERA_LIST_RESPONSE",
            "cameras": camera_list,
            "count": len(camera_list),
            "timestamp": datetime.now().isoformat(),
            "request_id": message.get("request_id")
        }
        self.socket.send_json(response)

    def _handle_camera_capabilities(self, message: Dict):
        """Handle camera capabilities request"""
        camera_id = message.get("camera_id")

        if not camera_id or camera_id not in self.available_cameras:
            self._send_error_response(message, f"Camera {camera_id} not found")
            return

        camera_info = self.available_cameras[camera_id]
        capabilities = camera_info.get("capabilities", {})

        # Request updated capabilities from driver
        driver_request = {
            "type": "CAMERA_CAPABILITIES",
            "camera_id": camera_id,
            "request_id": message.get("request_id"),
            "timestamp": datetime.now().isoformat()
        }
        self.socket.send_json(driver_request)

    def _handle_camera_health(self, message: Dict):
        """Handle camera health request"""
        health_report = {
            "service_status": "healthy" if self.driver_process and self.driver_process.poll() is None else "degraded",
            "driver_running": self.driver_process is not None and self.driver_process.poll() is None,
            "cameras_available": len(self.available_cameras),
            "active_streams": len(self.active_streams),
            "camera_health": self.camera_health,
            "timestamp": datetime.now().isoformat(),
            "request_id": message.get("request_id")
        }

        response = {
            "type": "CAMERA_HEALTH_RESPONSE",
            **health_report
        }
        self.socket.send_json(response)

    def _send_error_response(self, original_message: Dict, error: str):
        """Send error response"""
        response = {
            "type": "ERROR",
            "error": error,
            "original_type": original_message.get("type"),
            "request_id": original_message.get("request_id"),
            "timestamp": datetime.now().isoformat()
        }
        self.socket.send_json(response)


def main():
    """Main entry point for USB camera service"""
    service = USBCameraService()

    try:
        service.start()
    except KeyboardInterrupt:
        logger.info("Shutting down USB camera service...")
        service.stop()


if __name__ == "__main__":
    main()