"""
SIP bridge configuration — ElevenLabs trunk ↔ Tailscale studio node.
"""

import os

# ── ElevenLabs ─────────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY      = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_PHONE_ID     = "phnum_01jwpe55q1fqgsrt2csxf0h9qb"
ELEVENLABS_AGENT_ID     = "agent_8301khcctanxeyf8g4m7ez5xmvnb"
ELEVENLABS_PHONE_NUMBER = "+420735204654"

# ElevenLabs SIP termination endpoint (obtain from ElevenLabs dashboard → Phone Numbers → SIP details)
# Typically: sip:<phone>@sip.elevenlabs.io   OR   the domain shown in the "Inbound URI" field
ELEVENLABS_SIP_DOMAIN   = os.getenv("ELEVENLABS_SIP_DOMAIN", "sip.elevenlabs.io")
ELEVENLABS_SIP_URI      = f"sip:{ELEVENLABS_PHONE_NUMBER}@{ELEVENLABS_SIP_DOMAIN}"

# ── Studio node (Tailscale) ────────────────────────────────────────────────────
STUDIO_TAILSCALE_IP  = "100.109.34.98"
STUDIO_LAN_IP        = "192.168.200.23"   # used as SIP source (reachable from carrier)
STUDIO_SSH_USER      = os.getenv("STUDIO_SSH_USER", "sparrow")
SIP_PORT             = 5060
RTP_PORT_START       = 10000
RTP_PORT_END         = 10100

# ── Asterisk SIP auth (shared secret for the ElevenLabs trunk leg) ─────────────
SIP_TRUNK_USERNAME   = os.getenv("SIP_TRUNK_USERNAME", "mia-studio")
SIP_TRUNK_PASSWORD   = os.getenv("SIP_TRUNK_PASSWORD", "")   # set in .env

# ── MIA voice pipeline endpoint (FastAPI WebSocket on studio) ──────────────────
MIA_WS_URL           = f"ws://{STUDIO_LAN_IP}:8000/ws"
