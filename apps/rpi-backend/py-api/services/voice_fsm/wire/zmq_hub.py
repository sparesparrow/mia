"""Hosts the envelope router on a ZeroMQ ROUTER socket (ADR-0020, REQ-VOICE-024).

Each peer (the API's relay, one DEALER per console WebSocket) is one ``Connection``, found by its ZeroMQ
identity. Envelope bytes pass through unchanged. Two frames are not envelopes:

- an EMPTY frame means the peer is gone: its connection is closed and forgotten;
- ``PING`` is answered with ``PONG``, so a peer can tell a silent router from a quiet machine.

Any frame refreshes the peer's liveness; a peer silent for ``idle_sec`` is dropped, which is how the hub
learns of a relay that died without saying goodbye. The socket is bound to loopback; nothing here
authenticates a peer (the API does that before it opens a DEALER).

``service()`` never blocks: the router loop polls ``socket`` next to its other sockets and calls it when readable.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Tuple

try:
    import zmq
except ImportError:  # pragma: no cover - the router itself needs pyzmq
    zmq = None  # type: ignore[assignment]

from .channel import MAX_MESSAGE_BYTES
from .router import Connection, EnvelopeRouter

logger = logging.getLogger(__name__)

DEFAULT_PORT = 5565
PING = b"ping"
PONG = b"pong"
IDLE_SEC = 10.0
_MAX_FRAMES_PER_SERVICE = 64


class ZmqHub:
    def __init__(
        self,
        router: EnvelopeRouter,
        context: Any,
        port: int = DEFAULT_PORT,
        host: str = "127.0.0.1",
        idle_sec: float = IDLE_SEC,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.router = router
        self._clock = clock
        self._idle_sec = idle_sec
        self.socket = context.socket(zmq.ROUTER)
        self.socket.setsockopt(zmq.LINGER, 0)
        try:
            if port:
                self.socket.bind(f"tcp://{host}:{port}")
                self.port = port
            else:
                self.port = self.socket.bind_to_random_port(f"tcp://{host}")
        except Exception:
            self.socket.close(0)  # an open socket would hang the context's term()
            raise
        # identity -> (connection, last frame seen)
        self._peers: Dict[bytes, Tuple[Connection, float]] = {}

    @property
    def peers(self) -> int:
        return len(self._peers)

    def service(self) -> None:
        """Handle every frame that is waiting, then drop peers that went quiet."""
        for _ in range(_MAX_FRAMES_PER_SERVICE):
            try:
                frames = self.socket.recv_multipart(zmq.NOBLOCK)
            except zmq.Again:
                break
            if len(frames) != 2:
                continue  # a DEALER sends one frame; anything else is not ours
            self._on_frame(frames[0], frames[1])
        self.reap()

    def flush(self) -> None:
        """Broadcast what the services produced outside any console request (speech, TTS, the clock)."""
        self.router.tick()

    def reap(self) -> None:
        now = self._clock()
        for identity, (connection, seen) in list(self._peers.items()):
            if not connection.alive or now - seen > self._idle_sec:
                self._forget(identity)

    def close(self) -> None:
        for identity in list(self._peers):
            self._forget(identity)
        self.socket.close(0)

    # ── Internals ─────────────────────────────────────────────────────────

    def _on_frame(self, identity: bytes, frame: bytes) -> None:
        if not frame:
            self._forget(identity)
            return
        if len(frame) > MAX_MESSAGE_BYTES:
            logger.warning(
                "voice hub: dropping an oversized frame (%d bytes)", len(frame)
            )
            return
        entry = self._peers.get(identity)
        if entry is not None and not entry[0].alive:
            self._forget(
                identity
            )  # the router dropped it (a failing sink): this is a new connection
            entry = None
        connection = entry[0] if entry else self._connect(identity)
        self._peers[identity] = (connection, self._clock())
        if frame == PING:
            self._send(identity, PONG)
            return
        connection.handle(frame)

    def _connect(self, identity: bytes) -> Connection:
        return self.router.connect(lambda data, _id=identity: self._send(_id, data))

    def _send(self, identity: bytes, data: bytes) -> None:
        # NOBLOCK: a peer that stops reading raises zmq.Again; the router treats that as a dead peer and drops it.
        self.socket.send_multipart([identity, data], zmq.NOBLOCK)

    def _forget(self, identity: bytes) -> None:
        entry = self._peers.pop(identity, None)
        if entry is not None:
            entry[0].close()
