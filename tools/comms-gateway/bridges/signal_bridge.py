"""
bridges/signal_bridge.py
─────────────────────────
Signal ↔ MIA via signal-cli-rest-api (Docker).

Docker: bbernhard/signal-cli-rest-api
  First-time setup: register or link your phone number.
  See: docker-compose.yml → service: signal-cli

REST API docs: http://<host>:8080/v1/about
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Callable, Awaitable

import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SIGNAL_REST_URL, SIGNAL_PHONE

log = logging.getLogger("signal_bridge")

MessageHandler = Callable[[dict], Awaitable[None]]


class SignalBridge:
    """
    Polls signal-cli-rest-api for new messages and forwards to MIA.
    Sends Signal messages via the REST API.
    """

    def __init__(self, on_message: MessageHandler, poll_interval: float = 2.0) -> None:
        self.on_message = on_message
        self.poll_interval = poll_interval
        self._running = False

    async def start(self) -> None:
        self._running = True
        log.info("Signal bridge polling %s for %s", SIGNAL_REST_URL, SIGNAL_PHONE)
        while self._running:
            try:
                await self._receive()
            except aiohttp.ClientError as exc:
                log.warning("Signal REST unavailable: %s", exc)
            await asyncio.sleep(self.poll_interval)

    async def _receive(self) -> None:
        url = f"{SIGNAL_REST_URL}/v1/receive/{SIGNAL_PHONE}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return
                messages = await resp.json()
                for envelope in messages or []:
                    msg = envelope.get("envelope", {})
                    data_msg = msg.get("dataMessage", {})
                    text = data_msg.get("message", "")
                    if not text:
                        continue
                    await self.on_message({
                        "platform": "signal",
                        "from": msg.get("source", ""),
                        "from_name": msg.get("sourceName", ""),
                        "text": text,
                        "timestamp": msg.get("timestamp"),
                    })

    async def send(self, recipient: str, text: str) -> bool:
        """Send a Signal message. recipient = phone number or group ID."""
        url = f"{SIGNAL_REST_URL}/v2/send"
        payload = {
            "number": SIGNAL_PHONE,
            "recipients": [recipient],
            "message": text,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status in (200, 201)
        except aiohttp.ClientError as exc:
            log.error("Signal send failed: %s", exc)
            return False

    def stop(self) -> None:
        self._running = False


async def register_signal_number(phone: str, use_voice: bool = False) -> None:
    """One-time: register phone number with Signal via signal-cli-rest-api."""
    url = f"{SIGNAL_REST_URL}/v1/register/{phone}"
    params = {"use_voice": str(use_voice).lower()}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            print(f"Register {phone}: {resp.status} {await resp.text()}")


async def verify_signal_number(phone: str, code: str) -> None:
    """One-time: verify the SMS/voice code received after register_signal_number."""
    url = f"{SIGNAL_REST_URL}/v1/register/{phone}/verify/{code}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url) as resp:
            print(f"Verify {phone}: {resp.status} {await resp.text()}")
