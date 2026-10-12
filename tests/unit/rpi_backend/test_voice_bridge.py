"""Router bridge, microphone gate and the speaking events around the voice state machine.

Everything here runs with fakes and a fake clock: no ZeroMQ, no audio, no sleeping.
"""

import json
from pathlib import Path

import pytest
from services import voice_command_router as router
from services.voice_fsm import ActionClass, Intent, Part, State, VoiceMachine
from services.voice_fsm.bridge import RouterBridge, parts_from_route, render_phrase
from services.voice_fsm.events import (
    FINISHED,
    STARTED,
    decode_speaking,
    decode_speaking_event,
    encode_feedback,
    encode_speaking,
)
from services.voice_fsm.mic_gate import MicGate

pytestmark = pytest.mark.req("REQ-VOICE-011", "REQ-VOICE-012", "REQ-VOICE-016")

SYSTEMD = Path(__file__).resolve().parents[3] / "infra" / "systemd"


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class Harness:
    """A bridge wired to fakes that record what the router would execute and publish."""

    def __init__(self, clock, classify=None, execute_result="Lights turned on."):
        self.clock = clock
        self.spoken = []
        self.ids = []
        self.feedback = []
        self.executed = []
        self.machine = VoiceMachine(clock)

        def execute(part):
            self.executed.append(part.name)
            return execute_result

        self.bridge = RouterBridge(
            self.machine,
            classify=classify
            or (
                lambda text: parts_from_route(
                    router.route_command(text), router.CONFIRM_THRESHOLD
                )
            ),
            execute=execute,
            publish_text=self._publish,
            publish_feedback=self.feedback.append,
        )

    def _publish(self, text, utterance_id):
        self.spoken.append(text)
        self.ids.append(utterance_id)

    def tts_finished(self, utterance_id=None):
        self.bridge.on_speaking(FINISHED, utterance_id)


@pytest.fixture
def clock():
    return Clock()


# ── Speaking events ───────────────────────────────────────────────────────


def test_speaking_events_round_trip():
    for event in (STARTED, FINISHED):
        topic, payload = encode_speaking(event, now=lambda: 1.5)
        assert topic == b"mia/voice/speaking"
        assert decode_speaking(payload) == event
        assert json.loads(payload)["timestamp"] == 1.5


def test_the_utterance_id_travels_with_the_speaking_event():
    _, payload = encode_speaking(FINISHED, utterance_id=7)
    assert decode_speaking_event(payload) == (FINISHED, 7)
    _, payload = encode_speaking(STARTED)
    assert decode_speaking_event(payload) == (STARTED, None)


def test_garbage_is_not_a_speaking_event():
    assert decode_speaking(b"not json") is None
    assert decode_speaking(b'{"event": "other"}') is None
    with pytest.raises(ValueError):
        encode_speaking("other")


def test_feedback_is_published_on_its_own_topic():
    topic, payload = encode_feedback("window", "yellow_countdown", "double_beep")
    assert topic == b"mia/voice/feedback"
    assert json.loads(payload) == {
        "state": "window",
        "led": "yellow_countdown",
        "tone": "double_beep",
    }


# ── Microphone gate ───────────────────────────────────────────────────────


def test_the_gate_turns_frames_into_silence_while_mia_speaks(clock):
    gate = MicGate(clock, tail_sec=0.3)
    frame = b"\x01\x02" * 240
    assert gate.apply(frame) == frame

    gate.on_event(STARTED)
    silent = gate.apply(frame)
    assert silent == b"\x00" * len(
        frame
    )  # same length, so downstream timing is unchanged


def test_the_gate_stays_closed_for_a_short_tail_after_the_speech(clock):
    gate = MicGate(clock, tail_sec=0.3)
    gate.on_event(STARTED)
    gate.on_event(FINISHED)
    assert not gate.is_open
    clock.now += 0.29
    assert not gate.is_open
    clock.now += 0.02
    assert gate.is_open


def test_a_finished_event_opens_the_gate_only_when_no_utterance_is_still_playing(clock):
    gate = MicGate(clock, tail_sec=0.3)
    gate.on_event(STARTED)
    gate.on_event(STARTED)  # a second utterance begins
    gate.on_event(FINISHED)
    clock.now += 1
    assert not gate.is_open
    gate.on_event(FINISHED)
    clock.now += 1
    assert gate.is_open


# ── Bridge ────────────────────────────────────────────────────────────────


def test_a_certain_command_runs_and_its_result_is_spoken(clock):
    h = Harness(clock)
    h.bridge.on_transcript("turn the lights on")
    assert h.executed == ["turn lights on"]
    assert h.spoken == ["Lights turned on."]
    h.tts_finished()
    assert h.machine.state is State.IDLE


def test_an_unclear_command_is_announced_and_runs_after_the_window(clock):
    h = Harness(clock)
    h.bridge.on_transcript("lights")
    assert h.executed == []
    assert len(h.spoken) == 1 and "in 5 seconds" in h.spoken[0]

    clock.now += 60
    h.bridge.poll()
    assert h.executed == []  # the window has not started: MIA is still talking

    h.tts_finished()
    clock.now += 4.9
    h.bridge.poll()
    assert h.executed == []
    clock.now += 0.2
    h.bridge.poll()
    assert len(h.executed) == 1


def test_stop_in_the_window_cancels_and_go_ahead_runs_it(clock):
    cancelled = Harness(clock)
    cancelled.bridge.on_transcript("lights")
    cancelled.tts_finished()
    cancelled.bridge.on_transcript("stop")
    assert cancelled.executed == []
    assert cancelled.machine.state is State.IDLE

    go = Harness(clock)
    go.bridge.on_transcript("lights")
    go.tts_finished()
    go.bridge.on_transcript("go ahead")
    assert len(go.executed) == 1


def test_a_yes_or_no_inside_another_word_is_not_an_answer(clock):
    seen = []

    def classify(text):
        seen.append(text)
        return ()

    h = Harness(clock, classify=classify)
    h.machine.handle(
        Intent((Part("message.send", ActionClass.MESSAGE, {}, certain=False),))
    )
    h.tts_finished()
    assert h.machine.state is State.CONFIRMING

    h.bridge.on_transcript("I know the answer")  # contains "no" only inside "know"
    assert seen == ["I know the answer"]  # routed as a new utterance, not taken as a no


def test_an_empty_result_does_not_leave_the_machine_waiting_for_speech(clock):
    h = Harness(clock, execute_result="")
    h.bridge.on_transcript("turn the lights on")
    assert h.spoken == []
    assert h.machine.state is State.IDLE


def test_the_utterance_id_is_sent_to_tts_and_a_stale_done_is_ignored(clock):
    h = Harness(clock)
    h.bridge.on_transcript("lights")  # announced, then waits for the speech to end
    assert h.ids == [1]
    h.tts_finished(utterance_id=99)  # not outstanding
    assert h.machine.state is State.SPEAKING
    h.tts_finished(utterance_id=1)
    assert h.machine.state is State.WINDOW


def test_every_state_change_is_published_as_feedback(clock):
    h = Harness(clock)
    h.bridge.on_wake()
    h.bridge.on_transcript("turn the lights on")
    states = [fb.state for fb in h.feedback]
    assert states[:3] == ["wake_caught", "listening", "analysing"]
    assert "executing" in states


def test_a_wake_event_reaches_the_machine(clock):
    h = Harness(clock)
    h.bridge.on_wake()
    assert h.machine.state is State.LISTENING


def test_unknown_speech_is_answered_politely(clock):
    h = Harness(clock)
    h.bridge.on_transcript("banana banana")
    assert h.spoken == ["Sorry, I didn't understand."]


# ── Phrases ───────────────────────────────────────────────────────────────


def test_phrases_render_with_parameters_and_fall_back_safely():
    assert render_phrase(
        "chain.announce", {"parts": ["a", "b"], "seconds": 5.0}
    ).startswith("I will a, b in 5 ")
    assert render_phrase("raw", {"text": "hello"}) == "hello"
    assert render_phrase("some.unknown.key", {}) == "some.unknown.key"
    assert render_phrase(
        "message.read", {"sender": "Petr"}
    )  # a missing parameter must not raise


# ── Wiring ────────────────────────────────────────────────────────────────


def test_the_router_hands_over_to_the_state_machine_only_when_asked(monkeypatch):
    monkeypatch.setattr(router, "main_fsm", lambda: "fsm")
    monkeypatch.setenv("VOICE_FSM", "1")
    assert router.main() == "fsm"


def _env(unit):
    """Environment= assignments of a unit, later lines winning."""
    values = {}
    for line in SYSTEMD.joinpath(unit).read_text(encoding="utf-8").splitlines():
        if line.startswith("Environment="):
            name, _, value = line[len("Environment=") :].partition("=")
            values[name] = value
    return values


def test_tts_audio_capture_and_router_agree_on_the_speaking_port():
    ports = {
        unit: _env(unit).get("ZMQ_SPEAKING_PORT")
        for unit in (
            "mia-tts.service",
            "mia-audio-capture.service",
            "mia-voice-router.service",
        )
    }
    assert set(ports.values()) == {"5563"}, ports


def test_the_state_machine_is_off_by_default_on_the_pi():
    assert _env("mia-voice-router.service").get("VOICE_FSM") == "0"


def test_the_bridge_answers_each_batch_with_its_own_id(clock):
    h = Harness(clock)
    seen = []
    original = h.machine.handle

    def spy(command):
        seen.append(command)
        return original(command)

    h.machine.handle = spy
    h.bridge.on_transcript("turn the lights on")
    from services.voice_fsm import ExecutionDone

    done = [c for c in seen if isinstance(c, ExecutionDone)]
    assert [d.batch_id for d in done] == [1]
