"""
Hardware Tools for MCP Integration

Provides unified interface for GPIO, OBD, and RF operations
used by the MIA Hardware MCP Server.
"""

import asyncio
import logging
import zmq
import zmq.asyncio
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from .gpio_controller import GPIOController

logger = logging.getLogger(__name__)


class HardwareTools:
    """Unified hardware interface for MCP server"""

    def __init__(self):
        self.gpio_controller = GPIOController()
        self.zmq_context = zmq.asyncio.Context()

        # Worker addresses from environment
        self.gpio_worker_address = "tcp://127.0.0.1:5555"
        self.obd_worker_address = "tcp://127.0.0.1:5556"
        self.rf_worker_address = "tcp://127.0.0.1:5557"

        # Worker sockets
        self.gpio_socket: Optional[zmq.asyncio.Socket] = None
        self.obd_socket: Optional[zmq.asyncio.Socket] = None
        self.rf_socket: Optional[zmq.asyncio.Socket] = None

        # Initialize connections
        self._initialize_connections()

    def _initialize_connections(self):
        """Initialize ZeroMQ connections to workers"""
        try:
            # GPIO worker
            self.gpio_socket = self.zmq_context.socket(zmq.REQ)
            self.gpio_socket.connect(self.gpio_worker_address)

            # OBD worker
            self.obd_socket = self.zmq_context.socket(zmq.REQ)
            self.obd_socket.connect(self.obd_worker_address)

            # RF worker
            self.rf_socket = self.zmq_context.socket(zmq.REQ)
            self.rf_socket.connect(self.rf_worker_address)

            logger.info("Hardware worker connections initialized")

        except Exception as e:
            logger.error(f"Failed to initialize hardware connections: {e}")

    async def _send_worker_request(self, socket: zmq.asyncio.Socket, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to worker and get response"""
        try:
            await socket.send_json(request)
            response = await socket.recv_json()
            return response
        except Exception as e:
            logger.error(f"Worker request failed: {e}")
            return {"status": "error", "message": str(e)}

    # GPIO Operations
    async def set_gpio_pin(self, pin: int, state: bool, mode: str = "OUTPUT") -> Dict[str, Any]:
        """Control GPIO pins - LED lights, relays, sensors"""
        try:
            if self.gpio_socket:
                request = {
                    "command": "set_gpio",
                    "pin": pin,
                    "state": state,
                    "mode": mode
                }
                response = await self._send_worker_request(self.gpio_socket, request)
                return {
                    "status": response.get("status", "unknown"),
                    "message": f"GPIO pin {pin} set to {state} in {mode} mode",
                    "details": response
                }
            else:
                # Fallback to direct GPIO controller
                success = self.gpio_controller.set_pin_high(pin) if state else self.gpio_controller.set_pin_low(pin)
                return {
                    "status": "success" if success else "error",
                    "message": f"GPIO pin {pin} set to {state}",
                    "details": {"fallback": True}
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to set GPIO pin {pin}: {str(e)}"
            }

    # OBD Operations
    async def query_obd(self, pid: str, service: str = "CURRENT_DATA") -> Dict[str, Any]:
        """Query vehicle diagnostics - speed, engine data, DTCs"""
        try:
            if self.obd_socket:
                request = {
                    "command": "query_obd",
                    "pid": pid,
                    "service": service
                }
                response = await self._send_worker_request(self.obd_socket, request)
                return {
                    "status": response.get("status", "unknown"),
                    "message": f"OBD query for PID {pid}",
                    "data": response.get("data", {}),
                    "details": response
                }
            else:
                return {
                    "status": "error",
                    "message": "OBD worker not available"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to query OBD PID {pid}: {str(e)}"
            }

    # RF Operations
    async def start_rf_capture(self, frequency: int = 433920000,
                              modulation: str = "FSK",
                              duration_ms: int = 10000) -> Dict[str, Any]:
        """Capture RF signals - remote controls, sensors"""
        try:
            if self.rf_socket:
                request = {
                    "command": "start_capture",
                    "frequency": frequency,
                    "modulation": modulation,
                    "duration_ms": duration_ms
                }
                response = await self._send_worker_request(self.rf_socket, request)
                return {
                    "status": response.get("status", "unknown"),
                    "message": f"RF capture started on {frequency}Hz for {duration_ms}ms",
                    "data": response.get("data", {}),
                    "details": response
                }
            else:
                return {
                    "status": "error",
                    "message": "RF worker not available"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to start RF capture: {str(e)}"
            }

    async def replay_rf_signal(self, frame_data: List[int],
                              frequency: int = 433920000,
                              modulation: str = "FSK") -> Dict[str, Any]:
        """Replay RF signals - garage doors, car remotes"""
        try:
            if self.rf_socket:
                request = {
                    "command": "replay_signal",
                    "frame_data": frame_data,
                    "frequency": frequency,
                    "modulation": modulation
                }
                response = await self._send_worker_request(self.rf_socket, request)
                return {
                    "status": response.get("status", "unknown"),
                    "message": f"RF signal replayed on {frequency}Hz",
                    "details": response
                }
            else:
                return {
                    "status": "error",
                    "message": "RF worker not available"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to replay RF signal: {str(e)}"
            }

    # Additional convenience methods
    async def get_vehicle_status(self) -> Dict[str, Any]:
        """Get comprehensive vehicle status"""
        try:
            # Query common OBD PIDs
            speed = await self.query_obd("0x0D")  # Vehicle speed
            rpm = await self.query_obd("0x0C")    # Engine RPM
            temp = await self.query_obd("0x05")   # Engine coolant temperature
            fuel_level = await self.query_obd("0x2F")  # Fuel level

            return {
                "status": "success",
                "vehicle_data": {
                    "speed_kmh": speed.get("data", {}).get("value"),
                    "engine_rpm": rpm.get("data", {}).get("value"),
                    "coolant_temp_c": temp.get("data", {}).get("value"),
                    "fuel_level_percent": fuel_level.get("data", {}).get("value")
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get vehicle status: {str(e)}"
            }

    async def control_interior_lights(self, state: bool) -> Dict[str, Any]:
        """Control interior lighting"""
        # Assume interior lights are connected to GPIO pin 18
        return await self.set_gpio_pin(18, state, "OUTPUT")

    async def check_engine_diagnostics(self) -> Dict[str, Any]:
        """Check for engine trouble codes"""
        try:
            dtc_response = await self.query_obd("03", "SHOW_DTC")  # Request trouble codes
            return {
                "status": dtc_response.get("status", "unknown"),
                "trouble_codes": dtc_response.get("data", {}).get("dtcs", []),
                "message": "Engine diagnostics check completed"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check engine diagnostics: {str(e)}"
            }

    def cleanup(self):
        """Clean up connections"""
        try:
            if self.gpio_socket:
                self.gpio_socket.close()
            if self.obd_socket:
                self.obd_socket.close()
            if self.rf_socket:
                self.rf_socket.close()
            self.zmq_context.term()
            logger.info("Hardware connections cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")