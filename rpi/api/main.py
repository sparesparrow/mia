"""
FastAPI Server for Raspberry Pi
Implements Phase 3.1: REST API Development
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import zmq
import json
import asyncio
import logging
from datetime import datetime
import psutil
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Device registry (in-memory for now)
device_registry: Dict[str, Dict[str, Any]] = {}
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


@app.on_event("startup")
async def startup_event():
    """Initialize ZeroMQ connection on startup"""
    logger.info("FastAPI server starting up...")
    logger.info("Connected to ZeroMQ router at tcp://localhost:5555")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    zmq_socket.close()
    zmq_context.term()
    logger.info("FastAPI server shutting down...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MIA Raspberry Pi API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/devices", response_model=Dict[str, Any])
async def list_devices():
    """
    GET /devices - List all connected devices
    Phase 3.1: REST API Development
    """
    return {
        "devices": list(device_registry.values()),
        "count": len(device_registry),
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
