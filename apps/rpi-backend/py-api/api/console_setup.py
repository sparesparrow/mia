"""First-run checklist for the web console (ADR-0029, REQ-WEB-008).

``GET /console/setup`` tells what is set up on this Pi and what to do next. It only looks: it reads whether a
setting is present, never its value, and it changes nothing. Enrollment itself stays where ADR-0025 puts it (the
phone, with a grant signed by the auth server); the API has no way to pair a phone or authorize a key.

Each step is ``{id, title, done, detail, how}``, plus ``action`` when the console page itself can do it. ``done``
is true, false, or null when the Pi cannot tell (the phone registry is root-only).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from api import console_agents, voice_console
from api.web_console import _auth_configured, console_gate
from fastapi import APIRouter, Depends

router = APIRouter(tags=["Web console"], dependencies=[Depends(console_gate)])

DEFAULT_STATE_DIR = "/var/lib/mia"
DEFAULT_PHONES_FILE = "/var/lib/mia-enroll/phones.json"
# ISO 3779: 17 characters, no I, O or Q (the VAG bridge applies the same rule).
_VIN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def _state_file(name: str) -> Path:
    return Path(os.environ.get("MIA_STATE_DIR", DEFAULT_STATE_DIR)) / name


def _step(
    step_id: str, title: str, done: Optional[bool], detail: str, how: str, action: Optional[str] = None
) -> Dict[str, Any]:
    step = {"id": step_id, "title": title, "done": done, "detail": detail, "how": how}
    if action:
        step["action"] = action
    return step


def _api_key() -> Dict[str, Any]:
    done = _auth_configured()
    return _step(
        "api_key",
        "API key",
        done,
        "set: the console and the app need it" if done else "not set: the API is open and the console is local only",
        "Put MIA_API_KEY=<a long random key> in /etc/mia/environment and restart mia-api.",
    )


def _vehicle() -> Dict[str, Any]:
    vin = os.environ.get("MIA_VEHICLE_VIN", "").strip().upper()
    model = os.environ.get("MIA_VEHICLE_MODEL", "").strip()
    missing = [name for name, value in (("VIN", vin), ("model", model)) if not value]
    if missing:
        detail = " and ".join(missing) + " not set"
    elif not _VIN.match(vin):
        detail = "the VIN is not a valid 17-character VIN"
    else:
        detail = "VIN and model set"
    return _step(
        "vehicle",
        "Vehicle identity",
        not missing and bool(_VIN.match(vin)),
        detail,
        "Set MIA_VEHICLE_VIN, MIA_VEHICLE_MODEL and MIA_VEHICLE_MODEL_YEAR in /etc/mia/environment"
        " (never commit a VIN).",
    )


def _phone() -> Dict[str, Any]:
    how = "Enroll a phone from the MIA app (the install wizard, ADR-0025); check with sudo mia-phone-registry list."
    path = Path(os.environ.get("MIA_PHONES_FILE", DEFAULT_PHONES_FILE))
    try:
        phones = json.loads(path.read_text(encoding="utf-8")).get("phones", {})
    except FileNotFoundError:
        return _step("phone", "A phone enrolled", False, "no phone enrolled yet", how)
    except PermissionError:
        return _step("phone", "A phone enrolled", None, "the phone registry is readable by root only", how)
    except (OSError, ValueError, AttributeError):
        return _step("phone", "A phone enrolled", None, "the phone registry is unreadable", how)
    count = len(phones) if isinstance(phones, dict) else 0
    detail = f"{count} phone{'s' if count != 1 else ''} enrolled" if count else "no phone enrolled yet"
    return _step("phone", "A phone enrolled", count > 0, detail, how)


def _voice_console() -> Dict[str, Any]:
    done = voice_console.console_enabled()
    return _step(
        "voice_console",
        "Voice console",
        done,
        f"on ({voice_console.console_backend()} backend)" if done else "off: the live voice view has nothing to show",
        "Set VOICE_CONSOLE=1 (and VOICE_CONSOLE_BACKEND=router once the voice router runs) for mia-api.",
    )


def _stored(step_id: str, title: str, done: bool, what: str, action: str) -> Dict[str, Any]:
    return _step(
        step_id,
        title,
        done,
        "chosen" if done else "defaults in use",
        f"Choose {what} on this page and save.",
        action,
    )


def steps() -> List[Dict[str, Any]]:
    return [
        _api_key(),
        _vehicle(),
        _phone(),
        _voice_console(),
        _stored(
            "voice_settings",
            "Voice settings",
            _state_file("voice_settings.json").is_file(),
            "the verbosity, persona and language",
            "voice",
        ),
        _stored(
            "audio_settings",
            "Audio",
            _state_file("audio_settings.json").is_file(),
            "the microphone and where replies are heard",
            "audio",
        ),
        _stored(
            "agent_shapes",
            "Agent personas",
            console_agents.stored(),
            "the personas that play the three agent roles",
            "agents",
        ),
    ]


@router.get("/console/setup")
async def get_setup() -> Dict[str, Any]:
    items = steps()
    done = sum(1 for s in items if s["done"] is True)
    return {
        "status": "ok",
        "message": f"{done} of {len(items)} done",
        "done": done,
        "total": len(items),
        "steps": items,
    }
