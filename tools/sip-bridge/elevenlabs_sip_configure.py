#!/usr/bin/env python3
"""
elevenlabs_sip_configure.py
────────────────────────────
Queries and updates the ElevenLabs SIP trunk configuration for the MIA phone number.

Usage:
    python elevenlabs_sip_configure.py status          # show current config
    python elevenlabs_sip_configure.py lock            # restrict allowed_addresses to studio IP
    python elevenlabs_sip_configure.py open            # allow all (0.0.0.0/0) — for testing
    python elevenlabs_sip_configure.py set-auth        # add username/password credentials
"""

import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    ELEVENLABS_API_KEY, ELEVENLABS_PHONE_ID, ELEVENLABS_PHONE_NUMBER,
    ELEVENLABS_SIP_DOMAIN, STUDIO_LAN_IP, SIP_TRUNK_USERNAME, SIP_TRUNK_PASSWORD,
)

EL_BASE = "https://api.elevenlabs.io/v1"


def headers() -> dict:
    if not ELEVENLABS_API_KEY:
        sys.exit("ELEVENLABS_API_KEY not set — export it or add to .env")
    return {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}


def get_status() -> dict:
    r = requests.get(f"{EL_BASE}/convai/phone-numbers/{ELEVENLABS_PHONE_ID}", headers=headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def print_status(data: dict) -> None:
    trunk = data.get("inbound_trunk") or {}
    print(f"\n{'═'*55}")
    print(f"  ElevenLabs SIP trunk — {data.get('phone_number')} ({data.get('label')})")
    print(f"{'═'*55}")
    print(f"  Provider:          {data.get('provider')}")
    print(f"  Agent:             {data.get('assigned_agent', {}).get('agent_name')}")
    print(f"  Inbound:           {data.get('supports_inbound')}")
    print(f"  Outbound:          {data.get('supports_outbound')}")
    print(f"\n  ── Inbound trunk ──")
    print(f"  Allowed addresses: {trunk.get('allowed_addresses')}")
    print(f"  Has auth:          {trunk.get('has_auth_credentials')}")
    print(f"  Username:          {trunk.get('username')}")
    print(f"  Remote domains:    {trunk.get('remote_domains')}")
    print(f"  Encryption:        {trunk.get('media_encryption')}")
    print(f"\n  SIP domain to use: {ELEVENLABS_SIP_DOMAIN}")
    print(f"  SIP URI:           sip:{data.get('phone_number')}@{ELEVENLABS_SIP_DOMAIN}")
    print()


def patch_inbound_trunk(payload: dict) -> dict:
    r = requests.patch(
        f"{EL_BASE}/convai/phone-numbers/{ELEVENLABS_PHONE_ID}",
        headers=headers(),
        json={"inbound_trunk": payload},
        timeout=15,
    )
    if not r.ok:
        sys.exit(f"PATCH failed {r.status_code}: {r.text}")
    return r.json()


def cmd_lock() -> None:
    """Restrict SIP source to studio LAN IP only."""
    data = patch_inbound_trunk({"allowed_addresses": [f"{STUDIO_LAN_IP}/32"]})
    print(f"[locked] allowed_addresses → {data.get('inbound_trunk', {}).get('allowed_addresses')}")


def cmd_open() -> None:
    """Allow SIP from any IP (testing only)."""
    data = patch_inbound_trunk({"allowed_addresses": ["0.0.0.0/0"]})
    print(f"[open] allowed_addresses → {data.get('inbound_trunk', {}).get('allowed_addresses')}")


def cmd_set_auth() -> None:
    """Enable username/password auth on the SIP trunk."""
    if not SIP_TRUNK_PASSWORD:
        sys.exit("SIP_TRUNK_PASSWORD not set — add to .env")
    data = patch_inbound_trunk({
        "username": SIP_TRUNK_USERNAME,
        "password": SIP_TRUNK_PASSWORD,
    })
    trunk = data.get("inbound_trunk", {})
    print(f"[auth] username={trunk.get('username')}  has_auth={trunk.get('has_auth_credentials')}")


COMMANDS = {
    "status":   lambda: print_status(get_status()),
    "lock":     cmd_lock,
    "open":     cmd_open,
    "set-auth": cmd_set_auth,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd not in COMMANDS:
        print(f"Usage: {sys.argv[0]} [{' | '.join(COMMANDS)}]")
        sys.exit(1)
    COMMANDS[cmd]()
