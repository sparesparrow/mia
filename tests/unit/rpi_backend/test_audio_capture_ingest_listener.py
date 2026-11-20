"""The phone-ingest port stays closed unless its feature flag is explicit."""

from types import SimpleNamespace

import pytest

from services import audio_capture

pytestmark = pytest.mark.req("REQ-VOICE-027")


class FakeThread:
    calls = []

    def __init__(self, *, target, args, daemon):
        self.calls.append((target, args, daemon))

    def start(self):
        pass


def test_auto_source_does_not_start_listener_when_phone_mic_is_off(monkeypatch):
    FakeThread.calls = []
    monkeypatch.setattr(audio_capture, "mic_source", SimpleNamespace(wants_phone=True, mode="auto"))
    monkeypatch.setattr(audio_capture.threading, "Thread", FakeThread)
    monkeypatch.delenv("VOICE_PHONE_MIC", raising=False)

    assert audio_capture.start_phone_ingest_listener(object()) is False
    assert FakeThread.calls == []


def test_phone_listener_starts_only_when_explicitly_enabled(monkeypatch):
    FakeThread.calls = []
    monkeypatch.setattr(audio_capture, "mic_source", SimpleNamespace(wants_phone=True, mode="auto"))
    monkeypatch.setattr(audio_capture.threading, "Thread", FakeThread)
    monkeypatch.setenv("VOICE_PHONE_MIC", "1")

    assert audio_capture.start_phone_ingest_listener("context") is True
    assert len(FakeThread.calls) == 1
    target, args, daemon = FakeThread.calls[0]
    assert target is audio_capture.listen_for_ingest
    assert args == ("context",)
    assert daemon is True


def test_usb_only_source_never_starts_phone_listener_even_if_enabled(monkeypatch):
    FakeThread.calls = []
    monkeypatch.setattr(audio_capture, "mic_source", SimpleNamespace(wants_phone=False, mode="usb"))
    monkeypatch.setattr(audio_capture.threading, "Thread", FakeThread)
    monkeypatch.setenv("VOICE_PHONE_MIC", "1")

    assert audio_capture.start_phone_ingest_listener(object()) is False
    assert FakeThread.calls == []
