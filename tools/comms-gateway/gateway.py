#!/usr/bin/env python3
"""
gateway.py — MIA Unified Comms Gateway
───────────────────────────────────────
Single FastAPI process that fans messages from all platforms into MIA WS
and routes MIA responses back to the originating platform.

Platforms:
  Telegram  — bot polling (+ optional MTProto user account)
  Signal    — signal-cli-rest-api polling
  WhatsApp  — Baileys webhook push
  SMS       — KDE Connect → Moto G15 SIM (send-only from here)

Run: uvicorn gateway:app --host 0.0.0.0 --port 9000
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiohttp
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    TELEGRAM_BOT_TOKEN, SIGNAL_PHONE, MIA_WS_URL, GATEWAY_PORT,
    KDECONNECT_MOTO_ID,
)
from bridges.kdeconnect import send_sms_async, SimDevice, connectivity_report
from bridges.telegram_bridge import TelegramBotBridge
from bridges.signal_bridge import SignalBridge
from bridges.whatsapp_bridge import WhatsAppBridge, phone_to_whatsapp_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("comms-gateway")

# ── Per-platform bridge instances ──────────────────────────────────────────────

_telegram: TelegramBotBridge | None = None
_signal: SignalBridge | None = None
_whatsapp: WhatsAppBridge | None = None

# Track which chat last messaged us (for reply routing)
_last_context: dict[str, Any] = {}   # platform → {chat_id, ...}


# ── MIA WS fan-in ──────────────────────────────────────────────────────────────

async def to_mia(message: dict) -> str | None:
    """Forward a normalized message to MIA WS, return MIA's text response."""
    _last_context[message["platform"]] = message
    try:
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(MIA_WS_URL, timeout=aiohttp.ClientTimeout(total=30)) as ws:
                await ws.send_json({"type": "comms_message", **message})
                resp = await asyncio.wait_for(ws.receive_json(), timeout=25)
                return resp.get("text") or resp.get("message")
    except Exception as exc:
        log.warning("MIA WS error: %s", exc)
        return None


async def on_message(msg: dict) -> None:
    """Called by every bridge when a message arrives."""
    log.info("[%s] %s: %s", msg["platform"], msg.get("from_name", msg.get("from")), msg.get("text", "")[:80])
    response = await to_mia(msg)
    if not response:
        return

    platform = msg["platform"]
    if platform == "telegram" and _telegram:
        await _telegram.send(msg["chat_id"], response)
    elif platform == "signal" and _signal:
        await _signal.send(msg["from"], response)
    elif platform == "whatsapp" and _whatsapp:
        await _whatsapp.send(msg["chat_id"], response)
    elif platform == "sms":
        await send_sms_async(msg["from"], response)


# ── Lifespan: start all bridges ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _telegram, _signal, _whatsapp
    tasks = []

    if TELEGRAM_BOT_TOKEN:
        _telegram = TelegramBotBridge(on_message)
        tasks.append(asyncio.create_task(_telegram.start(), name="telegram"))
        log.info("Telegram bot bridge started")

    if SIGNAL_PHONE:
        _signal = SignalBridge(on_message)
        tasks.append(asyncio.create_task(_signal.start(), name="signal"))
        log.info("Signal bridge started")

    _whatsapp = WhatsAppBridge(on_message)
    log.info("WhatsApp bridge ready (webhook mode)")

    yield

    for t in tasks:
        t.cancel()
    if _signal:
        _signal.stop()


app = FastAPI(title="MIA Comms Gateway", lifespan=lifespan)


# ── Webhook: WhatsApp (Baileys pushes here) ────────────────────────────────────

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    if _whatsapp:
        return await _whatsapp.handle_webhook(request)
    return JSONResponse({"status": "not configured"}, status_code=503)


# ── REST: send from MIA to any platform ───────────────────────────────────────

@app.post("/send/{platform}")
async def send_message(platform: str, request: Request):
    """
    MIA calls this to push a message to a specific platform.
    Body: {"to": "<chat_id or phone>", "text": "..."}
    """
    body = await request.json()
    to   = body.get("to", "")
    text = body.get("text", "")

    if platform == "telegram" and _telegram:
        await _telegram.send(to, text)
    elif platform == "signal" and _signal:
        await _signal.send(to, text)
    elif platform == "whatsapp" and _whatsapp:
        await _whatsapp.send(phone_to_whatsapp_id(to) if "@" not in to else to, text)
    elif platform == "sms":
        await send_sms_async(to, text)
    else:
        return JSONResponse({"error": f"unknown platform: {platform}"}, status_code=400)

    return {"status": "sent", "platform": platform, "to": to}


# ── Status ─────────────────────────────────────────────────────────────────────

@app.get("/status")
async def status():
    wa_status = await _whatsapp.status() if _whatsapp else {}
    return {
        "telegram": "active" if _telegram else "disabled",
        "signal":   "active" if _signal else "disabled",
        "whatsapp": wa_status,
        "sms_sim":  connectivity_report(KDECONNECT_MOTO_ID),
        "mia_ws":   MIA_WS_URL,
    }


@app.get("/whatsapp/qr")
async def whatsapp_qr():
    if _whatsapp:
        return {"qr_url": await _whatsapp.get_qr()}
    return JSONResponse({"error": "whatsapp not configured"}, status_code=503)


if __name__ == "__main__":
    uvicorn.run("gateway:app", host="0.0.0.0", port=GATEWAY_PORT, reload=False)
