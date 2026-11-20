"""The phone's microphone arrives here and goes on to the audio capture service (ADR-0021, REQ-VOICE-027).

``/ws/audio`` is off unless ``VOICE_PHONE_MIC=1`` and needs an ``X-API-Key`` with the ``write`` scope (a
microphone is more than a read). The first frame is text, ``{"v":1,"fmt":"s16le","rate":16000,"ch":1,"frame_ms":30}``;
the answer is ``{"ok":true}``, or the socket closes with 1003. Then every binary frame must be a whole multiple of
``FRAME_BYTES`` (960 bytes, 30 ms); anything else is dropped and counted.

Frames leave through a ZeroMQ PUSH socket to ``services/audio_capture.py`` (loopback, ``AUDIO_INGEST_PORT``,
default 5566). The socket has a high-water mark of ``SEND_HWM`` frames and is never waited on: when the capture
service is slow or absent the frame is dropped and counted. Only one phone streams at a time; a new one replaces
the old, which is closed with 1008. The raw audio is never written anywhere and logs hold counts only.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_BYTES = SAMPLE_RATE * FRAME_MS // 1000 * 2  # 960
SEND_HWM = 8
HEADER_TIMEOUT_SEC = 5.0
DEFAULT_PORT = 5566
_CLOSE_POLICY = 1008
_CLOSE_UNSUPPORTED = 1003
_EXPECTED_HEADER = {"v": 1, "fmt": "s16le", "rate": SAMPLE_RATE, "ch": 1, "frame_ms": FRAME_MS}


def phone_mic_enabled() -> bool:
    return os.environ.get("VOICE_PHONE_MIC", "0") == "1"


def ingest_port() -> int:
    try:
        return int(os.environ.get("AUDIO_INGEST_PORT", str(DEFAULT_PORT)))
    except ValueError:
        return DEFAULT_PORT


def header_ok(text: Any) -> bool:
    """True only for the one stream format the pipeline takes (16 kHz mono PCM16 in 30 ms frames)."""
    if not isinstance(text, str):
        return False
    try:
        data = json.loads(text)
    except ValueError:
        return False
    return isinstance(data, dict) and all(
        key in data and data[key] == value and type(data[key]) is type(value) for key, value in _EXPECTED_HEADER.items()
    )


class ZmqPusher:
    """PUSH socket to the capture service, created on first use so importing this module needs no ZeroMQ."""

    def __init__(self, port: Optional[int] = None) -> None:
        self._port = port if port is not None else ingest_port()
        self._ctx: Any = None
        self._sock: Any = None

    def push(self, frame: bytes) -> bool:
        """Queue ``frame``; False when the queue is full or ZeroMQ is unavailable."""
        try:
            import zmq
        except ImportError:  # pragma: no cover - pyzmq is a hard requirement of the API
            return False
        if self._sock is None:
            self._ctx = zmq.Context.instance()
            self._sock = self._ctx.socket(zmq.PUSH)
            self._sock.setsockopt(zmq.SNDHWM, SEND_HWM)
            self._sock.setsockopt(zmq.LINGER, 0)
            self._sock.connect(f"tcp://127.0.0.1:{self._port}")
        try:
            self._sock.send(frame, zmq.NOBLOCK)
        except zmq.Again:
            return False
        return True

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close(0)
            self._sock = None


class AudioIngest:
    """Counts and forwards frames; knows nothing about WebSockets, so it is tested on its own."""

    def __init__(self, pusher: Callable[[bytes], bool]) -> None:
        self._push = pusher
        self.frames_pushed = 0
        self.frames_dropped = 0  # queue full or capture service not listening
        self.bad_frames = 0  # not a whole number of 30 ms frames

    def accept(self, data: bytes) -> int:
        """Forward one binary message; returns the number of frames that went on."""
        if not data or len(data) % FRAME_BYTES:
            self.bad_frames += 1
            return 0
        sent = 0
        for start in range(0, len(data), FRAME_BYTES):
            if self._push(data[start : start + FRAME_BYTES]):
                self.frames_pushed += 1
                sent += 1
            else:
                self.frames_dropped += 1
        return sent

    def counts(self) -> Dict[str, int]:
        return {
            "pushed": self.frames_pushed,
            "dropped": self.frames_dropped,
            "bad": self.bad_frames,
        }


_pusher = ZmqPusher()
_active: Optional[WebSocket] = None


async def serve(websocket: WebSocket) -> None:
    global _active
    # Authenticate before anything else, so an unauthenticated probe cannot tell whether the feature is on.
    from api.auth import authenticate_websocket

    if not await authenticate_websocket(websocket, "write"):  # closes with 1008 on failure
        return
    if not phone_mic_enabled():
        await websocket.close(code=_CLOSE_POLICY)
        return
    await websocket.accept()
    try:
        first = await asyncio.wait_for(websocket.receive(), HEADER_TIMEOUT_SEC)
    except (asyncio.TimeoutError, WebSocketDisconnect, RuntimeError):
        await _close_quietly(websocket, _CLOSE_UNSUPPORTED)
        return
    if first.get("type") != "websocket.receive" or not header_ok(first.get("text")):
        await _close_quietly(websocket, _CLOSE_UNSUPPORTED)
        return

    previous, _active = _active, websocket
    if previous is not None:
        await _close_quietly(previous, _CLOSE_POLICY)
    await websocket.send_text('{"ok":true}')
    ingest = AudioIngest(_pusher.push)
    logger.info("phone microphone connected")
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            data = message.get("bytes")
            if data is not None:
                ingest.accept(data)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if _active is websocket:
            _active = None
        logger.info("phone microphone disconnected: %s", ingest.counts())


async def _close_quietly(websocket: WebSocket, code: int) -> None:
    try:
        await websocket.close(code=code)
    except Exception:  # already closed
        pass
