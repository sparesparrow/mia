"""Routes envelopes to services and events back to the sessions that asked for them (REQ-NET-008).

``EnvelopeRouter`` knows nothing about voice: it checks the version, finds the service by type and
keeps the session table. An unknown service, a wrong version or a garbled buffer is answered with a
status, never raised. ``VoiceService`` is the one service so far; it feeds peer commands to a
``VoiceMachine`` and turns the machine's effects into events.

Replies go to the sender only. Events go to every open session of the service that produced them. A service
may also have a snapshot for a session that has just opened (``on_open``): it goes to that session alone, right
after the Open reply, so a console starts from the machine's current settings (ADR-0019).
A peer can only send the commands in ``VoiceService.allowed``; the rest (``SpeakingDone``,
``ExecutionDone``, ``SafetyWarning``, ``IncomingMessage``, typed ``Intent``) enter the machine from
inside the Pi, never over a console connection.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
from typing import Callable, Dict, Iterable, List, Optional, Protocol, Tuple

from ..machine import VoiceMachine
from ..types import (
    Cancel,
    Command,
    Confirm,
    Deny,
    EndDictation,
    GoNow,
    Settings,
    SetVerbosity,
    Source,
    Wake,
)
from .channel import Channel, ChannelClosed
from .codec import (
    CodecError,
    decode_command,
    decode_envelope,
    encode_envelope,
    encode_event,
)
from .messages import WIRE_VERSION, Envelope, Op, Service, Status

logger = logging.getLogger(__name__)

Sink = Callable[[bytes], None]

# What a console may send: the two button roles, the answer buttons, wake, end of dictation and the
# verbosity setting. Not typed text or results that only the Pi's own services may report.
PEER_COMMANDS = frozenset(
    {Wake, GoNow, Cancel, Confirm, Deny, EndDictation, SetVerbosity}
)


class ServiceHandler(Protocol):
    def handle(self, payload: bytes) -> Tuple[Status, List[bytes]]:
        """Process one payload; return a status and event payloads to broadcast."""

    def tick(self) -> List[bytes]:
        """Advance time; return event payloads to broadcast."""

    # Optional: ``on_open(self) -> List[bytes]``, payloads for a session that has just opened.


class VoiceService:
    def __init__(
        self,
        machine: VoiceMachine,
        peer_source: Source = Source.CONSOLE,
        allowed: Iterable[type] = PEER_COMMANDS,
        on_settings: Optional[Callable[[Settings], None]] = None,
    ) -> None:
        self.machine = machine
        self.peer_source = peer_source
        self.allowed = frozenset(allowed)
        # Called for every settings change, before it is broadcast; the Pi persists it here.
        self.on_settings = on_settings

    def handle(self, payload: bytes) -> Tuple[Status, List[bytes]]:
        try:
            command = decode_command(payload)
        except CodecError as exc:
            logger.warning("voice: malformed command payload: %s", exc)
            return Status.MALFORMED, []
        if type(command) not in self.allowed:
            logger.warning(
                "voice: %s is not allowed from a peer", type(command).__name__
            )
            return Status.NOT_PERMITTED, []
        return Status.OK, self.submit(self._stamp(command))

    def submit(self, command: Command) -> List[bytes]:
        """Feed a command that is already trusted (in-process) and return the events to broadcast."""
        return self._events(self.machine.handle(command))

    def tick(self) -> List[bytes]:
        return self._events(self.machine.tick())

    def on_open(self) -> List[bytes]:
        """The settings in use now, for a session that has just opened."""
        return self._events([self.machine.settings()], persist=False)

    def _stamp(self, command: Command) -> Command:
        """The channel decides where a command came from, not the peer."""
        if any(f.name == "source" for f in dataclasses.fields(command)):
            return dataclasses.replace(command, source=self.peer_source)
        return command

    def _events(self, effects, persist: bool = True) -> List[bytes]:
        if persist and self.on_settings is not None:
            for effect in effects:
                if isinstance(effect, Settings):
                    self.on_settings(effect)
        return [
            payload
            for payload in (encode_event(e) for e in effects)
            if payload is not None
        ]


class Connection:
    """One peer: its sink for outgoing envelopes and the sessions it opened."""

    def __init__(self, router: "EnvelopeRouter", sink: Sink) -> None:
        self._router = router
        self.sink = sink
        self.sessions: Dict[str, int] = {}  # session id -> service
        self.alive = True

    def handle(self, data: bytes) -> None:
        """Process one received buffer. Replies and events go to the sinks; this never raises."""
        self._router._handle(self, data)

    def close(self) -> None:
        self._router._drop(self)


class EnvelopeRouter:
    def __init__(self) -> None:
        self._services: Dict[int, ServiceHandler] = {}
        self._connections: List[Connection] = []
        self._lock = threading.RLock()
        self._seq = 0

    def register(self, service: int, handler: ServiceHandler) -> None:
        self._services[int(service)] = handler

    def connect(self, sink: Sink) -> Connection:
        connection = Connection(self, sink)
        with self._lock:
            self._connections.append(connection)
        return connection

    def tick(self) -> None:
        """Advance every service's clock and broadcast what comes out."""
        with self._lock:
            for service, handler in self._services.items():
                self.broadcast(service, handler.tick())

    def broadcast(self, service: int, payloads: Iterable[bytes]) -> None:
        with self._lock:
            for payload in payloads:
                for connection in list(self._connections):
                    for session_id, session_service in list(
                        connection.sessions.items()
                    ):
                        if session_service == service:
                            self._seq = (self._seq + 1) & 0xFFFFFFFF
                            self._send(
                                connection,
                                Envelope(
                                    service=service,
                                    session_id=session_id,
                                    seq=self._seq,
                                    payload=payload,
                                ),
                            )

    def serve(
        self,
        channel: Channel,
        stop: Optional[threading.Event] = None,
        poll: float = 0.1,
    ) -> None:
        """Run one channel until it closes or ``stop`` is set (blocking; one thread per channel)."""
        connection = self.connect(channel.write)
        try:
            while not (stop and stop.is_set()):
                try:
                    data = channel.read(timeout=poll)
                except ChannelClosed:
                    break
                if data is None:
                    self.tick()
                    continue
                connection.handle(data)
                if not connection.alive:
                    break
        finally:
            connection.close()
            channel.close()

    # ── Internals ─────────────────────────────────────────────────────────

    def _send(self, connection: Connection, envelope: Envelope) -> None:
        if not connection.alive:
            return
        try:
            connection.sink(encode_envelope(envelope))
        except Exception as exc:  # a dead peer must not stop delivery to the others
            logger.warning("voice: dropping connection after send failure: %s", exc)
            self._drop(connection)

    def _drop(self, connection: Connection) -> None:
        with self._lock:
            connection.alive = False
            connection.sessions.clear()
            if connection in self._connections:
                self._connections.remove(connection)

    def _reply(self, connection: Connection, request: Envelope, status: Status) -> None:
        self._send(
            connection,
            Envelope(
                service=request.service,
                session_id=request.session_id,
                op=request.op,
                status=status,
                seq=request.seq,
            ),
        )

    def _handle(self, connection: Connection, data: bytes) -> None:
        with self._lock:
            try:
                request = decode_envelope(data)
            except CodecError as exc:
                logger.warning("voice: malformed envelope: %s", exc)
                self._send(
                    connection,
                    Envelope(service=Service.UNKNOWN, status=Status.MALFORMED),
                )
                return
            if request.version != WIRE_VERSION:
                self._reply(connection, request, Status.UNSUPPORTED_VERSION)
                return
            handler = self._services.get(request.service)
            if handler is None:
                self._reply(connection, request, Status.UNKNOWN_SERVICE)
                return

            if request.op == Op.OPEN:
                owner = self._owner(request.session_id)
                if not request.session_id or (
                    owner is not None and owner is not connection
                ):
                    self._reply(connection, request, Status.NOT_PERMITTED)
                else:
                    connection.sessions[request.session_id] = request.service
                    self._reply(connection, request, Status.OK)
                    self._send_snapshot(connection, request, handler)
                return
            if connection.sessions.get(request.session_id) != request.service:
                self._reply(connection, request, Status.UNKNOWN_SESSION)
                return
            if request.op == Op.CLOSE:
                del connection.sessions[request.session_id]
                self._reply(connection, request, Status.OK)
                return
            if request.op != Op.DATA:
                self._reply(connection, request, Status.MALFORMED)
                return

            status, events = handler.handle(request.payload)
            self._reply(connection, request, status)
            self.broadcast(request.service, events)

    def _send_snapshot(
        self, connection: Connection, request: Envelope, handler: ServiceHandler
    ) -> None:
        on_open = getattr(handler, "on_open", None)
        if on_open is None:
            return
        for payload in on_open():
            self._seq = (self._seq + 1) & 0xFFFFFFFF
            self._send(
                connection,
                Envelope(
                    service=request.service,
                    session_id=request.session_id,
                    seq=self._seq,
                    payload=payload,
                ),
            )

    def _owner(self, session_id: str) -> Optional[Connection]:
        for connection in self._connections:
            if session_id in connection.sessions:
                return connection
        return None
