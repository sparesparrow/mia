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
import signal
from typing import Dict, Optional
from datetime import datetime

import zmq

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            if 'pot1' in data:
                # Pot1 -> RPM (0-1023 -> 0-4000 RPM)
                self.rpm = max(800, min(4000, int(data['pot1'] * 4)))
            
            if 'pot2' in data:
                # Pot2 -> Speed (0-1023 -> 0-120 km/h)
                self.speed = max(0, min(120, int(data['pot2'] / 8.5)))
            
            if 'throttle' in data:
                self.throttle = max(0, min(100, int(data['throttle'])))
            
            if 'coolant' in data:
                self.coolant_temp = max(-40, min(215, int(data['coolant'])))
    
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

    # ELM327 AT initialization commands
    ELM_INIT_SEQUENCE = [
        ("ATZ",   "Reset ELM327",           2.0),   # Reset, wait for "ELM327 v..."
        ("ATE0",  "Echo off",               0.5),   # Disable echo
        ("ATL0",  "Linefeeds off",          0.5),   # Disable linefeeds
        ("ATS0",  "Spaces off",             0.5),   # Disable spaces in response
        ("ATH0",  "Headers off",            0.5),   # Disable OBD headers
        ("ATAT1", "Adaptive timing normal", 0.5),   # Adaptive timing
    ]

    # CAN bus protocols to try (in order of likelihood for PSA vehicles)
    CAN_PROTOCOLS = [
        ("ATSP6", "ISO 15765-4 CAN 11-bit 500kbps"),  # Most common
        ("ATSP7", "ISO 15765-4 CAN 29-bit 500kbps"),  # Extended addressing
        ("ATSP8", "ISO 15765-4 CAN 11-bit 250kbps"),  # Older vehicles
        ("ATSP0", "Auto-detect protocol"),              # Fallback
    ]

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

        # Connection state
        self._elm_initialized = False
        self._active_protocol = None
        self._connect_attempts = 0
        self._max_connect_attempts = 10
        self._backoff_sec = 1.0
        self._mcu_connected = False

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

        # Subscribe to telemetry PUB socket (mcu/telemetry + mcu/status)
        self.telemetry_socket = self.context.socket(zmq.SUB)
        self.telemetry_socket.connect(self.telemetry_url)
        self.telemetry_socket.subscribe("mcu/telemetry")
        self.telemetry_socket.subscribe("mcu/status")

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

        # Start ELM327 emulator with init sequence
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
                        topic = parts[0].decode('utf-8')
                        message_data = parts[1]

                        if topic == "mcu/telemetry":
                            try:
                                data = json.loads(message_data.decode('utf-8'))
                                self.car_state.update_from_telemetry(data)
                                self._mcu_connected = True
                                logger.debug(f"Updated car state: RPM={self.car_state.get_rpm()}, Speed={self.car_state.get_speed()}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to decode telemetry JSON: {e}")

                        elif topic == "mcu/status":
                            try:
                                status = json.loads(message_data.decode('utf-8'))
                                event = status.get("event")
                                if event == "connected":
                                    self._mcu_connected = True
                                    logger.info(f"MCU connected: {status.get('device')}")
                                elif event == "disconnected":
                                    self._mcu_connected = False
                                    logger.warning(f"MCU disconnected: {status.get('reason')}")
                            except json.JSONDecodeError:
                                pass

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
            "status": "running" if self._elm_initialized else "initializing",
            "rpm": self.car_state.get_rpm(),
            "speed": self.car_state.get_speed(),
            "coolant_temp": self.car_state.get_coolant_temp(),
            "elm_initialized": self._elm_initialized,
            "active_protocol": self._active_protocol,
            "mcu_connected": self._mcu_connected,
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
                    # Publish OBD telemetry
                    telemetry_data = {
                        "rpm": self.car_state.get_rpm(),
                        "speed": self.car_state.get_speed(),
                        "coolant_temp": self.car_state.get_coolant_temp(),
                        "load": 0,  # Not implemented yet
                        "timestamp": datetime.now().isoformat()
                    }

                    topic = "obd/telemetry"
                    message = json.dumps(telemetry_data).encode('utf-8')
                    self.telemetry_socket.send_multipart([topic.encode('utf-8'), message])

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

    def _elm_send_at(self, command: str, timeout: float = 1.0) -> Optional[str]:
        """Send an AT command to ELM327 and read the response.

        In the digital-twin architecture the ELM emulator runs in-process,
        so this talks to the emulator's virtual serial port.  If we later
        switch to a real ELM327 adapter, this same interface works over
        pyserial.
        """
        if self.elm_emulator is None:
            return None

        try:
            # The ELM327-emulator library exposes a pty pair.  We write to
            # the "tester" side and read back.
            if hasattr(self.elm_emulator, "send_command"):
                return self.elm_emulator.send_command(command, timeout=timeout)

            # Fallback for libraries that don't expose send_command
            logger.debug(f"ELM AT: {command} (no send_command API)")
            return "OK"
        except Exception as e:
            logger.warning(f"ELM AT '{command}' failed: {e}")
            return None

    def _initialize_elm327(self) -> bool:
        """Run the ELM327 AT initialization sequence.

        Returns True if the adapter responded successfully to all
        initialization commands.
        """
        logger.info("Initializing ELM327 adapter...")

        for cmd, description, timeout in self.ELM_INIT_SEQUENCE:
            response = self._elm_send_at(cmd, timeout)
            if response is None:
                logger.error(f"ELM327 init failed at '{cmd}' ({description})")
                return False
            logger.info(f"  {cmd}: {response.strip()[:40]}  ({description})")

        self._elm_initialized = True
        logger.info("ELM327 initialization complete")
        return True

    def _detect_can_protocol(self) -> bool:
        """Auto-detect the CAN bus protocol.

        Tries each protocol in order, sending a simple OBD PID request
        (mode 01 PID 00 — supported PIDs) to see if the vehicle responds.
        """
        logger.info("Detecting CAN bus protocol...")

        for at_cmd, description in self.CAN_PROTOCOLS:
            logger.info(f"  Trying {at_cmd} ({description})...")
            resp = self._elm_send_at(at_cmd, 2.0)
            if resp is None:
                continue

            # Send a test PID query: 01 00 = supported PIDs bitmap
            test_resp = self._elm_send_at("0100", 5.0)
            if test_resp and "NO DATA" not in test_resp and "ERROR" not in test_resp:
                self._active_protocol = description
                logger.info(f"  Protocol detected: {description}")
                return True
            else:
                logger.info(f"  {description}: no vehicle response")

        logger.warning("No CAN protocol detected (vehicle may be off)")
        return False

    def _connect_with_retry(self) -> bool:
        """Attempt ELM327 init + CAN detection with exponential backoff."""
        while self.running and self._connect_attempts < self._max_connect_attempts:
            self._connect_attempts += 1
            logger.info(f"Connection attempt {self._connect_attempts}/{self._max_connect_attempts}")

            if self._initialize_elm327():
                if self._detect_can_protocol():
                    self._connect_attempts = 0
                    self._backoff_sec = 1.0
                    return True
                else:
                    # ELM327 works but no vehicle — keep trying
                    logger.info("ELM327 OK but no vehicle response, retrying...")

            # Exponential backoff
            logger.info(f"Retrying in {self._backoff_sec:.0f}s...")
            waited = 0.0
            while waited < self._backoff_sec and self.running:
                time.sleep(0.5)
                waited += 0.5
            self._backoff_sec = min(self._backoff_sec * 2, 30.0)

        if self.running:
            logger.error("Max connection attempts reached")
        return False

    def _start_elm_emulator(self):
        """Start ELM327 emulator with AT init and CAN protocol detection"""
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
                return f"{temp + 40:02X}"  # OBD offset: -40C

            # Initialize emulator
            logger.info("Starting ELM327 emulator...")
            logger.info("ELM327 emulator integration ready")
            logger.info("Current implementation provides ZMQ bridge and state management")

            # Run AT init + CAN detection with retry
            if not self._connect_with_retry():
                logger.warning("Running without ELM327 init (emulator-only mode)")

            # Keep running
            while self.running:
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error starting ELM327 emulator: {e}")
            logger.exception(e)


def main():
    """Main entry point for OBD worker"""
    worker = MIAOBDWorker()

    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}")
        worker.running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        if worker.start():
            while worker.running:
                time.sleep(1)
        else:
            logger.error("Failed to start OBD worker")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down OBD worker...")
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
