"""WebSocket console for the voice state machine (ADR-0013, REQ-NET-008).

Binary frames are envelopes (``schemas/voice.fbs``). A console may send the button commands and
the verbosity setting and receives the machine's state, feedback cues and spoken phrases.

Off unless ``VOICE_CONSOLE=1``. The machine behind it lives in this process on the system clock, so
the console talks to a simulation, not to the voice pipeline that runs in ``voice_command_router``;
attaching the two is a separate step.

Like every WebSocket of this API it needs the ``X-API-Key`` header when keys are configured (REQ-SEC-001).
That check only needs a read key, so a read-only key can press the buttons; a stricter scope is a follow-up.
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
_CLOSE_TRY_AGAIN = 1013
OUTBOX_LIMIT = 256

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


class OutboxFull(Exception):
    """A console stopped reading and its queue of unsent frames is full."""


def make_sink(outbox: "asyncio.Queue[bytes]", overflowed: asyncio.Event):
    """The router's sink for one console.

    Raising makes the router drop the connection (it treats a failing sink as a dead peer), so one slow console
    cannot make the API buffer events without limit or hold up the others. ``put_nowait`` is only safe because
    every producer runs on the event loop thread: the machine is driven from this endpoint and nowhere else.
    """

    def sink(data: bytes) -> None:
        try:
            outbox.put_nowait(data)
        except asyncio.QueueFull:
            overflowed.set()
            raise OutboxFull("console is not reading") from None

    return sink


async def serve(websocket: WebSocket) -> None:
    # Authenticate before anything else, so an unauthenticated probe cannot tell whether the console is on.
    from api.auth import authenticate_websocket

    if not await authenticate_websocket(websocket):  # closes with 1008 on failure
        return
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
    outbox: "asyncio.Queue[bytes]" = asyncio.Queue(maxsize=OUTBOX_LIMIT)
    overflowed = asyncio.Event()
    connection = router.connect(make_sink(outbox, overflowed))

    async def forward() -> None:
        while True:
            await websocket.send_bytes(await outbox.get())

    async def clock() -> None:
        while True:
            await asyncio.sleep(TICK_SEC)
            router.tick()

    async def watch_overflow() -> None:
        await overflowed.wait()
        await websocket.close(code=_CLOSE_TRY_AGAIN)

    tasks = [asyncio.create_task(t()) for t in (forward, clock, watch_overflow)]
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
