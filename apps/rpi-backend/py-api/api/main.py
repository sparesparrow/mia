"""
FastAPI Server for Raspberry Pi
Implements Phase 3.1: REST API Development
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator
from typing import List, Optional, Dict, Any
import zmq
import zmq.asyncio
import json
import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime
import psutil
import os
import sys
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path for Mia package import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import device registry
try:
    from core.registry import DeviceRegistry, DeviceProfile, DeviceType, DeviceStatus
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False
    logger.warning("Device registry not available")

# Import authentication
try:
    from api.auth import require_auth, optional_auth, require_scope, APIKeyInfo
    from api.auth.api_key import get_api_key_auth
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    logger.warning("Authentication module not available")
    AUTH_AVAILABLE = False
    logger.warning("Authentication module not available")

try:
    from Mia.vehicle_codec import parse_citroen_telemetry
except ImportError:
    parse_citroen_telemetry = None
    logger.warning("Could not import Mia vehicle FlatBuffers codec. Telemetry decoding disabled.")

# Import session management
from api.sessions import (
    SessionManager, CreateSessionRequest, UpdateSessionRequest, ResumeSessionRequest
)

session_manager = SessionManager()

# ── Routers ───────────────────────────────────────────────────────────────
from api.routers.ota import router as ota_router
from api.routers.logs import router as logs_router

# ZeroMQ context and socket for messaging
zmq_context = zmq.Context()
zmq_socket = zmq_context.socket(zmq.DEALER)
zmq_socket.connect("tcp://localhost:5555")  # Connect to ZeroMQ router

# Device registry - use proper registry if available, otherwise simple dict
if REGISTRY_AVAILABLE:
    device_registry = DeviceRegistry(
        health_check_interval=5.0,
        device_timeout=30.0,
        persistence_path="/var/lib/mia/device_registry.json"
    )
else:
    device_registry = None

# Legacy simple dict for backward compatibility
device_registry_simple: Dict[str, Dict[str, Any]] = {}
telemetry_cache: Dict[str, Dict[str, Any]] = {}

# LED state tracking
led_state: Dict[str, Any] = {
    "mode": "off",
    "brightness": 128,
    "color": {"r": 255, "g": 255, "b": 255},
    "animation": "none",
    "ai_state": "idle",
    "emergency": False
}

# WebSocket connections
active_connections: List[WebSocket] = []
telemetry_tasks: List[asyncio.Task] = []

MCU_TELEMETRY_PORT = int(os.environ.get("ZMQ_MCU_PORT", "5556"))
VEHICLE_TELEMETRY_PORT = int(os.environ.get("ZMQ_VEHICLE_PORT", os.environ.get("ZMQ_PUB_PORT", "5557")))

# ── Transport health tracking ─────────────────────────────────────────
_transport_health: Dict[str, Any] = {
    "mcu_telemetry": {"connected": False, "last_message_at": None, "message_count": 0},
    "vehicle_telemetry": {"connected": False, "last_message_at": None, "message_count": 0},
    "broker": {"connected": False},
}
_api_start_time: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage API background consumers and registry lifecycle."""
    global _api_start_time
    _api_start_time = datetime.now().isoformat()
    logger.info("FastAPI server starting up...")
    logger.info("Connected to ZeroMQ router at tcp://localhost:5555")
    _transport_health["broker"]["connected"] = True

    if REGISTRY_AVAILABLE and device_registry:
        device_registry.start()
        logger.info("Device registry started")

    telemetry_tasks.clear()
    telemetry_tasks.extend(
        [
            asyncio.create_task(consume_mcu_telemetry(), name="mia-mcu-telemetry"),
            asyncio.create_task(consume_vehicle_telemetry(), name="mia-vehicle-telemetry"),
        ]
    )

    try:
        yield
    finally:
        for task in telemetry_tasks:
            task.cancel()
        for task in telemetry_tasks:
            with suppress(asyncio.CancelledError):
                await task
        telemetry_tasks.clear()

        if REGISTRY_AVAILABLE and device_registry:
            device_registry.stop()
            logger.info("Device registry stopped")

        if not zmq_socket.closed:
            zmq_socket.close(0)
        if not zmq_context.closed:
            zmq_context.term()
        logger.info("FastAPI server shutting down...")


app = FastAPI(title="MIA Raspberry Pi API", version="1.0.0", lifespan=lifespan)
app.include_router(ota_router)
app.include_router(logs_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class DeviceCommand(BaseModel):
    device: Optional[str] = None
    device_id: Optional[str] = None
    action: str
    params: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def normalize_device_field(self):
        """Accept both 'device' and 'device_id' — Android sends device_id."""
        if self.device_id and not self.device:
            self.device = self.device_id
        if not self.device:
            raise ValueError("Either 'device' or 'device_id' must be provided")
        return self


class GPIOCommand(BaseModel):
    pin: int
    direction: Optional[str] = "output"
    value: Optional[bool] = None


class TelemetryFilter(BaseModel):
    devices: Optional[List[str]] = None
    sensors: Optional[List[str]] = None


class LEDState(BaseModel):
    mode: Optional[str] = None
    brightness: Optional[int] = None
    color: Optional[Dict[str, int]] = None
    animation: Optional[str] = None
    ai_state: Optional[str] = None
    emergency: Optional[bool] = None


class LEDCommand(BaseModel):
    command: str
    params: Optional[Dict[str, Any]] = None


def _resolve_mcu_device_id(payload: Dict[str, Any]) -> str:
    for key in ("device_id", "node_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    device = payload.get("device")
    if isinstance(device, str) and device:
        if device.startswith("/dev/"):
            return f"serial-{os.path.basename(device)}"
        return device

    return "esp32-bridge"


def _sync_mcu_device_state(device_id: str, status: str, metadata: Optional[Dict[str, Any]] = None):
    metadata = {key: value for key, value in (metadata or {}).items() if value is not None}
    device_name = metadata.pop("name", device_id)
    timestamp = datetime.now().isoformat()
    device_type = getattr(DeviceType, "ESP32", getattr(DeviceType, "SERIAL", DeviceType.UNKNOWN))

    if REGISTRY_AVAILABLE and device_registry:
        profile = device_registry.get(device_id)
        if profile is None:
            profile = DeviceProfile(
                device_id=device_id,
                device_type=device_type,
                name=device_name,
                capabilities=["get_telemetry", "firmware_info"],
                metadata={"device_class": "esp32", **metadata},
            )
            device_registry.register(profile)
            profile = device_registry.get(device_id)

        if profile:
            profile.name = device_name or profile.name
            profile.metadata.update({"device_class": "esp32", **metadata})
            if status == "offline":
                profile.set_offline()
            elif status == "error":
                profile.set_error(metadata.get("error_message", "device reported an error"))
            else:
                profile.set_online()
        return

    device_entry = device_registry_simple.setdefault(
        device_id,
        {
            "device_id": device_id,
            "device_type": "esp32",
            "name": device_name,
            "capabilities": ["get_telemetry", "firmware_info"],
            "metadata": {},
        },
    )
    device_entry["name"] = device_name or device_entry["name"]
    device_entry["status"] = status
    device_entry["last_seen"] = timestamp
    device_entry["metadata"] = {**device_entry.get("metadata", {}), **metadata}
    device_entry["is_healthy"] = status == "online"
    device_entry["error_message"] = metadata.get("error_message") if status == "error" else None


def _handle_mcu_telemetry(payload: Dict[str, Any]) -> str:
    device_id = _resolve_mcu_device_id(payload)
    cache_entry = dict(telemetry_cache.get(device_id, {}))
    source_timestamp = payload.get("timestamp")

    cache_entry.update(payload)
    cache_entry["timestamp"] = datetime.now().isoformat()
    cache_entry["source"] = "mcu/telemetry"
    if source_timestamp is not None:
        cache_entry["source_timestamp"] = source_timestamp

    telemetry_cache[device_id] = cache_entry

    _transport_health["mcu_telemetry"]["connected"] = True
    _transport_health["mcu_telemetry"]["last_message_at"] = cache_entry["timestamp"]
    _transport_health["mcu_telemetry"]["message_count"] += 1

    _sync_mcu_device_state(
        device_id,
        "online",
        {
            "name": payload.get("device_name") or payload.get("name") or device_id,
            "transport": "serial",
            "last_topic": "mcu/telemetry",
        },
    )
    return device_id


def _handle_mcu_status(payload: Dict[str, Any]) -> str:
    device_id = _resolve_mcu_device_id(payload)
    cache_entry = dict(telemetry_cache.get(device_id, {}))
    event = payload.get("event", "unknown")

    cache_entry.update(
        {
            "transport_status": event,
            "transport_device": payload.get("device"),
            "transport_reason": payload.get("reason"),
            "transport_consecutive_errors": payload.get("consecutive_errors"),
            "timestamp": datetime.now().isoformat(),
            "source": "mcu/status",
        }
    )
    telemetry_cache[device_id] = {
        key: value for key, value in cache_entry.items() if value is not None
    }

    device_status = "online"
    if event == "disconnected":
        device_status = "offline"
    elif event == "error":
        device_status = "error"

    _sync_mcu_device_state(
        device_id,
        device_status,
        {
            "name": device_id,
            "transport": "serial",
            "serial_device": payload.get("device"),
            "last_topic": "mcu/status",
            "error_message": payload.get("reason"),
        },
    )
    return device_id


def _build_telemetry_source_summary() -> Dict[str, Any]:
    """Build a compact summary of known telemetry sources, freshness, and adapter info."""
    sources: Dict[str, Any] = {}
    now = datetime.now()

    for device_id, entry in telemetry_cache.items():
        ts_raw = entry.get("timestamp")
        age_seconds = None
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                age_seconds = round((now - ts).total_seconds(), 1)
            except (ValueError, TypeError):
                pass

        source_info: Dict[str, Any] = {
            "last_update": ts_raw,
            "age_seconds": age_seconds,
            "source": entry.get("source"),
        }

        adapter_caps = entry.get("adapter_capabilities")
        if adapter_caps:
            source_info["adapter_kind"] = adapter_caps.get("adapter_kind")
            source_info["capability_class"] = adapter_caps.get("capability_class")
            source_info["connection_state"] = adapter_caps.get("connection_state")

        sources[device_id] = source_info

    return sources


async def consume_mcu_telemetry():
    """
    Background task to consume JSON telemetry/status emitted by the serial bridge.
    """
    ctx = zmq.asyncio.Context()
    sub = ctx.socket(zmq.SUB)

    try:
        sub.connect(f"tcp://localhost:{MCU_TELEMETRY_PORT}")
        sub.setsockopt(zmq.SUBSCRIBE, b"mcu/telemetry")
        sub.setsockopt(zmq.SUBSCRIBE, b"mcu/status")
        logger.info(f"Connected to MCU telemetry subscriber on tcp://localhost:{MCU_TELEMETRY_PORT}")

        while True:
            try:
                parts = await sub.recv_multipart()
                if len(parts) != 2:
                    logger.warning(f"Unexpected MCU telemetry frame count: {len(parts)}")
                    continue

                topic = parts[0].decode("utf-8")
                payload = json.loads(parts[1].decode("utf-8"))

                if topic == "mcu/telemetry":
                    _handle_mcu_telemetry(payload)
                elif topic == "mcu/status":
                    _handle_mcu_status(payload)

            except asyncio.CancelledError:
                raise
            except json.JSONDecodeError as e:
                logger.warning(f"Malformed MCU JSON payload: {e}")
            except Exception as e:
                logger.error(f"Error processing MCU telemetry message: {e}")
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("MCU telemetry consumer cancelled")
        raise
    except Exception as e:
        logger.error(f"Failed to start MCU telemetry consumer: {e}")
    finally:
        sub.close(0)
        ctx.term()


async def consume_vehicle_telemetry():
    """
    Background task to consume vehicle telemetry from ZMQ PUB socket.
    Decodes FlatBuffers messages and updates the telemetry cache.
    """
    ctx = zmq.asyncio.Context()
    sub = ctx.socket(zmq.SUB)

    try:
        sub.connect(f"tcp://localhost:{VEHICLE_TELEMETRY_PORT}")
        sub.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to vehicle telemetry subscriber on tcp://localhost:{VEHICLE_TELEMETRY_PORT}")

        while True:
            try:
                # Receive raw FlatBuffers data
                msg = await sub.recv()

                if parse_citroen_telemetry:
                    data = parse_citroen_telemetry(msg, require_identifier=True)
                    source_timestamp_ms = data.pop("timestamp", 0)
                    data["timestamp"] = datetime.now().isoformat()
                    if source_timestamp_ms:
                        data["source_timestamp_ms"] = source_timestamp_ms

                    # Update global cache
                    telemetry_cache["vehicle"] = data

                    _transport_health["vehicle_telemetry"]["connected"] = True
                    _transport_health["vehicle_telemetry"]["last_message_at"] = data["timestamp"]
                    _transport_health["vehicle_telemetry"]["message_count"] += 1

                else:
                    # Wait a bit if we can't decode to avoid tight loop if something is spamming
                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error processing telemetry message: {e}")
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Vehicle telemetry consumer cancelled")
        raise
    except Exception as e:
        logger.error(f"Failed to start telemetry consumer: {e}")
    finally:
        sub.close(0)
        ctx.term()


@app.get("/")
async def root():
    """Root endpoint"""
    auth_status = "disabled"
    if AUTH_AVAILABLE:
        auth = get_api_key_auth()
        auth_status = "enabled" if auth.enabled else "disabled"

    return {
        "service": "MIA Raspberry Pi API",
        "version": "1.0.0",
        "status": "running",
        "auth": auth_status,
        "registry": "enabled" if REGISTRY_AVAILABLE else "disabled"
    }


@app.get("/auth/status")
async def auth_status():
    """
    GET /auth/status - Check authentication status
    """
    if not AUTH_AVAILABLE:
        return {
            "enabled": False,
            "message": "Authentication module not available"
        }
    
    auth = get_api_key_auth()
    return {
        "enabled": auth.enabled,
        "keys_configured": len(auth.list_keys()),
        "message": "Authentication enabled" if auth.enabled else "Authentication disabled (set MIA_API_KEY env var)"
    }


@app.get("/devices", response_model=Dict[str, Any])
async def list_devices():
    """
    GET /devices - List all connected devices
    Phase 3.1: REST API Development
    """
    if REGISTRY_AVAILABLE and device_registry:
        devices = device_registry.get_all()
        return {
            "devices": [d.to_dict() for d in devices],
            "count": len(devices),
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "devices": list(device_registry_simple.values()),
            "count": len(device_registry_simple),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# Device Registry Endpoints (Phase 2.3)
# ============================================================================

class DeviceRegistration(BaseModel):
    """Model for device registration"""
    device_id: str
    device_type: str
    name: Optional[str] = None
    capabilities: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@app.get("/registry/status", response_model=Dict[str, Any])
async def get_registry_status():
    """
    GET /registry/status - Get device registry status summary
    """
    if not REGISTRY_AVAILABLE or not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")

    return device_registry.get_status_summary()


@app.get("/registry/devices", response_model=Dict[str, Any])
async def get_registry_devices(
    device_type: Optional[str] = None,
    capability: Optional[str] = None,
    healthy_only: bool = False
):
    """
    GET /registry/devices - List devices with optional filters

    Query parameters:
    - device_type: Filter by device type (gpio, obd, serial, etc.)
    - capability: Filter by capability
    - healthy_only: Only return healthy (online and recently seen) devices
    """
    if not REGISTRY_AVAILABLE or not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")

    if healthy_only:
        devices = device_registry.get_healthy()
    elif device_type:
        try:
            dtype = DeviceType(device_type)
            devices = device_registry.get_by_type(dtype)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid device type: {device_type}")
    elif capability:
        devices = device_registry.get_by_capability(capability)
    else:
        devices = device_registry.get_all()

    return {
        "devices": [d.to_dict() for d in devices],
        "count": len(devices),
        "filters": {
            "device_type": device_type,
            "capability": capability,
            "healthy_only": healthy_only
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/registry/devices/{device_id}", response_model=Dict[str, Any])
async def get_registry_device(device_id: str):
    """
    GET /registry/devices/{device_id} - Get specific device by ID
    """
    if not REGISTRY_AVAILABLE or not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")

    device = device_registry.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    return {
        "device": device.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/registry/devices", response_model=Dict[str, Any])
async def register_device(registration: DeviceRegistration):
    """
    POST /registry/devices - Register a new device

    This endpoint is primarily for testing or manual device registration.
    In production, devices typically self-register via ZMQ.
    """
    if not REGISTRY_AVAILABLE or not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")

    try:
        dtype = DeviceType(registration.device_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid device type: {registration.device_type}")

    profile = DeviceProfile(
        device_id=registration.device_id,
        device_type=dtype,
        name=registration.name or "",
        capabilities=registration.capabilities or [],
        metadata=registration.metadata or {}
    )

    device_registry.register(profile)

    return {
        "success": True,
        "device": profile.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


@app.delete("/registry/devices/{device_id}", response_model=Dict[str, Any])
async def unregister_device(device_id: str):
    """
    DELETE /registry/devices/{device_id} - Unregister a device
    """
    if not REGISTRY_AVAILABLE or not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")

    if not device_registry.unregister(device_id):
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    return {
        "success": True,
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/registry/devices/{device_id}/heartbeat", response_model=Dict[str, Any])
async def device_heartbeat(device_id: str):
    """
    POST /registry/devices/{device_id}/heartbeat - Send device heartbeat
    """
    if not REGISTRY_AVAILABLE or not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")

    if not device_registry.heartbeat(device_id):
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    return {
        "success": True,
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/command")
async def send_command(command: DeviceCommand):
    """
    POST /command - Send command to device
    Phase 3.1: REST API Development
    """
    try:
        # Send command via ZeroMQ
        message = {
            "type": "DEVICE_COMMAND",
            "device": command.device,
            "action": command.action,
            "params": command.params or {},
            "timestamp": datetime.now().isoformat()
        }
        
        zmq_socket.send_multipart([b"", json.dumps(message).encode()])

        # Wait for response (with timeout)
        poller = zmq.Poller()
        poller.register(zmq_socket, zmq.POLLIN)

        if poller.poll(5000):  # 5 second timeout
            parts = zmq_socket.recv_multipart()
            response = json.loads(parts[-1])
            return {
                "success": True,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Command timeout - no response from device",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/telemetry")
async def get_telemetry(filter: Optional[TelemetryFilter] = None):
    """
    GET /telemetry - Fetch latest sensor readings
    Phase 3.1: REST API Development
    """
    if filter and filter.devices:
        # Filter by devices
        filtered_telemetry = {
            device: telemetry_cache.get(device, {})
            for device in filter.devices
            if device in telemetry_cache
        }
        return {
            "telemetry": filtered_telemetry,
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "telemetry": telemetry_cache,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/led/state")
async def get_led_state():
    """
    GET /led/state - Get current LED state
    """
    return {
        "led_state": led_state,
        "timestamp": datetime.now().isoformat()
    }


@app.put("/led/state")
async def set_led_state(state: LEDState):
    """
    PUT /led/state - Update LED state
    """
    global led_state

    # Update only provided fields
    for field, value in state.dict(exclude_unset=True).items():
        if value is not None:
            led_state[field] = value

    # Send command to LED controller via ZeroMQ
    try:
        message = {
            "type": "LED_COMMAND",
            "command": "set_state",
            "params": led_state,
            "timestamp": datetime.now().isoformat()
        }

        zmq_socket.send_multipart([b"", json.dumps(message).encode()])

        # Update local state immediately for responsiveness
        return {
            "success": True,
            "led_state": led_state,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error updating LED state: {e}")
        return {
            "success": False,
            "error": str(e),
            "led_state": led_state,
            "timestamp": datetime.now().isoformat()
        }


@app.post("/led/command")
async def send_led_command(command: LEDCommand):
    """
    POST /led/command - Send LED control command
    """
    try:
        message = {
            "type": "LED_COMMAND",
            "command": command.command,
            "params": command.params or {},
            "timestamp": datetime.now().isoformat()
        }

        zmq_socket.send_multipart([b"", json.dumps(message).encode()])

        return {
            "success": True,
            "command": command.command,
            "params": command.params,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending LED command: {e}")
        return {
            "success": False,
            "error": str(e),
            "command": command.command,
            "timestamp": datetime.now().isoformat()
        }


@app.get("/status")
async def get_status():
    """
    GET /status - System health and uptime
    Phase 3.1: REST API Development
    """
    try:
        # Get system information
        uptime_seconds = psutil.boot_time()
        uptime = datetime.now() - datetime.fromtimestamp(uptime_seconds)
        
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            "status": "healthy",
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime),
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "devices_connected": len(device_registry.get_all()) if (REGISTRY_AVAILABLE and device_registry) else len(device_registry_simple),
            "telemetry_sources": _build_telemetry_source_summary(),
            "transport_health": _transport_health,
            "api_start_time": _api_start_time,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time telemetry streaming
    Phase 3.2: WebSocket Real-Time Telemetry
    """
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket client connected. Total connections: {len(active_connections)}")
    
    try:
        while True:
            # Send telemetry updates every 100ms (10Hz)
            await asyncio.sleep(0.1)
            
            # Broadcast latest telemetry and LED state to all connected clients
            data = {}
            if telemetry_cache:
                data["telemetry"] = telemetry_cache
            data["led_state"] = led_state

            if data:
                await websocket.send_json({
                    "type": "telemetry",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining connections: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.websocket("/ws/telemetry")
async def telemetry_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for telemetry and LED control - Android app compatible
    """
    await websocket.accept()
    logger.info("Android telemetry WebSocket client connected")

    try:
        while True:
            # Send telemetry and LED state updates every 100ms (10Hz)
            await asyncio.sleep(0.1)

            # Prepare data for Android app
            data = {
                "telemetry": telemetry_cache,
                "led_state": led_state,
                "timestamp": datetime.now().isoformat()
            }

            await websocket.send_json(data)
    except WebSocketDisconnect:
        logger.info("Android telemetry WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Telemetry WebSocket error: {e}")


@app.post("/gpio/configure")
async def configure_gpio(gpio: GPIOCommand):
    """Configure GPIO pin"""
    try:
        message = {
            "type": "GPIO_CONFIGURE",
            "pin": gpio.pin,
            "direction": gpio.direction,
            "timestamp": datetime.now().isoformat()
        }
        
        zmq_socket.send_multipart([b"", json.dumps(message).encode()])

        poller = zmq.Poller()
        poller.register(zmq_socket, zmq.POLLIN)

        if poller.poll(5000):
            parts = zmq_socket.recv_multipart()
            response = json.loads(parts[-1])
            return {"success": True, "response": response}
        else:
            return {"success": False, "error": "Timeout"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gpio/set")
async def set_gpio(gpio: GPIOCommand):
    """Set GPIO pin value"""
    try:
        message = {
            "type": "GPIO_SET",
            "pin": gpio.pin,
            "value": gpio.value,
            "timestamp": datetime.now().isoformat()
        }

        zmq_socket.send_multipart([b"", json.dumps(message).encode()])

        poller = zmq.Poller()
        poller.register(zmq_socket, zmq.POLLIN)

        if poller.poll(5000):
            parts = zmq_socket.recv_multipart()
            response = json.loads(parts[-1])
            return {"success": True, "response": response}
        else:
            return {"success": False, "error": "Timeout"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gpio/{pin}")
async def get_gpio(pin: int):
    """Get GPIO pin value"""
    try:
        message = {
            "type": "GPIO_GET",
            "pin": pin,
            "timestamp": datetime.now().isoformat()
        }

        zmq_socket.send_multipart([b"", json.dumps(message).encode()])

        poller = zmq.Poller()
        poller.register(zmq_socket, zmq.POLLIN)

        if poller.poll(5000):
            parts = zmq_socket.recv_multipart()
            response = json.loads(parts[-1])
            return {"success": True, "response": response}
        else:
            return {"success": False, "error": "Timeout"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Device Alias Endpoints (Android compatibility)
# ============================================================================

@app.get("/devices/{device_id}", response_model=Dict[str, Any])
async def get_device_alias(device_id: str):
    """GET /devices/{device_id} — alias for /registry/devices/{device_id}"""
    return await get_registry_device(device_id)


@app.delete("/devices/{device_id}", response_model=Dict[str, Any])
async def delete_device_alias(device_id: str):
    """DELETE /devices/{device_id} — alias for /registry/devices/{device_id}"""
    return await unregister_device(device_id)


@app.post("/devices/{device_id}/heartbeat", response_model=Dict[str, Any])
async def device_heartbeat_alias(device_id: str):
    """POST /devices/{device_id}/heartbeat — alias for /registry/devices/{device_id}/heartbeat"""
    return await device_heartbeat(device_id)


# ============================================================================
# Session Management Endpoints
# ============================================================================

@app.post("/sessions", response_model=Dict[str, Any])
async def create_session(req: CreateSessionRequest):
    """POST /sessions — create a client session"""
    session = session_manager.create(req)
    return {
        "session": session.model_dump(mode="json"),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str):
    """GET /sessions/{session_id} — get session state"""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session": session.model_dump(mode="json"),
        "timestamp": datetime.now().isoformat()
    }


@app.patch("/sessions/{session_id}", response_model=Dict[str, Any])
async def update_session(session_id: str, req: UpdateSessionRequest):
    """PATCH /sessions/{session_id} — update subscriptions/metadata"""
    session = session_manager.update(session_id, req)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session": session.model_dump(mode="json"),
        "timestamp": datetime.now().isoformat()
    }


@app.delete("/sessions/{session_id}", response_model=Dict[str, Any])
async def delete_session(session_id: str):
    """DELETE /sessions/{session_id} — end session"""
    if not session_manager.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "success": True,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/sessions/{session_id}/handoff", response_model=Dict[str, Any])
async def session_handoff(session_id: str):
    """POST /sessions/{session_id}/handoff — generate handoff token (5 min TTL)"""
    token = session_manager.generate_handoff(session_id)
    if not token:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "handoff_token": token,
        "expires_in_seconds": 300,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/sessions/resume", response_model=Dict[str, Any])
async def resume_session(req: ResumeSessionRequest):
    """POST /sessions/resume — resume session with handoff token"""
    session = session_manager.resume_with_token(req.handoff_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired handoff token")
    return {
        "session": session.model_dump(mode="json"),
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# Feature Catalog Endpoint
# ============================================================================

@app.get("/features", response_model=Dict[str, Any])
async def get_features(category: Optional[str] = None, state: Optional[str] = None):
    """GET /features — serve the feature catalog as JSON.

    Query parameters:
    - category: filter by category name (e.g. 'automotive', 'voice')
    - state: filter by development state (IDEA, PLANNED, IMPLEMENTED, TESTED, QA, DEPLOYED)
    """
    catalog_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'docs', 'FEATURE_CATALOG.yaml'),
        '/opt/mia/docs/FEATURE_CATALOG.yaml',
    ]
    catalog = None
    for p in catalog_paths:
        try:
            with open(p) as f:
                catalog = yaml.safe_load(f)
            break
        except FileNotFoundError:
            continue

    if not catalog:
        raise HTTPException(status_code=404, detail="Feature catalog not found")

    categories = catalog.get("categories", {})

    if category:
        categories = {k: v for k, v in categories.items() if k == category}

    if state:
        state_upper = state.upper()
        categories = {
            k: [feat for feat in v if feat.get("state") == state_upper]
            for k, v in categories.items()
        }
        categories = {k: v for k, v in categories.items() if v}

    # Compute summary counts
    all_features = [f for feats in categories.values() for f in feats]
    summary = {}
    for f in all_features:
        s = f.get("state", "UNKNOWN")
        summary[s] = summary.get(s, 0) + 1

    return {
        "categories": categories,
        "total": len(all_features),
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# Thermal Health Endpoint
# ============================================================================

@app.get("/health/thermal", response_model=Dict[str, Any])
async def get_thermal_health():
    """GET /health/thermal — SoC temperature and thermal status."""
    thermal_path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(thermal_path) as f:
            temp_millic = int(f.read().strip())
        temp_c = temp_millic / 1000.0
    except (FileNotFoundError, ValueError):
        temp_c = None

    if temp_c is None:
        status = "unavailable"
    elif temp_c >= 90:
        status = "critical"
    elif temp_c >= 80:
        status = "throttle"
    elif temp_c >= 70:
        status = "warning"
    else:
        status = "normal"

    return {
        "temperature_c": temp_c,
        "status": status,
        "thresholds": {"warning": 70, "throttle": 80, "critical": 90},
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn

    # Read port from shared config, fallback to 8000
    config_port = 8000
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'contracts', 'config.json')
        with open(config_path) as f:
            config_port = json.load(f).get("api", {}).get("port", 8000)
    except Exception:
        pass

    uvicorn.run(app, host="0.0.0.0", port=config_port)
