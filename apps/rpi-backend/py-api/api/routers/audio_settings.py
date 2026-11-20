"""Where the microphone comes from and where replies are heard (ADR-0021, ADR-0019, REQ-VOICE-030).

The Pi owns the choice: ``GET /audio/settings`` reports it with what this Pi can really do, ``PUT`` changes it
(write scope, via the app-wide enforcement for non-GET requests). The choice lives in ``audio_settings.json`` in
``MIA_STATE_DIR``, a file of its own because the voice router rewrites ``voice_settings.json`` with only the
fields it knows.

Bluetooth audio and the phone speaker are reported as unavailable and a request for them is refused with 409:
this Pi has BlueZ but no audio daemon for A2DP/HFP (no bluealsa, PipeWire or PulseAudio), and there is no reply
audio path to the phone yet. Nothing here pretends otherwise.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("mia.audio_settings")

router = APIRouter(prefix="/audio", tags=["Audio"])

FILE_NAME = "audio_settings.json"
DEFAULT_STATE_DIR = "/var/lib/mia"
MIC_TRANSPORTS = ("wifi", "bluetooth")
REPLY_OUTPUTS = ("pi_speaker", "bluetooth_phone", "phone_speaker")
DEFAULTS = {"mic_transport": "wifi", "reply_output": "pi_speaker"}


def settings_path() -> Path:
    return Path(os.environ.get("MIA_STATE_DIR", DEFAULT_STATE_DIR)) / FILE_NAME


def bluetooth_audio_available() -> bool:
    """True only when an audio daemon that can carry A2DP/HFP is installed and running."""
    if shutil.which("bluealsa") or shutil.which("bluealsad"):
        return True
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000"))
    return any((runtime / name).exists() for name in ("pipewire-0", "pulse/native"))


def capabilities() -> Dict[str, Any]:
    bt = bluetooth_audio_available()
    return {
        "bt_audio_available": bt,
        "mic_transport": {"wifi": True, "bluetooth": False},  # no Bluetooth microphone path exists yet
        "reply_output": {
            "pi_speaker": True,
            "bluetooth_phone": False,  # needs a daemon (bt_audio_available) and an audio route
            "phone_speaker": False,  # no reply audio is sent to the phone yet
        },
    }


def load() -> Dict[str, str]:
    """The stored choice; a missing, damaged or unknown value gives the default."""
    values = dict(DEFAULTS)
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return values
    except (OSError, ValueError) as exc:
        logger.warning("audio settings unreadable, using defaults: %s", exc)
        return values
    if isinstance(data, dict):
        if data.get("mic_transport") in MIC_TRANSPORTS:
            values["mic_transport"] = data["mic_transport"]
        if data.get("reply_output") in REPLY_OUTPUTS:
            values["reply_output"] = data["reply_output"]
    return values


def save(values: Dict[str, str]) -> bool:
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, partial = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(values, indent=2) + "\n")
            os.replace(partial, path)
        except BaseException:
            os.unlink(partial)
            raise
    except OSError as exc:
        logger.warning("audio settings not saved: %s", exc)
        return False
    return True


def report() -> Dict[str, Any]:
    caps = capabilities()
    chosen = load()
    # A stored choice this Pi cannot serve (a daemon was removed) is reported, never silently followed.
    effective = {
        "mic_transport": chosen["mic_transport"] if caps["mic_transport"][chosen["mic_transport"]] else "wifi",
        "reply_output": chosen["reply_output"] if caps["reply_output"][chosen["reply_output"]] else "pi_speaker",
    }
    return {**chosen, "effective": effective, "capabilities": caps}


class AudioSettingsUpdate(BaseModel):
    mic_transport: str | None = None
    reply_output: str | None = None


@router.get("/settings")
async def get_audio_settings() -> Dict[str, Any]:
    return report()


@router.put("/settings")
async def put_audio_settings(update: AudioSettingsUpdate) -> Dict[str, Any]:
    caps = capabilities()
    chosen = load()
    for field, allowed in (("mic_transport", MIC_TRANSPORTS), ("reply_output", REPLY_OUTPUTS)):
        value = getattr(update, field)
        if value is None:
            continue
        if value not in allowed:
            raise HTTPException(status_code=422, detail=f"unknown {field}: {value}")
        if not caps[field][value]:
            raise HTTPException(status_code=409, detail={"error": "unavailable", "field": field, "value": value})
        chosen[field] = value
    if not save(chosen):
        raise HTTPException(status_code=500, detail="settings not saved")
    return report()
