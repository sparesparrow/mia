"""
bridges/whatsapp_bridge.py
───────────────────────────
WhatsApp ↔ MIA via Baileys REST bridge (Docker).

Docker image: davidsemakula/whatsapp-web-js-rest   (or similar Baileys wrapper)
First-time: scan QR code from http://studio:3000/qr  with the Moto G15 WhatsApp.

Linking to existing WhatsApp account (no separate number needed).
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Callable, Awaitable

import aiohttp
from fastapi import Request

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import WHATSAPP_BRIDGE_URL

log = logging.getLogger("whatsapp_bridge")

MessageHandler = Callable[[dict], Awaitable[None]]


class WhatsAppBridge:
    """
    Receives WhatsApp messages via webhook (push from Baileys container).
    Sends messages via Baileys REST API.
    """

    def __init__(self, on_message: MessageHandler) -> None:
        self.on_message = on_message

    async def handle_webhook(self, request: Request) -> dict:
        """Call this from the FastAPI /webhook/whatsapp route."""
        body = await request.json()
        msg_type = body.get("type", "")
        if msg_type == "message":
            message = body.get("message", {})
            text = message.get("body", "") or message.get("caption", "")
            if text:
                await self.on_message({
                    "platform": "whatsapp",
                    "from": message.get("from", ""),
                    "from_name": message.get("notifyName", ""),
                    "chat_id": message.get("from", ""),
                    "text": text,
                    "message_id": message.get("id", {}).get("id", ""),
                })
        return {"status": "ok"}

    async def send(self, chat_id: str, text: str) -> bool:
        """
        Send a WhatsApp message.
        chat_id format: "420XXXXXXXXX@c.us"  (international number without +)
        """
        url = f"{WHATSAPP_BRIDGE_URL}/send"
        payload = {"chatId": chat_id, "message": text}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status in (200, 201)
        except aiohttp.ClientError as exc:
            log.error("WhatsApp send failed: %s", exc)
            return False

    async def get_qr(self) -> str:
        """Return the QR code URL for linking WhatsApp (open in browser on Moto G15)."""
        return f"{WHATSAPP_BRIDGE_URL}/qr"

    async def status(self) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{WHATSAPP_BRIDGE_URL}/status", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return await resp.json()
        except Exception as exc:
            return {"error": str(exc)}


def phone_to_whatsapp_id(phone: str) -> str:
    """Convert E.164 phone to WhatsApp chat ID. '+420776168749' → '420776168749@c.us'"""
    return phone.lstrip("+") + "@c.us"
