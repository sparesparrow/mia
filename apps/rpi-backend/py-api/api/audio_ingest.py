"""Phone microphone WebSocket ingest for the Pi audio capture service (ADR-0021)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

import zmq
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

FRAME_BYTES = 960  # 16 kHz, mono, signed 16-bit PCM, 30 ms
MAX_MESSAGE_BYTES = FRAME_BYTES * 6
PHONE_AUDIO_PORT = int(os.environ.get("ZMQ_PHONE_AUDIO_PORT", "5564"))
_active_socket: Optional[WebSocket] = None
_push_socket = None


def _enabled() -> bool:
    return os.environ.get("VOICE_PHONE_MIC", "0") == "1"


def _get_push_socket():
    global _push_socket
    if _push_socket is None:
        context = zmq.Context.instance()
        _push_socket = context.socket(zmq.PUSH)
        _push_socket.setsockopt(zmq.LINGER, 0)
        _push_socket.setsockopt(zmq.SNDHWM, 8)
        _push_socket.connect(f"tcp://127.0.0.1:{PHONE_AUDIO_PORT}")
    return _push_socket


def _valid_format(message: object) -> bool:
    return (
        isinstance(message, dict)
        and type(message.get("v")) is int
        and message.get("v") == 1
        and message.get("fmt") == "s16le"
        and type(message.get("rate")) is int
        and message.get("rate") == 16000
        and type(message.get("ch")) is int
        and message.get("ch") == 1
        and type(message.get("frame_ms")) is int
        and message.get("frame_ms") == 30
    )


async def serve(websocket: WebSocket) -> None:
    """Accept one authenticated phone stream and forward bounded PCM frames to audio_capture."""
    global _active_socket

    from api.auth import authenticate_websocket

    if not await authenticate_websocket(websocket, required_scope="write"):
        return
    if not _enabled():
        await websocket.close(code=1008, reason="phone microphone is disabled")
        return

    previous = _active_socket
    _active_socket = websocket
    if previous is not None and previous is not websocket:
        try:
            await previous.close(code=1008, reason="replaced by a newer phone microphone session")
        except Exception:
            pass

    accepted_frames = 0
    dropped_frames = 0
    try:
        await websocket.accept()
        try:
            first = await asyncio.wait_for(websocket.receive(), timeout=5.0)
            if first.get("type") == "websocket.disconnect":
                return
            if first.get("text") is None:
                await websocket.close(code=1003, reason="audio format must be declared first")
                return
            try:
                format_message = json.loads(first["text"])
            except (TypeError, json.JSONDecodeError):
                format_message = None
            if not _valid_format(format_message):
                await websocket.close(code=1003, reason="unsupported audio format")
                return
            await websocket.send_json({"ok": True})
            await websocket.send_json({"mic": "open"})
        except asyncio.TimeoutError:
            await websocket.close(code=1008, reason="audio format handshake timed out")
            return
        except Exception as exc:
            logger.info("Phone microphone handshake ended: %s", exc.__class__.__name__)
            return

        push_socket = _get_push_socket()
        while _active_socket is websocket:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            payload = message.get("bytes")
            if payload is None:
                await websocket.close(code=1003, reason="expected binary PCM frames")
                break
            if not payload or len(payload) > MAX_MESSAGE_BYTES or len(payload) % FRAME_BYTES:
                dropped_frames += max(1, len(payload) // FRAME_BYTES)
                continue
            for offset in range(0, len(payload), FRAME_BYTES):
                try:
                    push_socket.send(payload[offset:offset + FRAME_BYTES], flags=zmq.NOBLOCK)
                    accepted_frames += 1
                except zmq.Again:
                    dropped_frames += 1

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Phone microphone stream ended: %s", exc.__class__.__name__)
    finally:
        if _active_socket is websocket:
            _active_socket = None
        logger.info(
            "Phone microphone stream closed: accepted_frames=%d dropped_frames=%d",
            accepted_frames,
            dropped_frames,
        )
