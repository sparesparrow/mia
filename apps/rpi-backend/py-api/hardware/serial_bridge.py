import zmq
import serial
import serial.tools.list_ports
import json
import math
import random
import time
import os
import signal
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("mia.serial_bridge")


class SimulationSerialSource:
    """Generates synthetic MCU telemetry when no physical serial device is available.

    Produces realistic OBD-style payloads at roughly 1 Hz so downstream
    consumers (OBD worker, Audi bridge, WebSocket clients) can be developed
    and tested without hardware.
    """

    def __init__(self, interval: float = 1.0):
        self._interval = interval
        self._tick = 0
        self._base_rpm = 820.0
        self._base_speed = 0.0
        self._base_coolant = 42.0

    def readline(self) -> bytes:
        """Return one JSON-encoded telemetry line, sleeping to simulate baud rate timing."""
        time.sleep(self._interval)
        self._tick += 1

        # Slowly-varying values that look like a parked engine idling
        rpm = self._base_rpm + 30 * math.sin(self._tick * 0.1) + random.uniform(-5, 5)
        speed = max(0.0, self._base_speed + random.uniform(-0.5, 0.5))
        coolant = self._base_coolant + 0.05 * min(self._tick, 600) + random.uniform(-0.2, 0.2)
        fuel = max(0, min(100, 68.5 - 0.001 * self._tick + random.uniform(-0.1, 0.1)))
        voltage = 12.3 + 0.2 * math.sin(self._tick * 0.05) + random.uniform(-0.05, 0.05)

        payload = {
            "device_id": "simulation_0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "speed_kmh": round(speed, 1),
            "engine_rpm": round(rpm, 0),
            "coolant_temp_c": round(coolant, 1),
            "fuel_level_percent": round(fuel, 1),
            "battery_voltage": round(voltage, 2),
        }
        return (json.dumps(payload) + "\n").encode()

    @property
    def is_open(self) -> bool:
        return True

    def close(self):
        pass


class SerialBridge:
    def __init__(self, serial_port="/dev/ttyUSB0", baud_rate=115200, zmq_endpoint="tcp://*:5556",
                 simulation=None):
        """
        Args:
            simulation: Tri-state control.
                ``None``  (default) – auto-detect: use hardware if available, else simulate.
                ``True``  – force simulation mode regardless of hardware.
                ``False`` – disable simulation; fail if no hardware found.
        """
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.zmq_endpoint = zmq_endpoint
        self.context = zmq.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.running = True

        # Simulation control
        self._simulation_requested = simulation
        self.simulation_mode = False

        # Reconnect state
        self._backoff_sec = 1.0
        self._max_backoff_sec = 30.0
        self._consecutive_errors = 0
        self._serial: Optional[serial.Serial] = None

        # Adapter metadata for downstream consumers
        self._adapter_kind = "unknown"
        self._device_path: Optional[str] = None
        self._message_count = 0

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down")
        self.running = False

    def _find_serial_device(self) -> Optional[str]:
        """Auto-detect serial device if configured port is unavailable.

        Checks the configured port first (e.g. /dev/obd2 symlink created by
        udev rules). Falls back to scanning for common USB-serial chipsets
        used in ELM327/OBD adapters and Arduino/ESP32 boards.
        """
        if os.path.exists(self.serial_port):
            return self.serial_port

        # Scan for USB-serial adapters
        obd_keywords = {"ch340", "cp210", "ftdi", "pl2303", "elm327", "obd"}
        try:
            for port in serial.tools.list_ports.comports():
                desc = (port.description or "").lower()
                if any(kw in desc for kw in obd_keywords):
                    logger.info(f"Auto-detected serial device: {port.device} ({port.description})")
                    return port.device
        except OSError as exc:
            logger.warning(f"Failed to enumerate serial devices: {exc}")

        return None

    def _safe_close_serial(self) -> None:
        """Close the active serial connection without raising during shutdown paths."""
        if self._serial is None:
            return

        try:
            self._serial.close()
        except (serial.SerialException, OSError, AttributeError) as exc:
            logger.debug(f"Ignoring serial close error: {exc}")
        finally:
            self._serial = None

    def _connect_serial(self) -> Optional[serial.Serial]:
        """Attempt to open the serial port with backoff on failure.

        When simulation is allowed (``simulation=None`` or ``True``), returns a
        :class:`SimulationSerialSource` instead of ``None`` when no physical
        device is found.
        """
        # Force simulation mode
        if self._simulation_requested is True:
            return self._enter_simulation()

        device = self._find_serial_device()
        if not device:
            # Auto-detect: fall back to simulation when no hardware found
            if self._simulation_requested is None:
                return self._enter_simulation()
            return None

        try:
            ser = serial.Serial(device, self.baud_rate, timeout=1)
            logger.info(f"Serial connected: {device} @ {self.baud_rate}")
            self._backoff_sec = 1.0  # reset on success
            self._consecutive_errors = 0
            self._device_path = device
            self._adapter_kind = self._detect_adapter_kind(device)
            self.simulation_mode = False

            # Publish connection event
            self.pub_socket.send_multipart([
                b"mcu/status",
                json.dumps({"event": "connected", "device": device}).encode()
            ])
            return ser

        except serial.SerialException as e:
            logger.warning(f"Cannot open {device}: {e}")
            if self._simulation_requested is None:
                return self._enter_simulation()
            return None

    def _enter_simulation(self):
        """Switch to simulation mode and return a synthetic serial source."""
        if not self.simulation_mode:
            logger.warning("No serial device available. Running in simulation mode.")
        self.simulation_mode = True
        self._adapter_kind = "simulation"
        self._device_path = "simulation"

        self.pub_socket.send_multipart([
            b"mcu/status",
            json.dumps({"event": "connected", "device": "simulation", "simulation": True}).encode()
        ])
        return SimulationSerialSource()

    def _backoff_wait(self):
        """Exponential backoff between reconnect attempts."""
        logger.info(f"Reconnecting in {self._backoff_sec:.0f}s...")

        # Sleep in small increments so we can check self.running
        waited = 0.0
        while waited < self._backoff_sec and self.running:
            time.sleep(0.5)
            waited += 0.5

        self._backoff_sec = min(self._backoff_sec * 2, self._max_backoff_sec)

    def run(self):
        """Main loop with automatic reconnection.

        When running in simulation mode the read loop uses
        :class:`SimulationSerialSource` instead of a physical serial port.
        """
        self.pub_socket.bind(self.zmq_endpoint)
        logger.info(f"Bound ZMQ PUB to {self.zmq_endpoint}")

        while self.running:
            # ── Connect phase ──────────────────────────────────────
            if self._serial is None:
                self._serial = self._connect_serial()
                if self._serial is None:
                    self._backoff_wait()
                    continue

            # ── Read phase ─────────────────────────────────────────
            try:
                line = self._serial.readline().decode(errors="replace").strip()
                if not line:
                    continue

                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        self._publish_telemetry(data)
                    except json.JSONDecodeError:
                        logger.debug(f"Malformed JSON: {line[:80]}")

            except (serial.SerialException, OSError) as e:
                # USB cable pulled, device disappeared, etc.
                self._consecutive_errors += 1
                logger.warning(f"Serial disconnected: {e}")

                self.pub_socket.send_multipart([
                    b"mcu/status",
                    json.dumps({
                        "event": "disconnected",
                        "reason": str(e),
                        "consecutive_errors": self._consecutive_errors,
                    }).encode()
                ])

                self._safe_close_serial()

                self._backoff_wait()

            except Exception as e:
                logger.error(f"Unexpected serial error: {e}")
                self._consecutive_errors += 1
                self._safe_close_serial()
                self._backoff_wait()

        # ── Cleanup ────────────────────────────────────────────────
        self._safe_close_serial()
        self.pub_socket.close()
        self.context.term()
        logger.info("Serial bridge stopped")

    def _publish_telemetry(self, data):
        """Publish telemetry data to ZMQ.

        Attaches adapter capability metadata on the first message and then
        periodically (every 50 messages) so downstream consumers like the
        VAG Audi bridge can infer transport capabilities without polling.
        """
        self._message_count += 1

        if "adapter_capabilities" not in data and self._should_attach_adapter_metadata():
            data["adapter_capabilities"] = self._build_adapter_metadata()

        payload = json.dumps(data)
        self.pub_socket.send_multipart([b"mcu/telemetry", payload.encode('utf-8')])

    def _should_attach_adapter_metadata(self) -> bool:
        """Attach metadata on the first message and then every 50 messages."""
        return self._message_count <= 1 or self._message_count % 50 == 0

    def _build_adapter_metadata(self) -> dict:
        """Build a lightweight adapter capability block for the telemetry payload."""
        transport = "simulation" if self.simulation_mode else "usb_serial"
        return {
            "adapter_kind": self._adapter_kind,
            "transport": transport,
            "device_path_or_address": self._device_path,
            "connection_state": "connected",
        }

    @staticmethod
    def _detect_adapter_kind(device_path: str) -> str:
        """Best-effort adapter type detection from the serial port listing."""
        obd_keywords = {"elm327": "elm327", "obdlink": "obdlink", "obd": "elm327"}
        try:
            for port in serial.tools.list_ports.comports():
                if port.device == device_path:
                    desc = (port.description or "").lower()
                    for keyword, kind in obd_keywords.items():
                        if keyword in desc:
                            return kind
        except OSError as exc:
            logger.debug(f"Failed to inspect adapter kind for {device_path}: {exc}")
        return "unknown"


def run_bridge():
    sim_env = os.environ.get("MIA_SERIAL_SIMULATION", "").lower()
    simulation = True if sim_env in ("1", "true", "yes") else None
    bridge = SerialBridge(simulation=simulation)
    bridge.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bridge()
