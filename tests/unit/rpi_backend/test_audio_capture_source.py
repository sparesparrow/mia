"""Which microphone the pipeline hears, and how long the phone path stays muted (ADR-0021, REQ-VOICE-027)."""

import pytest
from services.mic_source import (
    BUFFER_FRAMES,
    FRESH_SEC,
    JITTER_FRAMES,
    MicSource,
    source_mode,
    tail_seconds,
)
from services.voice_fsm.events import FINISHED, STARTED
from services.voice_fsm.mic_gate import MicGate

pytestmark = pytest.mark.req("REQ-VOICE-027")

SILENCE = b"\x00" * 960
LOCAL = b"\x07\x00" * 480


def phone(n):
    return bytes([n]) * 960


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def make(mode="auto", tail=0.8):
    clock = Clock()
    local = MicGate(clock, tail_sec=0.3)
    remote = MicGate(clock, tail_sec=tail)
    return MicSource(mode, clock, local, remote), clock, local, remote


def feed(source, count, start=1):
    for n in range(start, start + count):
        source.push_phone(phone(n))


def test_environment_values_are_normalised():
    assert source_mode("PHONE") == "phone"
    assert source_mode("nonsense") == "auto"
    assert tail_seconds("1.5") == 1.5
    assert tail_seconds("abc") == 0.8
    assert tail_seconds("-1") == 0.8


def test_usb_mode_never_plays_the_phone():
    source, *_ = make("usb")
    feed(source, 5)
    assert source.next_frame(LOCAL) == LOCAL
    assert source.next_frame(None) == SILENCE


def test_auto_prefers_a_fresh_phone_and_falls_back_to_the_local_device():
    source, clock, *_ = make("auto")
    assert source.next_frame(LOCAL) == LOCAL  # no phone yet
    feed(source, JITTER_FRAMES)
    assert source.next_frame(LOCAL) == phone(1)  # sources are never mixed
    clock.now += FRESH_SEC + 0.01
    assert source.next_frame(LOCAL) == LOCAL  # the phone went quiet
    assert source.next_frame(None) == SILENCE  # and no local device either


def test_phone_mode_gives_silence_until_the_jitter_buffer_is_primed():
    source, *_ = make("phone")
    feed(source, JITTER_FRAMES - 1)
    assert source.next_frame(LOCAL) == SILENCE
    source.push_phone(phone(9))
    assert source.next_frame(LOCAL) == phone(1)


def test_an_underrun_waits_for_the_jitter_target_again():
    source, *_ = make("phone")
    feed(source, JITTER_FRAMES)
    for _ in range(JITTER_FRAMES):
        source.next_frame(None)
    assert source.next_frame(None) == SILENCE and source.underruns == 1
    feed(source, 1, start=20)
    assert source.next_frame(None) == SILENCE  # not primed again yet


def test_the_buffer_keeps_the_newest_ten_frames():
    source, *_ = make("phone")
    feed(source, BUFFER_FRAMES + 4)
    assert source.dropped_overflow == 4
    assert source.next_frame(None) == phone(5)


def test_the_phone_is_muted_while_mia_speaks_and_for_the_tail_and_the_buffer_is_flushed():
    source, clock, local, remote = make("phone", tail=0.8)
    feed(source, 6)
    for gate in (local, remote):
        gate.on_event(STARTED)
    assert source.next_frame(None) == SILENCE
    assert source.flushed == 6  # what was buffered is stale
    for gate in (local, remote):
        gate.on_event(FINISHED)
    feed(source, JITTER_FRAMES)
    clock.now += 0.5  # past the local tail (0.3) but inside the phone tail (0.8)
    assert source.next_frame(None) == SILENCE
    feed(source, JITTER_FRAMES, start=50)
    clock.now += 0.4  # now past the phone tail too
    assert source.next_frame(None) == phone(50)  # only frames sent after the tail are played


def test_local_frames_still_use_the_short_tail():
    source, clock, local, remote = make("usb")
    local.on_event(STARTED)
    assert source.next_frame(LOCAL) == SILENCE
    local.on_event(FINISHED)
    clock.now += 0.35
    assert source.next_frame(LOCAL) == LOCAL
