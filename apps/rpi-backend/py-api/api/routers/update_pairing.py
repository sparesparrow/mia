"""Pairing a phone for software updates (ADR-0023, REQ-UPD-004).

The phone makes its own SSH key pair and sends the public half here, with an admin API key. The entry written
to the update user's key list can run one command and nothing else:

    command="sudo /opt/mia/bin/mia-apply-update",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding

sshd reads the list through ``AuthorizedKeysCommand`` (infra/deploy/rpi/install-update-access.sh), so the file
can belong to the service user that runs this API. Only a bare key type and its base64 body are accepted: the
phone cannot add its own options, newlines or a different command.
"""

from __future__ import annotations

import base64
import binascii
import fcntl
import hashlib
import logging
import os
import re
import struct
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.dependencies import require_scope

logger = logging.getLogger("mia.update_pairing")

router = APIRouter(prefix="/admin/update", tags=["Update"])

DEFAULT_AUTHORIZED_KEYS = "/etc/mia/update_authorized_keys"
FORCED_COMMAND = "sudo /opt/mia/bin/mia-apply-update"
OPTIONS = f'command="{FORCED_COMMAND}",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding'
KEY_TYPES = (
    "ssh-ed25519",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "ssh-rsa",
)
MAX_KEYS = 8
LABEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
_KEY_RE = re.compile(r"^(" + "|".join(re.escape(t) for t in KEY_TYPES) + r") ([A-Za-z0-9+/]{16,2048}={0,2})(?: \S.*)?$")


class PairRequest(BaseModel):
    public_key: str = Field(..., max_length=2048, description="One OpenSSH public key line")
    label: str = Field(..., description="Short name for this phone, [A-Za-z0-9._-], up to 32 characters")


def _path() -> Path:
    return Path(os.environ.get("MIA_AUTHORIZED_KEYS", DEFAULT_AUTHORIZED_KEYS))


def parse_public_key(line: str):
    """Return (type, base64 body) of a single bare OpenSSH public key, or raise ValueError."""
    if "\n" in line or "\r" in line or "\0" in line:
        raise ValueError("the key must be one line")
    match = _KEY_RE.match(line.strip())
    if not match:
        raise ValueError("not a plain OpenSSH public key (type, base64 body, optional comment); options are refused")
    key_type, body = match.groups()
    try:
        blob = base64.b64decode(body, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("the key body is not valid base64") from None
    if len(blob) < 4:
        raise ValueError("the key body is too short")
    (length,) = struct.unpack(">I", blob[:4])
    if blob[4:4 + length] != key_type.encode():
        raise ValueError("the key body does not match its type")
    return key_type, body


def fingerprint(body: str) -> str:
    digest = hashlib.sha256(base64.b64decode(body)).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def _read(path: Path) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith(OPTIONS + " "):
            continue
        parts = line[len(OPTIONS) + 1:].split(" ")
        if len(parts) == 3 and parts[2].startswith("mia-phone:"):
            entries.append({"type": parts[0], "body": parts[1], "label": parts[2][len("mia-phone:"):]})
    return entries


def _write(path: Path, entries: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(f"{OPTIONS} {e['type']} {e['body']} mia-phone:{e['label']}\n" for e in entries)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".update_authorized_keys.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except OSError:
        Path(tmp).unlink(missing_ok=True)
        raise


def _locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(str(path) + ".lock", "w")
    fcntl.flock(handle, fcntl.LOCK_EX)
    return handle


@router.get("/pair")
async def list_paired(_user=Depends(require_scope("admin"))):
    """Paired phones: label and fingerprint, never the whole key."""
    return {"phones": [{"label": e["label"], "fingerprint": fingerprint(e["body"])} for e in _read(_path())]}


@router.post("/pair")
async def pair_phone(request: PairRequest, _user=Depends(require_scope("admin"))):
    """Authorise a phone's public key for the update command. Repeating the same key and label changes nothing."""
    if not LABEL_RE.match(request.label):
        raise HTTPException(status_code=422, detail="label must be 1-32 characters of A-Z a-z 0-9 . _ -")
    try:
        key_type, body = parse_public_key(request.public_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    path = _path()
    with _locked(path):
        entries = _read(path)
        same = [e for e in entries if e["body"] == body and e["type"] == key_type]
        if same and same[0]["label"] == request.label:
            return {"status": "already_paired", "label": request.label, "fingerprint": fingerprint(body)}
        entries = [e for e in entries if e not in same and e["label"] != request.label]
        if len(entries) >= MAX_KEYS:
            raise HTTPException(status_code=409, detail=f"at most {MAX_KEYS} phones can be paired; revoke one first")
        entries.append({"type": key_type, "body": body, "label": request.label})
        try:
            _write(path, entries)
        except OSError:
            logger.exception("cannot write %s", path)
            raise HTTPException(status_code=500, detail="cannot write the update key list") from None
    logger.info("paired phone %s", request.label)
    return {"status": "paired", "label": request.label, "fingerprint": fingerprint(body)}


@router.delete("/pair/{label}")
async def revoke_phone(label: str, _user=Depends(require_scope("admin"))):
    if not LABEL_RE.match(label):
        raise HTTPException(status_code=422, detail="bad label")
    path = _path()
    with _locked(path):
        entries = _read(path)
        kept = [e for e in entries if e["label"] != label]
        if len(kept) == len(entries):
            raise HTTPException(status_code=404, detail="no such phone")
        _write(path, kept)
    return {"status": "revoked", "label": label}
