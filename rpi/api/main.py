"""
FastAPI Server for Raspberry Pi
Implements Phase 3.1: REST API Development
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import zmq
<<<<<<< HEAD
=======
import zmq.asyncio
>>>>>>> 5376269 (rebase)
import json
import asyncio
import logging
from datetime import datetime
import psutil
import os
<<<<<<< HEAD
=======
import sys
>>>>>>> 5376269 (rebase)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

<<<<<<< HEAD
=======
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
except ImportError:
    AUTH_AVAILABLE = False
    logger.warning("Authentication module not available")

try:
    import Mia.Vehicle.CitroenTelemetry as CitroenTelemetry
    import Mia.Vehicle.DpfStatus as DpfStatus
except ImportError:
    CitroenTelemetry = None
    DpfStatus = None
    logger.warning("Could not import Mia.Vehicle FlatBuffers bindings. Telemetry decoding disabled.")

>>>>>>> 5376269 (rebase)
app = FastAPI(title="MIA Raspberry Pi API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ZeroMQ context and socket for messaging
zmq_context = zmq.Context()
zmq_socket = zmq_context.socket(zmq.DEALER)
zmq_socket.connect("tcp://localhost:5555")  # Connect to ZeroMQ router

<<<<<<< HEAD
# Device registry (in-memory for now)
device_registry: Dict[str, Dict[str, Any]] = {}
=======
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
>>>>>>> 5376269 (rebase)
telemetry_cache: Dict[str, Dict[str, Any]] = {}

# WebSocket connections
active_connections: List[WebSocket] = []


# Pydantic models
class DeviceCommand(BaseModel):
    device: str
    action: str
    params: Optional[Dict[str, Any]] = None


class GPIOCommand(BaseModel):
    pin: int
    direction: Optional[str] = "output"
    value: Optional[bool] = None


class TelemetryFilter(BaseModel):
    devices: Optional[List[str]] = None
    sensors: Optional[List[str]] = None


<<<<<<< HEAD
=======
async def consume_telemetry():
    """
    Background task to consume vehicle telemetry from ZMQ PUB socket.
    Decodes FlatBuffers messages and updates the telemetry cache.
    """
    ctx = zmq.asyncio.Context()
    sub = ctx.socket(zmq.SUB)
    port = int(os.environ.get('ZMQ_PUB_PORT', 5557))
    
    try:
        sub.connect(f"tcp://localhost:{port}")
        sub.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to vehicle telemetry subscriber on tcp://localhost:{port}")
        
        while True:
            try:
                # Receive raw FlatBuffers data
                msg = await sub.recv()
                
                if CitroenTelemetry:
                    # Decode FlatBuffers message
                    telemetry = CitroenTelemetry.CitroenTelemetry.GetRootAs(msg, 0)
                    
                    data = {
                        "rpm": round(telemetry.Rpm(), 1),
                        "speed_kmh": round(telemetry.SpeedKmh(), 1),
                        "coolant_temp_c": round(telemetry.CoolantTempC(), 1),
                        "dpf_soot_mass_g": round(telemetry.DpfSootMassG(), 2),
                        "oil_temp_c": round(telemetry.OilTemperatureC(), 1),
                        "eolys_level_pct": round(telemetry.EolysAdditiveLevelPercent(), 1),
                        "eolys_level_l": round(telemetry.EolysAdditiveLevelL(), 2),
                        "dpf_status": telemetry.DpfRegenerationStatus(),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Update global cache
                    telemetry_cache["vehicle"] = data
                    
                else:
                    # Wait a bit if we can't decode to avoid tight loop if something is spamming
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error processing telemetry message: {e}")
                await asyncio.sleep(1)
                
    except Exception as e:
        logger.error(f"Failed to start telemetry consumer: {e}")


>>>>>>> 5376269 (rebase)
@app.on_event("startup")
async def startup_event():
    """Initialize ZeroMQ connection on startup"""
    logger.info("FastAPI server starting up...")
    logger.info("Connected to ZeroMQ router at tcp://localhost:5555")
<<<<<<< HEAD
=======
    
    # Start device registry
    if REGISTRY_AVAILABLE and device_registry:
        device_registry.start()
        logger.info("Device registry started")
    
    # Start telemetry consumer background task
    asyncio.create_task(consume_telemetry())
>>>>>>> 5376269 (rebase)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
<<<<<<< HEAD
=======
    # Stop device registry
    if REGISTRY_AVAILABLE and device_registry:
        device_registry.stop()
        logger.info("Device registry stopped")
    
>>>>>>> 5376269 (rebase)
    zmq_socket.close()
    zmq_context.term()
    logger.info("FastAPI server shutting down...")


@app.get("/")
async def root():
    """Root endpoint"""
<<<<<<< HEAD
    return {
        "service": "MIA Raspberry Pi API",
        "version": "1.0.0",
        "status": "running"
=======
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
>>>>>>> 5376269 (rebase)
    }


@app.get("/devices", response_model=Dict[str, Any])
async def list_devices():
    """
    GET /devices - List all connected devices
    Phase 3.1: REST API Development
    """
<<<<<<< HEAD
    return {
        "devices": list(device_registry.values()),
        "count": len(device_registry),
=======
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
>>>>>>> 5376269 (rebase)
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
        
        zmq_socket.send_json(message)
        
        # Wait for response (with timeout)
        poller = zmq.Poller()
        poller.register(zmq_socket, zmq.POLLIN)
        
        if poller.poll(5000):  # 5 second timeout
            response = zmq_socket.recv_json()
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
            "devices_connected": len(device_registry),
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
            
            # Broadcast latest telemetry to all connected clients
            if telemetry_cache:
                await websocket.send_json({
                    "type": "telemetry",
                    "data": telemetry_cache,
                    "timestamp": datetime.now().isoformat()
                })
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining connections: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


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
        
        zmq_socket.send_json(message)
        
        poller = zmq.Poller()
        poller.register(zmq_socket, zmq.POLLIN)
        
        if poller.poll(5000):
            response = zmq_socket.recv_json()
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
        
        zmq_socket.send_json(message)
        
        poller = zmq.Poller()
        poller.register(zmq_socket, zmq.POLLIN)
        
        if poller.poll(5000):
            response = zmq_socket.recv_json()
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
        
        zmq_socket.send_json(message)
        
        poller = zmq.Poller()
        poller.register(zmq_socket, zmq.POLLIN)
        
        if poller.poll(5000):
            response = zmq_socket.recv_json()
            return {"success": True, "response": response}
        else:
            return {"success": False, "error": "Timeout"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
