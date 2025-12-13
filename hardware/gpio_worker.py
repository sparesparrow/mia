"""
GPIO Worker - Hardware Control
Implements Phase 2.2: GPIO Control & Sensor Integration
Listens to ZeroMQ messages and controls GPIO pins
"""
import zmq
import json
import logging
import time
from typing import Dict, Optional
from datetime import datetime

# Try to import GPIO libraries
GPIO_AVAILABLE = False
USE_GPIOZERO = False

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    USE_GPIOZERO = False
except ImportError:
    try:
        import gpiozero
        GPIO_AVAILABLE = True
        USE_GPIOZERO = True
    except ImportError:
        GPIO_AVAILABLE = False
        USE_GPIOZERO = False
        logging.warning("No GPIO library available. Running in simulation mode.")

# Try to import FlatBuffers bindings
try:
    import Mia.GPIOCommand as GPIOCommand
    import Mia.GPIOResponse as GPIOResponse
    import Mia.SensorTelemetry as SensorTelemetry
    FLATBUFFERS_AVAILABLE = True
except ImportError:
    GPIOCommand = None
    GPIOResponse = None
    SensorTelemetry = None
    FLATBUFFERS_AVAILABLE = False
    logging.warning("FlatBuffers bindings not available. Using JSON messages only.")

# Try to import sensor drivers
try:
    from hardware.sensor_drivers import SensorManager, DHT11Sensor, HCSR04Sensor, BMP180Sensor, AnalogSensor
    SENSORS_AVAILABLE = True
except ImportError:
    SensorManager = None
    SENSORS_AVAILABLE = False
    logging.warning("Sensor drivers not available. Sensor functionality disabled.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPIOWorker:
    """
    GPIO Worker that controls Raspberry Pi GPIO pins
    Subscribes to ZeroMQ messages and executes GPIO commands
    """
    
    def __init__(self, broker_url: str = "tcp://localhost:5555"):
        self.broker_url = broker_url
        self.context = zmq.Context()
        self.socket = None
        self.running = False
        self.pin_states: Dict[int, Dict[str, any]] = {}  # pin -> {direction, value}

        # Sensor manager
        self.sensor_manager = None
        if SENSORS_AVAILABLE:
            self.sensor_manager = SensorManager(max_threads=2)
            logger.info("Sensor manager initialized")

        if GPIO_AVAILABLE:
            if USE_GPIOZERO:
                logger.info("Using gpiozero library")
            else:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                logger.info("Using RPi.GPIO library")
        else:
            logger.warning("Running in simulation mode - no actual GPIO control")
    
    def start(self):
        """Start the GPIO worker"""
        self.socket = self.context.socket(zmq.DEALER)
        # Generate unique worker ID
        import uuid
        worker_id = str(uuid.uuid4())
        self.socket.setsockopt_string(zmq.IDENTITY, worker_id)
        self.socket.connect(self.broker_url)
        
        self.running = True
        logger.info(f"GPIO worker started, connected to {self.broker_url}")
        
        # Register with broker
        self._register_worker()

        # Setup sensors if available
        self._setup_sensors()

        # Start message loop
        self._message_loop()
        
        return True
    
    def stop(self):
        """Stop the GPIO worker"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.context.term()
        
        if GPIO_AVAILABLE and not USE_GPIOZERO:
            GPIO.cleanup()
        
        logger.info("GPIO worker stopped")
    
    def _register_worker(self):
        """Register this worker with the broker"""
        capabilities = ["GPIO_CONFIGURE", "GPIO_SET", "GPIO_GET", "GPIO_STATUS"]

        # Add sensor capabilities if available
        if self.sensor_manager:
            capabilities.extend(["SENSOR_READ", "SENSOR_LIST", "SENSOR_CONFIG"])

        message = {
            "type": "WORKER_REGISTER",
            "worker_type": "GPIO",
            "capabilities": capabilities,
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
                    # Receive multi-part message
                    message_parts = self.socket.recv_multipart()

                    if len(message_parts) >= 2:
                        # First part is message type, second is payload
                        message_type = message_parts[0].decode('utf-8')
                        payload = message_parts[1]

                        # Try to parse as FlatBuffers first, then JSON
                        message = self._parse_message(message_type, payload)
                        if message:
                            self._handle_message(message_type, message)
                    elif len(message_parts) == 1:
                        # Legacy single-part JSON message
                        try:
                            message = json.loads(message_parts[0].decode('utf-8'))
                            message_type = message.get("type", "UNKNOWN")
                            self._handle_message(message_type, message)
                        except json.JSONDecodeError:
                            logger.error("Failed to parse JSON message")
            except zmq.ZMQError as e:
                if self.running:
                    logger.error(f"ZMQ error: {e}")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                time.sleep(0.1)

    def _parse_message(self, message_type: str, payload: bytes):
        """Parse message payload - try FlatBuffers first, then JSON"""
        # Try FlatBuffers parsing first
        if FLATBUFFERS_AVAILABLE:
            try:
                if message_type in ["GPIO_CONFIGURE", "GPIO_SET", "GPIO_GET"]:
                    if GPIOCommand:
                        fb_message = GPIOCommand.GPIOCommand.GetRootAs(payload, 0)
                        return {
                            "type": message_type,
                            "pin": fb_message.Pin(),
                            "direction": fb_message.Direction(),
                            "value": fb_message.Value(),
                            "timestamp": fb_message.Timestamp(),
                            "format": "flatbuffers"
                        }
                elif message_type == "GPIO_STATUS":
                    return {
                        "type": message_type,
                        "format": "flatbuffers"
                    }
            except Exception as e:
                logger.debug(f"FlatBuffers parsing failed for {message_type}: {e}")

        # Fallback to JSON parsing
        try:
            message = json.loads(payload.decode('utf-8'))
            message["format"] = "json"
            return message
        except json.JSONDecodeError:
            logger.error(f"Failed to parse message as JSON or FlatBuffers: {message_type}")
            return None
    
    def _handle_message(self, message_type: str, message: Dict):
        """Handle incoming message"""
        # Correlation id for broker to route responses back to clients
        self._current_request_id: Optional[str] = message.get("request_id")
        self._current_format: str = message.get("format", "json")

        try:
            if message_type == "GPIO_CONFIGURE":
                self._handle_configure(message)
            elif message_type == "GPIO_SET":
                self._handle_set(message)
            elif message_type == "GPIO_GET":
                self._handle_get(message)
            elif message_type == "GPIO_STATUS":
                self._handle_status(message)
            elif message_type == "SENSOR_READ":
                self._handle_sensor_read(message)
            elif message_type == "SENSOR_LIST":
                self._handle_sensor_list(message)
            elif message_type == "SENSOR_CONFIG":
                self._handle_sensor_config(message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling {message_type}: {e}")
            self._send_error(str(e))
    
    def _handle_configure(self, message: Dict):
        """Handle GPIO configure command"""
        pin = message.get("pin")
        direction = message.get("direction", 1)  # Default to Output (1)
        request_id = message.get("request_id")

        if pin is None:
            self._send_error("Missing pin parameter")
            return

        try:
            # Convert direction enum to string for GPIO library
            direction_str = "output"
            if hasattr(GPIOCommand, 'GPIODirection') and direction == GPIOCommand.GPIODirection_Input:
                direction_str = "input"
            elif hasattr(GPIOCommand, 'GPIODirection') and direction == GPIOCommand.GPIODirection_PWM:
                direction_str = "pwm"

            if GPIO_AVAILABLE:
                if USE_GPIOZERO:
                    # gpiozero handles configuration automatically
                    pass
                else:
                    if direction_str == "output":
                        GPIO.setup(pin, GPIO.OUT)
                    elif direction_str == "input":
                        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    else:
                        raise ValueError(f"Invalid direction: {direction_str}")

            # Store pin state
            if pin not in self.pin_states:
                self.pin_states[pin] = {}
            self.pin_states[pin]["direction"] = direction_str

            # Send response in appropriate format
            if self._current_format == "flatbuffers" and GPIOResponse:
                import flatbuffers
                builder = flatbuffers.Builder(256)

                error_msg = builder.CreateString("")  # Empty error message for success

                GPIOResponse.GPIOResponseStart(builder)
                GPIOResponse.GPIOResponseAddPin(builder, pin)
                GPIOResponse.GPIOResponseAddSuccess(builder, True)
                GPIOResponse.GPIOResponseAddValue(builder, False)  # Not applicable for configure
                GPIOResponse.GPIOResponseAddErrorMessage(builder, error_msg)
                GPIOResponse.GPIOResponseAddTimestamp(builder, int(datetime.now().timestamp() * 1000000))
                fb_response = GPIOResponse.GPIOResponseEnd(builder)
                builder.Finish(fb_response)

                self.socket.send(b"GPIO_CONFIGURE_RESPONSE", zmq.SNDMORE)
                self.socket.send(builder.Output())
            else:
                # JSON response
                response = {
                    "type": "GPIO_CONFIGURE_RESPONSE",
                    "pin": pin,
                    "direction": direction_str,
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                }
                self.socket.send_json(response)

            logger.info(f"Configured GPIO pin {pin} as {direction_str}")
        except Exception as e:
            logger.error(f"Error configuring pin {pin}: {e}")
            self._send_error(f"Failed to configure pin {pin}: {e}")
    
    def _handle_set(self, message: Dict):
        """Handle GPIO set command"""
        pin = message.get("pin")
        value = message.get("value", False)
        request_id = message.get("request_id")

        if pin is None:
            self._send_error("Missing pin parameter")
            return

        try:
            if GPIO_AVAILABLE:
                if USE_GPIOZERO:
                    # Would need to create/update device objects
                    logger.warning("gpiozero set not fully implemented")
                else:
                    GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)

            # Update pin state
            if pin not in self.pin_states:
                self.pin_states[pin] = {"direction": "output"}
            self.pin_states[pin]["value"] = value

            # Send response in appropriate format
            if self._current_format == "flatbuffers" and GPIOResponse:
                import flatbuffers
                builder = flatbuffers.Builder(256)

                error_msg = builder.CreateString("")  # Empty error message for success

                GPIOResponse.GPIOResponseStart(builder)
                GPIOResponse.GPIOResponseAddPin(builder, pin)
                GPIOResponse.GPIOResponseAddSuccess(builder, True)
                GPIOResponse.GPIOResponseAddValue(builder, value)
                GPIOResponse.GPIOResponseAddErrorMessage(builder, error_msg)
                GPIOResponse.GPIOResponseAddTimestamp(builder, int(datetime.now().timestamp() * 1000000))
                fb_response = GPIOResponse.GPIOResponseEnd(builder)
                builder.Finish(fb_response)

                self.socket.send(b"GPIO_SET_RESPONSE", zmq.SNDMORE)
                self.socket.send(builder.Output())
            else:
                # JSON response
                response = {
                    "type": "GPIO_SET_RESPONSE",
                    "pin": pin,
                    "value": value,
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                }
                self.socket.send_json(response)

            logger.info(f"Set GPIO pin {pin} to {value}")
        except Exception as e:
            logger.error(f"Error setting pin {pin}: {e}")
            self._send_error(f"Failed to set pin {pin}: {e}")
    
    def _handle_get(self, message: Dict):
        """Handle GPIO get command"""
        pin = message.get("pin")
        request_id = message.get("request_id")

        if pin is None:
            self._send_error("Missing pin parameter")
            return

        try:
            value = False
            if GPIO_AVAILABLE:
                if USE_GPIOZERO:
                    # Would need device object
                    logger.warning("gpiozero get not fully implemented")
                else:
                    value = bool(GPIO.input(pin))
            else:
                # Simulation mode - return stored value
                value = self.pin_states.get(pin, {}).get("value", False)

            # Send response in appropriate format
            if self._current_format == "flatbuffers" and GPIOResponse:
                import flatbuffers
                builder = flatbuffers.Builder(256)

                error_msg = builder.CreateString("")  # Empty error message for success

                GPIOResponse.GPIOResponseStart(builder)
                GPIOResponse.GPIOResponseAddPin(builder, pin)
                GPIOResponse.GPIOResponseAddSuccess(builder, True)
                GPIOResponse.GPIOResponseAddValue(builder, value)
                GPIOResponse.GPIOResponseAddErrorMessage(builder, error_msg)
                GPIOResponse.GPIOResponseAddTimestamp(builder, int(datetime.now().timestamp() * 1000000))
                fb_response = GPIOResponse.GPIOResponseEnd(builder)
                builder.Finish(fb_response)

                self.socket.send(b"GPIO_GET_RESPONSE", zmq.SNDMORE)
                self.socket.send(builder.Output())
            else:
                # JSON response
                response = {
                    "type": "GPIO_GET_RESPONSE",
                    "pin": pin,
                    "value": value,
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                }
                self.socket.send_json(response)

            logger.info(f"Got GPIO pin {pin} value: {value}")
        except Exception as e:
            logger.error(f"Error getting pin {pin}: {e}")
            self._send_error(f"Failed to get pin {pin}: {e}")
    
    def _handle_status(self, message: Dict):
        """Handle GPIO status request"""
        request_id = message.get("request_id")
        pins = []
        for pin, state in self.pin_states.items():
            pins.append({
                "pin": pin,
                "direction": state.get("direction", "unknown"),
                "value": state.get("value", None)
            })

        response = {
            "type": "GPIO_STATUS_RESPONSE",
            "pins": pins,
            "status": "running" if GPIO_AVAILABLE else "error",
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
        }
        self.socket.send_json(response)

    def _setup_sensors(self):
        """Setup available sensors"""
        if not self.sensor_manager:
            return

        try:
            # Example sensor setup - in production this would be configurable
            logger.info("Setting up sensors...")

            # Add DHT11 sensor (example)
            # dht_sensor = DHT11Sensor(pin=4, sensor_id="dht11_01")
            # self.sensor_manager.add_sensor(dht_sensor, priority=1)

            # Add HC-SR04 sensor (example)
            # hc_sensor = HCSR04Sensor(trigger_pin=5, echo_pin=6, sensor_id="hc_sr04_01")
            # self.sensor_manager.add_sensor(hc_sensor, priority=2)

            # Add BMP180 sensor (example)
            # bmp_sensor = BMP180Sensor(sensor_id="bmp180_01")
            # self.sensor_manager.add_sensor(bmp_sensor, priority=1)

            # Add analog sensor (example)
            # analog_sensor = AnalogSensor(pin=0, sensor_type=SensorType.VOLTAGE, sensor_id="analog_01")
            # self.sensor_manager.add_sensor(analog_sensor, priority=3)

            logger.info("Sensor setup complete")
        except Exception as e:
            logger.error(f"Error setting up sensors: {e}")

    def _handle_sensor_read(self, message: Dict):
        """Handle sensor read request"""
        sensor_id = message.get("sensor_id")
        request_id = message.get("request_id")

        if not self.sensor_manager:
            self._send_error("Sensor manager not available")
            return

        try:
            if sensor_id:
                # Read specific sensor
                data = self.sensor_manager.read_sensor(sensor_id)
                if data:
                    # Send sensor data
                    if SensorTelemetry and self._current_format == "flatbuffers":
                        import flatbuffers
                        builder = flatbuffers.Builder(256)

                        sensor_id_str = builder.CreateString(data.sensor_id)

                        SensorTelemetry.SensorTelemetryStart(builder)
                        SensorTelemetry.SensorTelemetryAddSensorId(builder, sensor_id_str)
                        SensorTelemetry.SensorTelemetryAddSensorType(builder, data.sensor_type.value.encode('utf-8')[0])  # Simplified
                        SensorTelemetry.SensorTelemetryAddValue(builder, data.value)
                        unit_str = builder.CreateString(data.unit)
                        SensorTelemetry.SensorTelemetryAddUnit(builder, unit_str)
                        SensorTelemetry.SensorTelemetryAddTimestamp(builder, int(data.timestamp * 1000000))
                        fb_message = SensorTelemetry.SensorTelemetryEnd(builder)
                        builder.Finish(fb_message)

                        self.socket.send(b"SENSOR_DATA", zmq.SNDMORE)
                        self.socket.send(builder.Output())
                    else:
                        response = {
                            "type": "SENSOR_DATA",
                            "data": data.to_dict(),
                            "timestamp": datetime.now().isoformat(),
                            "request_id": request_id
                        }
                        self.socket.send_json(response)
                else:
                    self._send_error(f"Sensor {sensor_id} read failed")
            else:
                # Read all sensors
                all_data = self.sensor_manager.read_all_sensors()
                response = {
                    "type": "SENSOR_DATA_ALL",
                    "data": {k: v.to_dict() if v else None for k, v in all_data.items()},
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id
                }
                self.socket.send_json(response)

        except Exception as e:
            logger.error(f"Error reading sensor: {e}")
            self._send_error(f"Sensor read error: {e}")

    def _handle_sensor_list(self, message: Dict):
        """Handle sensor list request"""
        request_id = message.get("request_id")

        if not self.sensor_manager:
            self._send_error("Sensor manager not available")
            return

        try:
            sensor_ids = self.sensor_manager.list_sensors()
            sensors_info = []

            for sensor_id in sensor_ids:
                stats = self.sensor_manager.get_sensor_stats(sensor_id)
                if stats:
                    sensors_info.append(stats)

            response = {
                "type": "SENSOR_LIST",
                "sensors": sensors_info,
                "count": len(sensors_info),
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }
            self.socket.send_json(response)

        except Exception as e:
            logger.error(f"Error listing sensors: {e}")
            self._send_error(f"Sensor list error: {e}")

    def _handle_sensor_config(self, message: Dict):
        """Handle sensor configuration request"""
        action = message.get("action")  # "add", "remove", "update"
        sensor_config = message.get("sensor_config", {})
        request_id = message.get("request_id")

        if not self.sensor_manager:
            self._send_error("Sensor manager not available")
            return

        try:
            if action == "add":
                sensor_type = sensor_config.get("type")
                sensor_id = sensor_config.get("sensor_id")
                config = sensor_config.get("config", {})

                # Create sensor based on type
                sensor = None
                if sensor_type == "dht11":
                    sensor = DHT11Sensor(
                        pin=config.get("pin", 4),
                        sensor_id=sensor_id,
                        config=config
                    )
                elif sensor_type == "hcsr04":
                    sensor = HCSR04Sensor(
                        trigger_pin=config.get("trigger_pin", 5),
                        echo_pin=config.get("echo_pin", 6),
                        sensor_id=sensor_id,
                        config=config
                    )
                elif sensor_type == "bmp180":
                    sensor = BMP180Sensor(
                        sensor_id=sensor_id,
                        config=config
                    )
                elif sensor_type == "analog":
                    from hardware.sensor_drivers.base_sensor import SensorType as SensorTypeEnum
                    stype = SensorTypeEnum(config.get("sensor_type", "voltage"))
                    sensor = AnalogSensor(
                        pin=config.get("pin", 0),
                        sensor_type=stype,
                        sensor_id=sensor_id,
                        config=config
                    )

                if sensor and self.sensor_manager.add_sensor(sensor):
                    response = {
                        "type": "SENSOR_CONFIG_RESPONSE",
                        "action": "add",
                        "sensor_id": sensor_id,
                        "success": True,
                        "timestamp": datetime.now().isoformat(),
                        "request_id": request_id
                    }
                    self.socket.send_json(response)
                else:
                    self._send_error(f"Failed to add sensor {sensor_id}")

            elif action == "remove":
                sensor_id = sensor_config.get("sensor_id")
                if self.sensor_manager.remove_sensor(sensor_id):
                    response = {
                        "type": "SENSOR_CONFIG_RESPONSE",
                        "action": "remove",
                        "sensor_id": sensor_id,
                        "success": True,
                        "timestamp": datetime.now().isoformat(),
                        "request_id": request_id
                    }
                    self.socket.send_json(response)
                else:
                    self._send_error(f"Failed to remove sensor {sensor_id}")

            else:
                self._send_error(f"Unknown sensor config action: {action}")

        except Exception as e:
            logger.error(f"Error configuring sensor: {e}")
            self._send_error(f"Sensor config error: {e}")

    def _send_error(self, error: str):
        """Send error response"""
        # Try to include request id if currently processing a request
        request_id = getattr(self, "_current_request_id", None)
        response = {
            "type": "ERROR",
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
        }
        self.socket.send_json(response)


def main():
    """Main entry point for GPIO worker"""
    worker = GPIOWorker()
    
    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Shutting down GPIO worker...")
        worker.stop()


if __name__ == "__main__":
    main()
