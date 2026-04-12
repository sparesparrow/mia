"""
MIA Unified Comms Gateway — configuration
All secrets via env / .env file.
"""

import os

# ── Tailscale nodes ────────────────────────────────────────────────────────────
STUDIO_IP       = "100.109.34.98"       # main hub, runs gateway + Asterisk
SPARENOVO_IP    = "100.120.128.10"      # secondary node (OpenSUSE)
MOTO_IP         = "100.64.125.20"       # Android Moto G15 Power

# ── KDE Connect device IDs ─────────────────────────────────────────────────────
KDECONNECT_MOTO_ID    = "4751dbed3a424a068f80b66f84b1d655"  # moto g15 power (SIM)
KDECONNECT_WINDOWS_ID = "_521d1df7_34aa_48a0_8e62_cba989ac5f36_"  # DESKTOP-E98SQDH (SIM)

# ── Telegram ───────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_ID     = os.getenv("TELEGRAM_API_ID", "")   # for MTProto user account
TELEGRAM_API_HASH   = os.getenv("TELEGRAM_API_HASH", "")

# ── Signal (signal-cli-rest-api, Docker on studio) ────────────────────────────
SIGNAL_REST_URL     = os.getenv("SIGNAL_REST_URL", "http://studio:8080")
SIGNAL_PHONE        = os.getenv("SIGNAL_PHONE", "")  # e.g. +420735204654

# ── WhatsApp (Baileys bridge, Docker on studio) ────────────────────────────────
WHATSAPP_BRIDGE_URL = os.getenv("WHATSAPP_BRIDGE_URL", "http://studio:3000")

# ── MIA core ──────────────────────────────────────────────────────────────────
MIA_WS_URL          = os.getenv("MIA_WS_URL", f"ws://{STUDIO_IP}:8000/ws")
GATEWAY_PORT        = int(os.getenv("GATEWAY_PORT", "9000"))
