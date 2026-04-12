"""
MIA Logs Router — view systemd journal entries for MIA services.

Replaces SSH for log access in headless in-car deployment.
The Android app or any HTTP client on the MIA-Car WiFi can query logs.
"""

import subprocess
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger("mia.logs")

router = APIRouter(prefix="/logs", tags=["Logs"])

# Allowed service names (prevent arbitrary unit queries)
ALLOWED_SERVICES = {
    "mia-api", "mia-gpio-worker", "mia-serial-bridge",
    "mia-obd-worker", "mia-led-monitor", "mia-citroen-bridge",
    "mia-ble-advertiser", "mia-ble-obd", "mia-usb-camera",
    "mia-audio-capture", "mia-wake-word", "mia-stt",
    "mia-voice-router", "mia-tts", "mia-power-monitor",
    "mia-selftest", "zmq-broker",
}


@router.get("/services", response_model=Dict[str, Any])
async def list_log_services():
    """List services whose logs can be queried."""
    return {"services": sorted(ALLOWED_SERVICES)}


@router.get("/{service}", response_model=Dict[str, Any])
async def get_service_logs(
    service: str,
    lines: int = Query(50, ge=1, le=500),
    priority: Optional[str] = Query(None, pattern="^[0-7]$"),
    since: Optional[str] = Query(None, description="e.g. '5 min ago', '1h ago', '2025-01-01'"),
    grep: Optional[str] = Query(None, max_length=100),
):
    """
    Return recent journal entries for a MIA service.

    Parameters:
      - lines: number of log lines (max 500)
      - priority: syslog level 0-7 (0=emerg, 7=debug)
      - since: journalctl --since value
      - grep: filter lines containing this text
    """
    if service not in ALLOWED_SERVICES:
        raise HTTPException(404, f"Unknown service: {service}. Use GET /logs/services to list.")

    cmd = ["journalctl", "-u", service, "-n", str(lines), "--no-pager", "-o", "short-iso"]

    if priority:
        cmd.extend(["-p", priority])
    if since:
        cmd.extend(["--since", since])
    if grep:
        cmd.extend(["--grep", grep])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Journal query timed out")

    log_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

    return {
        "service": service,
        "count": len(log_lines),
        "lines": log_lines,
    }
