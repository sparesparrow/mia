"""WebSocket console for the voice state machine (ADR-0013, REQ-NET-008).

Binary frames are envelopes (``schemas/voice.fbs``). A console may send the button commands and
the verbosity setting and receives the machine's state, feedback cues and spoken phrases.

Off unless ``VOICE_CONSOLE=1``. The machine behind it lives in this process on the system clock, so
the console talks to a simulation, not to the voice pipeline that runs in ``voice_command_router``;
attaching the two is a separate step. The socket has no authentication, like the other WebSockets
of this API, so enable it only on a link you trust.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

TICK_SEC = 0.1
_CLOSE_POLICY = 1008
_CLOSE_UNSUPPORTED = 1003

_router: Optional[Any] = None


def console_enabled() -> bool:
    return os.environ.get("VOICE_CONSOLE", "0") == "1"


def get_router() -> Any:
    """The shared router with its simulated voice service, built on first use."""
    global _router
    if _router is None:
        from services.voice_fsm import VoiceMachine
        from services.voice_fsm.wire import EnvelopeRouter, Service, VoiceService

        router = EnvelopeRouter()
        router.register(Service.VOICE, VoiceService(VoiceMachine(time.monotonic)))
        _router = router
    return _router


async def serve(websocket: WebSocket) -> None:
    if not console_enabled():
        await websocket.close(code=_CLOSE_POLICY)
        return
    try:
        router = get_router()
    except ImportError as exc:  # the generated bindings are missing
        logger.error("voice console unavailable: %s", exc)
        await websocket.close(code=_CLOSE_POLICY)
        return

    await websocket.accept()
    outbox: "asyncio.Queue[bytes]" = asyncio.Queue()
    connection = router.connect(outbox.put_nowait)

    async def forward() -> None:
        while True:
            await websocket.send_bytes(await outbox.get())

    async def clock() -> None:
        while True:
            await asyncio.sleep(TICK_SEC)
            router.tick()

    tasks = [asyncio.create_task(forward()), asyncio.create_task(clock())]
    try:
        while connection.alive:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            data = message.get("bytes")
            if data is None:
                await websocket.close(code=_CLOSE_UNSUPPORTED)  # envelopes are binary
                break
            connection.handle(data)
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()
        connection.close()
