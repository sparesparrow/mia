"""Channels and the envelope router (REQ-NET-009, REQ-NET-008).

Everything runs on 127.0.0.1, a socketpair, a unix socket in a temp dir or in memory. No hardware, no
sleeping to wait for a result: reads use timeouts and the machine runs on a fake clock.
"""

import socket
import struct
import tempfile
import threading
from pathlib import Path

import pytest
from services.voice_fsm import (
    ActionClass,
    Cancel,
    Confirm,
    Deny,
    EndDictation,
    ExecutionDone,
    Feedback,
    GoNow,
    IncomingMessage,
    Intent,
    Part,
    SafetyWarning,
    Settings,
    SetVerbosity,
    Source,
    Speak,
    SpeakingDone,
    State,
    StateChanged,
    Verbosity,
    VoiceMachine,
    Wake,
)
from services.voice_fsm.wire import (
    MAX_MESSAGE_BYTES,
    PEER_COMMANDS,
    ChannelClosed,
    Envelope,
    EnvelopeRouter,
    FramedChannel,
    LoopbackChannel,
    MessageTooLarge,
    Op,
    Service,
    SocketListener,
    Status,
    UdpChannel,
    VoiceService,
    connect_tcp,
    connect_unix,
    decode_envelope,
    decode_event,
    encode_command,
    encode_envelope,
)

pytestmark = pytest.mark.req("REQ-NET-009", "REQ-NET-008")


# ── Channels ──────────────────────────────────────────────────────────────


def test_loopback_delivers_in_order_and_polls_without_blocking():
    a, b = LoopbackChannel.pair()
    assert b.read(timeout=0) is None
    for i in range(3):
        a.write(bytes([i]))
    assert [b.read(timeout=0) for _ in range(3)] == [b"\x00", b"\x01", b"\x02"]
    assert b.read(timeout=0.01) is None


def test_loopback_close_reaches_the_peer_after_queued_messages():
    a, b = LoopbackChannel.pair()
    a.write(b"last words")
    a.close()
    assert not a.is_open and not b.is_open
    assert b.read(timeout=0) == b"last words"
    with pytest.raises(ChannelClosed):
        b.read(timeout=0)
    with pytest.raises(ChannelClosed):
        b.read(timeout=0)  # stays closed
    with pytest.raises(ChannelClosed):
        b.write(b"x")


def test_every_channel_refuses_oversized_messages():
    a, _ = LoopbackChannel.pair()
    with pytest.raises(MessageTooLarge):
        a.write(b"x" * (MAX_MESSAGE_BYTES + 1))
    x, y = socket.socketpair()
    with pytest.raises(MessageTooLarge):
        FramedChannel(x).write(b"x" * (MAX_MESSAGE_BYTES + 1))
    y.close()


def test_framed_channel_round_trips_over_a_stream_pair():
    x, y = socket.socketpair()
    a, b = FramedChannel(x), FramedChannel(y)
    a.write(b"hello")
    a.write(b"")
    a.write(b"x" * 10_000)
    assert b.read(timeout=1) == b"hello"
    assert b.read(timeout=1) == b""
    assert b.read(timeout=1) == b"x" * 10_000
    assert b.read(timeout=0.01) is None


def test_framed_channel_reassembles_a_message_that_arrives_in_pieces():
    x, y = socket.socketpair()
    reader = FramedChannel(y)
    frame = struct.pack(">I", 5) + b"abcde" + struct.pack(">I", 2) + b"zz"
    for i in range(len(frame) - 1):
        x.sendall(frame[i : i + 1])
        got = reader.read(timeout=0.001)
        assert got is None or i >= 8  # the first message completes with byte 9
    x.sendall(frame[-1:])
    messages = [
        m for m in (reader.read(timeout=0.2), reader.read(timeout=0.2)) if m is not None
    ]
    # whichever of the two frames was not yet returned is still buffered
    assert messages[-1] == b"zz"


def test_framed_channel_splits_two_messages_that_arrive_together():
    x, y = socket.socketpair()
    x.sendall(struct.pack(">I", 1) + b"a" + struct.pack(">I", 1) + b"b")
    reader = FramedChannel(y)
    assert [reader.read(timeout=1), reader.read(timeout=1)] == [b"a", b"b"]


def test_framed_channel_drops_a_stream_that_announces_an_absurd_frame():
    x, y = socket.socketpair()
    reader = FramedChannel(y)
    x.sendall(struct.pack(">I", MAX_MESSAGE_BYTES + 1))
    with pytest.raises(ChannelClosed):
        reader.read(timeout=1)
    assert not reader.is_open


def test_framed_channel_reports_the_peer_closing():
    x, y = socket.socketpair()
    reader = FramedChannel(y)
    x.close()
    with pytest.raises(ChannelClosed):
        reader.read(timeout=1)
    with pytest.raises(ChannelClosed):
        reader.write(b"x")


def test_tcp_listener_hands_out_a_channel_per_connection():
    listener = SocketListener.tcp("127.0.0.1", 0)
    try:
        assert listener.accept(timeout=0) is None
        client = connect_tcp("127.0.0.1", listener.address[1])
        server = listener.accept(timeout=2)
        client.write(b"ping")
        assert server.read(timeout=2) == b"ping"
        server.write(b"pong")
        assert client.read(timeout=2) == b"pong"
        other = connect_tcp("127.0.0.1", listener.address[1])
        assert listener.accept(timeout=2) is not server
        other.close()
        client.close()
        server.close()
    finally:
        listener.close()
    with pytest.raises(ChannelClosed):
        listener.accept(timeout=0)


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"), reason="no unix sockets on this platform"
)
def test_unix_socket_listener_round_trips():
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        path = str(Path(directory) / "voice.sock")
        listener = SocketListener.unix(path)
        try:
            client = connect_unix(path)
            server = listener.accept(timeout=2)
            client.write(b"over a unix socket")
            assert server.read(timeout=2) == b"over a unix socket"
            client.close()
            server.close()
        finally:
            listener.close()


def test_udp_channel_is_one_datagram_per_message_and_ignores_strangers():
    a, b = UdpChannel.pair()
    try:
        a.write(b"one")
        a.write(b"two")
        assert [b.read(timeout=1), b.read(timeout=1)] == [b"one", b"two"]
        assert b.read(timeout=0.01) is None

        stranger = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        stranger.sendto(b"spoof", b.address)
        stranger.close()
        a.write(b"real")
        assert b.read(timeout=1) == b"real"  # the spoofed datagram was dropped
        assert b.read(timeout=0.01) is None
    finally:
        a.close()
        b.close()
    with pytest.raises(ChannelClosed):
        a.write(b"x")


# ── Router ────────────────────────────────────────────────────────────────


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


class Peer:
    """A connection whose outgoing envelopes are collected for inspection."""

    def __init__(self, router, session="s1", service=Service.VOICE, open_session=True):
        self.session = session
        self.inbox = []
        self.connection = router.connect(self.inbox.append)
        if open_session:
            self.send(Op.OPEN, service=service, seq=1)
            self.take()

    def send(
        self,
        op=Op.DATA,
        payload=b"",
        service=Service.VOICE,
        seq=0,
        version=1,
        session=None,
    ):
        self.connection.handle(
            encode_envelope(
                Envelope(
                    service,
                    self.session if session is None else session,
                    op,
                    Status.OK,
                    seq,
                    payload,
                    version,
                )
            )
        )

    def command(self, command, seq=0):
        self.send(payload=encode_command(command), seq=seq)

    def take(self):
        out = [decode_envelope(m) for m in self.inbox]
        self.inbox.clear()
        return out

    def events(self):
        return [decode_event(e.payload) for e in self.take() if e.payload]


@pytest.fixture
def setup():
    clock = Clock()
    machine = VoiceMachine(clock)
    service = VoiceService(machine)
    router = EnvelopeRouter()
    router.register(Service.VOICE, service)
    return clock, machine, service, router


def test_open_data_and_close_are_answered_with_the_senders_sequence_number(setup):
    _, machine, _, router = setup
    peer = Peer(router, open_session=False)
    peer.send(Op.OPEN, seq=11)
    reply, snapshot = peer.take()
    assert (reply.status, reply.seq, reply.op, reply.session_id) == (
        Status.OK,
        11,
        Op.OPEN,
        "s1",
    )
    # After the reply, the opener alone gets the machine's settings (ADR-0019).
    assert (snapshot.op, snapshot.session_id) == (Op.DATA, "s1")
    assert decode_event(snapshot.payload) == Settings(Verbosity.NORMAL)

    peer.command(Wake(), seq=12)
    reply, *events = peer.take()
    assert (reply.status, reply.seq) == (Status.OK, 12)
    assert machine.state is State.LISTENING
    assert any(isinstance(decode_event(e.payload), StateChanged) for e in events)

    peer.send(Op.CLOSE, seq=13)
    assert peer.take()[0].status == Status.OK
    peer.command(Cancel())
    assert peer.take()[0].status == Status.UNKNOWN_SESSION


def test_a_wrong_version_an_unknown_service_and_garbage_are_answered_not_raised(setup):
    _, machine, _, router = setup
    peer = Peer(router)
    peer.send(version=2, payload=encode_command(Wake()))
    assert peer.take()[0].status == Status.UNSUPPORTED_VERSION
    peer.send(service=42, payload=encode_command(Wake()))
    assert peer.take()[0].status == Status.UNKNOWN_SERVICE
    peer.send(service=Service.UNKNOWN, payload=encode_command(Wake()))
    assert peer.take()[0].status == Status.UNKNOWN_SERVICE
    peer.connection.handle(b"\xff" * 40)
    assert peer.take()[0].status == Status.MALFORMED
    peer.send(payload=b"garbage payload")
    assert peer.take()[0].status == Status.MALFORMED
    assert machine.state is State.IDLE


def test_data_without_an_open_session_is_refused(setup):
    _, machine, _, router = setup
    peer = Peer(router, open_session=False)
    peer.command(Wake())
    assert peer.take()[0].status == Status.UNKNOWN_SESSION
    assert machine.state is State.IDLE


def test_a_session_id_belongs_to_the_connection_that_opened_it(setup):
    _, _, _, router = setup
    first = Peer(router, session="shared")
    second = Peer(router, session="shared", open_session=False)
    second.send(Op.OPEN)
    assert second.take()[0].status == Status.NOT_PERMITTED
    second.send(Op.OPEN, session="")
    assert second.take()[0].status == Status.NOT_PERMITTED
    first.send(Op.OPEN)  # opening it again from the owner is fine
    assert first.take()[0].status == Status.OK


def test_events_reach_every_open_session_and_nobody_else(setup):
    _, _, _, router = setup
    sender, watcher, closed, never_opened = (
        Peer(router, "a"),
        Peer(router, "b"),
        Peer(router, "c"),
        Peer(router, "d", open_session=False),
    )
    closed.send(Op.CLOSE)
    closed.take()
    sender.command(Wake())
    assert {type(e) for e in sender.events()} >= {StateChanged, Feedback}
    assert {type(e) for e in watcher.events()} >= {StateChanged, Feedback}
    assert closed.take() == [] and never_opened.take() == []


def test_events_carry_the_recipients_session_id_and_a_rising_sequence(setup):
    _, _, _, router = setup
    a, b = Peer(router, "a"), Peer(router, "b")
    a.command(Wake())
    a_events, b_events = a.take()[1:], b.take()
    assert {e.session_id for e in a_events} == {"a"} and {
        e.session_id for e in b_events
    } == {"b"}
    seqs = [e.seq for e in b_events]
    assert seqs == sorted(set(seqs))


def test_a_peer_cannot_send_what_only_the_pi_may_report(setup):
    _, machine, _, router = setup
    peer = Peer(router)
    forbidden = [
        SafetyWarning("warning.coolant_high"),
        SpeakingDone(),
        ExecutionDone("read.result"),
        IncomingMessage("Jana", "hi"),
        Intent((Part("lights.on", ActionClass.COMFORT),)),
    ]
    for command in forbidden:
        peer.command(command)
        (reply,) = peer.take()
        assert reply.status == Status.NOT_PERMITTED, type(command).__name__
    assert machine.state is State.IDLE


def test_the_channel_decides_the_source_not_the_peer(setup):
    _, machine, _, router = setup
    seen = []
    original = machine.handle
    machine.handle = lambda command: seen.append(command) or original(command)
    peer = Peer(router)
    for command in (
        Wake(Source.CAR),
        GoNow(Source.VOICE),
        Cancel(Source.RULE),
        SetVerbosity(Verbosity.QUIET, Source.CAR),
    ):
        peer.command(command)
    assert [c.source for c in seen] == [Source.CONSOLE] * 4
    assert seen[3].level is Verbosity.QUIET


def test_a_broken_peer_is_dropped_and_the_others_still_get_their_events(setup):
    _, _, _, router = setup
    healthy = Peer(router, "ok")

    def broken_sink(_):
        raise ConnectionResetError("peer went away")

    bad = router.connect(broken_sink)
    bad.handle(encode_envelope(Envelope(Service.VOICE, "bad", Op.OPEN, Status.OK, 1)))
    assert not bad.alive
    healthy.command(Wake())
    assert any(isinstance(e, StateChanged) for e in healthy.events())


def test_tick_broadcasts_what_the_clock_causes(setup):
    clock, machine, service, router = setup
    peer = Peer(router)
    router.broadcast(Service.VOICE, service.submit(Wake()))
    peer.take()
    clock.now += 60
    router.tick()
    assert machine.state is State.IDLE
    assert any(
        isinstance(e, StateChanged) and e.current is State.IDLE for e in peer.events()
    )


# ── Voice and button give the same machine effects (REQ-VOICE-015 groundwork) ──

CHAIN = (
    Part("read.voltage", ActionClass.READ, {}, True),
    Part("lights.on", ActionClass.COMFORT, {}, False),
)
MESSAGE = (Part("message.send", ActionClass.MESSAGE, {"to": "Jana"}, False),)

SETUPS = {
    "idle": [],
    "listening": [Wake()],
    "window": [Intent(CHAIN), SpeakingDone()],
    "confirming": [Intent(MESSAGE), SpeakingDone()],
    "dictating": [Intent((Part("note.dictate", ActionClass.NOTE),)), SpeakingDone()],
}
PRESSES = {
    "go_now": GoNow,
    "cancel": Cancel,
    "confirm": Confirm,
    "deny": Deny,
    "end_dictation": EndDictation,
    "wake": Wake,
}


def test_every_button_press_is_a_command_a_console_may_send():
    assert set(PRESSES.values()) <= set(PEER_COMMANDS)


def _run(setup_commands, press, wire_source=None):
    """Press once on a fresh machine; return its state and the effects the press caused.

    With ``wire_source`` the press travels as an envelope from a console peer instead.
    """
    machine = VoiceMachine(Clock())
    for command in setup_commands:
        machine.handle(command)
    if wire_source is None:
        effects = machine.handle(press)
        return machine.state, effects

    caused = []
    original = machine.handle
    machine.handle = lambda command: caused.append(original(command)) or caused[-1]
    router = EnvelopeRouter()
    router.register(Service.VOICE, VoiceService(machine, peer_source=wire_source))
    peer = Peer(router)
    peer.command(press)
    assert peer.take()[0].status == Status.OK
    assert len(caused) == 1
    return machine.state, caused[0]


@pytest.mark.parametrize("name", sorted(SETUPS))
@pytest.mark.parametrize("press", sorted(PRESSES))
def test_the_same_command_gives_the_same_effects_whatever_its_source(name, press):
    cls = PRESSES[press]
    by_source = [
        _run(SETUPS[name], cls(source))
        for source in (Source.VOICE, Source.BUTTON, Source.CONSOLE)
    ]
    over_the_wire = _run(SETUPS[name], cls(Source.VOICE), wire_source=Source.BUTTON)
    assert by_source[0] == by_source[1] == by_source[2] == over_the_wire


# ── End to end over real channels ─────────────────────────────────────────


def test_a_console_drives_the_machine_over_a_channel_and_sees_its_state():
    clock = Clock()
    machine = VoiceMachine(clock)
    service = VoiceService(machine)
    router = EnvelopeRouter()
    router.register(Service.VOICE, service)

    server_end, client = LoopbackChannel.pair()
    stop = threading.Event()
    thread = threading.Thread(target=router.serve, args=(server_end, stop), daemon=True)
    thread.start()

    def send(op, payload=b"", seq=0):
        client.write(
            encode_envelope(
                Envelope(Service.VOICE, "console", op, Status.OK, seq, payload)
            )
        )

    def read_until(predicate, limit=20):
        seen = []
        for _ in range(limit):
            data = client.read(timeout=2)
            assert data is not None, f"timed out; saw {seen}"
            envelope = decode_envelope(data)
            event = decode_event(envelope.payload) if envelope.payload else None
            seen.append(event or envelope.status)
            if predicate(envelope, event):
                return seen
        raise AssertionError(f"not seen in {limit} messages: {seen}")

    try:
        send(Op.OPEN, seq=1)
        read_until(lambda env, ev: env.seq == 1 and env.status == Status.OK)

        # The Pi's own services report in-process; "turn the lights on and say the voltage" is
        # one certain read and one uncertain comfort part.
        router.broadcast(Service.VOICE, service.submit(Intent(CHAIN)))
        spoken = read_until(lambda env, ev: isinstance(ev, Speak))
        assert Speak in {type(e) for e in spoken}
        router.broadcast(Service.VOICE, service.submit(SpeakingDone()))
        read_until(
            lambda env, ev: isinstance(ev, Feedback) and ev.led == "yellow_countdown"
        )
        assert machine.state is State.WINDOW

        send(Op.DATA, encode_command(GoNow(Source.CONSOLE)), seq=2)
        read_until(lambda env, ev: isinstance(ev, Feedback) and ev.state == "executing")
        assert machine.state is State.EXECUTING

        send(Op.CLOSE, seq=3)
        read_until(lambda env, ev: env.seq == 3)
    finally:
        stop.set()
        client.close()
        thread.join(timeout=2)
    assert not thread.is_alive()
