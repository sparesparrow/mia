"""Read-only list of phones paired for software updates (ADR-0023, REQ-UPD-004).

The API cannot pair, change or revoke a phone. A paired key runs `sudo /opt/mia/bin/mia-apply-update` as root
over SSH, so adding one is an administrator action on the Pi: `sudo /opt/mia/bin/mia-update-pair add <label>
'<public key>'` (bin/mia-update-pair). The key list /etc/mia/update_authorized_keys is owned by root, mode 644, so
the service user that runs this API can read it and nothing more.
"""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from api.auth.api_key import get_api_key_auth
from api.auth.dependencies import require_scope

router = APIRouter(prefix="/admin/update", tags=["Update"])

DEFAULT_AUTHORIZED_KEYS = "/etc/mia/update_authorized_keys"


def _path() -> Path:
    return Path(os.environ.get("MIA_AUTHORIZED_KEYS", DEFAULT_AUTHORIZED_KEYS))


def _fingerprint(body: str) -> str:
    return "SHA256:" + base64.b64encode(hashlib.sha256(base64.b64decode(body)).digest()).decode().rstrip("=")


def _read(path: Path) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return entries
    for line in lines:
        parts = line.rsplit(" ", 3)
        if len(parts) == 4 and parts[3].startswith("mia-phone:"):
            try:
                entries.append({"label": parts[3][len("mia-phone:"):], "fingerprint": _fingerprint(parts[2])})
            except ValueError:
                continue
    return entries


@router.get("/pair")
async def list_paired(_user=Depends(require_scope("admin"))):
    """Paired phones: label and fingerprint, never the whole key. Refused when authentication is disabled."""
    if not get_api_key_auth().enabled:
        raise HTTPException(status_code=503, detail="update pairing needs API authentication; it is disabled")
    return {"phones": _read(_path())}
