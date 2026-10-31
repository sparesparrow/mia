"""Ignition falling edge triggers the shutdown path in services/power_monitor.py (mocked, never powers off)."""

import importlib.util
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

pytestmark = pytest.mark.req("REQ-CAR-001")

MODULE = Path(__file__).resolve().parents[3] / "apps" / "rpi-backend" / "py-api" / "services" / "power_monitor.py"


@pytest.fixture
def pm(monkeypatch):
    """Load power_monitor with a fake RPi.GPIO so the real monitor_gpio() code path runs."""
    gpio = types.SimpleNamespace(
        BCM="BCM",
        IN="IN",
        PUD_UP="PUD_UP",
        FALLING="FALLING",
        LOW=0,
        HIGH=1,
        level=0,
        callback=None,
        bouncetime=None,
        edge_pin=None,
        edge=None,
        pull=None,
    )
    gpio.setmode = mock.Mock()
    gpio.setup = lambda pin, mode, pull_up_down=None: setattr(gpio, "pull", pull_up_down)
    gpio.input = lambda pin: gpio.level
    gpio.cleanup = mock.Mock()

    def add_event_detect(pin, edge, callback=None, bouncetime=None):
        gpio.edge_pin, gpio.edge, gpio.callback, gpio.bouncetime = pin, edge, callback, bouncetime

    gpio.add_event_detect = add_event_detect
    rpi = types.ModuleType("RPi")
    rpi.GPIO = gpio
    monkeypatch.setitem(sys.modules, "RPi", rpi)
    monkeypatch.setitem(sys.modules, "RPi.GPIO", gpio)
    monkeypatch.delenv("IGNITION_GPIO_PIN", raising=False)
    spec = importlib.util.spec_from_file_location("mia_power_monitor_under_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.signal, "pause", lambda: None)
    monkeypatch.setattr(module.time, "sleep", lambda _s: None)
    module.fake_gpio = gpio
    return module


def test_watches_bcm17_with_pull_up_on_the_falling_edge(pm):
    pm.monitor_gpio()
    g = pm.fake_gpio
    assert (g.edge_pin, g.edge, g.pull) == (17, "FALLING", "PUD_UP")
    assert g.bouncetime == int(pm.DEBOUNCE_SECONDS * 1000)


def test_stable_low_publishes_notice_then_powers_off_once(pm):
    with mock.patch.object(pm.subprocess, "run") as run, mock.patch.object(pm, "publish_shutdown_notice") as notice:
        pm.monitor_gpio()
        g = pm.fake_gpio
        g.level = g.LOW
        g.callback(17)
        g.callback(17)  # a second edge must not repeat the shutdown
    notice.assert_called_once()
    run.assert_called_once_with(["systemctl", "poweroff"], check=False)


def test_glitch_that_returns_high_does_not_power_off(pm):
    with mock.patch.object(pm.subprocess, "run") as run, mock.patch.object(pm, "publish_shutdown_notice") as notice:
        pm.monitor_gpio()
        g = pm.fake_gpio
        g.level = g.HIGH
        g.callback(17)
    notice.assert_not_called()
    run.assert_not_called()


def test_shutdown_notice_precedes_poweroff(pm):
    order = []
    with mock.patch.object(
        pm, "publish_shutdown_notice", side_effect=lambda: order.append("notice")
    ), mock.patch.object(pm.subprocess, "run", side_effect=lambda *a, **k: order.append("poweroff")):
        pm.monitor_gpio()
        pm.fake_gpio.level = pm.fake_gpio.LOW
        pm.fake_gpio.callback(17)
    assert order == ["notice", "poweroff"]


def test_simulation_mode_never_calls_poweroff(pm, monkeypatch):
    handlers = {}
    monkeypatch.setattr(pm.signal, "signal", lambda sig, fn: handlers.setdefault(sig, fn))
    with mock.patch.object(pm.subprocess, "run") as run, mock.patch.object(pm, "publish_shutdown_notice") as notice:
        pm.monitor_simulation()
        with pytest.raises(SystemExit):
            handlers[pm.signal.SIGTERM](pm.signal.SIGTERM, None)
    notice.assert_called_once()
    run.assert_not_called()
