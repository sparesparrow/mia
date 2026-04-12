"""
MIA OTA Update Router — upload, apply, and roll back code updates.

Designed for headless in-car deployment where SSH is not available.
Updates are delivered as tarballs over HTTP (e.g., from the Android app
or a laptop on the MIA-Car WiFi network).

Flow:
  1. POST /ota/upload   → upload tarball, extract to staging
  2. POST /ota/apply    → swap staging → live, restart services
  3. POST /ota/rollback → swap back to previous version
  4. GET  /ota/status   → current version, staging info, rollback available
"""

import os
import logging
import tarfile
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException

logger = logging.getLogger("mia.ota")

router = APIRouter(prefix="/ota", tags=["OTA"])

# ── Paths ─────────────────────────────────────────────────────────────────
MIA_BASE = Path(os.environ.get("MIA_BASE_DIR", "/opt/mia"))
LIVE_DIR = MIA_BASE / "apps"
STAGING_DIR = MIA_BASE / "staging"
ROLLBACK_DIR = MIA_BASE / "rollback"
VERSION_FILE = MIA_BASE / "VERSION"
OTA_LOG = MIA_BASE / "data" / "ota_history.log"

# Max upload size: 50 MB
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Services to restart after apply
MIA_SERVICES = [
    "mia-api",
    "mia-gpio-worker",
    "mia-serial-bridge",
    "mia-obd-worker",
    "mia-led-monitor",
    "mia-voice-router",
    "mia-stt",
    "mia-tts",
    "mia-wake-word",
    "mia-audio-capture",
]


def _current_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "unknown"


def _log_ota_event(action: str, detail: str):
    OTA_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = f"{datetime.now().isoformat()} [{action}] {detail}"
    with open(OTA_LOG, "a") as f:
        f.write(entry + "\n")
    logger.info(entry)


@router.get("/status", response_model=Dict[str, Any])
async def ota_status():
    """Current OTA state: version, staging content, rollback availability."""
    return {
        "current_version": _current_version(),
        "staging_ready": STAGING_DIR.exists() and any(STAGING_DIR.iterdir()),
        "rollback_available": ROLLBACK_DIR.exists() and any(ROLLBACK_DIR.iterdir()),
        "live_dir": str(LIVE_DIR),
    }


@router.post("/upload", response_model=Dict[str, Any])
async def ota_upload(file: UploadFile = File(...)):
    """
    Upload a .tar.gz update bundle.

    The tarball is expected to contain the apps/ directory structure
    (i.e., tar root should have rpi-backend/py-api/...).
    """
    if not file.filename or not file.filename.endswith((".tar.gz", ".tgz")):
        raise HTTPException(400, "Upload must be a .tar.gz or .tgz file")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")

    sha256 = hashlib.sha256(content).hexdigest()

    # Clear and extract to staging
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True)

    staging_tar = STAGING_DIR / "update.tar.gz"
    staging_tar.write_bytes(content)

    try:
        with tarfile.open(staging_tar, "r:gz") as tar:
            # Security: reject paths with .. or absolute paths
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    shutil.rmtree(STAGING_DIR)
                    raise HTTPException(400, f"Unsafe path in tarball: {member.name}")
            tar.extractall(STAGING_DIR)
    except tarfile.TarError as e:
        shutil.rmtree(STAGING_DIR)
        raise HTTPException(400, f"Invalid tarball: {e}")

    staging_tar.unlink()
    _log_ota_event("upload", f"sha256={sha256[:16]}... size={len(content)} file={file.filename}")

    return {
        "status": "staged",
        "sha256": sha256,
        "size_bytes": len(content),
        "staging_dir": str(STAGING_DIR),
    }


@router.post("/apply", response_model=Dict[str, Any])
async def ota_apply():
    """
    Swap staging → live. The current live becomes the rollback.

    1. Move live → rollback (atomic rename)
    2. Move staging → live
    3. Restart MIA services
    """
    if not STAGING_DIR.exists() or not any(STAGING_DIR.iterdir()):
        raise HTTPException(400, "No staged update to apply. Upload first.")

    # Save rollback
    if ROLLBACK_DIR.exists():
        shutil.rmtree(ROLLBACK_DIR)
    if LIVE_DIR.exists():
        shutil.copytree(LIVE_DIR, ROLLBACK_DIR)

    old_version = _current_version()

    # Swap: copy staging content over live
    try:
        for item in STAGING_DIR.iterdir():
            dest = LIVE_DIR / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    except Exception as e:
        _log_ota_event("apply_failed", str(e))
        raise HTTPException(500, f"Failed to apply update: {e}")

    shutil.rmtree(STAGING_DIR)

    # Restart services
    restarted = []
    failed = []
    for svc in MIA_SERVICES:
        result = subprocess.run(
            ["systemctl", "restart", svc],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            restarted.append(svc)
        else:
            failed.append(svc)

    new_version = _current_version()
    _log_ota_event("apply", f"{old_version} → {new_version}, restarted={len(restarted)}, failed={len(failed)}")

    return {
        "status": "applied",
        "old_version": old_version,
        "new_version": new_version,
        "restarted": restarted,
        "failed": failed,
        "rollback_available": True,
    }


@router.post("/rollback", response_model=Dict[str, Any])
async def ota_rollback():
    """Restore the previous version from rollback."""
    if not ROLLBACK_DIR.exists() or not any(ROLLBACK_DIR.iterdir()):
        raise HTTPException(400, "No rollback available.")

    old_version = _current_version()

    try:
        if LIVE_DIR.exists():
            shutil.rmtree(LIVE_DIR)
        shutil.copytree(ROLLBACK_DIR, LIVE_DIR)
        shutil.rmtree(ROLLBACK_DIR)
    except Exception as e:
        _log_ota_event("rollback_failed", str(e))
        raise HTTPException(500, f"Rollback failed: {e}")

    # Restart services
    for svc in MIA_SERVICES:
        subprocess.run(["systemctl", "restart", svc],
                       capture_output=True, timeout=30)

    new_version = _current_version()
    _log_ota_event("rollback", f"{old_version} → {new_version}")

    return {
        "status": "rolled_back",
        "restored_version": new_version,
    }
