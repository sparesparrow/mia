"""/ws/audio takes the phone's microphone and pushes it on without ever blocking (ADR-0021, REQ-VOICE-027)."""

import json
import time

import pytest
from api import audio_ingest, main as api_main
from api.auth import api_key as api_key_module
from api.auth import dependencies as deps
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

pytestmark = pytest.mark.req("REQ-VOICE-027")

WRITE_KEY = "mia_api_readwrite_0123456789abcd"
READ_KEY = "mia_api_readonly_0123456789abcdef"
HEADER = json.dumps({"v": 1, "fmt": "s16le", "rate": 16000, "ch": 1, "frame_ms": 30})
FRAME = b"\x01\x00" * 480


class FakePusher:
    def __init__(self, capacity=8):
        self.capacity = capacity
        self.frames = []

    def push(self, frame):
        if len(self.frames) >= self.capacity:
            return False
        self.frames.append(frame)
        return True


@pytest.fixture
def pusher(monkeypatch):
    fake = FakePusher()
    monkeypatch.setattr(audio_ingest, "_pusher", fake)
    monkeypatch.setattr(audio_ingest, "_active", None)
    return fake


@pytest.fixture
def client(monkeypatch, pusher):
    monkeypatch.setenv("VOICE_PHONE_MIC", "1")
    monkeypatch.delenv("MIA_AUTH_DISABLED", raising=False)
    monkeypatch.delenv("MIA_API_KEYS", raising=False)
    monkeypatch.setenv("MIA_API_KEY", WRITE_KEY)
    deps._verified.clear()
    monkeypatch.setattr(deps, "_warned_open", False)
    monkeypatch.setattr(api_key_module, "_api_key_auth", api_key_module.APIKeyAuth())
    api_key_module.get_api_key_auth().add_key(READ_KEY, "reader", scopes=["read"])
    yield TestClient(api_main.app)
    deps._verified.clear()
    api_key_module._api_key_auth = None


@pytest.fixture
def ingest_client(client, monkeypatch, pusher):
    # The route builds its AudioIngest around the module pusher's push method.
    monkeypatch.setattr(audio_ingest, "_pusher", pusher)
    return client


def _expect_close(client, headers, code):
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect("/ws/audio", headers=headers) as ws:
            ws.send_text(HEADER)
            ws.receive_text()
    assert closed.value.code == code


def test_header_accepts_only_the_pipeline_format():
    assert audio_ingest.header_ok(HEADER)
    for bad in (
        "not json",
        "[]",
        json.dumps({"v": 1, "fmt": "s16le", "rate": 48000, "ch": 1, "frame_ms": 30}),
        json.dumps({"v": 1, "fmt": "f32", "rate": 16000, "ch": 1, "frame_ms": 30}),
        json.dumps({"v": 1, "fmt": "s16le", "rate": 16000, "ch": 2, "frame_ms": 30}),
        json.dumps({"v": 1, "fmt": "s16le", "rate": 16000, "ch": 1}),
        None,
    ):
        assert not audio_ingest.header_ok(bad)


def test_frames_are_split_counted_and_dropped_when_the_queue_is_full():
    fake = FakePusher(capacity=3)
    ingest = audio_ingest.AudioIngest(fake.push)
    assert ingest.accept(FRAME * 2) == 2
    assert ingest.accept(FRAME * 2) == 1  # the third fits, the fourth is dropped, never waited for
    assert ingest.counts() == {"pushed": 3, "dropped": 1, "bad": 0, "oversized": 0}
    assert all(len(f) == audio_ingest.FRAME_BYTES for f in fake.frames)


def test_a_message_that_is_not_whole_frames_is_dropped_and_counted():
    fake = FakePusher()
    ingest = audio_ingest.AudioIngest(fake.push)
    assert ingest.accept(FRAME[:-2]) == 0
    assert ingest.accept(b"") == 0
    assert ingest.counts()["bad"] == 2 and fake.frames == []


def test_a_message_over_the_cap_is_rejected_before_splitting_or_pushing():
    fake = FakePusher(capacity=100)
    ingest = audio_ingest.AudioIngest(fake.push)
    assert audio_ingest.MAX_MESSAGE_BYTES == audio_ingest.FRAME_BYTES * 32
    assert ingest.accept(FRAME * 32) == 32
    assert ingest.accept(FRAME * 33) == 0
    assert len(fake.frames) == 32
    assert ingest.counts()["oversized"] == 1


def test_the_socket_never_blocks_and_drops_when_the_listener_does_not_keep_up(real_zmq):
    zmq, _ = real_zmq
    ctx = zmq.Context()
    pull = ctx.socket(zmq.PULL)  # bound, never read: the capture service stuck
    pull.setsockopt(zmq.RCVHWM, 1)
    port = pull.bind_to_random_port("tcp://127.0.0.1")
    pusher = audio_ingest.ZmqPusher(port=port)
    started = time.monotonic()
    try:
        # More than loopback buffers can hold, so the queue must fill whatever the platform's buffer sizes.
        results = [pusher.push(FRAME) for _ in range(20000)]
    finally:
        pusher.close()
        pull.close(0)
        ctx.term()
    assert time.monotonic() - started < 5.0  # never waited for the listener
    assert False in results and True in results


def test_a_write_key_streams_frames_to_the_pusher(ingest_client, pusher):
    with ingest_client.websocket_connect("/ws/audio", headers={"X-API-Key": WRITE_KEY}) as ws:
        ws.send_text(HEADER)
        assert ws.receive_json() == {"ok": True}
        ws.send_bytes(FRAME * 2)
        ws.send_bytes(FRAME)
    assert len(pusher.frames) == 3


def test_an_oversized_message_closes_with_message_too_big(ingest_client):
    with pytest.raises(WebSocketDisconnect) as closed:
        with ingest_client.websocket_connect("/ws/audio", headers={"X-API-Key": WRITE_KEY}) as ws:
            ws.send_text(HEADER)
            assert ws.receive_json() == {"ok": True}
            ws.send_bytes(FRAME * 33)
            ws.receive_text()
    assert closed.value.code == 1009


def test_a_read_only_key_is_refused(ingest_client):
    _expect_close(ingest_client, {"X-API-Key": READ_KEY}, 1008)


def test_no_key_is_refused(ingest_client):
    _expect_close(ingest_client, {}, 1008)


def test_no_key_is_refused_even_when_global_auth_is_disabled(ingest_client, monkeypatch):
    monkeypatch.setenv("MIA_AUTH_DISABLED", "1")
    monkeypatch.delenv("MIA_API_KEY", raising=False)
    monkeypatch.delenv("MIA_API_KEYS", raising=False)
    monkeypatch.setattr(api_key_module, "_api_key_auth", api_key_module.APIKeyAuth())
    deps._verified.clear()
    _expect_close(ingest_client, {}, 1008)


def test_the_endpoint_is_off_unless_enabled(ingest_client, monkeypatch):
    monkeypatch.delenv("VOICE_PHONE_MIC", raising=False)
    _expect_close(ingest_client, {"X-API-Key": WRITE_KEY}, 1008)


def test_a_wrong_header_closes_with_1003(ingest_client):
    with pytest.raises(WebSocketDisconnect) as closed:
        with ingest_client.websocket_connect("/ws/audio", headers={"X-API-Key": WRITE_KEY}) as ws:
            ws.send_text(json.dumps({"v": 1, "fmt": "s16le", "rate": 8000, "ch": 1, "frame_ms": 30}))
            ws.receive_text()
    assert closed.value.code == 1003


def test_a_second_phone_replaces_the_first(ingest_client):
    headers = {"X-API-Key": WRITE_KEY}
    with ingest_client.websocket_connect("/ws/audio", headers=headers) as first:
        first.send_text(HEADER)
        assert first.receive_json() == {"ok": True}
        with ingest_client.websocket_connect("/ws/audio", headers=headers) as second:
            second.send_text(HEADER)
            assert second.receive_json() == {"ok": True}
            with pytest.raises(WebSocketDisconnect) as closed:
                first.receive_text()
            assert closed.value.code == 1008
