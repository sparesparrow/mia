"""The /ws/voice endpoint carries envelopes to a simulated voice machine (REQ-NET-008).

It is off unless VOICE_CONSOLE=1. These tests use FastAPI's TestClient, so no server or hardware.
"""

import pytest
from api import main as api_main
from api import voice_console
from fastapi.testclient import TestClient
from services.voice_fsm import (
    Cancel,
    Feedback,
    SafetyWarning,
    SetVerbosity,
    Source,
    State,
    StateChanged,
    Verbosity,
    Wake,
)
from services.voice_fsm.wire import (
    Envelope,
    Op,
    Service,
    Status,
    decode_envelope,
    decode_event,
    encode_command,
    encode_envelope,
)
from starlette.websockets import WebSocketDisconnect

pytestmark = pytest.mark.req("REQ-NET-008", "REQ-NET-009")


@pytest.fixture(scope="module")
def app_client():
    # One client for the module: starting the app (its lifespan) takes seconds.
    with TestClient(api_main.app) as client:
        yield client


@pytest.fixture
def client(app_client, monkeypatch):
    monkeypatch.setenv("VOICE_CONSOLE", "1")
    monkeypatch.setattr(voice_console, "_router", None)
    return app_client


def _send(ws, op, payload=b"", seq=0, session="console", **fields):
    ws.send_bytes(
        encode_envelope(
            Envelope(Service.VOICE, session, op, Status.OK, seq, payload, **fields)
        )
    )


def _next(ws):
    return decode_envelope(ws.receive_bytes())


def test_the_console_is_off_unless_enabled(app_client, monkeypatch):
    monkeypatch.delenv("VOICE_CONSOLE", raising=False)
    with pytest.raises(WebSocketDisconnect):
        with app_client.websocket_connect("/ws/voice"):
            pass


def test_a_wake_press_changes_the_machine_and_comes_back_as_events(client):
    with client.websocket_connect("/ws/voice") as ws:
        _send(ws, Op.OPEN, seq=1)
        assert _next(ws).seq == 1

        _send(ws, Op.DATA, encode_command(Wake(Source.CONSOLE)), seq=2)
        reply = _next(ws)
        assert (reply.seq, reply.status) == (2, Status.OK)

        events = []
        while not any(
            isinstance(e, Feedback) and e.state == "listening" for e in events
        ):
            events.append(decode_event(_next(ws).payload))
        assert StateChanged(State.IDLE, State.LISTENING) in events

        _send(ws, Op.DATA, encode_command(Cancel(Source.CONSOLE)), seq=3)
        assert _next(ws).seq == 3


def test_a_text_frame_is_refused_and_the_connection_closed(client):
    with client.websocket_connect("/ws/voice") as ws:
        ws.send_text("hello")
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_bytes()
        assert closed.value.code == 1003


def test_commands_only_the_pi_may_report_are_refused_over_the_socket(client):
    with client.websocket_connect("/ws/voice") as ws:
        _send(ws, Op.OPEN, seq=1)
        _next(ws)
        _send(ws, Op.DATA, encode_command(SafetyWarning("warn.coolant")), seq=2)
        assert _next(ws).status == Status.NOT_PERMITTED
        _send(ws, Op.DATA, encode_command(SetVerbosity(Verbosity.QUIET)), seq=3)
        assert _next(ws).status == Status.OK


def test_a_second_console_sees_the_first_ones_button_presses(client):
    with client.websocket_connect("/ws/voice") as first, client.websocket_connect(
        "/ws/voice"
    ) as second:
        _send(first, Op.OPEN, seq=1, session="a")
        _next(first)
        _send(second, Op.OPEN, seq=1, session="b")
        _next(second)
        _send(first, Op.DATA, encode_command(Wake()), seq=2, session="a")
        assert _next(first).seq == 2
        seen = decode_event(_next(second).payload)
        assert isinstance(seen, Feedback)  # the machine's first effect is the wake cue


def test_a_console_that_stops_reading_is_dropped_instead_of_buffered_without_limit():
    import asyncio

    async def scenario():
        outbox = asyncio.Queue(maxsize=voice_console.OUTBOX_LIMIT)
        overflowed = asyncio.Event()
        sink = voice_console.make_sink(outbox, overflowed)
        for i in range(voice_console.OUTBOX_LIMIT):
            sink(bytes([i % 256]))
        assert not overflowed.is_set()
        with pytest.raises(voice_console.OutboxFull):
            sink(b"one too many")
        assert overflowed.is_set() and outbox.qsize() == voice_console.OUTBOX_LIMIT

    asyncio.run(scenario())


def test_the_router_drops_a_console_whose_sink_overflows_and_keeps_the_others():
    import asyncio

    from services.voice_fsm import VoiceMachine
    from services.voice_fsm.wire import EnvelopeRouter, VoiceService

    async def scenario():
        router = EnvelopeRouter()
        service = VoiceService(VoiceMachine(lambda: 0.0))
        router.register(Service.VOICE, service)
        slow_box, slow_flag = asyncio.Queue(maxsize=2), asyncio.Event()
        ok_box = asyncio.Queue()
        slow = router.connect(voice_console.make_sink(slow_box, slow_flag))
        fine = router.connect(ok_box.put_nowait)
        for connection, name in ((slow, "slow"), (fine, "fine")):
            connection.handle(
                encode_envelope(Envelope(Service.VOICE, name, Op.OPEN, Status.OK, 1))
            )
        fine.handle(
            encode_envelope(
                Envelope(
                    Service.VOICE, "fine", Op.DATA, Status.OK, 2, encode_command(Wake())
                )
            )
        )
        assert not slow.alive and slow_flag.is_set()
        assert fine.alive and ok_box.qsize() > 2

    asyncio.run(scenario())
