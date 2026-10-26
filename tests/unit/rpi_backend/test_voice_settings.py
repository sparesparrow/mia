"""Verbosity read back, remembered across restarts and set by voice (REQ-VOICE-017, ADR-0019).

Fakes and a fake clock: no ZeroMQ, no audio, no sleeping. The store writes into pytest's temporary directory.
"""

import json
import os

import pytest
from api import voice_console
from services.voice_fsm import (
    Feedback,
    Settings,
    SetVerbosity,
    Source,
    Speak,
    SpeakingDone,
    State,
    Verbosity,
    VoiceMachine,
    Wake,
)
from services.voice_fsm.bridge import RouterBridge
from services.voice_fsm.events import FEEDBACK_TOPIC, feedback_frames
from services.voice_fsm.settings_store import FILE_NAME, SettingsStore
from services.voice_fsm.wire import (
    Envelope,
    EnvelopeRouter,
    Op,
    Service,
    Status,
    VoiceService,
    decode_envelope,
    decode_event,
    encode_command,
    encode_envelope,
    encode_event,
)

pytestmark = pytest.mark.req("REQ-VOICE-017")


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


# ── Store ─────────────────────────────────────────────────────────────────


def test_the_store_keeps_the_verbosity_across_a_restart(tmp_path):
    SettingsStore(tmp_path / FILE_NAME).save(Settings(Verbosity.CHATTY))
    assert SettingsStore(tmp_path / FILE_NAME).load() == Settings(Verbosity.CHATTY)
    assert json.loads((tmp_path / FILE_NAME).read_text()) == {"verbosity": "chatty"}
    assert [p.name for p in tmp_path.iterdir()] == [
        FILE_NAME
    ]  # no temporary file left behind


def test_a_missing_damaged_or_unknown_file_gives_the_defaults(tmp_path):
    path = tmp_path / FILE_NAME
    assert SettingsStore(path).load() == Settings(Verbosity.NORMAL)
    for body in ("{not json", "[1, 2]", '{"verbosity": "shouting"}', "\x00\x01"):
        path.write_text(body)
        assert SettingsStore(path).load() == Settings(Verbosity.NORMAL), body


def test_the_state_directory_comes_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("MIA_STATE_DIR", str(tmp_path / "state"))
    store = SettingsStore.from_env()
    assert store.save(Settings(Verbosity.QUIET))
    assert (tmp_path / "state" / FILE_NAME).exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_a_write_that_fails_is_reported_and_never_raised(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        assert (
            SettingsStore(locked / FILE_NAME).save(Settings(Verbosity.QUIET)) is False
        )
    finally:
        locked.chmod(0o700)


def test_a_path_that_cannot_be_a_directory_is_reported_and_never_raised(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    assert SettingsStore(blocker / FILE_NAME).save(Settings(Verbosity.QUIET)) is False


# ── Machine ───────────────────────────────────────────────────────────────


def test_the_machine_reports_its_settings_on_every_change_in_any_state():
    machine = VoiceMachine(Clock())
    assert machine.settings() == Settings(Verbosity.NORMAL)

    out = machine.handle(SetVerbosity(Verbosity.CHATTY))
    assert Settings(Verbosity.CHATTY) in out
    assert machine.state is State.SPEAKING  # "Okay, chatty."

    busy = VoiceMachine(Clock())
    busy.handle(Wake())
    assert busy.state is State.LISTENING
    out = busy.handle(SetVerbosity(Verbosity.QUIET))
    assert Settings(Verbosity.QUIET) in out
    assert busy.settings() == Settings(Verbosity.QUIET)


def test_a_machine_starts_from_the_stored_level(tmp_path):
    store = SettingsStore(tmp_path / FILE_NAME)
    store.save(Settings(Verbosity.QUIET))
    assert VoiceMachine(
        Clock(), verbosity=store.load().verbosity
    ).settings() == Settings(Verbosity.QUIET)


# ── Bridge: by voice ──────────────────────────────────────────────────────


def _bridge(saved, classified):
    machine = VoiceMachine(Clock())

    def classify(text):
        classified.append(text)
        return ()

    bridge = RouterBridge(
        machine,
        classify=classify,
        execute=lambda part: "",
        publish_text=lambda text, utterance_id: None,
        on_settings=saved.append,
    )
    return machine, bridge


@pytest.mark.parametrize(
    "said, level",
    [
        ("quiet mode", Verbosity.QUIET),
        ("Chatty mode.", Verbosity.CHATTY),
        ("switch to normal mode", Verbosity.NORMAL),
        ("go to quiet mode", Verbosity.QUIET),
        ("be  chatty mode", Verbosity.CHATTY),
    ],
)
def test_the_spoken_modes_set_the_verbosity_and_it_is_saved(said, level):
    saved, classified = [], []
    machine, bridge = _bridge(saved, classified)
    if level is Verbosity.NORMAL:
        machine.handle(SetVerbosity(Verbosity.QUIET))
    bridge.on_transcript(said)
    assert machine.verbosity is level
    assert saved[-1] == Settings(level)
    assert classified == []


@pytest.mark.parametrize(
    "said",
    [
        "read the quiet mode settings",
        "is quiet mode on",
        "quiet",
        "mode",
        "quieter mode",
    ],
)
def test_a_sentence_that_only_mentions_a_mode_is_still_a_request(said):
    saved, classified = [], []
    machine, bridge = _bridge(saved, classified)
    bridge.on_transcript(said)
    assert machine.verbosity is Verbosity.NORMAL
    assert saved == [] and classified == [said]


def test_the_router_feedback_frames_take_the_state_name_as_it_is():
    # voice_command_router used fb.state.value on a plain string and crashed on the first cue.
    topic, payload = feedback_frames(Feedback("listening", "blue", "none"))
    assert topic == FEEDBACK_TOPIC
    assert json.loads(payload) == {"state": "listening", "led": "blue", "tone": "none"}


# ── Router: read back on open, broadcast on change ────────────────────────


class Peer:
    def __init__(self, router, session):
        self.session = session
        self.inbox = []
        self.connection = router.connect(self.inbox.append)

    def send(self, op, payload=b"", seq=1):
        self.connection.handle(
            encode_envelope(
                Envelope(Service.VOICE, self.session, op, Status.OK, seq, payload)
            )
        )

    def take(self):
        out = [decode_envelope(m) for m in self.inbox]
        self.inbox.clear()
        return out


def test_an_opened_session_alone_gets_the_settings_and_every_session_sees_a_change():
    saved = []
    machine = VoiceMachine(Clock(), verbosity=Verbosity.CHATTY)
    router = EnvelopeRouter()
    router.register(Service.VOICE, VoiceService(machine, on_settings=saved.append))
    first, second = Peer(router, "a"), Peer(router, "b")

    first.send(Op.OPEN)
    reply, snapshot = first.take()
    assert reply.status == Status.OK and not reply.payload
    assert decode_event(snapshot.payload) == Settings(Verbosity.CHATTY)
    assert saved == []  # reading back is not a change

    second.send(Op.OPEN)
    second.take()
    assert first.take() == []  # another console opening does not resend the settings

    first.send(
        Op.DATA, encode_command(SetVerbosity(Verbosity.QUIET, Source.CONSOLE)), seq=2
    )
    for peer in (first, second):
        events = [decode_event(e.payload) for e in peer.take() if e.payload]
        assert Settings(Verbosity.QUIET) in events
    assert saved == [Settings(Verbosity.QUIET)]


# ── Console ───────────────────────────────────────────────────────────────


def test_the_console_machine_starts_from_the_store_and_saves_a_change(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("MIA_STATE_DIR", str(tmp_path))
    SettingsStore(tmp_path / FILE_NAME).save(Settings(Verbosity.QUIET))
    monkeypatch.setattr(voice_console, "_router", None)
    router = voice_console.get_router()
    console = Peer(router, "c")
    console.send(Op.OPEN)
    _, snapshot = console.take()
    assert decode_event(snapshot.payload) == Settings(Verbosity.QUIET)

    console.send(
        Op.DATA, encode_command(SetVerbosity(Verbosity.CHATTY, Source.CONSOLE)), seq=2
    )
    assert SettingsStore(tmp_path / FILE_NAME).load() == Settings(Verbosity.CHATTY)
    monkeypatch.setattr(voice_console, "_router", None)


def test_simulated_speech_lets_the_console_machine_finish_speaking():
    clock = Clock()
    machine = VoiceMachine(clock)
    router = EnvelopeRouter()
    router.register(
        Service.VOICE,
        voice_console.SimulatedSpeech(VoiceService(machine), clock, speak_sec=1.5),
    )
    console = Peer(router, "c")
    console.send(Op.OPEN)

    console.send(
        Op.DATA, encode_command(SetVerbosity(Verbosity.CHATTY, Source.CONSOLE)), seq=2
    )
    assert (
        machine.state is State.SPEAKING
    )  # "Okay, chatty." and nothing would ever say it ended

    clock.now += 1.0
    router.tick()
    assert machine.state is State.SPEAKING
    clock.now += 0.5
    router.tick()
    assert machine.state is State.IDLE


def test_simulated_speech_ends_utterances_one_after_the_other():
    class TwoUtterances:
        def __init__(self):
            self.submitted = []

        def handle(self, payload):
            said = [Speak("a", {}, 0, 1), Speak("b", {}, 0, 2)]
            return Status.OK, [encode_event(s) for s in said]

        def tick(self):
            return []

        def submit(self, command):
            self.submitted.append(command)
            return []

    clock = Clock()
    fake = TwoUtterances()
    speech = voice_console.SimulatedSpeech(fake, clock, speak_sec=1.0)
    speech.handle(b"")
    clock.now += 1.0
    speech.tick()
    assert fake.submitted == [SpeakingDone(1)]
    clock.now += 1.0
    speech.tick()
    assert fake.submitted == [SpeakingDone(1), SpeakingDone(2)]
