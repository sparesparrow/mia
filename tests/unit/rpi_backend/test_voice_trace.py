"""The voice scenario helpers: trace, ordered expectation, scenario files, stimuli (REQ-VOICE-028).

No audio, no network: a fake clock stands in for time, a fake socket for ZeroMQ.
"""

import importlib
import json
import sys
import textwrap
import time

import pytest
from support import voice_stimuli
from support.voice_rig import MachineRig, run_scenario
from support.voice_scenarios import ScenarioError, load_all, parse_scenario
from support.voice_trace import (
    ExpectationFailed,
    VoiceTrace,
    expect,
    normalize_text,
    parse_step,
)

pytestmark = pytest.mark.req("REQ-VOICE-028")


class Clock:
    """Time that only moves when something sleeps."""

    def __init__(self):
        self.now = 0.0
        self.slept = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        self.slept += seconds


def _trace(*events):
    clock = Clock()
    trace = VoiceTrace(clock)
    for kind, fields in events:
        clock.now += 0.5
        trace.add(kind, **fields)
    return trace, clock


def test_text_is_compared_lower_case_without_punctuation():
    assert normalize_text("  Turn the LIGHTS off!! ") == "turn the lights off"
    assert normalize_text("Okay, quiet.") == normalize_text("okay quiet")


def test_steps_match_as_an_ordered_subsequence_with_other_events_between():
    trace, clock = _trace(
        ("state", {"state": "listening"}),
        ("feedback", {"state": "listening", "led": "blue", "tone": "none"}),
        ("transcript", {"text": "Turn the lights off."}),
        ("state", {"state": "executing"}),
    )
    hits = expect(
        trace,
        [
            {"state": "listening"},
            {"transcript": {"text": "turn the lights off"}},
            {"state": "executing"},
        ],
        clock=clock,
        sleep=clock.sleep,
    )
    assert [h["kind"] for h in hits] == ["state", "transcript", "state"]


def test_order_matters_and_an_event_serves_only_one_step():
    trace, clock = _trace(("state", {"state": "idle"}), ("state", {"state": "listening"}))
    with pytest.raises(ExpectationFailed):
        expect(trace, [{"state": "listening"}, {"state": "idle"}], 0.2, clock=clock, sleep=clock.sleep)
    with pytest.raises(ExpectationFailed):
        expect(trace, [{"state": "idle"}, {"state": "idle"}], 0.2, clock=clock, sleep=clock.sleep)


def test_contains_looks_at_the_words_and_the_phrase_key():
    trace, clock = _trace(("spoken", {"text": "Send it? Say yes or no.", "phrase": "message.confirm"}))
    for step in ({"contains": "SEND IT"}, {"contains": "say yes"}, {"phrase": "message.confirm"}):
        expect(trace, [{"spoken": step}], clock=clock, sleep=clock.sleep)
    with pytest.raises(ExpectationFailed):
        expect(trace, [{"spoken": {"contains": "lights"}}], 0.1, clock=clock, sleep=clock.sleep)


def test_a_step_waits_for_a_late_event_until_its_own_timeout():
    clock = Clock()
    trace = VoiceTrace(clock)
    sleeps = []

    def sleep(seconds):
        clock.sleep(seconds)
        sleeps.append(clock.now)
        if clock.now >= 1.0 and not any(e["kind"] == "state" for e in trace.events):
            trace.add("state", state="listening")

    assert expect(trace, [{"state": "listening", "timeout": 2}], 0.1, clock=clock, sleep=sleep)
    assert 1.0 <= sleeps[-1] < 2.0


def test_a_missing_event_times_out_without_real_waiting():
    trace, clock = _trace(("state", {"state": "listening"}))
    with pytest.raises(ExpectationFailed):
        expect(trace, [{"state": "listening"}, {"state": "idle", "timeout": 4}], 1, clock=clock, sleep=clock.sleep)
    assert 4 <= clock.slept < 4.1  # the second step's own timeout, not the default


def test_the_failure_shows_what_matched_what_failed_and_what_was_seen():
    trace, clock = _trace(
        ("state", {"state": "listening"}),
        ("feedback", {"state": "listening", "led": "blue", "tone": "none"}),
    )
    with pytest.raises(ExpectationFailed) as failure:
        expect(
            trace,
            [{"state": "listening"}, {"spoken": {"contains": "hello"}}, {"state": "idle"}],
            0.2,
            clock=clock,
            sleep=clock.sleep,
        )
    text = str(failure.value)
    assert "[ok  ] 1. state(state='listening') (trace #0)" in text
    assert "[FAIL] 2. spoken(contains='hello')" in text
    assert "[    ] 3. state(state='idle')" in text
    assert "step 2 did not appear within 0.2s" in text
    assert "#1" in text and "feedback(state='listening', led='blue'" in text


def test_an_empty_trace_is_reported_as_empty():
    with pytest.raises(ExpectationFailed, match=r"\(empty\)"):
        VoiceTrace(Clock()).expect([{"state": "idle"}], 0, clock=Clock(), sleep=lambda s: None)


def test_start_skips_what_happened_before_the_stimulus():
    trace, clock = _trace(("state", {"state": "idle"}), ("state", {"state": "listening"}))
    expect(trace, [{"state": "listening"}], start=1, clock=clock, sleep=clock.sleep)
    with pytest.raises(ExpectationFailed):
        expect(trace, [{"state": "idle"}], 0.1, start=1, clock=clock, sleep=clock.sleep)


@pytest.mark.parametrize(
    "step",
    [
        "idle",
        {},
        {"state": "idle", "spoken": "x"},
        {"colour": "red"},
        {"state": "idle", "timeout": -1},
        {"state": "idle", "timeout": "soon"},
    ],
)
def test_a_malformed_step_is_rejected(step):
    with pytest.raises(ValueError):
        parse_step(step)


def test_zmq_messages_become_normalized_events():
    trace = VoiceTrace(Clock())
    trace.feed_zmq(b"mia/voice/feedback", json.dumps({"state": "listening", "led": "blue", "tone": "none"}).encode())
    trace.feed_zmq(b"mia/voice/response", json.dumps({"text": "Okay, quiet."}).encode())
    trace.feed_zmq(b"mia/voice/speaking", json.dumps({"event": "started"}).encode())
    trace.feed_zmq(b"mia/voice/transcript", json.dumps({"text": "be quiet"}).encode())
    trace.feed_zmq(b"mia/voice/response", b"not json")
    kinds = [e["kind"] for e in trace.events]
    assert kinds == ["feedback", "state", "spoken", "mic", "transcript"]
    assert trace.events[3]["muted"] is True


@pytest.fixture
def real_zmq(monkeypatch):
    """Other test modules replace sys.modules["zmq"] with a MagicMock; load the real one for this test."""
    for name in [n for n in sys.modules if n == "zmq" or n.startswith("zmq.")]:
        monkeypatch.delitem(sys.modules, name)
    return importlib.import_module("zmq")


def test_the_zmq_tap_collects_published_messages_on_a_private_context(real_zmq):
    zmq = real_zmq
    context = zmq.Context()
    pub = context.socket(zmq.PUB)
    pub.bind("inproc://voice-trace-test")
    trace = VoiceTrace()
    tap = trace.tap_zmq(["inproc://voice-trace-test"], context=context)
    try:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not len(trace):
            pub.send_multipart([b"mia/voice/transcript", json.dumps({"text": "cancel"}).encode()])
            time.sleep(0.05)
        assert trace.events[0]["text"] == "cancel"
    finally:
        tap.stop()
        pub.close(0)
        context.term()


def test_a_failing_scenario_fails_loudly_in_the_machine_layer():
    scenario = parse_scenario(
        {
            "name": "x",
            "layers": ["machine"],
            "timeout": 1,
            "stimulus": {"kind": "button", "button": "Wake"},
            "expect": [{"state": "listening"}, {"state": "executing"}],
        }
    )
    with pytest.raises(ExpectationFailed, match=r"\[FAIL\] 2\. state"):
        run_scenario(MachineRig(), scenario)


# ── scenario files ───────────────────────────────────────────────────────────


def _scenario(**overrides):
    data = {"name": "s", "stimulus": {"kind": "button", "button": "Wake"}, "expect": [{"state": "listening"}]}
    data.update(overrides)
    return data


def test_every_committed_scenario_file_is_valid():
    scenarios = load_all()
    assert len({s.name for s in scenarios}) == len(scenarios) >= 9


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"stimulus": {"kind": "button", "button": "Honk"}}, "button must be one of"),
        ({"stimulus": {"kind": "teleport"}}, "unknown stimulus kind"),
        ({"stimulus": {"kind": "typed", "text": "hi"}}, "not live yet"),
        ({"stimulus": {"kind": "setting", "mood": "happy"}}, "exactly one of"),
        ({"stimulus": {"kind": "setup", "intent": "dictate"}}, "cannot run through /ws/voice"),
        ({"expect": []}, "non-empty list"),
        ({"expect": [{"state": "idle", "timeout": -2}]}, "step 1"),
        ({"expect": [{"smell": "burnt"}]}, "step 1"),
        ({"layers": ["moon"]}, "layers"),
        ({"pending": "later"}, "names the requirement"),
        ({"colour": "red"}, "unknown keys"),
        ({"timeout": 0}, "timeout"),
    ],
)
def test_a_malformed_scenario_is_rejected_with_a_reason(overrides, message):
    with pytest.raises(ScenarioError, match=message):
        parse_scenario(_scenario(**overrides))


def test_a_pending_scenario_may_use_a_stimulus_that_is_not_live():
    scenario = parse_scenario(
        _scenario(pending="REQ-VOICE-025: typed text", stimulus={"kind": "typed", "text": "hi"})
    )
    assert scenario.pending.startswith("REQ-VOICE-025")


def test_the_name_must_match_the_file_name(tmp_path):
    from support.voice_scenarios import load_scenario

    path = tmp_path / "other.yaml"
    path.write_text(textwrap.dedent("""
        name: s
        stimulus: {kind: button, button: Wake}
        expect: [{state: listening}]
    """))
    with pytest.raises(ScenarioError, match="must equal the file name"):
        load_scenario(path)
    path.write_text("name: [unclosed")
    with pytest.raises(ScenarioError, match="not valid YAML"):
        load_scenario(path)


# ── stimuli ──────────────────────────────────────────────────────────────────


def test_press_sends_the_button_as_a_command():
    from services.voice_fsm import Cancel, Confirm, Deny, EndDictation, GoNow, Wake

    sent = []

    class Target:
        def send_command(self, command):
            sent.append(type(command))

    for button in voice_stimuli.BUTTONS:
        voice_stimuli.press(Target(), button)
    assert sent == [Wake, GoNow, Cancel, Confirm, Deny, EndDictation]
    with pytest.raises(ValueError):
        voice_stimuli.press(Target(), "Honk")


def test_inject_transcript_publishes_on_the_transcript_topic():
    frames = []

    class Pub:
        def send_multipart(self, parts):
            frames.append(parts)

    voice_stimuli.inject_transcript(Pub(), "turn the lights off")
    topic, body = frames[0]
    assert topic == b"mia/voice/transcript"
    assert json.loads(body)["text"] == "turn the lights off"


def test_play_wav_runs_aplay_on_the_device_and_refuses_without_it(tmp_path, monkeypatch):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    calls = []
    monkeypatch.setattr(voice_stimuli.shutil, "which", lambda name: "/usr/bin/aplay")
    monkeypatch.setattr(voice_stimuli.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    voice_stimuli.play_wav(str(wav), "plughw:Loopback,0,0")
    assert calls == [["/usr/bin/aplay", "-q", "-D", "plughw:Loopback,0,0", str(wav)]]

    monkeypatch.setattr(voice_stimuli.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="Pi only"):
        voice_stimuli.play_wav(str(wav), "default")
    with pytest.raises(FileNotFoundError):
        voice_stimuli.play_wav(str(tmp_path / "missing.wav"), "default")


def test_streaming_over_the_audio_websocket_is_not_available_yet():
    with pytest.raises(NotImplementedError, match="REQ-VOICE-027"):
        voice_stimuli.stream_wav_ws("a.wav", "ws://pi/ws/audio")
