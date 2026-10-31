"""The Android app's LED commands on /ws/telemetry change the LED state."""

import copy
import os
import sys

import pytest

PY_API = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", "apps", "rpi-backend", "py-api")
sys.path.insert(0, PY_API)

from api import main as api_main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

pytestmark = pytest.mark.req("REQ-NET-011")


@pytest.fixture
def client(monkeypatch):
    original = copy.deepcopy(api_main.led_state)
    sent = []

    class FakeSocket:
        # Replaces the whole socket: other tests can leave a MagicMock in place of zmq
        def send_multipart(self, frames):
            sent.append(frames)

    monkeypatch.setattr(api_main, "zmq_socket", FakeSocket())
    test_client = TestClient(api_main.app)
    test_client.sent = sent
    yield test_client
    api_main.led_state.clear()
    api_main.led_state.update(original)


def _send_and_read_state(client, commands):
    """Send the commands, then read frames until the state shows the last command was applied."""
    with client.websocket_connect("/ws/telemetry") as websocket:
        for command in commands:
            websocket.send_json(command)
        state = None
        for _ in range(40):
            state = websocket.receive_json()["led_state"]
            if len(client.sent) >= sum(1 for _ in commands) or not commands:
                break
        return state


@pytest.mark.parametrize(
    "command, field, value",
    [
        ({"action": "set_ai_state", "ai_state": "listening"}, "ai_state", "listening"),
        ({"action": "set_mode", "mode": "Night"}, "mode", "Night"),
        ({"action": "set_brightness", "brightness": 200}, "brightness", 200),
        ({"action": "set_brightness", "brightness": 999}, "brightness", 255),
        ({"action": "set_brightness", "brightness": -5}, "brightness", 0),
        ({"action": "trigger_emergency"}, "emergency", True),
        ({"action": "start_animation", "animation": "pulse", "speed": 100}, "animation", "pulse"),
    ],
)
def test_valid_command_changes_the_state(client, command, field, value):
    state = _send_and_read_state(client, [command])
    assert state[field] == value
    assert api_main.led_state[field] == value
    assert client.get("/led/state").json()["led_state"][field] == value
    assert client.sent, "the command is forwarded to the LED controller"


def test_clear_emergency_and_stop_animation(client):
    api_main.led_state.update({"emergency": True, "animation": "pulse"})
    state = _send_and_read_state(client, [{"action": "clear_emergency"}, {"action": "stop_animation"}])
    assert state["emergency"] is False
    assert state["animation"] == "none"


@pytest.mark.parametrize(
    "command",
    [
        {"action": "set_ai_state", "ai_state": "dancing"},
        {"action": "set_ai_state", "ai_state": 3},
        {"action": "set_mode", "mode": ""},
        {"action": "set_mode", "mode": "x" * 40},
        {"action": "set_brightness", "brightness": "bright"},
        {"action": "set_brightness", "brightness": True},
        {"action": "set_brightness", "brightness": float("nan")},
        {"action": "start_animation", "animation": 5},
        {"action": "reboot"},
        {"nothing": "here"},
    ],
)
def test_invalid_or_unknown_command_is_ignored(client, command):
    before = copy.deepcopy(api_main.led_state)
    with client.websocket_connect("/ws/telemetry") as websocket:
        websocket.send_json(command)
        websocket.send_text("not json")
        websocket.send_text("[1, 2]")
        for _ in range(5):
            state = websocket.receive_json()["led_state"]
    assert state == before
    assert api_main.led_state == before
    assert not client.sent
