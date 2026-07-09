"""
ANPR (Automatic Number Plate Recognition) API Router
FastAPI endpoints for license plate detection and status checking
"""

import logging
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel
import asyncio
import urllib.error
import urllib.request

from services.anpr_service import get_anpr_service, process_image_data
from services.edalnice_service import get_edalnice_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/anpr", tags=["anpr"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"ANPR client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"ANPR client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to client: {e}")
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)


manager = ConnectionManager()

# Pydantic models
class ANPRCaptureRequest(BaseModel):
    """Request to trigger camera capture on ESP32"""
    device_id: str
    capture_count: Optional[int] = 1
    quality: Optional[int] = 85  # JPEG quality 1-100
    auto_process: Optional[bool] = True
    camera_url: Optional[str] = None


class ANPRProcessRequest(BaseModel):
    """Request to process uploaded image"""
    image_base64: Optional[str] = None  # Base64 encoded image data
    auto_check_edalnice: Optional[bool] = True


class LicensePlateScan(BaseModel):
    """License plate scan result"""
    id: Optional[str] = None
    timestamp: str
    plate_text: str
    confidence: float
    device_id: Optional[str] = None
    image_path: Optional[str] = None


class ScanResult(BaseModel):
    """Result of edalnice.cz check"""
    scan_id: str
    plate: str
    is_exempted: bool
    exemption_reason: Optional[str] = None
    status: str  # exempted, ok, debt, not_found, error
    checked_at: str
    cache_hit: Optional[bool] = False


def _camera_url_from_request(request: ANPRCaptureRequest) -> Optional[str]:
    """Resolve ESP32-CAM control URL from request or environment."""
    if request.camera_url:
        return request.camera_url.rstrip("/")

    if request.device_id.startswith("http://") or request.device_id.startswith("https://"):
        return request.device_id.rstrip("/")

    env_key = f"ANPR_CAMERA_URL_{request.device_id.upper().replace('-', '_')}"
    camera_url = os.environ.get(env_key) or os.environ.get("ANPR_CAMERA_URL")
    return camera_url.rstrip("/") if camera_url else None


def _post_camera_command(camera_url: str, command: str) -> Dict[str, Any]:
    """Send a control command to the ESP32-CAM HTTP control server."""
    url = f"{camera_url}/{command.lstrip('/')}"
    request = urllib.request.Request(
        url,
        data=b"{}",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body) if body else {}
            return {"status": "success", "camera_status": response.status, "camera_response": payload}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "camera_status": exc.code, "message": body or exc.reason}


async def _trigger_camera_capture(request: ANPRCaptureRequest) -> Dict[str, Any]:
    """Trigger configured ESP32-CAM capture endpoint."""
    camera_url = _camera_url_from_request(request)
    job_id = f"capture_{request.device_id}_{datetime.now().timestamp()}"

    if not camera_url:
        return {
            "status": "pending",
            "job_id": job_id,
            "device_id": request.device_id,
            "message": "No camera_url or ANPR_CAMERA_URL configured; capture was not sent to hardware",
            "timestamp": datetime.now().isoformat(),
        }

    result = await asyncio.to_thread(_post_camera_command, camera_url, "capture")
    result.update({
        "job_id": job_id,
        "device_id": request.device_id,
        "camera_url": camera_url,
        "timestamp": datetime.now().isoformat(),
    })

    await manager.broadcast({"type": "capture_result", "data": result})
    return result


# API Endpoints

@router.post("/capture")
async def trigger_capture(request: ANPRCaptureRequest) -> Dict[str, Any]:
    """
    Trigger image capture on ESP32 camera

    Args:
        request: Capture request with device_id and parameters

    Returns:
        Capture job status
    """
    try:
        return await _trigger_camera_capture(request)
    except Exception as e:
        logger.error(f"Error triggering capture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def process_image(
    file: Optional[UploadFile] = File(None),
    auto_check_edalnice_form: Optional[bool] = Form(None, alias="auto_check_edalnice"),
    auto_check_edalnice_query: Optional[bool] = Query(None, alias="auto_check_edalnice"),
) -> Dict[str, Any]:
    """
    Process uploaded image to detect license plates

    Args:
        file: Image file to process
        auto_check_edalnice: Automatically check edalnice.cz for detected plates

    Returns:
        Detected plates and their status
    """
    try:
        if not file:
            raise HTTPException(status_code=400, detail="No image file provided")

        # Read image data
        image_data = await file.read()

        if not image_data:
            raise HTTPException(status_code=400, detail="Empty image file")

        # Process image
        anpr_result = await process_image_data(image_data)

        if anpr_result.get("status") == "error":
            raise HTTPException(status_code=500, detail=anpr_result.get("message"))

        auto_check_edalnice = (
            auto_check_edalnice_form
            if auto_check_edalnice_form is not None
            else auto_check_edalnice_query
            if auto_check_edalnice_query is not None
            else True
        )

        # Check plates against edalnice.cz if requested
        scan_results = []
        if auto_check_edalnice and anpr_result.get("plates"):
            edalnice_service = get_edalnice_service()
            await edalnice_service.initialize()

            for plate_data in anpr_result["plates"][:3]:  # Limit to top 3 plates
                try:
                    plate_text = plate_data["text"]
                    edalnice_result = await edalnice_service.query_vehicle(plate_text)

                    scan_results.append({
                        "plate": plate_text,
                        "confidence": plate_data["confidence"],
                        "is_exempted": edalnice_result.get("is_exempted", False),
                        "exemption_reason": edalnice_result.get("exemption_reason"),
                        "edalnice_status": edalnice_result.get("status"),
                        "timestamp": datetime.now().isoformat(),
                    })

                    # Broadcast to WebSocket clients
                    await manager.broadcast({
                        "type": "plate_detected",
                        "data": scan_results[-1],
                    })

                except Exception as e:
                    logger.error(f"Error checking edalnice for {plate_data['text']}: {e}")

        return {
            "status": "success",
            "anpr": anpr_result,
            "scan_results": scan_results,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_scan_history(
    device_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Get history of plate scans

    Args:
        device_id: Filter by device ID
        limit: Number of records to return
        offset: Pagination offset

    Returns:
        List of plate scans
    """
    try:
        # In production, query database here
        # For now, return empty list with schema
        return {
            "status": "success",
            "scans": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching scan history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{scan_id}")
async def get_scan_status(scan_id: str) -> Dict[str, Any]:
    """
    Get status of a specific scan

    Args:
        scan_id: Scan ID

    Returns:
        Scan status and results
    """
    try:
        # In production, query database here
        return {
            "status": "not_found",
            "message": f"Scan {scan_id} not found",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching scan status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    """
    Get vehicle alerts (exempted vehicles, debts, etc.)

    Args:
        limit: Number of alerts to return

    Returns:
        List of vehicle alerts
    """
    try:
        # In production, query database for vehicles marked as exempted
        return {
            "status": "success",
            "alerts": [],
            "total": 0,
            "limit": limit,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time ANPR stream

    Broadcasts detected plates and alerts to connected clients
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for client messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # Handle ping/keep-alive
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})

                # Handle plate lookup request
                elif message.get("type") == "lookup":
                    plate = message.get("plate")
                    if plate:
                        edalnice_service = get_edalnice_service()
                        await edalnice_service.initialize()
                        result = await edalnice_service.query_vehicle(plate)

                        await websocket.send_json({
                            "type": "lookup_result",
                            "plate": plate,
                            "result": result,
                            "timestamp": datetime.now().isoformat(),
                        })

                elif message.get("type") == "capture":
                    capture_request = ANPRCaptureRequest(
                        device_id=message.get("device_id", "esp32-camera"),
                        capture_count=message.get("capture_count", 1),
                        quality=message.get("quality", 85),
                        auto_process=message.get("auto_process", True),
                        camera_url=message.get("camera_url"),
                    )
                    result = await _trigger_camera_capture(capture_request)

                    await websocket.send_json({
                        "type": "capture_result",
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                    })

            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.post("/config")
async def update_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update ANPR service configuration

    Args:
        config: Configuration dict (ocr_languages, min_confidence, etc.)

    Returns:
        Updated configuration
    """
    try:
        # In production, persist configuration
        return {
            "status": "success",
            "config": config,
            "message": "Configuration updated",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check ANPR service health"""
    try:
        anpr_service = get_anpr_service()
        edalnice_service = get_edalnice_service()

        return {
            "status": "healthy",
            "services": {
                "anpr": {
                    "ready": anpr_service.ready,
                    "message": "ANPR OCR ready" if anpr_service.ready else "ANPR OCR not initialized",
                },
                "edalnice": {
                    "ready": True,
                    "message": "Edalnice service available",
                },
            },
            "websocket_clients": len(manager.active_connections),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
