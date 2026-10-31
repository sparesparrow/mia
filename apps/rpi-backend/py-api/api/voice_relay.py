"""Relays /ws/voice to the voice router over ZeroMQ (ADR-0020, REQ-VOICE-024).

The machine lives in ``voice_command_router``; this process only carries bytes. Per WebSocket it opens one
DEALER to the router's loopback ROUTER socket and forwards binary frames both ways without decoding them.

- A frame that is empty means "disconnect" to the router, so empty frames from the console are not forwarded;
  when the WebSocket ends, one empty frame is sent.
- ``ping`` goes out every ``PING_SEC``; the router answers ``pong``. Nothing received for ``SILENCE_SEC``
  (the router is down or stuck) closes the WebSocket with 1013 "voice router offline".
- The router's frames wait in a queue of ``OUTBOX_LIMIT`` for the WebSocket; a console that stops reading
  is closed with 1013, as in the simulated backend.
- A text frame is refused with 1003, like in ``voice_console``.

Authentication happens in ``voice_console.serve`` before this runs.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Optional

try:
    import zmq
    import zmq.asyncio as zmq_asyncio
except ImportError:  # pragma: no cover - pyzmq is a hard requirement of the API
    zmq = None  # type: ignore[assignment]
    zmq_asyncio = None  # type: ignore[assignment]

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

PING = b"ping"
PONG = b"pong"
PING_SEC = 2.0
SILENCE_SEC = 6.0
WATCH_SEC = 0.25
OUTBOX_LIMIT = 256
MAX_FRAME_BYTES = 64 * 1024
DEFAULT_PORT = 5565
CLOSE_UNSUPPORTED = 1003
CLOSE_TRY_AGAIN = 1013
OFFLINE_REASON = "voice router offline"

# Read at call time so a test can replace it with a fake clock.
_clock = time.monotonic


def endpoint() -> str:
    explicit = os.environ.get("VOICE_CONSOLE_ENDPOINT")
    if explicit:
        return explicit
    return f"tcp://127.0.0.1:{int(os.environ.get('VOICE_CONSOLE_PORT', DEFAULT_PORT))}"


class _Session:
    """State shared by the tasks of one relayed WebSocket."""

    def __init__(self, websocket: WebSocket, sock: Any) -> None:
        self.websocket = websocket
        self.sock = sock
        self.outbox: "asyncio.Queue[bytes]" = asyncio.Queue(maxsize=OUTBOX_LIMIT)
        self.last_rx = _clock()
        self.router_seen = False
        self.close_code: Optional[int] = None
        self.close_reason = ""

    def close_with(self, code: int, reason: str = "") -> None:
        if self.close_code is None:
            self.close_code, self.close_reason = code, reason


async def _from_console(s: _Session) -> None:
    while True:
        message = await s.websocket.receive()
        if message["type"] == "websocket.disconnect":
            return
        data = message.get("bytes")
        if data is None:
            s.close_with(CLOSE_UNSUPPORTED)  # envelopes are binary
            return
        if not data:
            continue  # an empty frame would read as a disconnect to the router
        if len(data) > MAX_FRAME_BYTES:
            s.close_with(CLOSE_UNSUPPORTED)
            return
        try:
            await s.sock.send(data, zmq.NOBLOCK)
        except zmq.Again:
            logger.warning("voice relay: router queue is full, frame dropped")


async def _from_router(s: _Session) -> None:
    while True:
        data = await s.sock.recv()
        s.last_rx = _clock()
        s.router_seen = True
        if data == PONG or not data:
            continue
        try:
            s.outbox.put_nowait(data)
        except asyncio.QueueFull:
            s.close_with(CLOSE_TRY_AGAIN, "console is not reading")
            return


async def _to_console(s: _Session) -> None:
    while True:
        await s.websocket.send_bytes(await s.outbox.get())


async def _ping(s: _Session) -> None:
    while True:
        try:
            await s.sock.send(PING, zmq.NOBLOCK)
        except zmq.Again:
            pass
        await asyncio.sleep(PING_SEC)


async def _watch(s: _Session) -> None:
    while True:
        await asyncio.sleep(WATCH_SEC)
        if _clock() - s.last_rx > SILENCE_SEC:
            logger.warning(
                "voice relay: no word from the router for %.0f s", SILENCE_SEC
            )
            s.close_with(CLOSE_TRY_AGAIN, OFFLINE_REASON)
            return


async def serve_relay(websocket: WebSocket) -> None:
    """Relay one already authenticated console until either side ends."""
    if zmq is None:
        await websocket.close(code=CLOSE_TRY_AGAIN)
        return
    await websocket.accept()
    context = zmq_asyncio.Context()
    sock = context.socket(zmq.DEALER)
    sock.setsockopt(zmq.LINGER, 0)
    sock.connect(endpoint())
    session = _Session(websocket, sock)
    tasks = [
        asyncio.create_task(t(session))
        for t in (_from_console, _from_router, _to_console, _ping, _watch)
    ]
    try:
        # Whichever task ends first (console gone, overflow, silence, a failed send) ends the session.
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if session.router_seen:
            try:  # tell the router this console is gone; a short linger lets the frame leave
                sock.setsockopt(zmq.LINGER, 500)
                await sock.send(b"", zmq.NOBLOCK)
            except (
                Exception
            ):  # noqa: BLE001 - nothing more to do for a socket that cannot send
                pass
        sock.close()
        context.term()
    if session.close_code is not None:
        try:
            await websocket.close(code=session.close_code, reason=session.close_reason)
        except (RuntimeError, WebSocketDisconnect):
            pass  # the console is already gone
