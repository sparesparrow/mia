"""A small transport interface for envelopes (REQ-NET-009, ADR-0013).

A ``Channel`` moves whole messages (one ``write`` = one ``read`` on the other side); a ``Listener``
hands out a channel per incoming connection. Stream transports (TCP, unix socket, serial) need a
length prefix to find message boundaries; ``FramedChannel`` adds it. Datagram transports (UDP) do not.

Implemented here: ``LoopbackChannel`` (in memory, for tests and in-process peers), ``FramedChannel``
over any connected stream socket, ``SocketListener`` for TCP and unix sockets, and ``UdpChannel``.
ZeroMQ, BLE and a serial line are not implemented yet; a serial line is a ``FramedChannel`` over a
stream with ``recv`` / ``sendall``.

Nothing here authenticates a peer. A listener must be bound to loopback or a link that is trusted by
other means; who may send which command is decided one layer up (``VoiceService``).
"""

from __future__ import annotations

import queue
import select
import socket
import struct
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple

MAX_MESSAGE_BYTES = 64 * 1024
_HEADER = struct.Struct(">I")
SEND_TIMEOUT_SEC = (
    2.0  # a peer that stops reading is dropped instead of stalling every other peer
)


class ChannelClosed(Exception):
    """The channel is closed (here or by the peer) and holds no more messages."""


class MessageTooLarge(ValueError):
    pass


class Channel(ABC):
    @abstractmethod
    def write(self, data: bytes) -> None:
        """Send one message. Raises ``ChannelClosed`` if the channel cannot carry it."""

    @abstractmethod
    def read(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Return the next message, None if none arrived within ``timeout`` seconds.

        ``timeout=None`` waits until a message arrives or the channel closes, ``0`` only polls.
        Raises ``ChannelClosed`` once the channel is closed and nothing is left to read.
        """

    @property
    @abstractmethod
    def is_open(self) -> bool: ...

    @abstractmethod
    def close(self) -> None: ...


class Listener(ABC):
    @abstractmethod
    def accept(self, timeout: Optional[float] = None) -> Optional[Channel]:
        """Return the next incoming channel, None on timeout. Raises ``ChannelClosed`` when closed."""

    @abstractmethod
    def close(self) -> None: ...


def _remaining(deadline: Optional[float]) -> Optional[float]:
    """Seconds left until ``deadline`` for ``select``: None blocks, 0 polls."""
    return None if deadline is None else max(deadline - time.monotonic(), 0.0)


def _readable(sock: socket.socket, deadline: Optional[float]) -> bool:
    """Wait until ``sock`` can be read. Waiting with select keeps the socket's own timeout free for writes."""
    ready, _, _ = select.select([sock], [], [], _remaining(deadline))
    return bool(ready)


def _deadline(timeout: Optional[float]) -> Optional[float]:
    return None if timeout is None else time.monotonic() + timeout


def _check_size(data: bytes) -> None:
    if len(data) > MAX_MESSAGE_BYTES:
        raise MessageTooLarge(f"{len(data)} bytes exceeds {MAX_MESSAGE_BYTES}")


# ── In memory ─────────────────────────────────────────────────────────────

_EOF = object()


class LoopbackChannel(Channel):
    """One end of an in-memory pair. Closing either end closes both; queued messages stay readable."""

    def __init__(self) -> None:
        self._inbox: "queue.Queue[object]" = queue.Queue()
        self._peer: Optional[LoopbackChannel] = None
        self._open = True
        self._lock = threading.Lock()

    @classmethod
    def pair(cls) -> Tuple["LoopbackChannel", "LoopbackChannel"]:
        a, b = cls(), cls()
        a._peer, b._peer = b, a
        return a, b

    def write(self, data: bytes) -> None:
        _check_size(data)
        peer = self._peer
        if not self._open or peer is None or not peer._open:
            raise ChannelClosed("loopback channel is closed")
        peer._inbox.put(bytes(data))

    def read(self, timeout: Optional[float] = None) -> Optional[bytes]:
        try:
            if timeout is None:
                item = self._inbox.get()
            elif timeout <= 0:
                item = self._inbox.get_nowait()
            else:
                item = self._inbox.get(timeout=timeout)
        except queue.Empty:
            if not self._open:
                raise ChannelClosed("loopback channel is closed") from None
            return None
        if item is _EOF:
            self._inbox.put(_EOF)  # stay closed for the next read
            raise ChannelClosed("loopback channel is closed")
        return item  # type: ignore[return-value]

    @property
    def is_open(self) -> bool:
        return self._open

    def close(self) -> None:
        with self._lock:
            if not self._open:
                return
            self._open = False
        self._inbox.put(_EOF)
        peer = self._peer
        if peer is not None and peer._open:
            peer._open = False
            peer._inbox.put(_EOF)


# ── Streams (TCP, unix socket, anything with recv / sendall) ──────────────


class FramedChannel(Channel):
    """Length-prefixed messages over a connected stream socket (4-byte big-endian length)."""

    def __init__(self, stream: socket.socket) -> None:
        self._sock = stream
        self._sock.settimeout(SEND_TIMEOUT_SEC)
        self._buffer = bytearray()
        self._open = True
        self._write_lock = threading.Lock()

    def write(self, data: bytes) -> None:
        _check_size(data)
        if not self._open:
            raise ChannelClosed("stream is closed")
        try:
            with self._write_lock:
                self._sock.sendall(_HEADER.pack(len(data)) + data)
        except OSError as exc:
            self.close()
            raise ChannelClosed(str(exc)) from exc

    def _frame(self) -> Optional[bytes]:
        if len(self._buffer) < _HEADER.size:
            return None
        (length,) = _HEADER.unpack_from(self._buffer)
        if length > MAX_MESSAGE_BYTES:
            self.close()
            raise ChannelClosed(
                f"frame of {length} bytes exceeds {MAX_MESSAGE_BYTES}; stream dropped"
            )
        end = _HEADER.size + length
        if len(self._buffer) < end:
            return None
        data = bytes(self._buffer[_HEADER.size : end])
        del self._buffer[:end]
        return data

    def read(self, timeout: Optional[float] = None) -> Optional[bytes]:
        deadline = _deadline(timeout)
        while True:
            frame = self._frame()
            if frame is not None:
                return frame
            if not self._open:
                raise ChannelClosed("stream is closed")
            try:
                if not _readable(self._sock, deadline):
                    return None
                chunk = self._sock.recv(4096)
            except (BlockingIOError, socket.timeout):
                return None
            except (OSError, ValueError) as exc:
                self.close()
                raise ChannelClosed(str(exc)) from exc
            if not chunk:
                self.close()
                raise ChannelClosed("peer closed the stream")
            self._buffer.extend(
                chunk
            )  # a partial frame stays buffered; the loop waits for the rest

    @property
    def is_open(self) -> bool:
        return self._open

    def close(self) -> None:
        if not self._open:
            return
        self._open = False
        try:
            self._sock.close()
        except OSError:
            pass


class SocketListener(Listener):
    """Accepts connections on a bound, listening stream socket (TCP or unix) as ``FramedChannel``."""

    def __init__(self, server: socket.socket) -> None:
        self._server = server
        self._open = True

    @classmethod
    def tcp(cls, host: str = "127.0.0.1", port: int = 0) -> "SocketListener":
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        return cls(server)

    @classmethod
    def unix(cls, path: str) -> "SocketListener":
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen()
        return cls(server)

    @property
    def address(self):
        return self._server.getsockname()

    def accept(self, timeout: Optional[float] = None) -> Optional[Channel]:
        if not self._open:
            raise ChannelClosed("listener is closed")
        try:
            if not _readable(self._server, _deadline(timeout)):
                return None
            conn, _ = self._server.accept()
        except (BlockingIOError, socket.timeout):
            return None
        except (OSError, ValueError) as exc:
            self._open = False
            raise ChannelClosed(str(exc)) from exc
        return FramedChannel(conn)

    def close(self) -> None:
        if self._open:
            self._open = False
            try:
                self._server.close()
            except OSError:
                pass


def connect_tcp(host: str, port: int, timeout: float = 5.0) -> FramedChannel:
    return FramedChannel(socket.create_connection((host, port), timeout=timeout))


def connect_unix(path: str) -> FramedChannel:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(path)
    return FramedChannel(sock)


# ── Datagrams ─────────────────────────────────────────────────────────────


class UdpChannel(Channel):
    """One UDP socket talking to one peer: one message is one datagram, no framing.

    Datagrams from any other address are dropped. UDP can lose and reorder messages, so it suits
    state and cue broadcasts to an LED node, not commands that must arrive.
    """

    def __init__(
        self, local: Tuple[str, int], peer: Optional[Tuple[str, int]] = None
    ) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(local)
        self._peer = peer
        self._open = True

    @property
    def address(self) -> Tuple[str, int]:
        return self._sock.getsockname()

    def connect_to(self, peer: Tuple[str, int]) -> None:
        self._peer = peer

    @classmethod
    def pair(cls, host: str = "127.0.0.1") -> Tuple["UdpChannel", "UdpChannel"]:
        a, b = cls((host, 0)), cls((host, 0))
        a.connect_to(b.address)
        b.connect_to(a.address)
        return a, b

    def write(self, data: bytes) -> None:
        _check_size(data)
        if not self._open:
            raise ChannelClosed("udp channel is closed")
        if self._peer is None:
            raise ChannelClosed("udp channel has no peer")
        try:
            self._sock.sendto(data, self._peer)
        except OSError as exc:
            raise ChannelClosed(str(exc)) from exc

    def read(self, timeout: Optional[float] = None) -> Optional[bytes]:
        deadline = _deadline(timeout)
        while True:
            if not self._open:
                raise ChannelClosed("udp channel is closed")
            try:
                if not _readable(self._sock, deadline):
                    return None
                data, sender = self._sock.recvfrom(MAX_MESSAGE_BYTES + 1)
            except (BlockingIOError, socket.timeout):
                return None
            except (OSError, ValueError) as exc:
                self._open = False
                raise ChannelClosed(str(exc)) from exc
            if sender != self._peer or len(data) > MAX_MESSAGE_BYTES:
                continue  # not from our peer, or truncated: drop it
            return data

    @property
    def is_open(self) -> bool:
        return self._open

    def close(self) -> None:
        if self._open:
            self._open = False
            try:
                self._sock.close()
            except OSError:
                pass
