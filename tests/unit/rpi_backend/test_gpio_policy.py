"""GPIO pin policy: allowlist, config overrides, API status codes, worker and simulation guards."""

import importlib
import json
import os
import sys
import types

import pytest

PY_API = os.path.join(os.path.dirname(__file__), "..", "..", "..", "apps", "rpi-backend", "py-api")
sys.path.insert(0, PY_API)

from api import main as api_main  # noqa: E402
from api.auth import api_key as api_key_module  # noqa: E402
from api.auth import dependencies as deps  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from hardware import gpio_policy  # noqa: E402

pytestmark = pytest.mark.req("REQ-HW-010")

API_KEY = "mia_api_gpiopolicy_0123456789abcdef"


@pytest.fixture(autouse=True)
def clean_policy(monkeypatch):
    for name in ("MIA_GPIO_POLICY_FILE", "MIA_GPIO_ALLOWED_PINS", "IGNITION_GPIO_PIN"):
        monkeypatch.delenv(name, raising=False)
    gpio_policy.reset_policy()
    yield
    gpio_policy.reset_policy()


# ── policy decisions ──────────────────────────────────────────────────


@pytest.mark.parametrize("pin", [4, 5, 22, 27])
@pytest.mark.parametrize("direction", ["input", "output"])
def test_general_purpose_pins_allow_both_directions(pin, direction):
    assert gpio_policy.get_policy().check(pin, direction) == pin


@pytest.mark.parametrize("pin", [0, 1, 2, 3, 7, 8, 9, 10, 11, 14, 15])
@pytest.mark.parametrize("direction", ["input", "output"])
def test_eeprom_i2c_spi_uart_pins_are_denied(pin, direction):
    with pytest.raises(gpio_policy.PinDenied):
        gpio_policy.get_policy().check(pin, direction)
    with pytest.raises(gpio_policy.PinDenied):
        gpio_policy.get_policy().check_read(pin)


def test_ignition_pin_is_input_only():
    policy = gpio_policy.get_policy()
    assert policy.check(17, "input") == 17
    assert policy.check_read(17) == 17
    with pytest.raises(gpio_policy.PinDenied):
        policy.check(17, "output")


def test_ignition_pin_follows_the_power_monitor_env(monkeypatch):
    monkeypatch.setenv("IGNITION_GPIO_PIN", "27")
    gpio_policy.reset_policy()
    policy = gpio_policy.get_policy()
    with pytest.raises(gpio_policy.PinDenied):
        policy.check(27, "output")
    assert policy.check(27, "input") == 27


@pytest.mark.parametrize("pin", [-1, 28, 40, 1000, "4", None, True])
def test_malformed_pins_are_invalid(pin):
    with pytest.raises(gpio_policy.PinInvalid):
        gpio_policy.get_policy().check(pin, "output")


@pytest.mark.parametrize("direction", ["both", "", None, "OUTPUT", 1])
def test_bad_direction_is_invalid(direction):
    with pytest.raises(gpio_policy.PinInvalid):
        gpio_policy.get_policy().check(22, direction)


def test_pin_outside_the_allowlist_is_denied(monkeypatch):
    monkeypatch.setenv("MIA_GPIO_ALLOWED_PINS", "4:io")
    gpio_policy.reset_policy()
    with pytest.raises(gpio_policy.PinDenied):
        gpio_policy.get_policy().check(5, "output")


# ── configuration overrides ───────────────────────────────────────────


def test_compact_env_override(monkeypatch):
    monkeypatch.setenv("MIA_GPIO_ALLOWED_PINS", "4:io, 5:o, 6:i")
    gpio_policy.reset_policy()
    policy = gpio_policy.get_policy()
    assert policy.as_dict() == {4: ["input", "output"], 5: ["output"], 6: ["input"]}
    with pytest.raises(gpio_policy.PinDenied):
        policy.check(5, "input")
    with pytest.raises(gpio_policy.PinDenied):
        policy.check(22, "output")  # default list is replaced, not extended


def test_yaml_file_override_wins_over_env(tmp_path, monkeypatch):
    path = tmp_path / "gpio.yaml"
    path.write_text("pins:\n  12: [input, output]\n  13: [input]\n")
    monkeypatch.setenv("MIA_GPIO_POLICY_FILE", str(path))
    monkeypatch.setenv("MIA_GPIO_ALLOWED_PINS", "4:io")
    gpio_policy.reset_policy()
    policy = gpio_policy.get_policy()
    assert policy.check(12, "output") == 12
    with pytest.raises(gpio_policy.PinDenied):
        policy.check(13, "output")
    with pytest.raises(gpio_policy.PinDenied):
        policy.check(4, "input")


@pytest.mark.parametrize(
    "text",
    ["pins:\n  2: [output]\n", "pins:\n  4: [sideways]\n", "pins:\n  99: [input]\n", "pins: []\n", "- not a mapping\n"],
)
def test_invalid_yaml_is_rejected(tmp_path, text):
    path = tmp_path / "gpio.yaml"
    path.write_text(text)
    with pytest.raises(gpio_policy.GPIOPolicyError):
        gpio_policy.build_policy({"MIA_GPIO_POLICY_FILE": str(path)})


@pytest.mark.parametrize("value", ["4", "4:x", "a:io", "4:", "2:o", "30:i"])
def test_invalid_compact_override_is_rejected(value):
    with pytest.raises(gpio_policy.GPIOPolicyError):
        gpio_policy.build_policy({"MIA_GPIO_ALLOWED_PINS": value})


def test_override_cannot_make_the_ignition_pin_an_output(monkeypatch):
    monkeypatch.setenv("MIA_GPIO_ALLOWED_PINS", "17:io,4:io")
    gpio_policy.reset_policy()
    with pytest.raises(gpio_policy.PinDenied):
        gpio_policy.get_policy().check(17, "output")


def test_invalid_config_fails_closed(monkeypatch):
    monkeypatch.setenv("MIA_GPIO_POLICY_FILE", "/nonexistent/gpio.yaml")
    gpio_policy.reset_policy()
    policy = gpio_policy.get_policy()
    for pin in (4, 17, 22):
        with pytest.raises(gpio_policy.PinDenied):
            policy.check_read(pin)


# ── API status codes ──────────────────────────────────────────────────


class FakeSocket:
    """Stands in for the API's ZMQ DEALER socket."""

    def __init__(self, reply=None):
        self.reply = reply
        self.sent = []
        self.closed = False

    def send_multipart(self, parts):
        self.sent.append(json.loads(parts[-1]))

    def recv_multipart(self):
        return [b"", json.dumps(self.reply).encode()]


class FakePoller:
    answer = True

    def register(self, *_args):
        pass

    def poll(self, _timeout):
        return [("sock", 1)] if FakePoller.answer else []


@pytest.fixture
def api(monkeypatch):
    for name in ("MIA_API_KEY", "MIA_API_KEYS", "MIA_AUTH_DISABLED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MIA_API_KEYS", API_KEY)
    deps._verified.clear()
    monkeypatch.setattr(deps, "_warned_open", False)
    monkeypatch.setattr(api_key_module, "_api_key_auth", api_key_module.APIKeyAuth())
    socket = FakeSocket({"type": "GPIO_SET_RESPONSE", "success": True})
    monkeypatch.setattr(api_main, "zmq_socket", socket)
    monkeypatch.setattr(api_main, "zmq", types.SimpleNamespace(Poller=FakePoller, POLLIN=1))
    FakePoller.answer = True
    client = TestClient(api_main.app, headers={"X-API-Key": API_KEY})
    client.socket = socket
    yield client
    deps._verified.clear()
    api_key_module._api_key_auth = None


def test_api_allowed_pin_reaches_the_worker(api):
    r = api.post("/gpio/configure", json={"pin": 22, "direction": "output"})
    assert r.status_code == 200 and r.json()["success"] is True
    r = api.post("/gpio/set", json={"pin": 22, "value": True})
    assert r.status_code == 200
    assert [m["type"] for m in api.socket.sent] == ["GPIO_CONFIGURE", "GPIO_SET"]


def test_api_ignition_pin_can_be_read(api):
    api.socket.reply = {"type": "GPIO_GET_RESPONSE", "pin": 17, "value": True, "success": True}
    r = api.get("/gpio/17")
    assert r.status_code == 200 and r.json()["response"]["value"] is True


@pytest.mark.parametrize("pin", [0, 1, 2, 3, 7, 8, 9, 10, 11, 14, 15])
def test_api_denies_reserved_pins_with_403_and_never_asks_the_worker(api, pin):
    assert api.post("/gpio/configure", json={"pin": pin, "direction": "output"}).status_code == 403
    assert api.post("/gpio/set", json={"pin": pin, "value": True}).status_code == 403
    assert api.get(f"/gpio/{pin}").status_code == 403
    assert api.socket.sent == []


def test_api_denies_output_on_the_ignition_pin(api):
    assert api.post("/gpio/configure", json={"pin": 17, "direction": "output"}).status_code == 403
    assert api.post("/gpio/set", json={"pin": 17, "value": False}).status_code == 403
    assert api.post("/gpio/configure", json={"pin": 17, "direction": "input"}).status_code == 200


@pytest.mark.parametrize(
    "path,body",
    [
        ("/gpio/configure", {"pin": 22, "direction": "sideways"}),
        ("/gpio/configure", {"pin": 22, "direction": None}),
        ("/gpio/configure", {"pin": 99, "direction": "output"}),
        ("/gpio/configure", {"pin": -1, "direction": "output"}),
        ("/gpio/configure", {"pin": "abc"}),
        ("/gpio/set", {"pin": 22}),
        ("/gpio/set", {"pin": 99, "value": True}),
    ],
)
def test_api_invalid_values_are_422(api, path, body):
    assert api.post(path, json=body).status_code == 422
    assert api.socket.sent == []


def test_api_get_out_of_range_pin_is_422(api):
    assert api.get("/gpio/99").status_code == 422
    assert api.get("/gpio/abc").status_code == 422


def test_api_worker_timeout_is_504_not_200(api):
    FakePoller.answer = False
    r = api.post("/gpio/set", json={"pin": 22, "value": True})
    assert r.status_code == 504
    assert api.get("/gpio/22").status_code == 504


def test_api_worker_error_is_502_and_worker_policy_denial_is_403(api):
    api.socket.reply = {"type": "ERROR", "error": "Failed to set pin 22: boom"}
    assert api.post("/gpio/set", json={"pin": 22, "value": True}).status_code == 502
    api.socket.reply = {"type": "ERROR", "error": gpio_policy.DENIED_PREFIX + "pin 22 does not allow output"}
    assert api.post("/gpio/set", json={"pin": 22, "value": True}).status_code == 403


def test_api_requires_the_key_before_the_policy(api):
    assert TestClient(api_main.app).post("/gpio/set", json={"pin": 2, "value": True}).status_code == 401


def test_api_policy_override_applies(api, monkeypatch):
    monkeypatch.setenv("MIA_GPIO_ALLOWED_PINS", "5:i")
    gpio_policy.reset_policy()
    assert api.post("/gpio/set", json={"pin": 22, "value": True}).status_code == 403
    assert api.post("/gpio/set", json={"pin": 5, "value": True}).status_code == 403
    assert api.get("/gpio/5").status_code == 200


# ── worker and simulation guards ──────────────────────────────────────


@pytest.fixture
def worker(monkeypatch):
    mod = importlib.import_module("hardware.gpio_worker")
    monkeypatch.setattr(mod, "GPIO_AVAILABLE", False)
    w = mod.GPIOWorker.__new__(mod.GPIOWorker)
    w.pin_states = {}
    w.sent = []

    class Sock:
        def send_multipart(self, parts):
            w.sent.append(json.loads(parts[-1]))

    w.socket = Sock()
    return w


def test_worker_refuses_denied_pins_and_directions(worker):
    worker._handle_message({"type": "GPIO_CONFIGURE", "pin": 2, "direction": "output"})
    worker._handle_message({"type": "GPIO_CONFIGURE", "pin": 17, "direction": "output"})
    worker._handle_message({"type": "GPIO_SET", "pin": 11, "value": True})
    worker._handle_message({"type": "GPIO_GET", "pin": 14})
    assert [m["type"] for m in worker.sent] == ["ERROR"] * 4
    assert all(m["error"].startswith(gpio_policy.DENIED_PREFIX) for m in worker.sent)
    assert worker.pin_states == {}


def test_worker_pin_zero_is_denied_not_missing(worker):
    worker._handle_message({"type": "GPIO_CONFIGURE", "pin": 0, "direction": "output"})
    assert "reserved" in worker.sent[0]["error"]


def test_worker_allows_a_configured_output_and_input_read_of_ignition(worker):
    worker._handle_message({"type": "GPIO_SET", "pin": 22, "value": True})
    assert worker.sent[-1]["type"] == "ERROR"  # not configured as output yet
    worker._handle_message({"type": "GPIO_CONFIGURE", "pin": 22, "direction": "output"})
    worker._handle_message({"type": "GPIO_SET", "pin": 22, "value": True})
    worker._handle_message({"type": "GPIO_GET", "pin": 17})
    assert [m["type"] for m in worker.sent[1:]] == ["GPIO_CONFIGURE_RESPONSE", "GPIO_SET_RESPONSE", "GPIO_GET_RESPONSE"]


@pytest.mark.asyncio
async def test_simulation_client_and_controller_are_guarded():
    from hardware.gpio import GPIOController, GPIOMode, SimulationGPIOClient

    client = SimulationGPIOClient()
    assert (await client.send_gpio_configure_request(2, "output"))["success"] is False
    assert (await client.send_gpio_configure_request(17, "output"))["success"] is False
    assert (await client.send_gpio_set_request(22, True))["success"] is False  # not configured
    assert (await client.send_gpio_get_request(9))["success"] is False
    assert client._pin_configs == {}

    gpio = GPIOController(simulation=True)
    await gpio.connect()
    with pytest.raises(gpio_policy.PinDenied):
        await gpio.configure_pin(3, GPIOMode.INPUT)
    with pytest.raises(gpio_policy.PinDenied):
        await gpio.configure_pin(17, GPIOMode.OUTPUT)
    assert await gpio.configure_pin(17, GPIOMode.INPUT) is True
    await gpio.disconnect()
