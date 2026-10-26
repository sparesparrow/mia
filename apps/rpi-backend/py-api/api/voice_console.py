"""WebSocket console for the voice state machine (ADR-0013, REQ-NET-008).

Binary frames are envelopes (``schemas/voice.fbs``). A console may send the button commands and
the verbosity setting and receives the machine's state, feedback cues and spoken phrases.

Off unless ``VOICE_CONSOLE=1``. The machine behind it lives in this process on the system clock, so
the console talks to a simulation, not to the voice pipeline that runs in ``voice_command_router``;
attaching the two is a separate step. With no speaker attached, ``SimulatedSpeech`` reports each utterance
finished after ``SPEAK_SEC``, so the machine leaves ``speaking`` as it would on the Pi.

A console that opens a session first receives the machine's settings (ADR-0019): verbosity, persona and
language, with the personas and languages this Pi has. A change is kept in the settings store in
``MIA_STATE_DIR``, the same file the voice router reads when it starts. Every spoken phrase reaches the console
with its words, in the persona and language in use (ADR-0015).

Like every WebSocket of this API it needs the ``X-API-Key`` header when keys are configured (REQ-SEC-001).
That check only needs a read key, so a read-only key can press the buttons; a stricter scope is a follow-up.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Callable, List, Optional, Tuple

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

TICK_SEC = 0.1
_CLOSE_POLICY = 1008
_CLOSE_UNSUPPORTED = 1003
_CLOSE_TRY_AGAIN = 1013
OUTBOX_LIMIT = 256
SPEAK_SEC = 1.5

_router: Optional[Any] = None


def console_enabled() -> bool:
    return os.environ.get("VOICE_CONSOLE", "0") == "1"


def get_router() -> Any:
    """The shared router with its simulated voice service, built on first use."""
    global _router
    if _router is None:
        from services.voice_fsm import VoiceMachine
        from services.voice_fsm.personas import Phrasebook
        from services.voice_fsm.settings_store import SettingsStore
        from services.voice_fsm.wire import EnvelopeRouter, Service, VoiceService

        store = SettingsStore.from_env()
        stored = store.load()
        book = Phrasebook.load()
        machine = VoiceMachine(
            time.monotonic,
            verbosity=stored.verbosity,
            persona=stored.persona,
            personas=book.names,
            language=stored.language,
            languages=book.languages,
        )
        service = VoiceService(machine, on_settings=store.save, render=book.render)
        router = EnvelopeRouter()
        router.register(Service.VOICE, SimulatedSpeech(service, time.monotonic))
        _router = router
    return _router


class SimulatedSpeech:
    """The console's stand-in for TTS: every utterance ends ``speak_sec`` after the previous one, one after the
    other as a speaker plays them, and the machine hears ``SpeakingDone`` for it. A stopped utterance's late
    ``SpeakingDone`` is ignored by the machine, as a real one would be."""

    def __init__(
        self, service: Any, clock: Callable[[], float], speak_sec: float = SPEAK_SEC
    ) -> None:
        self.service = service
        self._clock = clock
        self._speak_sec = speak_sec
        self._ends: List[Tuple[float, int]] = []

    def handle(self, payload: bytes):
        status, events = self.service.handle(payload)
        self._note(events)
        return status, events

    def on_open(self) -> List[bytes]:
        return self.service.on_open()

    def tick(self) -> List[bytes]:
        from services.voice_fsm import SpeakingDone

        events = self.service.tick()
        self._note(events)
        now = self._clock()
        while self._ends and self._ends[0][0] <= now:
            _, utterance = self._ends.pop(0)
            done = self.service.submit(SpeakingDone(utterance))
            self._note(done)
            events = events + done
        return events

    def _note(self, events: List[bytes]) -> None:
        from services.voice_fsm import Speak
        from services.voice_fsm.wire import CodecError, decode_event

        for payload in events:
            try:
                event = decode_event(payload)
            except CodecError:
                continue
            if isinstance(event, Speak):
                start = max(self._clock(), self._ends[-1][0] if self._ends else 0.0)
                self._ends.append((start + self._speak_sec, event.id))


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
