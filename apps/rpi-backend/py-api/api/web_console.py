"""The Pi's own web console: configuration and a live view without the phone (ADR-0029, REQ-WEB-006).

``GET /console/`` serves one static page (``api/console/``) that runs in any browser on the Pi's screen or on a
laptop on the car's network. The page reads the API it already has (``/status``, ``/telemetry``,
``/audio/settings``) and two routes added here:

- ``GET /console/voice/events``: the voice machine as newline-delimited JSON, one event per line. The API opens a
  session of its own on the voice machine (the in-process simulation or, with ``VOICE_CONSOLE_BACKEND=router``, the
  router over ZeroMQ) and never sends it a command, so the stream only watches.
- ``POST /console/voice/settings``: verbosity, persona and language. These are the three settings commands of the
  console protocol (``spec/interfaces/voice.md``); the machine checks and stores them as it does for the phone.

Neither route, nor anything on the page, writes to a vehicle bus, a GPIO pin, the LEDs or ``/command``.

Who may reach it (``console_gate``), on top of the API's own key check:

- ``MIA_WEB_CONSOLE=0`` turns every ``/console`` route off (404).
- A loopback client (a browser on the Pi) may always use it.
- A client on a private, link-local or unique-local address may use it only when an API key is configured, so the
  page is never open on the car's network without authentication.
- Any other address is refused. With no key configured the ``Host`` header must name loopback too, so a
  DNS-rebinding page in a local browser cannot read the stream.

The voice routes also need ``VOICE_CONSOLE=1``, the switch that exposes the voice machine over ``/ws/voice``.
"""

from __future__ import annotations

import asyncio
import dataclasses
import ipaddress
import json
import logging
import os
import re
import secrets
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from api import voice_console, voice_relay
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("mia.web_console")

router = APIRouter(tags=["Web console"])

STATIC_DIR = Path(__file__).resolve().parent / "console"
# The page's own files, served by name so nothing else under the directory is reachable.
PAGE_FILES = {
    "/console/": ("index.html", "text/html; charset=utf-8"),
    "/console/console.js": ("console.js", "text/javascript; charset=utf-8"),
    "/console/console.css": ("console.css", "text/css; charset=utf-8"),
}
PUBLIC_PAGE_PATHS = frozenset({"/console", *PAGE_FILES})  # must equal auth CONSOLE_PAGE_PATHS

# The page loads nothing from elsewhere: the Pi in the car has no internet of its own.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-cache",
}

KEEPALIVE_SEC = 10.0
TICK_SEC = voice_console.TICK_SEC
OPEN_TIMEOUT_SEC = 3.0
REPLY_TIMEOUT_SEC = 2.0
OUTBOX_LIMIT = 256
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})
# The car's network: RFC 1918, link-local and unique-local. Listed, not ``is_private``, which also counts
# documentation and reserved ranges.
LOCAL_NETWORKS = tuple(
    ipaddress.ip_network(n)
    for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16", "fc00::/7", "fe80::/10")
)


def console_on() -> bool:
    return os.environ.get("MIA_WEB_CONSOLE", "1").strip() != "0"


def _auth_configured() -> bool:
    try:
        from api.auth import auth_configured
    except ImportError:  # the API runs without its auth module: treat as open
        return False
    return auth_configured()


def _client_address(request: Request) -> Optional[ipaddress._BaseAddress]:
    host = request.client.host if request.client else ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def _host_name(request: Request) -> str:
    host = request.headers.get("host", "")
    if host.startswith("["):
        return host.split("]", 1)[0] + "]"
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def client_allowed(request: Request) -> Optional[str]:
    """None if this client may use the console, else the reason it may not."""
    address = _client_address(request)
    if address is None:
        return "unknown client address"
    if address.is_loopback:
        if not _auth_configured() and _host_name(request).lower() not in _LOOPBACK_HOSTS:
            return "with no API key configured the console answers only to localhost"
        return None
    if any(address in network for network in LOCAL_NETWORKS):
        if not _auth_configured():
            return "set MIA_API_KEY on the Pi before opening the console from the network"
        return None
    return "the console is only served to the Pi itself and its local network"


async def console_gate(request: Request) -> None:
    if not console_on():
        raise HTTPException(status_code=404, detail="Not Found")
    reason = client_allowed(request)
    if reason is not None:
        logger.warning("web console refused %s: %s", request.client, reason)
        raise HTTPException(status_code=403, detail=reason)


# ── The page ──────────────────────────────────────────────────────────────


@router.get("/console", include_in_schema=False, dependencies=[Depends(console_gate)])
async def console_redirect() -> RedirectResponse:
    return RedirectResponse("/console/", status_code=307)


def _page_file(path: str) -> FileResponse:
    name, media_type = PAGE_FILES[path]
    return FileResponse(STATIC_DIR / name, media_type=media_type, headers=SECURITY_HEADERS)


@router.get("/console/", include_in_schema=False, dependencies=[Depends(console_gate)])
async def console_page() -> FileResponse:
    return _page_file("/console/")


@router.get("/console/console.js", include_in_schema=False, dependencies=[Depends(console_gate)])
async def console_script() -> FileResponse:
    return _page_file("/console/console.js")


@router.get("/console/console.css", include_in_schema=False, dependencies=[Depends(console_gate)])
async def console_style() -> FileResponse:
    return _page_file("/console/console.css")


# ── Voice machine peers ───────────────────────────────────────────────────


class VoiceUnavailable(Exception):
    """The voice machine cannot be reached (console off, router down, bindings missing)."""


class _SimPeer:
    """A connection to the simulated machine in this process (``VOICE_CONSOLE_BACKEND=sim``).

    The simulation only moves when someone ticks it, as each ``/ws/voice`` console does; a watcher ticks it too,
    so a phrase it is watching ends on time even when no phone is connected.
    """

    backend = "sim"

    def __init__(self) -> None:
        try:
            self._router = voice_console.get_router()
        except ImportError as exc:  # the generated bindings are missing
            raise VoiceUnavailable(f"voice bindings missing: {exc}") from exc
        self._inbox: "asyncio.Queue[bytes]" = asyncio.Queue(maxsize=OUTBOX_LIMIT)
        self._connection = self._router.connect(self._sink)
        self._ticker = asyncio.create_task(self._tick())

    def _sink(self, data: bytes) -> None:
        try:
            self._inbox.put_nowait(data)
        except asyncio.QueueFull:
            raise voice_console.OutboxFull("web console is not reading") from None

    async def _tick(self) -> None:
        while True:
            await asyncio.sleep(TICK_SEC)
            self._router.tick()

    async def send(self, data: bytes) -> None:
        self._connection.handle(data)

    async def recv(self, timeout: float) -> Optional[bytes]:
        if not self._connection.alive and self._inbox.empty():
            raise VoiceUnavailable("dropped by the voice machine")
        try:
            return await asyncio.wait_for(self._inbox.get(), timeout)
        except asyncio.TimeoutError:
            return None

    async def close(self) -> None:
        self._ticker.cancel()
        self._connection.close()


class _RouterPeer:
    """A DEALER on the voice router's loopback ROUTER socket, as ``voice_relay`` opens per WebSocket."""

    backend = "router"

    def __init__(self) -> None:
        if voice_relay.zmq is None:
            raise VoiceUnavailable("pyzmq is not installed")
        zmq = voice_relay.zmq
        self._context = voice_relay.zmq_asyncio.Context()
        self._sock = self._context.socket(zmq.DEALER)
        self._sock.setsockopt(zmq.LINGER, 0)
        self._sock.connect(voice_relay.endpoint())
        self._last_rx = voice_relay._clock()
        self._seen = False
        self._pinger = asyncio.create_task(self._ping())

    async def _ping(self) -> None:
        zmq = voice_relay.zmq
        while True:
            try:
                await self._sock.send(voice_relay.PING, zmq.NOBLOCK)
            except zmq.Again:
                pass
            await asyncio.sleep(voice_relay.PING_SEC)

    async def send(self, data: bytes) -> None:
        await self._sock.send(data, voice_relay.zmq.NOBLOCK)

    async def recv(self, timeout: float) -> Optional[bytes]:
        clock = voice_relay._clock
        deadline = clock() + timeout
        while True:
            if clock() - self._last_rx > voice_relay.SILENCE_SEC:
                raise VoiceUnavailable(voice_relay.OFFLINE_REASON)
            left = deadline - clock()
            if left <= 0:
                return None
            if not await self._sock.poll(int(min(left, voice_relay.WATCH_SEC) * 1000)):
                continue
            data = await self._sock.recv()
            self._last_rx = clock()
            self._seen = True
            if data and data != voice_relay.PONG:
                return data

    async def close(self) -> None:
        self._pinger.cancel()
        if self._seen:
            try:  # tell the hub this peer is gone, as the relay does
                self._sock.setsockopt(voice_relay.zmq.LINGER, 500)
                await self._sock.send(b"", voice_relay.zmq.NOBLOCK)
            except Exception:  # noqa: BLE001 - a socket that cannot send has nothing more to say
                pass
        self._sock.close()
        self._context.term()


def open_peer() -> Any:
    if not voice_console.console_enabled():
        raise VoiceUnavailable("the voice console is off (VOICE_CONSOLE=1 turns it on)")
    if voice_console.console_backend() == "router":
        return _RouterPeer()
    return _SimPeer()


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


EVENT_TYPES = {
    "StateChanged": "state",
    "Feedback": "feedback",
    "Speak": "speak",
    "Transcript": "transcript",
    "Settings": "settings",
}


def event_json(event: Any) -> Dict[str, Any]:
    """A decoded voice event as a JSON object with a ``type`` (see ``spec/interfaces/voice.md``)."""
    name = type(event).__name__
    fields = dataclasses.asdict(event) if dataclasses.is_dataclass(event) else {}
    return {"type": EVENT_TYPES.get(name, name.lower()), **{k: _plain(v) for k, v in fields.items()}}


class _Session:
    """One session of the web console on the voice machine; the envelope router sends it every event."""

    def __init__(self, peer: Any) -> None:
        from services.voice_fsm.wire import Op, Service

        self.peer = peer
        self.id = "web-" + secrets.token_hex(4)
        self.events: List[bytes] = []  # event payloads not yet read, in arrival order
        self._seq = 0
        self._op = Op
        self._service = Service

    def _envelope(self, op: int, payload: bytes = b"") -> bytes:
        from services.voice_fsm.wire import Envelope, Status, encode_envelope

        self._seq += 1
        return encode_envelope(Envelope(self._service.VOICE, self.id, op, Status.OK, self._seq, payload))

    async def open(self) -> None:
        """Open the session; the settings snapshot that follows the OK reply is read as the first event."""
        from services.voice_fsm.wire import Status

        await self.peer.send(self._envelope(self._op.OPEN))
        seq = self._seq
        deadline = asyncio.get_running_loop().time() + OPEN_TIMEOUT_SEC
        while True:
            left = deadline - asyncio.get_running_loop().time()
            if left <= 0:
                raise VoiceUnavailable("the voice machine did not answer")
            envelope = await self._next(left)
            if envelope is None:
                continue
            if envelope.op == self._op.OPEN and envelope.seq == seq:
                if envelope.status != Status.OK:
                    raise VoiceUnavailable(f"session refused ({Status(envelope.status).name})")
                return

    async def command(self, command: Any) -> int:
        """Send one command and return the status the machine answered with."""
        from services.voice_fsm.wire import encode_command

        await self.peer.send(self._envelope(self._op.DATA, encode_command(command)))
        seq = self._seq
        deadline = asyncio.get_running_loop().time() + REPLY_TIMEOUT_SEC
        while True:
            left = deadline - asyncio.get_running_loop().time()
            if left <= 0:
                raise VoiceUnavailable("the voice machine did not answer")
            envelope = await self._next(left)
            if envelope is not None and not envelope.payload and envelope.seq == seq:
                return envelope.status

    async def _next(self, timeout: float):
        from services.voice_fsm.wire import CodecError, decode_envelope

        data = await self.peer.recv(timeout)
        if data is None:
            return None
        try:
            envelope = decode_envelope(data)
        except CodecError:
            logger.warning("web console: malformed envelope from the voice machine")
            return None
        if envelope.payload:
            self.events.append(envelope.payload)
        return envelope

    async def next_event(self, timeout: float) -> Optional[Dict[str, Any]]:
        from services.voice_fsm.wire import CodecError, decode_event

        while not self.events:
            if await self._next(timeout) is None:
                return None
        payload = self.events.pop(0)
        try:
            return event_json(decode_event(payload))
        except CodecError:
            return None

    async def close(self) -> None:
        await self.peer.close()


def _line(obj: Dict[str, Any]) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


async def voice_event_lines(request: Request) -> AsyncIterator[bytes]:
    """The stream behind ``/console/voice/events``; it ends with an ``unavailable`` line when the machine goes."""
    try:
        peer = open_peer()
    except VoiceUnavailable as exc:
        yield _line({"type": "unavailable", "reason": str(exc)})
        return
    session = _Session(peer)
    try:
        yield _line({"type": "hello", "backend": peer.backend, "session": session.id})
        await session.open()
        quiet = 0.0
        while not await request.is_disconnected():
            event = await session.next_event(1.0)
            if event is None:
                quiet += 1.0
                if quiet >= KEEPALIVE_SEC:
                    quiet = 0.0
                    yield _line({"type": "keepalive"})
                continue
            quiet = 0.0
            yield _line(event)
    except VoiceUnavailable as exc:
        yield _line({"type": "unavailable", "reason": str(exc)})
    finally:
        await session.close()


@router.get("/console/voice/events", dependencies=[Depends(console_gate)])
async def voice_events(request: Request) -> StreamingResponse:
    """Watch the voice machine: newline-delimited JSON, read scope (the app-wide check)."""
    return StreamingResponse(
        voice_event_lines(request),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class VoiceSettingsUpdate(BaseModel):
    verbosity: Optional[str] = None
    persona: Optional[str] = None
    language: Optional[str] = None


def settings_commands(update: VoiceSettingsUpdate) -> List[Any]:
    """The console commands for a settings form; a value that cannot be a setting is refused with 422."""
    from services.voice_fsm import SetLanguage, SetVerbosity, Source, SwitchPersona, Verbosity

    commands: List[Any] = []
    if update.verbosity is not None:
        try:
            commands.append(SetVerbosity(Verbosity(update.verbosity), Source.CONSOLE))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"unknown verbosity {update.verbosity!r}") from None
    for value, what, make in (
        (update.persona, "persona", lambda v: SwitchPersona(v, Source.CONSOLE)),
        (update.language, "language", lambda v: SetLanguage(v, Source.CONSOLE)),
    ):
        if value is None:
            continue
        if not _NAME.match(value):
            raise HTTPException(status_code=422, detail=f"unusable {what} {value!r}")
        commands.append(make(value))
    if not commands:
        raise HTTPException(status_code=422, detail="nothing to change")
    return commands


@router.post("/console/voice/settings", dependencies=[Depends(console_gate)])
async def put_voice_settings(update: VoiceSettingsUpdate) -> Dict[str, Any]:
    """Change verbosity, persona or language (write scope, the app-wide check for non-GET requests).

    The answer carries the settings the machine reports afterwards; a persona or language this Pi does not have
    is not an error here: the machine keeps what it has, and the answer shows it.
    """
    from services.voice_fsm.wire import Status

    commands = settings_commands(update)
    try:
        peer = open_peer()
    except VoiceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    session = _Session(peer)
    try:
        await session.open()
        for command in commands:
            status = await session.command(command)
            if status != Status.OK:
                raise HTTPException(status_code=409, detail=f"{type(command).__name__} refused ({Status(status).name})")
        # The change is broadcast right after the reply; the last settings seen are the ones in use.
        settings = None
        while (event := await session.next_event(0.3)) is not None:
            if event["type"] == "settings":
                settings = event
    except VoiceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    finally:
        await session.close()
    return {"status": "ok", "message": "voice settings sent", "settings": settings}
