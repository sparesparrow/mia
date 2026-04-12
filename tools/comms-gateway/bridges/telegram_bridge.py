"""
bridges/telegram_bridge.py
───────────────────────────
Telegram ↔ MIA gateway.

Two modes:
  bot   — Telegram Bot API via python-telegram-bot (no phone number needed)
  user  — MTProto user account via telethon (receives all messages in conversations)

Set TELEGRAM_BOT_TOKEN for bot mode.
Set TELEGRAM_API_ID + TELEGRAM_API_HASH for user/MTProto mode.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Callable, Awaitable

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH, MIA_WS_URL

log = logging.getLogger("telegram_bridge")

MessageHandler = Callable[[dict], Awaitable[None]]


# ── Bot mode (Bot API) ─────────────────────────────────────────────────────────

class TelegramBotBridge:
    """
    Receives messages via webhook/polling, forwards to MIA WS.
    Requires: pip install python-telegram-bot
    """

    def __init__(self, on_message: MessageHandler) -> None:
        self.on_message = on_message

    async def start(self) -> None:
        try:
            from telegram.ext import ApplicationBuilder, MessageHandler as TGHandler, filters
            from telegram import Update
        except ImportError:
            log.error("pip install python-telegram-bot")
            return

        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        async def _handle(update: Update, ctx) -> None:
            msg = update.effective_message
            if not msg:
                return
            await self.on_message({
                "platform": "telegram",
                "mode": "bot",
                "from": str(msg.from_user.id if msg.from_user else "unknown"),
                "from_name": msg.from_user.full_name if msg.from_user else "",
                "chat_id": str(msg.chat_id),
                "text": msg.text or "",
                "message_id": msg.message_id,
            })

        app.add_handler(TGHandler(filters.TEXT & ~filters.COMMAND, _handle))
        log.info("Telegram bot polling started")
        async with app:
            await app.start()
            await app.updater.start_polling()
            await asyncio.Event().wait()   # run forever
            await app.updater.stop()
            await app.stop()

    async def send(self, chat_id: str, text: str) -> None:
        from telegram import Bot
        async with Bot(TELEGRAM_BOT_TOKEN) as bot:
            await bot.send_message(chat_id=int(chat_id), text=text)


# ── User/MTProto mode (Telethon) ───────────────────────────────────────────────

class TelegramUserBridge:
    """
    Full user account — sees all conversations, can send/receive anywhere.
    Requires: pip install telethon
    Session file stored at /tmp/mia_telegram.session (persist across restarts)
    """

    def __init__(self, on_message: MessageHandler, session_path: str = "/tmp/mia_telegram.session") -> None:
        self.on_message = on_message
        self.session_path = session_path
        self._client = None

    async def start(self) -> None:
        try:
            from telethon import TelegramClient, events
        except ImportError:
            log.error("pip install telethon")
            return

        client = TelegramClient(self.session_path, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        self._client = client

        @client.on(events.NewMessage(incoming=True))
        async def _handler(event):
            sender = await event.get_sender()
            await self.on_message({
                "platform": "telegram",
                "mode": "user",
                "from": str(sender.id) if sender else "unknown",
                "from_name": getattr(sender, "first_name", "") + " " + getattr(sender, "last_name", ""),
                "chat_id": str(event.chat_id),
                "text": event.raw_text,
            })

        await client.start()
        log.info("Telegram user account connected")
        await client.run_until_disconnected()

    async def send(self, chat_id: str | int, text: str) -> None:
        if self._client:
            await self._client.send_message(int(chat_id), text)
