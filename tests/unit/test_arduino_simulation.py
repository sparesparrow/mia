"""Unit tests for Arduino controller simulation mode."""

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


def load_arduino_module():
    """Import the arduino module directly for unit testing."""
    module_path = Path(__file__).resolve().parents[2] / "apps" / "rpi-backend" / "py-api" / "hardware" / "arduino.py"
    spec = importlib.util.spec_from_file_location("mia_arduino", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# ── SimulationSerial tests ────────────────────────────────────────────


def test_simulation_serial_handshake():
    """SimulationSerial should respond to MIA_HANDSHAKE with MIA_READY."""
    module = load_arduino_module()
    ser = module.SimulationSerial()

    ser.write(b"MIA_HANDSHAKE\n")
    response = ser.readline()

    assert b"MIA_READY" in response
    assert ser.is_open is True


def test_simulation_serial_ping():
    """SimulationSerial should respond to MIA_PING with MIA_PONG."""
    module = load_arduino_module()
    ser = module.SimulationSerial()

    ser.write(b"MIA_PING\n")
    response = ser.readline()

    assert b"MIA_PONG" in response


def test_simulation_serial_arbitrary_command():
    """SimulationSerial should echo OK: for unknown commands."""
    module = load_arduino_module()
    ser = module.SimulationSerial()

    ser.write(b"LED_SET pin:13,value:1\n")
    response = ser.readline().decode()

    assert response.startswith("OK:")


def test_simulation_serial_close():
    """Close should mark the connection as not open."""
    module = load_arduino_module()
    ser = module.SimulationSerial()
    assert ser.is_open is True

    ser.close()
    assert ser.is_open is False


# ── ArduinoController simulation discover tests ──────────────────────


@pytest.mark.asyncio
async def test_discover_returns_simulated_device_when_forced():
    """simulation=True should return a simulated device without scanning ports."""
    module = load_arduino_module()
    ctrl = module.ArduinoController(simulation=True)

    devices = await ctrl.discover_devices()

    assert len(devices) == 1
    assert devices[0].port == "simulation"
    assert "simulation" in devices[0].capabilities
    assert ctrl.simulation_mode is True


@pytest.mark.asyncio
async def test_discover_falls_back_when_no_hardware(monkeypatch):
    """simulation=None should fall back to simulation when no ports match."""
    module = load_arduino_module()
    ctrl = module.ArduinoController(simulation=None)

    monkeypatch.setattr(module.serial.tools.list_ports, "comports", lambda: [])

    devices = await ctrl.discover_devices()

    assert len(devices) == 1
    assert devices[0].port == "simulation"
    assert ctrl.simulation_mode is True


@pytest.mark.asyncio
async def test_discover_no_fallback_when_disabled(monkeypatch):
    """simulation=False should return empty list when no hardware found."""
    module = load_arduino_module()
    ctrl = module.ArduinoController(simulation=False)

    monkeypatch.setattr(module.serial.tools.list_ports, "comports", lambda: [])

    devices = await ctrl.discover_devices()

    assert devices == []
    assert ctrl.simulation_mode is False


# ── ArduinoController simulation connect tests ───────────────────────


@pytest.mark.asyncio
async def test_connect_simulation_device():
    """Connecting to 'simulation' port should use SimulationSerial."""
    module = load_arduino_module()
    ctrl = module.ArduinoController(simulation=True)

    await ctrl.discover_devices()
    success = await ctrl.connect_device("simulation")

    assert success is True
    assert "simulation" in ctrl.connections
    assert isinstance(ctrl.connections["simulation"], module.SimulationSerial)


@pytest.mark.asyncio
async def test_send_command_to_simulation():
    """Commands to a simulated device should return OK responses."""
    module = load_arduino_module()
    ctrl = module.ArduinoController(simulation=True)

    await ctrl.discover_devices()
    await ctrl.connect_device("simulation")

    response = await ctrl.send_command("simulation", "LED_SET", pin=13, value=1)

    assert response is not None
    assert "OK:" in response


@pytest.mark.asyncio
async def test_disconnect_simulation_device():
    """Disconnecting a simulated device should clean up correctly."""
    module = load_arduino_module()
    ctrl = module.ArduinoController(simulation=True)

    await ctrl.discover_devices()
    await ctrl.connect_device("simulation")
    success = await ctrl.disconnect_device("simulation")

    assert success is True
    assert "simulation" not in ctrl.connections
