"""The router hosts the console's machine: bridge service, ZeroMQ hub and the API's relay (ADR-0020, REQ-VOICE-024).

No hardware. The hub and the relay use real loopback ZeroMQ sockets created in the tests. The relay tests drive the
API with a TestClient while a thread plays the router's loop, so they cover the same classes ``main_fsm`` wires up.
"""

import threading
import time

import pytest
from api import main as api_main
from api import voice_console, voice_relay
from fastapi.testclient import TestClient
from services import voice_command_router as router
from services.voice_fsm import (
    Cancel,
    Feedback,
    GoNow,
    Intent,
    Settings,
    SetVerbosity,
    Source,
    Speak,
    State,
    StateChanged,
    Verbosity,
    VoiceMachine,
    Wake,
)
from services.voice_fsm.bridge import RouterBridge, parts_from_route
from services.voice_fsm.events import FINISHED, encode_listen
from services.voice_fsm.wire import (
    PEER_COMMANDS,
    Envelope,
    EnvelopeRouter,
    Op,
    Service,
    Status,
    Transcript,
    decode_envelope,
    decode_event,
    encode_command,
    encode_envelope,
    zmq_hub,
)
from services.voice_fsm.wire.bridge_service import BridgeVoiceService
from starlette.websockets import WebSocketDisconnect

pytestmark = pytest.mark.req("REQ-VOICE-024")


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class Host:
    """A bridge, its machine and the service a console would talk to, all on fakes and a fake clock."""

    def __init__(self, clock=None, **machine_args):
        self.clock = clock or Clock()
        self.executed = []
        self.spoken = []
        self.feedback = []
        self.listens = 0
        self.machine = VoiceMachine(self.clock, **machine_args)
        self.bridge = RouterBridge(
            self.machine,
            classify=lambda text: parts_from_route(
                router.route_command(text), router.CONFIRM_THRESHOLD
            ),
            execute=self._execute,
            publish_text=lambda text, uid: self.spoken.append((text, uid)),
            publish_feedback=self.feedback.append,
            on_listen=self._listened,
        )
        self.service = BridgeVoiceService(self.bridge)
        self.seen = []
        self.bridge.observers.append(self.seen.extend)

    def _execute(self, part):
        self.executed.append(part.name)
        return "Done."

    def _listened(self):
        self.listens += 1

    def payloads(self):
        return [decode_event(p) for p in self.service.drain()]


# ── Bridge: submit and observers ──────────────────────────────────────────


def test_observers_hear_a_transcript_and_the_effects_it_caused():
    host = Host()
    host.bridge.on_wake()
    host.seen.clear()
    host.bridge.on_transcript("turn the lights on")
    assert host.seen[0] == Transcript("turn the lights on")
    assert any(isinstance(e, Speak) for e in host.seen)
    assert host.executed == ["turn lights on"]


def test_observers_hear_what_a_tick_and_a_tts_event_produce():
    host = Host()
    host.bridge.on_wake()
    host.seen.clear()
    host.clock.now += host.machine.listen_timeout_sec + 1
    host.bridge.poll()
    assert any(
        isinstance(e, StateChanged) and e.current is State.IDLE for e in host.seen
    )

    host.bridge.on_wake()
    host.bridge.on_transcript("what is the system status")
    uid = next(e.id for e in host.seen if isinstance(e, Speak))
    host.seen.clear()
    host.bridge.on_speaking(FINISHED, uid)
    assert any(isinstance(e, StateChanged) for e in host.seen)


def test_a_failing_observer_does_not_stop_the_voice_loop():
    host = Host()

    def broken(items):
        raise RuntimeError("boom")

    host.bridge.observers.insert(0, broken)
    host.bridge.on_wake()
    assert host.machine.state is State.LISTENING
    assert host.seen  # the next observer was still told


def test_submit_applies_the_command_once_and_returns_its_effects():
    host = Host()
    effects = host.bridge.submit(Wake(Source.CONSOLE))
    assert host.machine.state is State.LISTENING
    assert any(isinstance(e, StateChanged) for e in effects)
    assert host.feedback  # the bridge's own side effect ran
    assert len([e for e in host.seen if isinstance(e, StateChanged)]) == 1


def test_a_listen_request_follows_a_wake_that_was_not_spoken():
    host = Host()
    host.bridge.submit(Wake(Source.CONSOLE))
    assert host.listens == 1
    host.bridge.submit(Wake(Source.BUTTON))  # already listening: no new request
    assert host.listens == 1
    host.bridge.submit(Cancel(Source.CONSOLE))
    host.bridge.on_wake()  # a spoken wake word starts the recogniser by itself
    assert host.listens == 1


def test_the_listen_topic_is_a_json_event_on_its_own_topic():
    topic, body = encode_listen("console", now=lambda: 1.5)
    assert topic == b"mia/voice/listen"
    assert b'"source": "console"' in body


# ── BridgeVoiceService ────────────────────────────────────────────────────


def test_the_peer_commands_are_unchanged():
    assert {c.__name__ for c in PEER_COMMANDS} == {
        "Wake",
        "GoNow",
        "Cancel",
        "Confirm",
        "Deny",
        "EndDictation",
        "SetVerbosity",
        "SwitchPersona",
        "SetLanguage",
    }


def test_a_console_command_is_applied_once_and_comes_back_as_events():
    host = Host()
    status, events = host.service.handle(encode_command(Wake()))
    assert status == Status.OK
    decoded = [decode_event(p) for p in events]
    assert [type(e) for e in decoded].count(StateChanged) == 1
    assert host.machine.state is State.LISTENING
    assert host.service.drain() == []  # nothing is left to be sent twice


def test_a_go_now_from_a_console_executes_the_pending_part_once():
    host = Host()
    host.bridge.on_wake()
    host.bridge.on_transcript(
        "lights"
    )  # one of two concepts: uncertain, so the window opens
    assert host.machine.state in (State.SPEAKING, State.WINDOW)
    for _, uid in list(host.spoken):
        host.bridge.on_speaking(FINISHED, uid)
    assert host.machine.state is State.WINDOW
    host.service.drain()
    host.service.handle(encode_command(GoNow()))
    assert host.executed == [
        "turn lights off"
    ]  # once, not once per layer that saw the command


def test_the_service_does_not_tick_the_machine():
    host = Host()
    host.service.handle(encode_command(Wake()))
    host.clock.now += host.machine.listen_timeout_sec + 1
    assert host.service.tick() == []  # only the bridge's poll moves time
    assert host.machine.state is State.LISTENING
    host.bridge.poll()
    assert [type(decode_event(p)) for p in host.service.tick()].count(StateChanged) == 1


def test_events_of_every_origin_reach_the_service_with_the_words():
    host = Host()
    host.bridge.on_wake()
    host.bridge.on_transcript("what is the system status")
    events = host.payloads()
    assert any(isinstance(e, Transcript) for e in events)
    spoken = [e for e in events if isinstance(e, Speak)]
    assert spoken and all(e.text for e in spoken)


def test_what_only_the_pi_may_report_is_refused_and_the_machine_untouched():
    host = Host()
    status, events = host.service.handle(encode_command(Intent((), Source.CONSOLE)))
    assert status == Status.NOT_PERMITTED and events == []
    assert host.machine.state is State.IDLE and not host.seen


def test_the_channel_stamps_the_source_whatever_the_peer_claims():
    host = Host()
    seen = []
    original = host.bridge.submit
    host.bridge.submit = lambda command: (seen.append(command), original(command))[1]
    host.service.handle(encode_command(Wake(Source.CAR)))
    assert seen[0].source is Source.CONSOLE


# ── ZmqHub over real loopback sockets ─────────────────────────────────────


@pytest.fixture
def zmq_env(real_zmq, monkeypatch):
    zmq, zmq_asyncio = real_zmq
    monkeypatch.setattr(zmq_hub, "zmq", zmq)
    monkeypatch.setattr(voice_relay, "zmq", zmq)
    monkeypatch.setattr(voice_relay, "zmq_asyncio", zmq_asyncio)
    ctx = zmq.Context()
    opened = []

    def dealer(port):
        sock = ctx.socket(zmq.DEALER)
        sock.setsockopt(zmq.LINGER, 0)
        sock.connect(f"tcp://127.0.0.1:{port}")
        opened.append(sock)
        return sock

    yield zmq, ctx, dealer
    for sock in opened:
        sock.close(0)
    ctx.term()


def _hub(zmq_env, host, **kwargs):
    zmq, ctx, _ = zmq_env
    envelope_router = EnvelopeRouter()
    envelope_router.register(Service.VOICE, host.service)
    hub = zmq_hub.ZmqHub(envelope_router, ctx, port=0, **kwargs)
    return hub, envelope_router


def _open(session="s"):
    return encode_envelope(Envelope(Service.VOICE, session, Op.OPEN, Status.OK, 1))


def _data(payload, session="s", seq=2):
    return encode_envelope(
        Envelope(Service.VOICE, session, Op.DATA, Status.OK, seq, payload)
    )


def _pump(zmq, hub, clients, want, timeout=3.0):
    """Run the hub like the router loop and collect envelopes per client until ``want(frames)`` holds."""
    frames = {id(c): [] for c in clients}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        hub.service()
        hub.flush()
        for client in clients:
            while client.poll(1):
                frames[id(client)].append(client.recv())
        if want(frames):
            break
    return [frames[id(c)] for c in clients]


def test_the_hub_gives_each_identity_a_connection_and_answers_ping(zmq_env):
    zmq, _, dealer = zmq_env
    host = Host()
    hub, envelope_router = _hub(zmq_env, host)
    try:
        a, b = dealer(hub.port), dealer(hub.port)
        a.send(_open("a"))
        b.send(_open("b"))
        a.send(zmq_hub.PING)
        got_a, got_b = _pump(
            zmq, hub, [a, b], lambda f: len(f[id(a)]) >= 3 and len(f[id(b)]) >= 2
        )
        assert hub.peers == 2
        assert zmq_hub.PONG in got_a
        envelopes = [decode_envelope(f) for f in got_a if f != zmq_hub.PONG]
        assert envelopes[0].status == Status.OK
        assert isinstance(decode_event(envelopes[1].payload), Settings)
        assert len(envelope_router._connections) == 2
    finally:
        hub.close()


def test_the_open_snapshot_comes_from_the_routers_machine(zmq_env):
    zmq, _, dealer = zmq_env
    host = Host(verbosity=Verbosity.QUIET)
    hub, _ = _hub(zmq_env, host)
    try:
        a = dealer(hub.port)
        a.send(_open())
        (frames,) = _pump(zmq, hub, [a], lambda f: len(f[id(a)]) >= 2)
        snapshot = decode_event(decode_envelope(frames[1]).payload)
        assert isinstance(snapshot, Settings) and snapshot.verbosity is Verbosity.QUIET
    finally:
        hub.close()


def test_an_empty_frame_disconnects_only_that_peer(zmq_env):
    zmq, _, dealer = zmq_env
    host = Host()
    hub, envelope_router = _hub(zmq_env, host)
    try:
        a, b = dealer(hub.port), dealer(hub.port)
        a.send(_open("a"))
        b.send(_open("b"))
        _pump(zmq, hub, [a, b], lambda f: len(f[id(a)]) >= 2 and len(f[id(b)]) >= 2)
        a.send(b"")
        _pump(zmq, hub, [a, b], lambda f: hub.peers == 1)
        assert hub.peers == 1 and len(envelope_router._connections) == 1
        host.bridge.on_wake()  # an event from the pipeline still reaches the one left
        _, got_b = _pump(zmq, hub, [a, b], lambda f: len(f[id(b)]) >= 1)
        assert got_b and not _pump(zmq, hub, [a], lambda f: False, timeout=0.2)[0]
    finally:
        hub.close()


def test_a_console_command_is_seen_by_every_console_and_applied_once(zmq_env):
    zmq, _, dealer = zmq_env
    host = Host()
    hub, _ = _hub(zmq_env, host)
    try:
        a, b = dealer(hub.port), dealer(hub.port)
        a.send(_open("a"))
        b.send(_open("b"))
        _pump(zmq, hub, [a, b], lambda f: len(f[id(a)]) >= 2 and len(f[id(b)]) >= 2)
        a.send(_data(encode_command(SetVerbosity(Verbosity.CHATTY)), "a"))
        got_a, got_b = _pump(
            zmq, hub, [a, b], lambda f: len(f[id(a)]) >= 2 and len(f[id(b)]) >= 1
        )
        assert host.machine.verbosity is Verbosity.CHATTY
        for frames in (got_a, got_b):
            settings = [
                e
                for e in (
                    decode_event(decode_envelope(f).payload)
                    for f in frames
                    if decode_envelope(f).payload
                )
                if isinstance(e, Settings)
            ]
            assert [s.verbosity for s in settings] == [Verbosity.CHATTY]
    finally:
        hub.close()


def test_speech_and_tts_events_reach_a_console_that_sent_nothing(zmq_env):
    zmq, _, dealer = zmq_env
    host = Host()
    hub, _ = _hub(zmq_env, host)
    try:
        a = dealer(hub.port)
        a.send(_open())
        _pump(zmq, hub, [a], lambda f: len(f[id(a)]) >= 2)
        host.bridge.on_wake()
        host.bridge.on_transcript("what is the system status")
        (frames,) = _pump(
            zmq,
            hub,
            [a],
            lambda f: any(
                isinstance(decode_event(decode_envelope(x).payload), Transcript)
                for x in f[id(a)]
            ),
        )
        kinds = {type(decode_event(decode_envelope(x).payload)) for x in frames}
        assert Transcript in kinds and Feedback in kinds
    finally:
        hub.close()


def test_a_peer_that_goes_silent_is_dropped(zmq_env):
    zmq, _, dealer = zmq_env
    clock = Clock()
    host = Host()
    hub, envelope_router = _hub(zmq_env, host, idle_sec=10.0, clock=clock)
    try:
        a = dealer(hub.port)
        a.send(_open())
        _pump(zmq, hub, [a], lambda f: len(f[id(a)]) >= 2)
        assert hub.peers == 1
        clock.now += 11
        hub.reap()
        assert hub.peers == 0 and not envelope_router._connections
    finally:
        hub.close()


def test_a_port_that_cannot_be_bound_does_not_leave_a_socket_open(zmq_env):
    zmq, ctx, _ = zmq_env
    host = Host()
    hub, envelope_router = _hub(zmq_env, host)
    try:
        with pytest.raises(zmq.ZMQError):
            zmq_hub.ZmqHub(envelope_router, ctx, port=hub.port)
    finally:
        hub.close()


# ── Relay: the API against a router thread ────────────────────────────────


class RouterThread(threading.Thread):
    """The router's loop without the services around it: hub, bridge poll, flush."""

    def __init__(self, zmq, ctx, host):
        super().__init__(daemon=True)
        self.zmq = zmq
        self.host = host
        envelope_router = EnvelopeRouter()
        envelope_router.register(Service.VOICE, host.service)
        self.hub = zmq_hub.ZmqHub(envelope_router, ctx, port=0)
        self.stop = threading.Event()

    def run(self):
        poller = self.zmq.Poller()
        poller.register(self.hub.socket, self.zmq.POLLIN)
        while not self.stop.is_set():
            ready = dict(poller.poll(20))
            if self.hub.socket in ready:
                self.hub.service()
            self.host.bridge.poll()
            self.hub.reap()
            self.hub.flush()
        self.hub.close()


@pytest.fixture(scope="module")
def app_client():
    with TestClient(api_main.app) as client:
        yield client


@pytest.fixture
def relay_client(app_client, zmq_env, monkeypatch, tmp_path):
    zmq, ctx, _ = zmq_env
    host = Host(clock=time.monotonic)
    thread = RouterThread(zmq, ctx, host)
    thread.start()
    monkeypatch.setenv("VOICE_CONSOLE", "1")
    monkeypatch.setenv("VOICE_CONSOLE_BACKEND", "router")
    monkeypatch.setenv("VOICE_CONSOLE_ENDPOINT", f"tcp://127.0.0.1:{thread.hub.port}")
    monkeypatch.setenv("MIA_STATE_DIR", str(tmp_path))
    yield app_client, thread, host
    thread.stop.set()
    thread.join(5)


def _send(ws, op, payload=b"", seq=0, session="console"):
    ws.send_bytes(
        encode_envelope(Envelope(Service.VOICE, session, op, Status.OK, seq, payload))
    )


def _next(ws):
    return decode_envelope(ws.receive_bytes())


def _open_ws(ws, seq=1, session="console"):
    _send(ws, Op.OPEN, seq=seq, session=session)
    reply = _next(ws)
    assert (reply.seq, reply.status) == (seq, Status.OK)
    snapshot = decode_event(_next(ws).payload)
    assert isinstance(snapshot, Settings)
    return snapshot


def test_the_default_backend_stays_the_simulation(monkeypatch):
    monkeypatch.delenv("VOICE_CONSOLE_BACKEND", raising=False)
    assert voice_console.console_backend() == "sim"
    monkeypatch.setenv("VOICE_CONSOLE_BACKEND", "nonsense")
    assert voice_console.console_backend() == "sim"
    monkeypatch.setenv("VOICE_CONSOLE_BACKEND", "router")
    assert voice_console.console_backend() == "router"


def test_a_console_drives_the_routers_machine_through_the_relay(relay_client):
    client, thread, host = relay_client
    with client.websocket_connect("/ws/voice") as first, client.websocket_connect(
        "/ws/voice"
    ) as second:
        _open_ws(first, session="one")
        _open_ws(second, session="two")
        _send(first, Op.DATA, encode_command(Wake()), seq=2, session="one")
        assert _next(first).status == Status.OK  # the reply goes to the sender only
        seen = decode_event(_next(first).payload)
        assert isinstance(seen, Feedback)
        assert isinstance(
            decode_event(_next(second).payload), Feedback
        )  # every console sees it
        assert (
            host.machine.state is State.LISTENING
        )  # the router's machine, not a simulation
        assert thread.hub.peers == 2


def test_the_router_hears_the_console_leave(relay_client):
    client, thread, _ = relay_client
    with client.websocket_connect("/ws/voice") as ws:
        _open_ws(ws)
        assert thread.hub.peers == 1
    deadline = time.monotonic() + 3
    while thread.hub.peers and time.monotonic() < deadline:
        time.sleep(0.02)
    assert thread.hub.peers == 0  # the empty frame, not the idle timeout (10 s)


def test_speech_in_the_router_reaches_a_console_through_the_relay(relay_client):
    client, _, host = relay_client
    with client.websocket_connect("/ws/voice") as ws:
        _open_ws(ws)
        host.bridge.on_wake()
        host.bridge.on_transcript("what is the system status")
        kinds = set()
        for _ in range(12):
            kinds.add(type(decode_event(_next(ws).payload)))
            if Transcript in kinds:
                break
        assert Transcript in kinds


def test_a_text_frame_is_refused_with_1003(relay_client):
    client, _, _ = relay_client
    with client.websocket_connect("/ws/voice") as ws:
        ws.send_text("hello")
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_bytes()
        assert closed.value.code == 1003


def test_a_dead_router_closes_the_console_with_1013(app_client, zmq_env, monkeypatch):
    zmq, ctx, _ = zmq_env
    # Nothing listens on this port. The fake clock jumps a second at every look, so six seconds of silence
    # pass in a few polls.
    probe = ctx.socket(zmq.ROUTER)
    port = probe.bind_to_random_port("tcp://127.0.0.1")
    probe.close(0)

    class JumpingClock:
        now = 0.0

        def __call__(self):
            self.now += 1.0
            return self.now

    monkeypatch.setenv("VOICE_CONSOLE", "1")
    monkeypatch.setenv("VOICE_CONSOLE_BACKEND", "router")
    monkeypatch.setenv("VOICE_CONSOLE_ENDPOINT", f"tcp://127.0.0.1:{port}")
    monkeypatch.setattr(voice_relay, "_clock", JumpingClock())
    monkeypatch.setattr(voice_relay, "WATCH_SEC", 0.01)
    with app_client.websocket_connect("/ws/voice") as ws:
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_bytes()
        assert closed.value.code == 1013
