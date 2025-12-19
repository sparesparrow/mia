"""
USB Camera Driver - Video Streaming Hardware Control
Implements USB camera detection, configuration, and video streaming capabilities
Supports Generalplus and other UVC-compliant USB cameras for MIA system video streaming
"""
import cv2
import json
import logging
import time
import threading
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import zmq
import numpy as np

# Try to import FlatBuffers bindings for video streaming
try:
    import Mia.VideoStreamStart as VideoStreamStart
    import Mia.VideoStreamData as VideoStreamData
    import Mia.VideoStreamStop as VideoStreamStop
    import Mia.VideoStreamStatus as VideoStreamStatus
    import Mia.VideoStreamConfig as VideoStreamConfig
    FLATBUFFERS_AVAILABLE = True
except ImportError:
    VideoStreamStart = None
    VideoStreamData = None
    VideoStreamStop = None
    VideoStreamStatus = None
    VideoStreamConfig = None
    FLATBUFFERS_AVAILABLE = False
    logging.warning("Video streaming FlatBuffers bindings not available. Using JSON messages only.")

# Try to import MQTT client for streaming
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logging.warning("MQTT client not available. Video streaming will use ZeroMQ only.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class USBCameraDriver:
    """
    USB Camera Driver for video streaming
    Handles camera detection, configuration, and video capture/streaming
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

        # Camera management
        self.cameras: Dict[str, Dict] = {}  # camera_id -> camera_info
        self.active_streams: Dict[str, Dict] = {}  # session_id -> stream_info
        self.capture_threads: Dict[str, threading.Thread] = {}

        # MQTT client for streaming
        self.mqtt_client = None
        self._init_mqtt()

        # Video encoding settings
        self.default_config = {
            'width': 1280,
            'height': 720,
            'fps': 30,
            'codec': 'MJPEG',  # MJPEG for compatibility, H.264 for efficiency
            'bitrate': 2000000,  # 2 Mbps
            'keyframe_interval': 30
        }

    def _init_mqtt(self):
        """Initialize MQTT client for video streaming"""
        if not MQTT_AVAILABLE:
            return

        try:
            self.mqtt_client = mqtt.Client(client_id=f"usb_camera_{id(self)}")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"MQTT client connected to {self.mqtt_broker}:{self.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to initialize MQTT client: {e}")
            self.mqtt_client = None

    def _detect_cameras(self) -> List[Dict]:
        """Detect available USB cameras"""
        cameras = []

        # Try to detect cameras using OpenCV
        for i in range(10):  # Check first 10 camera indices
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Get camera properties
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)

                    camera_info = {
                        'camera_id': f'usb_camera_{i}',
                        'device_index': i,
                        'name': f'USB Camera {i}',
                        'capabilities': {
                            'width': width,
                            'height': height,
                            'fps': fps,
                            'formats': ['MJPEG', 'YUYV']  # Common UVC formats
                        },
                        'status': 'available'
                    }

                    # Try to identify camera model (Generalplus specific)
                    try:
                        # Get camera name if available
                        name = cap.get(cv2.CAP_PROP_BACKEND_NAME) or f'Camera {i}'
                        camera_info['name'] = name
                    except:
                        pass

                    cameras.append(camera_info)
                    cap.release()
                else:
                    cap.release()
                    break  # Stop at first unavailable camera
            except Exception as e:
                logger.debug(f"Error checking camera {i}: {e}")
                break

        logger.info(f"Detected {len(cameras)} USB cameras")
        return cameras

    def _get_camera_capabilities(self, camera_id: str) -> Optional[Dict]:
        """Get detailed capabilities for a specific camera"""
        if camera_id not in self.cameras:
            return None

        camera_info = self.cameras[camera_id]
        device_index = camera_info['device_index']

        try:
            cap = cv2.VideoCapture(device_index)
            if not cap.isOpened():
                return None

            # Get supported resolutions and frame rates
            capabilities = {
                'resolutions': [],
                'frame_rates': [],
                'codecs': ['MJPEG', 'H264'] if self._supports_h264(cap) else ['MJPEG']
            }

            # Common resolutions to test
            test_resolutions = [
                (1920, 1080), (1280, 720), (1024, 768),
                (800, 600), (640, 480), (320, 240)
            ]

            for width, height in test_resolutions:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                if actual_width == width and actual_height == height:
                    capabilities['resolutions'].append((width, height))

            # Test frame rates
            test_fps = [30, 25, 20, 15, 10, 5]
            for fps in test_fps:
                cap.set(cv2.CAP_PROP_FPS, fps)
                actual_fps = cap.get(cv2.CAP_PROP_FPS)
                if abs(actual_fps - fps) < 1.0:  # Close enough
                    capabilities['frame_rates'].append(fps)

            cap.release()
            return capabilities

        except Exception as e:
            logger.error(f"Error getting capabilities for camera {camera_id}: {e}")
            return None

    def _supports_h264(self, cap) -> bool:
        """Check if camera supports H.264 encoding"""
        # This is a simplified check - in practice, you'd need to query UVC controls
        # or check camera model against known H.264 capable devices
        try:
            # Try to set H.264 related properties
            fourcc = cap.get(cv2.CAP_PROP_FOURCC)
            codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            return 'H264' in codec or 'AVC1' in codec
        except:
            return False

    def _start_video_stream(self, session_id: str, camera_id: str, config: Dict) -> bool:
        """Start video streaming for a camera"""
        if camera_id not in self.cameras:
            logger.error(f"Camera {camera_id} not found")
            return False

        if session_id in self.active_streams:
            logger.warning(f"Stream {session_id} already active")
            return False

        camera_info = self.cameras[camera_id]
        device_index = camera_info['device_index']

        try:
            # Open camera with specified configuration
            cap = cv2.VideoCapture(device_index)

            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_id}")
                return False

            # Configure camera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.get('width', self.default_config['width']))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.get('height', self.default_config['height']))
            cap.set(cv2.CAP_PROP_FPS, config.get('fps', self.default_config['fps']))

            # Verify settings were applied
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = cap.get(cv2.CAP_PROP_FPS)

            logger.info(f"Camera {camera_id} configured: {actual_width}x{actual_height}@{actual_fps}fps")

            # Store stream information
            self.active_streams[session_id] = {
                'camera_id': camera_id,
                'config': config,
                'capture': cap,
                'frame_count': 0,
                'start_time': time.time(),
                'last_frame_time': 0,
                'thread': None
            }

            # Start capture thread
            thread = threading.Thread(target=self._capture_thread, args=(session_id,))
            thread.daemon = True
            self.capture_threads[session_id] = thread
            thread.start()

            logger.info(f"Started video stream {session_id} for camera {camera_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start stream {session_id}: {e}")
            return False

    def _capture_thread(self, session_id: str):
        """Background thread for video frame capture and streaming"""
        if session_id not in self.active_streams:
            return

        stream_info = self.active_streams[session_id]
        cap = stream_info['capture']
        config = stream_info['config']
        frame_interval = 1.0 / config.get('fps', 30)

        logger.info(f"Capture thread started for stream {session_id}")

        try:
            while session_id in self.active_streams and self.running:
                current_time = time.time()

                # Maintain frame rate
                if current_time - stream_info['last_frame_time'] < frame_interval:
                    time.sleep(0.001)  # Small sleep to prevent busy waiting
                    continue

                # Capture frame
                ret, frame = cap.read()
                if not ret:
                    logger.error(f"Failed to capture frame for stream {session_id}")
                    break

                # Process and stream frame
                stream_info['frame_count'] += 1
                stream_info['last_frame_time'] = current_time

                # Encode frame based on codec
                codec = config.get('codec', 'MJPEG').upper()
                if codec == 'MJPEG':
                    encoded_frame = self._encode_mjpeg(frame)
                elif codec == 'H264':
                    encoded_frame = self._encode_h264(frame)
                else:
                    encoded_frame = self._encode_mjpeg(frame)  # Fallback

                if encoded_frame:
                    self._send_video_frame(session_id, encoded_frame, stream_info['frame_count'], current_time)

        except Exception as e:
            logger.error(f"Error in capture thread for {session_id}: {e}")
        finally:
            # Cleanup
            if cap.isOpened():
                cap.release()

            # Remove from active streams
            if session_id in self.active_streams:
                del self.active_streams[session_id]

            if session_id in self.capture_threads:
                del self.capture_threads[session_id]

            logger.info(f"Capture thread ended for stream {session_id}")

    def _encode_mjpeg(self, frame: np.ndarray) -> Optional[bytes]:
        """Encode frame as MJPEG"""
        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]  # 80% quality
            ret, encoded_img = cv2.imencode('.jpg', frame, encode_param)
            if ret:
                return encoded_img.tobytes()
        except Exception as e:
            logger.error(f"MJPEG encoding error: {e}")
        return None

    def _encode_h264(self, frame: np.ndarray) -> Optional[bytes]:
        """Encode frame as H.264 (placeholder - would need proper H.264 encoder)"""
        # For now, fallback to MJPEG. Real H.264 would require:
        # - OpenCV with ffmpeg/gstreamer backend
        # - Hardware acceleration (if available)
        # - Proper H.264 encoder setup
        logger.warning("H.264 encoding not implemented, falling back to MJPEG")
        return self._encode_mjpeg(frame)

    def _send_video_frame(self, session_id: str, frame_data: bytes, frame_number: int, timestamp: float):
        """Send video frame via MQTT or ZeroMQ"""
        try:
            # Create video frame message
            if FLATBUFFERS_AVAILABLE and VideoStreamData:
                # FlatBuffers message
                import flatbuffers
                builder = flatbuffers.Builder(1024 + len(frame_data))

                session_id_str = builder.CreateString(session_id)
                video_data_vec = builder.CreateByteVector(frame_data)

                VideoStreamData.VideoStreamDataStart(builder)
                VideoStreamData.VideoStreamDataAddSessionId(builder, session_id_str)
                VideoStreamData.VideoStreamDataAddSequenceNumber(builder, frame_number)
                VideoStreamData.VideoStreamDataAddFrameNumber(builder, frame_number)
                VideoStreamData.VideoStreamDataAddVideoData(builder, video_data_vec)
                VideoStreamData.VideoStreamDataAddTimestamp(builder, int(timestamp * 1000000))
                VideoStreamData.VideoStreamDataAddKeyframe(builder, (frame_number % 30) == 0)  # Every 30 frames
                VideoStreamData.VideoStreamDataAddEndOfStream(builder, False)
                fb_message = VideoStreamData.VideoStreamDataEnd(builder)
                builder.Finish(fb_message)

                message_data = builder.Output()
                message_type = b"VIDEO_STREAM_DATA"
            else:
                # JSON message
                message = {
                    "type": "VIDEO_STREAM_DATA",
                    "session_id": session_id,
                    "sequence_number": frame_number,
                    "frame_number": frame_number,
                    "video_data": frame_data.hex(),  # Base64 would be better but hex for simplicity
                    "timestamp": timestamp,
                    "keyframe": (frame_number % 30) == 0,
                    "end_of_stream": False
                }
                message_data = json.dumps(message).encode('utf-8')
                message_type = b"VIDEO_STREAM_DATA_JSON"

            # Send via MQTT if available, otherwise ZeroMQ
            if self.mqtt_client and MQTT_AVAILABLE:
                topic = f"mia/video/{session_id}/frame"
                self.mqtt_client.publish(topic, message_data, qos=1)
            else:
                # Send via ZeroMQ socket
                if self.socket:
                    self.socket.send(message_type, zmq.SNDMORE)
                    self.socket.send(message_data)

        except Exception as e:
            logger.error(f"Error sending video frame: {e}")

    def _stop_video_stream(self, session_id: str) -> bool:
        """Stop video streaming"""
        if session_id not in self.active_streams:
            logger.warning(f"Stream {session_id} not active")
            return False

        try:
            # Stop capture thread
            if session_id in self.capture_threads:
                thread = self.capture_threads[session_id]
                # Thread will stop naturally when stream is removed
                thread.join(timeout=1.0)

            # Clean up stream resources
            stream_info = self.active_streams[session_id]
            cap = stream_info.get('capture')
            if cap and cap.isOpened():
                cap.release()

            del self.active_streams[session_id]

            logger.info(f"Stopped video stream {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping stream {session_id}: {e}")
            return False

    def start(self):
        """Start the USB camera driver"""
        self.socket = self.context.socket(zmq.DEALER)
        worker_id = f"usb_camera_driver_{id(self)}"
        self.socket.setsockopt_string(zmq.IDENTITY, worker_id)
        self.socket.connect(self.broker_url)

        self.running = True
        logger.info(f"USB Camera Driver started, connected to {self.broker_url}")

        # Detect available cameras
        detected_cameras = self._detect_cameras()
        for camera in detected_cameras:
            self.cameras[camera['camera_id']] = camera

        # Register with broker
        self._register_driver()

        # Start message loop
        self._message_loop()

        return True

    def stop(self):
        """Stop the USB camera driver"""
        self.running = False

        # Stop all active streams
        active_session_ids = list(self.active_streams.keys())
        for session_id in active_session_ids:
            self._stop_video_stream(session_id)

        # Stop MQTT client
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

        # Close ZeroMQ socket
        if self.socket:
            self.socket.close()
        self.context.term()

        logger.info("USB Camera Driver stopped")

    def _register_driver(self):
        """Register this driver with the broker"""
        capabilities = ["VIDEO_STREAM_START", "VIDEO_STREAM_STOP", "VIDEO_STREAM_STATUS", "CAMERA_LIST", "CAMERA_CAPABILITIES"]

        message = {
            "type": "WORKER_REGISTER",
            "worker_type": "USB_CAMERA",
            "capabilities": capabilities,
            "cameras": list(self.cameras.keys()),
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

                    if len(message_parts) >= 2:
                        message_type = message_parts[0].decode('utf-8')
                        payload = message_parts[1]

                        message = self._parse_message(message_type, payload)
                        if message:
                            self._handle_message(message_type, message)

            except zmq.ZMQError as e:
                if self.running:
                    logger.error(f"ZMQ error: {e}")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                time.sleep(0.1)

    def _parse_message(self, message_type: str, payload: bytes):
        """Parse message payload"""
        # Try FlatBuffers first, then JSON
        if FLATBUFFERS_AVAILABLE:
            try:
                if message_type == "VIDEO_STREAM_START" and VideoStreamStart:
                    fb_message = VideoStreamStart.VideoStreamStart.GetRootAs(payload, 0)
                    config_fb = fb_message.Config()

                    return {
                        "type": message_type,
                        "session_id": fb_message.SessionId().decode('utf-8'),
                        "camera_id": fb_message.CameraId().decode('utf-8'),
                        "config": {
                            "width": config_fb.Width(),
                            "height": config_fb.Height(),
                            "frame_rate": config_fb.FrameRate(),
                            "codec": config_fb.Codec().decode('utf-8'),
                            "bitrate_kbps": config_fb.BitrateKbps(),
                            "keyframe_interval": config_fb.KeyframeInterval()
                        },
                        "format": "flatbuffers"
                    }
                elif message_type == "VIDEO_STREAM_STOP" and VideoStreamStop:
                    fb_message = VideoStreamStop.VideoStreamStop.GetRootAs(payload, 0)
                    return {
                        "type": message_type,
                        "session_id": fb_message.SessionId().decode('utf-8'),
                        "reason": fb_message.Reason().decode('utf-8'),
                        "format": "flatbuffers"
                    }
            except Exception as e:
                logger.debug(f"FlatBuffers parsing failed for {message_type}: {e}")

        # Fallback to JSON
        try:
            message = json.loads(payload.decode('utf-8'))
            message["format"] = "json"
            return message
        except json.JSONDecodeError:
            logger.error(f"Failed to parse message as JSON: {message_type}")
            return None

    def _handle_message(self, message_type: str, message: Dict):
        """Handle incoming message"""
        self._current_request_id = message.get("request_id")
        self._current_format = message.get("format", "json")

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
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling {message_type}: {e}")
            self._send_error(str(e))

    def _handle_stream_start(self, message: Dict):
        """Handle video stream start request"""
        session_id = message.get("session_id")
        camera_id = message.get("camera_id")
        config = message.get("config", self.default_config)

        if not session_id or not camera_id:
            self._send_error("Missing session_id or camera_id")
            return

        # Merge with default config
        stream_config = {**self.default_config, **config}

        if self._start_video_stream(session_id, camera_id, stream_config):
            self._send_stream_response("VIDEO_STREAM_START", session_id, True, "Stream started")
        else:
            self._send_stream_response("VIDEO_STREAM_START", session_id, False, "Failed to start stream")

    def _handle_stream_stop(self, message: Dict):
        """Handle video stream stop request"""
        session_id = message.get("session_id")
        reason = message.get("reason", "user_request")

        if not session_id:
            self._send_error("Missing session_id")
            return

        if self._stop_video_stream(session_id):
            self._send_stream_response("VIDEO_STREAM_STOP", session_id, True, f"Stream stopped: {reason}")
        else:
            self._send_stream_response("VIDEO_STREAM_STOP", session_id, False, "Failed to stop stream")

    def _handle_stream_status(self, message: Dict):
        """Handle stream status request"""
        session_id = message.get("session_id")

        if session_id and session_id in self.active_streams:
            stream_info = self.active_streams[session_id]
            status_info = {
                "session_id": session_id,
                "status": "active",
                "frames_sent": stream_info["frame_count"],
                "bytes_sent": 0,  # Would need to track this
                "avg_fps": stream_info["frame_count"] / max(1, time.time() - stream_info["start_time"]),
                "error_message": ""
            }
        else:
            status_info = {
                "session_id": session_id or "unknown",
                "status": "inactive",
                "frames_sent": 0,
                "bytes_sent": 0,
                "avg_fps": 0.0,
                "error_message": "Stream not found" if session_id else "No session specified"
            }

        self._send_stream_status(status_info)

    def _handle_camera_list(self, message: Dict):
        """Handle camera list request"""
        camera_list = []
        for camera_id, camera_info in self.cameras.items():
            camera_list.append({
                "camera_id": camera_id,
                "name": camera_info.get("name", camera_id),
                "status": camera_info.get("status", "unknown"),
                "capabilities": camera_info.get("capabilities", {})
            })

        response = {
            "type": "CAMERA_LIST_RESPONSE",
            "cameras": camera_list,
            "count": len(camera_list),
            "timestamp": datetime.now().isoformat(),
            "request_id": self._current_request_id
        }
        self.socket.send_json(response)

    def _handle_camera_capabilities(self, message: Dict):
        """Handle camera capabilities request"""
        camera_id = message.get("camera_id")

        if not camera_id:
            self._send_error("Missing camera_id")
            return

        capabilities = self._get_camera_capabilities(camera_id)

        response = {
            "type": "CAMERA_CAPABILITIES_RESPONSE",
            "camera_id": camera_id,
            "capabilities": capabilities,
            "timestamp": datetime.now().isoformat(),
            "request_id": self._current_request_id
        }
        self.socket.send_json(response)

    def _send_stream_response(self, response_type: str, session_id: str, success: bool, message: str):
        """Send stream operation response"""
        if self._current_format == "flatbuffers" and VideoStreamStop:
            # Would implement FlatBuffers response here
            pass
        else:
            response = {
                "type": f"{response_type}_RESPONSE",
                "session_id": session_id,
                "success": success,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "request_id": self._current_request_id
            }
            self.socket.send_json(response)

    def _send_stream_status(self, status_info: Dict):
        """Send stream status response"""
        if self._current_format == "flatbuffers" and VideoStreamStatus:
            # Would implement FlatBuffers status here
            pass
        else:
            response = {
                "type": "VIDEO_STREAM_STATUS_RESPONSE",
                **status_info,
                "timestamp": datetime.now().isoformat(),
                "request_id": self._current_request_id
            }
            self.socket.send_json(response)

    def _send_error(self, error: str):
        """Send error response"""
        response = {
            "type": "ERROR",
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "request_id": getattr(self, "_current_request_id", None)
        }
        self.socket.send_json(response)


def main():
    """Main entry point for USB camera driver"""
    driver = USBCameraDriver()

    try:
        driver.start()
    except KeyboardInterrupt:
        logger.info("Shutting down USB camera driver...")
        driver.stop()


if __name__ == "__main__":
    main()