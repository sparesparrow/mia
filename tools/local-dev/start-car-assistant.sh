#!/bin/bash

# Mobile Intelligent Assistant (MIA) - Car Assistant Startup Script
# This script starts all required services for the car assistant agent

set -e

echo "🚗 Starting Mobile Intelligent Assistant (MIA) - Car Assistant"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is available
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✓${NC} $service is running on port $port"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not running on port $port"
        return 1
    fi
}

# Function to start a service in background
start_service() {
    local name=$1
    local command=$2
    local logfile=$3

    echo -e "${BLUE}Starting $name...${NC}"
    if [ -n "$logfile" ]; then
        $command > "$logfile" 2>&1 &
        echo $! > "${name}.pid"
        echo -e "${GREEN}✓${NC} $name started (PID: $!, logs: $logfile)"
    else
        $command &
        echo $! > "${name}.pid"
        echo -e "${GREEN}✓${NC} $name started (PID: $!)"
    fi
}

# Create logs directory
mkdir -p logs

echo "Checking prerequisites..."

# Check if required packages are installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

if ! command -v npx &> /dev/null; then
    echo -e "${RED}Error: npm/npx is not installed${NC}"
    exit 1
fi

# Check if MCP prompts is installed
if ! npx @sparesparrow/mcp-prompts --help &> /dev/null; then
    echo -e "${YELLOW}Installing MCP prompts package...${NC}"
    sudo npm install -g @sparesparrow/mcp-prompts
fi

echo -e "${GREEN}Prerequisites check passed${NC}"

# Start hardware workers (these would be separate processes in production)
echo "Starting hardware simulation workers..."

# GPIO Worker (inline Python script)
python3 << 'GPIO_EOF' &
"""
GPIO Worker - Hardware Control
Implements Phase 2.2: GPIO Control & Sensor Integration
Listens to ZeroMQ messages and controls GPIO pins
"""
import zmq
import json
import logging
import time
import serial
import threading
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

    def __init__(self, broker_url: str = "tcp://localhost:5555", serial_port: str = "/dev/ttyUSB0"):
        self.broker_url = broker_url
        self.serial_port = serial_port
        self.context = zmq.Context()
        self.socket = None
        self.running = False
        self.pin_states: Dict[int, Dict[str, any]] = {}  # pin -> {direction, value}

        # Serial communication for ESP32/Nucleus
        self.serial_bridge = None
        self._init_serial_bridge()

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

    def _init_serial_bridge(self):
        """Initialize serial communication with ESP32/Nucleus"""
        try:
            self.serial_bridge = serial.Serial(
                port=self.serial_port,
                baudrate=115200,
                timeout=1.0,
                write_timeout=1.0
            )
            logger.info(f"Serial bridge initialized on {self.serial_port}")
        except Exception as e:
            logger.warning(f"Failed to initialize serial bridge on {self.serial_port}: {e}")
            self.serial_bridge = None

    def _send_serial_command(self, command: Dict) -> Optional[Dict]:
        """Send command to ESP32/Nucleus over serial and wait for response"""
        if not self.serial_bridge:
            logger.warning("Serial bridge not available")
            return None

        try:
            # Send command as JSON
            cmd_json = json.dumps(command) + "\n"
            self.serial_bridge.write(cmd_json.encode())

            # Read response
            response_line = self.serial_bridge.readline().decode().strip()
            if response_line:
                return json.loads(response_line)
        except Exception as e:
            logger.error(f"Serial communication error: {e}")
            return None

        return None

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

        # Add RF capabilities for NucleusESP32
        capabilities.extend(["RF_CAPTURE", "RF_TRANSMIT", "RF_LISTEN", "RF_CONFIG"])

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
                        message_type = message_parts[0].decode("utf-8")
                        payload = message_parts[1]

                        # Try to parse as FlatBuffers first, then JSON
                        message = self._parse_message(message_type, payload)
                        if message:
                            self._handle_message(message_type, message)
                    elif len(message_parts) == 1:
                        # Legacy single-part JSON message
                        try:
                            message = json.loads(message_parts[0].decode("utf-8"))
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
            message = json.loads(payload.decode("utf-8"))
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
            elif message_type == "RF_CAPTURE":
                self._handle_rf_capture(message)
            elif message_type == "RF_TRANSMIT":
                self._handle_rf_transmit(message)
            elif message_type == "RF_LISTEN":
                self._handle_rf_listen(message)
            elif message_type == "RF_CONFIG":
                self._handle_rf_config(message)
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
            if hasattr(GPIOCommand, "GPIODirection") and direction == GPIOCommand.GPIODirection_Input:
                direction_str = "input"
            elif hasattr(GPIOCommand, "GPIODirection") and direction == GPIOCommand.GPIODirection_PWM:
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
                        SensorTelemetry.SensorTelemetryAddSensorType(builder, data.sensor_type.value.encode("utf-8")[0])  # Simplified
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

    # RF Command Handlers for NucleusESP32 Integration
    def _handle_rf_capture(self, message: Dict):
        """Handle RF capture command via ESP32/Nucleus"""
        try:
            frequency = message.get("frequency", 433.92)  # Default 433MHz
            modulation = message.get("modulation", "ASK")  # ASK, FSK, etc.
            duration_ms = message.get("duration_ms", 1000)
            request_id = message.get("request_id")

            # Send RF command over serial to ESP32
            nucleus_cmd = {
                "action": "rf_capture",
                "frequency": frequency,
                "modulation": modulation.lower(),
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat()
            }

            # For now, simulate RF capture response
            # In real implementation, this would communicate with ESP32
            logger.info(f"RF Capture: freq={frequency}MHz, mod={modulation}, duration={duration_ms}ms")

            # Simulate capture response
            rf_data = {
                "frequency": frequency,
                "modulation": modulation,
                "duration_ms": duration_ms,
                "data_length": 128,  # Simulated data length
                "signal_strength": -45.2,
                "captured_at": datetime.now().isoformat()
            }

            response = {
                "type": "RF_CAPTURE_RESPONSE",
                "success": True,
                "rf_data": rf_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
            self.socket.send_json(response)

        except Exception as e:
            logger.error(f"Error in RF capture: {e}")
            self._send_error(f"RF capture failed: {e}")

    def _handle_rf_transmit(self, message: Dict):
        """Handle RF transmit command via ESP32/Nucleus"""
        try:
            frequency = message.get("frequency", 433.92)
            modulation = message.get("modulation", "ASK")
            data = message.get("data", [])  # Raw signal data
            repeat_count = message.get("repeat_count", 1)
            request_id = message.get("request_id")

            # Send RF transmit command to ESP32
            nucleus_cmd = {
                "action": "rf_transmit",
                "frequency": frequency,
                "modulation": modulation.lower(),
                "data": data,
                "repeat_count": repeat_count,
                "timestamp": datetime.now().isoformat()
            }

            logger.info("RF Transmit: freq={}MHz, mod={}, data_len={}".format(frequency, modulation, len(data)))

            # Simulate transmit response
            response = {
                "type": "RF_TRANSMIT_RESPONSE",
                "success": True,
                "frequency": frequency,
                "modulation": modulation,
                "data_transmitted": len(data),
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
            self.socket.send_json(response)

        except Exception as e:
            logger.error(f"Error in RF transmit: {e}")
            self._send_error(f"RF transmit failed: {e}")

    def _handle_rf_listen(self, message: Dict):
        """Handle RF listen/monitor command via ESP32/Nucleus"""
        try:
            frequency = message.get("frequency", 433.92)
            modulation = message.get("modulation", "ASK")
            timeout_ms = message.get("timeout_ms", 5000)
            request_id = message.get("request_id")

            # Start continuous RF listening
            nucleus_cmd = {
                "action": "rf_listen",
                "frequency": frequency,
                "modulation": modulation.lower(),
                "timeout_ms": timeout_ms,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"RF Listen: freq={frequency}MHz, mod={modulation}, timeout={timeout_ms}ms")

            # Simulate listen response
            response = {
                "type": "RF_LISTEN_RESPONSE",
                "success": True,
                "status": "listening",
                "frequency": frequency,
                "modulation": modulation,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
            self.socket.send_json(response)

        except Exception as e:
            logger.error(f"Error in RF listen: {e}")
            self._send_error(f"RF listen failed: {e}")

    def _handle_rf_config(self, message: Dict):
        """Handle RF configuration command"""
        try:
            config_type = message.get("config_type", "general")
            parameters = message.get("parameters", {})
            request_id = message.get("request_id")

            # Send RF configuration to ESP32
            nucleus_cmd = {
                "action": "rf_config",
                "config_type": config_type,
                "parameters": parameters,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"RF Config: type={config_type}, params={parameters}")

            # Simulate config response
            response = {
                "type": "RF_CONFIG_RESPONSE",
                "success": True,
                "config_type": config_type,
                "applied_parameters": parameters,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
            self.socket.send_json(response)

        except Exception as e:
            logger.error(f"Error in RF config: {e}")
            self._send_error(f"RF config failed: {e}")


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
GPIO_EOF
echo $! > gpio_worker.pid
echo -e "${GREEN}✓${NC} GPIO Worker started (PID: $!, logs: logs/gpio_worker.log)"

# OBD Worker (inline Python script)
python3 << 'OBD_EOF' &

"""
OBD Worker - ELM327 Simulator Service
Implements Digital Twin Architecture for OBD-II simulation

This service integrates with the MIA ZeroMQ messaging bus:
- Subscribes to hardware telemetry (from serial_bridge) via PUB/SUB on port 5556
- Registers with ZeroMQ broker (port 5555) for command/control
- Runs ELM327 emulator with dynamic PID values based on real-time hardware input
"""
import sys
import os
import json
import logging
import threading
import time
from typing import Dict, Optional
from datetime import datetime

import zmq

# Try to import FlatBuffers bindings
try:
    import Mia.VehicleTelemetry as VehicleTelemetry
    import Mia.DpfStatus as DpfStatus
    FLATBUFFERS_AVAILABLE = True
except ImportError:
    VehicleTelemetry = None
    DpfStatus = None
    FLATBUFFERS_AVAILABLE = False
    logging.warning("FlatBuffers bindings not available. Using JSON telemetry.")

# Try to import ELM327 emulator
try:
    from elm import Elm
    from elm.obd_message import ObdMessage
    ELM327_AVAILABLE = True
except ImportError as e:
    ELM327_AVAILABLE = False
    logging.warning(f"ELM327-emulator not available: {e}. OBD simulation disabled.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DynamicCarState:
    """
    Shared car state that gets updated from hardware telemetry
    and used by ELM327 emulator for dynamic PID responses
    """
    def __init__(self):
        self.rpm = 800  # Engine RPM (0-8000)
        self.speed = 0  # Vehicle speed (0-255 km/h)
        self.throttle = 0  # Throttle position (0-100%)
        self.coolant_temp = 85  # Coolant temperature (°C)
        self.maf = 0  # Mass Air Flow (g/s)
        self.lock = threading.Lock()

    def update_from_telemetry(self, data: Dict):
        """Update state from MCU telemetry data"""
        with self.lock:
            # Map Arduino ADC values (0-1023) to car parameters
            if "pot1" in data:
                # Pot1 -> RPM (0-1023 -> 0-4000 RPM)
                self.rpm = max(800, min(4000, int(data["pot1"] * 4)))

            if "pot2" in data:
                # Pot2 -> Speed (0-1023 -> 0-120 km/h)
                self.speed = max(0, min(120, int(data["pot2"] / 8.5)))

            if "throttle" in data:
                self.throttle = max(0, min(100, int(data["throttle"])))

            if "coolant" in data:
                self.coolant_temp = max(-40, min(215, int(data["coolant"])))

    def get_rpm(self) -> int:
        with self.lock:
            return self.rpm

    def get_speed(self) -> int:
        with self.lock:
            return self.speed

    def get_coolant_temp(self) -> int:
        with self.lock:
            return self.coolant_temp


class MIAOBDWorker:
    """
    OBD Worker that integrates with MIA ZeroMQ architecture

    Responsibilities:
    - Listen to hardware telemetry via PUB/SUB (port 5556)
    - Register with ZeroMQ broker for command/control (port 5555)
    - Run ELM327 emulator with dynamic PID responses
    """

    def __init__(self,
                 broker_url: str = "tcp://localhost:5555",
                 telemetry_url: str = "tcp://localhost:5556"):
        self.broker_url = broker_url
        self.telemetry_url = telemetry_url
        self.context = zmq.Context()
        self.broker_socket: Optional[zmq.Socket] = None
        self.telemetry_socket: Optional[zmq.Socket] = None
        self.running = False

        self.car_state = DynamicCarState()
        self.elm_emulator = None
        self.elm_thread: Optional[threading.Thread] = None

        # Telemetry publishing
        self.last_telemetry_publish = 0
        self.telemetry_interval = 0.1  # 10Hz

        if not ELM327_AVAILABLE:
            logger.error("ELM327-emulator not installed. Install with: pip install ELM327-emulator")

    def start(self):
        """Start the OBD worker"""
        if not ELM327_AVAILABLE:
            logger.error("Cannot start OBD worker: ELM327-emulator not available")
            return False

        # Connect to broker for command/control
        self.broker_socket = self.context.socket(zmq.DEALER)
        import uuid
        worker_id = str(uuid.uuid4())
        self.broker_socket.setsockopt_string(zmq.IDENTITY, worker_id)
        self.broker_socket.connect(self.broker_url)

        # Subscribe to telemetry PUB socket
        self.telemetry_socket = self.context.socket(zmq.SUB)
        self.telemetry_socket.connect(self.telemetry_url)
        self.telemetry_socket.subscribe("mcu/telemetry")  # Subscribe to MCU telemetry topic

        self.running = True
        logger.info(f"OBD worker started, connected to broker at {self.broker_url}")
        logger.info(f"Subscribed to telemetry at {self.telemetry_url}")

        # Register with broker
        self._register_worker()

        # Start telemetry listener thread
        telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        telemetry_thread.start()

        # Start broker message handler thread
        broker_thread = threading.Thread(target=self._broker_message_loop, daemon=True)
        broker_thread.start()

        # Start telemetry publishing thread
        telemetry_pub_thread = threading.Thread(target=self._telemetry_publish_loop, daemon=True)
        telemetry_pub_thread.start()

        # Start ELM327 emulator in main thread
        self._start_elm_emulator()

        return True

    def stop(self):
        """Stop the OBD worker"""
        self.running = False

        if self.broker_socket:
            self.broker_socket.close()
        if self.telemetry_socket:
            self.telemetry_socket.close()

        if self.elm_emulator:
            # ELM327 emulator cleanup if needed
            pass

        self.context.term()
        logger.info("OBD worker stopped")

    def _register_worker(self):
        """Register this worker with the broker"""
        message = {
            "type": "WORKER_REGISTER",
            "worker_type": "OBD",
            "capabilities": ["OBD_STATUS", "OBD_PID_QUERY", "OBD_RESET"],
            "timestamp": datetime.now().isoformat()
        }
        self.broker_socket.send_json(message)
        logger.info("Registered OBD worker with broker")

    def _telemetry_loop(self):
        """Listen for telemetry updates from serial bridge"""
        poller = zmq.Poller()
        poller.register(self.telemetry_socket, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(100))  # 100ms timeout

                if self.telemetry_socket in socks and socks[self.telemetry_socket] == zmq.POLLIN:
                    # Receive multipart: [topic][message]
                    parts = self.telemetry_socket.recv_multipart()
                    if len(parts) >= 2:
                        topic = parts[0].decode("utf-8")
                        message_data = parts[1]

                        if topic == "mcu/telemetry":
                            try:
                                data = json.loads(message_data.decode("utf-8"))
                                self.car_state.update_from_telemetry(data)
                                logger.debug(f"Updated car state from telemetry: RPM={self.car_state.get_rpm()}, Speed={self.car_state.get_speed()}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to decode telemetry JSON: {e}")
            except zmq.ZMQError as e:
                if self.running:
                    logger.error(f"ZMQ error in telemetry loop: {e}")
                break
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                time.sleep(0.1)

    def _broker_message_loop(self):
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
                logger.error(f"Error in broker message loop: {e}")
                time.sleep(0.1)

    def _handle_broker_message(self, message: Dict):
        """Handle incoming message from broker"""
        message_type = message.get("type")
        request_id = message.get("request_id")

        try:
            if message_type == "OBD_STATUS":
                self._handle_status_request(request_id)
            elif message_type == "OBD_PID_QUERY":
                self._handle_pid_query(message, request_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling {message_type}: {e}")
            self._send_error(request_id, str(e))

    def _handle_status_request(self, request_id: Optional[str]):
        """Handle OBD status request"""
        response = {
            "type": "OBD_STATUS_RESPONSE",
            "status": "running",
            "rpm": self.car_state.get_rpm(),
            "speed": self.car_state.get_speed(),
            "coolant_temp": self.car_state.get_coolant_temp(),
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
        self.broker_socket.send_json(response)

    def _handle_pid_query(self, message: Dict, request_id: Optional[str]):
        """Handle OBD PID query"""
        pid = message.get("pid", "")
        # This would be handled by the ELM327 emulator, but we can provide status
        response = {
            "type": "OBD_PID_QUERY_RESPONSE",
            "pid": pid,
            "status": "handled_by_emulator",
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
        self.broker_socket.send_json(response)

    def _telemetry_publish_loop(self):
        """Publish OBD telemetry data periodically"""
        if not self.telemetry_socket:
            return

        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_telemetry_publish >= self.telemetry_interval:
                    # Publish OBD telemetry using FlatBuffers if available
                    if FLATBUFFERS_AVAILABLE and VehicleTelemetry:
                        import flatbuffers
                        builder = flatbuffers.Builder(512)

                        # Get current state
                        rpm = self.car_state.get_rpm()
                        speed = self.car_state.get_speed()
                        coolant_temp = self.car_state.get_coolant_temp()

                        VehicleTelemetry.VehicleTelemetryStart(builder)
                        # Engine data
                        VehicleTelemetry.VehicleTelemetryAddRpm(builder, float(rpm))
                        VehicleTelemetry.VehicleTelemetryAddSpeedKmh(builder, float(speed))
                        VehicleTelemetry.VehicleTelemetryAddCoolantTempC(builder, float(coolant_temp))
                        VehicleTelemetry.VehicleTelemetryAddOilTemperatureC(builder, float(coolant_temp + 5))  # Estimate
                        VehicleTelemetry.VehicleTelemetryAddBatteryVoltage(builder, 13.8)  # Typical voltage

                        # DPF data (simulated)
                        VehicleTelemetry.VehicleTelemetryAddDpfSootLoadPercent(builder, 15.5)
                        VehicleTelemetry.VehicleTelemetryAddDpfSootMassG(builder, 2.3)
                        VehicleTelemetry.VehicleTelemetryAddDpfRegenerationStatus(builder, DpfStatus.DpfStatus_Normal)
                        VehicleTelemetry.VehicleTelemetryAddEolysAdditiveLevelPercent(builder, 85.0)
                        VehicleTelemetry.VehicleTelemetryAddEolysAdditiveLevelL(builder, 45.0)

                        # Additional sensors (simulated values)
                        VehicleTelemetry.VehicleTelemetryAddIntakeAirTempC(builder, float(coolant_temp - 10))
                        VehicleTelemetry.VehicleTelemetryAddFuelLevelPercent(builder, 75.0)
                        VehicleTelemetry.VehicleTelemetryAddEngineLoadPercent(builder, 45.0)

                        VehicleTelemetry.VehicleTelemetryAddTimestamp(builder, int(current_time * 1000000))

                        fb_message = VehicleTelemetry.VehicleTelemetryEnd(builder)
                        builder.Finish(fb_message)

                        topic = "obd/telemetry"
                        self.telemetry_socket.send_multipart([topic.encode("utf-8"), builder.Output()])
                    else:
                        # Fallback to JSON telemetry
                        telemetry_data = {
                            "rpm": self.car_state.get_rpm(),
                            "speed": self.car_state.get_speed(),
                            "coolant_temp": self.car_state.get_coolant_temp(),
                            "load": 0,  # Not implemented yet
                            "timestamp": datetime.now().isoformat()
                        }

                        topic = "obd/telemetry"
                        message = json.dumps(telemetry_data).encode("utf-8")
                        self.telemetry_socket.send_multipart([topic.encode("utf-8"), message])

                    self.last_telemetry_publish = current_time

                time.sleep(0.01)  # Small sleep to prevent CPU hogging

            except Exception as e:
                logger.error(f"Error in telemetry publish loop: {e}")
                time.sleep(0.1)

    def _send_error(self, request_id: Optional[str], error: str):
        """Send error response"""
        response = {
            "type": "ERROR",
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
        self.broker_socket.send_json(response)

    def _start_elm_emulator(self):
        """Start ELM327 emulator with dynamic PID bindings"""
        try:
            # Create dynamic OBD message dictionary
            obd_messages = ObdMessage.copy()

            # Override PIDs with dynamic functions
            # PID 0x0C: Engine RPM
            def get_rpm_pid():
                rpm = self.car_state.get_rpm()
                val = int(rpm * 4)  # RPM = (A*256 + B) / 4
                a = (val >> 8) & 0xFF
                b = val & 0xFF
                return f"{a:02X}{b:02X}"

            # PID 0x0D: Vehicle Speed
            def get_speed_pid():
                speed = self.car_state.get_speed()
                return f"{speed:02X}"

            # PID 0x05: Coolant Temperature
            def get_coolant_pid():
                temp = self.car_state.get_coolant_temp()
                return f"{temp + 40:02X}"  # OBD offset: -40°C

            # Update OBD message dictionary
            # Note: ELM327-emulator may need string values, so we'"'"'ll update periodically
            # For now, we'"'"'ll create a wrapper that calls these functions

            # Initialize emulator
            logger.info("Starting ELM327 emulator...")

            # The ELM327-emulator library structure may vary
            # This is a simplified integration - actual implementation may need
            # library-specific adjustments

            # For now, log that emulator would start here
            logger.info("ELM327 emulator integration ready")
            logger.info("Note: Full ELM327 emulator requires library-specific integration")
            logger.info("Current implementation provides ZMQ bridge and state management")

            # Keep running
            while self.running:
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error starting ELM327 emulator: {e}")
            logger.exception(e)


def main():
    """Main entry point for OBD worker"""
    worker = MIAOBDWorker()

    try:
        if worker.start():
            # Keep running
            while worker.running:
                time.sleep(1)
        else:
            logger.error("Failed to start OBD worker")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down OBD worker...")
        worker.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception(e)
        worker.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
OBD_EOF
echo $! > obd_worker.pid
echo -e "${GREEN}✓${NC} OBD Worker started (PID: $!, logs: logs/obd_worker.log)"

# RF Worker (inline Python script)
python3 << 'RF_EOF' &

"""
RF Hardware Worker

ZeroMQ-based RF signal capture and replay worker for NucleusESP32.
Interfaces with NucleusESP32 via serial/MQTT for RF operations.
"""

import asyncio
import logging
import zmq
import zmq.asyncio
from typing import Optional, Dict, Any, List
import time
import json
import serial
import paho.mqtt.client as mqtt

# Import ICD-generated types
from mia.core.messaging.messages import (
    RFCaptureStart, RFReplay, RFModulation,
    MessageEnvelope
)


class SerialBridge:
    """Serial communication bridge to NucleusESP32"""

    def __init__(self, port: str = "/dev/ttyACM0", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.logger = logging.getLogger(__name__)

    async def connect(self) -> bool:
        """Connect to NucleusESP32 via serial"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )
            await asyncio.sleep(0.1)  # Allow connection to stabilize

            # Test connection
            await self.send({"command": "ping"})
            response = await self.receive()
            if response and response.get("status") == "ok":
                self.logger.info(f"Connected to NucleusESP32 on {self.port}")
                return True
            else:
                self.logger.error("NucleusESP32 ping failed")
                return False

        except Exception as e:
            self.logger.error(f"Serial connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from NucleusESP32"""
        if self.serial:
            self.serial.close()
            self.serial = None
            self.logger.info("Disconnected from NucleusESP32")

    async def send(self, data: Dict[str, Any]) -> bool:
        """Send JSON command to NucleusESP32"""
        if not self.serial:
            return False

        try:
            json_str = json.dumps(data) + "\n"
            self.serial.write(json_str.encode("utf-8"))
            self.serial.flush()
            return True
        except Exception as e:
            self.logger.error(f"Serial send failed: {e}")
            return False

    async def receive(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Receive JSON response from NucleusESP32"""
        if not self.serial:
            return None

        try:
            # Non-blocking read with timeout
            start_time = time.time()
            buffer = ""

            while time.time() - start_time < timeout:
                if self.serial.in_waiting > 0:
                    char = self.serial.read().decode("utf-8")
                    buffer += char

                    if char == "\n":
                        # Complete line received
                        try:
                            return json.loads(buffer.strip())
                        except json.JSONDecodeError:
                            # Invalid JSON, continue reading
                            buffer = ""
                            continue

                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting

            return None  # Timeout

        except Exception as e:
            self.logger.error(f"Serial receive failed: {e}")
            return None


class MQTTBridge:
    """MQTT communication bridge to NucleusESP32"""

    def __init__(self, broker: str = "localhost", port: int = 1883,
                 client_id: str = "mia-rf-worker"):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.response_queue: asyncio.Queue = asyncio.Queue()
        self.logger = logging.getLogger(__name__)

    async def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(client_id=self.client_id)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            # Connect in background
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()

            # Wait for connection
            await asyncio.sleep(0.5)

            if self.connected:
                self.logger.info(f"Connected to MQTT broker {self.broker}:{self.port}")
                return True
            else:
                self.logger.error("MQTT connection failed")
                return False

        except Exception as e:
            self.logger.error(f"MQTT connection failed: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connect callback"""
        if rc == 0:
            self.connected = True
            client.subscribe("nucleus/rf/response")
        else:
            self.logger.error(f"MQTT connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            asyncio.create_task(self.response_queue.put(payload))
        except Exception as e:
            self.logger.error(f"MQTT message error: {e}")

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnect callback"""
        self.connected = False

    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
            self.connected = False
            self.logger.info("Disconnected from MQTT broker")

    async def send(self, data: Dict[str, Any]) -> bool:
        """Send command via MQTT"""
        if not self.client or not self.connected:
            return False

        try:
            self.client.publish("nucleus/rf/command", json.dumps(data))
            return True
        except Exception as e:
            self.logger.error(f"MQTT send failed: {e}")
            return False

    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Receive response via MQTT"""
        try:
            return await asyncio.wait_for(
                self.response_queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.logger.error(f"MQTT receive failed: {e}")
            return None


class RFZMQWorker:
    """ZeroMQ-based RF capture/replay worker"""

    def __init__(self,
                 zmq_address: str = "tcp://127.0.0.1:5557",
                 nucleus_interface: str = "serial",  # "serial" or "mqtt"
                 serial_port: str = "/dev/ttyACM0",
                 mqtt_broker: str = "localhost"):
        self.zmq_address = zmq_address
        self.nucleus_interface = nucleus_interface
        self.serial_port = serial_port
        self.mqtt_broker = mqtt_broker

        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None
        self.bridge: Optional[SerialBridge | MQTTBridge] = None

        self.logger = logging.getLogger(__name__)

        # RF operation state
        self.capture_active = False
        self.replay_active = False
        self.captured_frames: List[Dict[str, Any]] = []

    async def start(self):
        """Start the RF worker"""
        # Initialize ZeroMQ
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self.zmq_address)

        # Initialize NucleusESP32 bridge
        if self.nucleus_interface == "serial":
            self.bridge = SerialBridge(self.serial_port)
        elif self.nucleus_interface == "mqtt":
            self.bridge = MQTTBridge(self.mqtt_broker)
        else:
            raise ValueError(f"Unknown interface: {self.nucleus_interface}")

        # Connect to NucleusESP32
        if not await self.bridge.connect():
            self.logger.error("Failed to connect to NucleusESP32")
            return

        self.logger.info(f"RF worker started on {self.zmq_address}")

        try:
            await self._run()
        except Exception as e:
            self.logger.error(f"RF worker error: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the RF worker"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        if self.bridge:
            await self.bridge.disconnect()
        self.logger.info("RF worker stopped")

    async def _run(self):
        """Main worker loop"""
        while True:
            try:
                # Receive message
                message_data = await self.socket.recv_json()
                self.logger.debug(f"Received message: {message_data}")

                # Parse envelope
                envelope = MessageEnvelope(**message_data)

                # Handle message based on type
                response = await self._handle_message(envelope)

                # Send response
                response_data = {
                    "message_type": response.__class__.__name__,
                    "message_id": envelope.message_id,
                    "source": "rf-worker",
                    "payload": response.__dict__
                }

                await self.socket.send_json(response_data)

            except Exception as e:
                self.logger.error(f"Error handling message: {e}")
                # Send error response
                await self.socket.send_json({
                    "message_type": "Error",
                    "message_id": 0,
                    "source": "rf-worker",
                    "payload": {"error": str(e)}
                })

    async def _handle_message(self, envelope: MessageEnvelope) -> Dict[str, Any]:
        """Handle incoming message"""
        if envelope.message_type == "RFCaptureStart":
            cmd = RFCaptureStart(**envelope.payload)
            return await self._handle_capture_start(cmd)
        elif envelope.message_type == "RFReplay":
            cmd = RFReplay(**envelope.payload)
            return await self._handle_replay(cmd)
        else:
            raise ValueError(f"Unknown message type: {envelope.message_type}")

    async def _handle_capture_start(self, cmd: RFCaptureStart) -> Dict[str, Any]:
        """Handle RF capture start command"""
        try:
            self.logger.info(f"Starting RF capture: freq={cmd.frequency}Hz, mod={cmd.modulation}")

            # Prepare NucleusESP32 command
            nucleus_cmd = {
                "action": "start_capture",
                "frequency": cmd.frequency,
                "modulation": cmd.modulation.name.lower(),
                "sample_rate": cmd.sample_rate,
                "gain": cmd.gain,
                "bandwidth": cmd.bandwidth,
                "squelch": cmd.squelch,
                "duration_ms": cmd.duration_ms,
                "max_frames": cmd.max_frames
            }

            # Send command to NucleusESP32
            success = await self.bridge.send(nucleus_cmd)
            if not success:
                return {
                    "success": False,
                    "error_message": "Failed to send capture command",
                    "timestamp": int(time.time() * 1_000_000)
                }

            # Wait for response
            response = await self.bridge.receive(timeout=2.0)
            if response and response.get("status") == "capture_started":
                self.capture_active = True
                return {
                    "success": True,
                    "message": "RF capture started",
                    "config": nucleus_cmd,
                    "timestamp": int(time.time() * 1_000_000)
                }
            else:
                return {
                    "success": False,
                    "error_message": "NucleusESP32 capture failed",
                    "timestamp": int(time.time() * 1_000_000)
                }

        except Exception as e:
            self.logger.error(f"RF capture failed: {e}")
            return {
                "success": False,
                "error_message": str(e),
                "timestamp": int(time.time() * 1_000_000)
            }

    async def _handle_replay(self, cmd: RFReplay) -> Dict[str, Any]:
        """Handle RF replay command"""
        try:
            self.logger.info(f"Starting RF replay: freq={cmd.frequency}Hz, frames={len(cmd.frame_data)}")

            # Prepare NucleusESP32 command
            nucleus_cmd = {
                "action": "replay_signal",
                "frequency": cmd.frequency,
                "modulation": cmd.modulation.name.lower(),
                "frame_data": cmd.frame_data,
                "repeat_count": cmd.repeat_count,
                "tx_power": cmd.tx_power
            }

            # Send command to NucleusESP32
            success = await self.bridge.send(nucleus_cmd)
            if not success:
                return {
                    "success": False,
                    "error_message": "Failed to send replay command",
                    "timestamp": int(time.time() * 1_000_000)
                }

            # Wait for response
            response = await self.bridge.receive(timeout=5.0)
            if response and response.get("status") == "replay_complete":
                frames_sent = response.get("frames_sent", 0)
                return {
                    "success": True,
                    "message": f"RF replay completed: {frames_sent} frames sent",
                    "frames_sent": frames_sent,
                    "timestamp": int(time.time() * 1_000_000)
                }
            else:
                return {
                    "success": False,
                    "error_message": "NucleusESP32 replay failed",
                    "timestamp": int(time.time() * 1_000_000)
                }

        except Exception as e:
            self.logger.error(f"RF replay failed: {e}")
            return {
                "success": False,
                "error_message": str(e),
                "timestamp": int(time.time() * 1_000_000)
            }

    def get_capture_status(self) -> Dict[str, Any]:
        """Get current capture status"""
        return {
            "active": self.capture_active,
            "frames_captured": len(self.captured_frames)
        }

    def get_replay_status(self) -> Dict[str, Any]:
        """Get current replay status"""
        return {
            "active": self.replay_active
        }


async def main():
    """Main entry point for RF worker"""
    logging.basicConfig(level=logging.INFO)

    # Try serial first, fallback to MQTT
    worker = RFZMQWorker(nucleus_interface="serial")
    try:
        await worker.start()
    except Exception as e:
        print(f"Serial interface failed: {e}, trying MQTT...")
        worker = RFZMQWorker(nucleus_interface="mqtt")
        await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
RF_EOF
echo $! > rf_worker.pid
echo -e "${GREEN}✓${NC} RF Worker started (PID: $!, logs: logs/rf_worker.log)"

# Wait a moment for workers to start
sleep 2

echo "Starting MCP services..."

# Note: MCP Prompts service will be started by Cursor MCP integration
# Start MIA Hardware MCP Server
start_service "mia_hardware" "env PYTHONPATH=/home/mia/projects/mia/modules python3 mia/modules/hardware-bridge/hardware_server.py" "logs/mia_hardware.log"

# Start MIA Core Orchestrator
start_service "mia_orchestrator" "env PYTHONPATH=/home/mia/projects/mia/modules python3 mia/modules/core-orchestrator/main.py" "logs/mia_orchestrator.log"

echo ""
echo -e "${GREEN}🎉 Mobile Intelligent Assistant (MIA) Car Assistant Started!${NC}"
echo ""
echo "Services running:"
echo "  • GPIO Worker:     tcp://127.0.0.1:5555"
echo "  • OBD Worker:      tcp://127.0.0.1:5556"
echo "  • RF Worker:       tcp://127.0.0.1:5557"
echo "  • MCP Prompts:     Available via Cursor MCP integration"
echo "  • MIA Hardware:    Available via MCP"
echo "  • MIA Orchestrator: Available via MCP"
echo ""
echo "The car assistant is now ready to accept commands through Cursor MCP integration."
echo "Use natural language commands like:"
echo "  • 'Turn on the interior lights'"
echo "  • 'Check my fuel level'"
echo "  • 'What's my engine temperature?'"
echo "  • 'Open the garage door'"
echo ""
echo "To stop all services, run: ./stop_car_assistant.sh"
echo ""

# Keep the script running to show status
echo "Press Ctrl+C to stop monitoring..."
trap 'echo -e "\n${YELLOW}Stopping monitoring...${NC}"' INT

while true; do
    echo -e "${BLUE}Service Status Check:$(date)${NC}"
    check_port 5555 "GPIO Worker" || true
    check_port 5556 "OBD Worker" || true
    check_port 5557 "RF Worker" || true

    # Check if processes are still running
    for service in gpio_worker obd_worker rf_worker mia_hardware mia_orchestrator; do
        if [ -f "${service}.pid" ]; then
            pid=$(cat "${service}.pid")
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} $service (PID: $pid)"
            else
                echo -e "${RED}✗${NC} $service (PID: $pid - stopped)"
            fi
        fi
    done

    sleep 10
done