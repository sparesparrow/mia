"""
FastAPI Server for Hardware Management
Phase 3: FastAPI & Remote Control

Provides REST and WebSocket APIs for hardware control and monitoring,
integrating with the ZeroMQ messaging layer and hardware abstraction.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from ..hardware import HardwareManager
except ImportError as e:
    HardwareManager = None

try:
    from ..core.messaging.client import MessagingClient
except ImportError as e:
    MessagingClient = None

logger = logging.getLogger(__name__)

# Global hardware manager instance
hardware_manager: Optional[HardwareManager] = None

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []


# ============================================================================
# Pydantic Models for API
# ============================================================================

class GPIOConfig(BaseModel):
    """GPIO pin configuration"""
    pin: int = Field(..., ge=0, le=40, description="GPIO pin number (0-40)")
    mode: str = Field(..., pattern="^(input|output)$", description="Pin mode")
    name: Optional[str] = Field(None, description="Optional pin name")


class GPIOValue(BaseModel):
    """GPIO pin value"""
    pin: int = Field(..., ge=0, le=40, description="GPIO pin number")
    value: bool = Field(..., description="Pin value")


class SensorRegistration(BaseModel):
    """Sensor registration"""
    sensor_id: str = Field(..., description="Unique sensor identifier")
    sensor_type: str = Field(..., pattern="^(temperature|humidity|pressure|distance|light|motion|gas)$",
                             description="Type of sensor")
    location: Optional[str] = Field(None, description="Physical location")


class ArduinoCommand(BaseModel):
    """Arduino command"""
    port: str = Field(..., description="Serial port path")
    command: str = Field(..., description="Command to send")
    params: Optional[Dict[str, Any]] = Field(None, description="Command parameters")


class TelemetryFilter(BaseModel):
    """Telemetry filtering options"""
    sensor_ids: Optional[List[str]] = Field(None, description="Specific sensor IDs to include")
    sensor_types: Optional[List[str]] = Field(None, description="Sensor types to include")
    device_ids: Optional[List[str]] = Field(None, description="Device IDs to include")


class DeviceCommand(BaseModel):
    """Generic device command"""
    device_id: str = Field(..., description="Target device ID")
    action: str = Field(..., description="Action to perform")
    params: Optional[Dict[str, Any]] = Field(None, description="Action parameters")


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global hardware_manager

    # Startup
    logger.info("Starting MIA Hardware API server...")

    # Initialize hardware manager
    hardware_manager = HardwareManager()
    await hardware_manager.initialize()

    # Setup event handlers for WebSocket broadcasting
    hardware_manager.on_sensor_reading(broadcast_sensor_reading)

    logger.info("MIA Hardware API server started")

    yield

    # Shutdown
    logger.info("Shutting down MIA Hardware API server...")
    if hardware_manager:
        await hardware_manager.shutdown()
    logger.info("MIA Hardware API server stopped")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="MIA Hardware Management API",
    description="REST and WebSocket APIs for hardware control and monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# WebSocket Broadcasting
# ============================================================================

async def broadcast_sensor_reading(reading):
    """Broadcast sensor readings to all WebSocket clients"""
    message = {
        "type": "sensor_reading",
        "data": {
            "sensor_id": reading.sensor_id,
            "sensor_type": reading.sensor_type.value,
            "value": reading.value,
            "unit": reading.unit,
            "timestamp": reading.timestamp,
            "metadata": reading.metadata
        },
        "timestamp": datetime.now().isoformat()
    }

    # Broadcast to all connected WebSocket clients
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.append(connection)

    # Remove disconnected clients
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


async def broadcast_hardware_status():
    """Broadcast hardware status updates"""
    if hardware_manager:
        summary = hardware_manager.get_hardware_summary()
        message = {
            "type": "hardware_status",
            "data": summary,
            "timestamp": datetime.now().isoformat()
        }

        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            if conn in active_connections:
                active_connections.remove(conn)


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "MIA Hardware Management API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "GET /health",
            "GET /hardware/status",
            "POST /gpio/configure",
            "POST /gpio/set",
            "GET /gpio/{pin}",
            "POST /sensors/register",
            "GET /sensors/readings",
            "GET /arduino/devices",
            "POST /arduino/command",
            "WS /ws"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        summary = hardware_manager.get_hardware_summary()
        return {
            "status": "healthy" if summary["initialized"] else "initializing",
            "hardware_manager": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/hardware/status")
async def get_hardware_status():
    """Get comprehensive hardware status"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        summary = hardware_manager.get_hardware_summary()
        return {
            "hardware": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Hardware status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hardware status retrieval failed: {str(e)}")


# ============================================================================
# GPIO Endpoints
# ============================================================================

@app.post("/gpio/configure")
async def configure_gpio(config: GPIOConfig):
    """Configure a GPIO pin"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        mode = config.mode == "output"
        success = await hardware_manager.register_gpio_pin(config.pin, mode, config.name)

        if success:
            return {
                "success": True,
                "pin": config.pin,
                "mode": config.mode,
                "message": f"GPIO pin {config.pin} configured as {config.mode}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to configure GPIO pin {config.pin}")

    except Exception as e:
        logger.error(f"GPIO configuration failed: {e}")
        raise HTTPException(status_code=500, detail=f"GPIO configuration failed: {str(e)}")


@app.post("/gpio/set")
async def set_gpio_pin(value: GPIOValue):
    """Set GPIO pin value"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        success = await hardware_manager.set_gpio_pin(value.pin, value.value)

        if success:
            return {
                "success": True,
                "pin": value.pin,
                "value": value.value,
                "message": f"GPIO pin {value.pin} set to {value.value}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to set GPIO pin {value.pin}")

    except Exception as e:
        logger.error(f"GPIO set failed: {e}")
        raise HTTPException(status_code=500, detail=f"GPIO set failed: {str(e)}")


@app.get("/gpio/{pin}")
async def get_gpio_pin(pin: int):
    """Get GPIO pin value"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    if pin < 0 or pin > 40:
        raise HTTPException(status_code=400, detail="Invalid pin number (0-40)")

    try:
        value = await hardware_manager.get_gpio_pin(pin)
        return {
            "success": True,
            "pin": pin,
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"GPIO read failed: {e}")
        raise HTTPException(status_code=500, detail=f"GPIO read failed: {str(e)}")


@app.get("/gpio/status")
async def get_gpio_status():
    """Get GPIO system status"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        status = await hardware_manager.get_gpio_status()
        return {
            "gpio": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"GPIO status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"GPIO status retrieval failed: {str(e)}")


# ============================================================================
# Sensor Endpoints
# ============================================================================

@app.post("/sensors/register")
async def register_sensor(registration: SensorRegistration):
    """Register a sensor"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        success = await hardware_manager.register_sensor(
            registration.sensor_type,
            registration.sensor_id,
            registration.location
        )

        if success:
            return {
                "success": True,
                "sensor_id": registration.sensor_id,
                "sensor_type": registration.sensor_type,
                "message": f"Sensor {registration.sensor_id} registered successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to register sensor {registration.sensor_id}")

    except Exception as e:
        logger.error(f"Sensor registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sensor registration failed: {str(e)}")


@app.get("/sensors/readings")
async def get_sensor_readings(filter_params: TelemetryFilter = None):
    """Get sensor readings with optional filtering"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        readings = await hardware_manager.read_all_sensors()

        # Apply filters if provided
        if filter_params:
            if filter_params.sensor_ids:
                readings = [r for r in readings if r.sensor_id in filter_params.sensor_ids]
            if filter_params.sensor_types:
                readings = [r for r in readings if r.sensor_type.value in filter_params.sensor_types]

        return {
            "readings": [
                {
                    "sensor_id": r.sensor_id,
                    "sensor_type": r.sensor_type.value,
                    "value": r.value,
                    "unit": r.unit,
                    "timestamp": r.timestamp,
                    "metadata": r.metadata
                }
                for r in readings
            ],
            "count": len(readings),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Sensor readings retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sensor readings retrieval failed: {str(e)}")


@app.get("/sensors/status")
async def get_sensor_status():
    """Get sensor system status"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        status = hardware_manager.get_sensor_status()
        return {
            "sensors": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Sensor status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sensor status retrieval failed: {str(e)}")


# ============================================================================
# Arduino Endpoints
# ============================================================================

@app.get("/arduino/devices")
async def get_arduino_devices():
    """Get discovered Arduino devices"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        devices = await hardware_manager.discover_arduino_devices()
        return {
            "devices": [
                {
                    "port": d.port,
                    "board_type": d.board_type,
                    "firmware_version": d.firmware_version,
                    "capabilities": d.capabilities,
                    "last_seen": d.last_seen
                }
                for d in devices
            ],
            "count": len(devices),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Arduino device discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Arduino device discovery failed: {str(e)}")


@app.post("/arduino/connect")
async def connect_arduino_device(port: str):
    """Connect to an Arduino device"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        success = await hardware_manager.connect_arduino_device(port)

        if success:
            return {
                "success": True,
                "port": port,
                "message": f"Connected to Arduino on {port}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Arduino on {port}")

    except Exception as e:
        logger.error(f"Arduino connection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Arduino connection failed: {str(e)}")


@app.post("/arduino/command")
async def send_arduino_command(cmd: ArduinoCommand):
    """Send command to Arduino device"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        response = await hardware_manager.send_arduino_command(
            cmd.port, cmd.command, **(cmd.params or {})
        )

        return {
            "success": True,
            "port": cmd.port,
            "command": cmd.command,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Arduino command failed: {e}")
        raise HTTPException(status_code=500, detail=f"Arduino command failed: {str(e)}")


# ============================================================================
# Device Management Endpoints
# ============================================================================

@app.get("/devices")
async def list_devices():
    """List all registered devices"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        devices = hardware_manager.registry.get_all()
        return {
            "devices": [d.to_dict() for d in devices],
            "count": len(devices),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Device listing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Device listing failed: {str(e)}")


@app.post("/devices/command")
async def send_device_command(command: DeviceCommand):
    """Send command to a device (generic interface)"""
    if not hardware_manager:
        raise HTTPException(status_code=503, detail="Hardware manager not initialized")

    try:
        # For now, this is a placeholder - in a full implementation,
        # this would route commands to appropriate device handlers
        logger.info(f"Device command: {command.device_id} -> {command.action}")

        return {
            "success": True,
            "device_id": command.device_id,
            "action": command.action,
            "message": f"Command sent to device {command.device_id}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Device command failed: {e}")
        raise HTTPException(status_code=500, detail=f"Device command failed: {str(e)}")


# ============================================================================
# WebSocket Endpoint
# ============================================================================

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
        # Send initial hardware status
        if hardware_manager:
            await broadcast_hardware_status()

        # Keep connection alive and handle client messages
        while True:
            try:
                # Receive message from client (optional)
                data = await websocket.receive_json()

                # Handle client commands if needed
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })

            except Exception:
                # Client may have disconnected or sent invalid data
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"WebSocket client cleanup. Remaining connections: {len(active_connections)}")


# ============================================================================
# Background Tasks
# ============================================================================

async def background_monitoring():
    """Background task for periodic hardware monitoring"""
    while True:
        try:
            if hardware_manager and active_connections:
                # Broadcast hardware status updates periodically
                await broadcast_hardware_status()

                # Read sensors periodically for real-time updates
                await hardware_manager.read_all_sensors()

        except Exception as e:
            logger.error(f"Background monitoring error: {e}")

        await asyncio.sleep(5.0)  # Update every 5 seconds


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    # Start background monitoring
    asyncio.create_task(background_monitoring())
    logger.info("Background monitoring started")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Application shutdown complete")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "rpi.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )