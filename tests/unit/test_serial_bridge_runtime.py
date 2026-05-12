"""Focused unit tests for serial bridge runtime helpers."""

import importlib.util
import json
import sys
from pathlib import Path


def load_serial_bridge_module():
    """Import the serial_bridge module directly for unit testing."""
    module_path = Path(__file__).resolve().parents[2] / "apps" / "rpi-backend" / "py-api" / "hardware" / "serial_bridge.py"
    spec = importlib.util.spec_from_file_location("mia_serial_bridge", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_find_serial_device_returns_none_when_enumeration_fails(monkeypatch):
    """Serial enumeration failures should not crash auto-detection."""
    module = load_serial_bridge_module()
    bridge = module.SerialBridge()

    monkeypatch.setattr(module.os.path, "exists", lambda path: False)
    monkeypatch.setattr(module.serial.tools.list_ports, "comports", lambda: (_ for _ in ()).throw(OSError("usb unavailable")))

    assert bridge._find_serial_device() is None


def test_safe_close_serial_clears_reference_on_close_error():
    """Closing a broken serial handle should not raise and should clear bridge state."""
    module = load_serial_bridge_module()
    bridge = module.SerialBridge()

    class BrokenSerial:
        def close(self):
            raise OSError("device vanished")

    bridge._serial = BrokenSerial()
    bridge._safe_close_serial()

    assert bridge._serial is None


def test_detect_adapter_kind_returns_unknown_when_port_scan_fails(monkeypatch):
    """Adapter kind detection should degrade to unknown when port inspection fails."""
    module = load_serial_bridge_module()
    monkeypatch.setattr(module.serial.tools.list_ports, "comports", lambda: (_ for _ in ()).throw(OSError("scan failed")))

    assert module.SerialBridge._detect_adapter_kind("/dev/ttyUSB0") == "unknown"


# ── Simulation mode tests ─────────────────────────────────────────────


def test_simulation_serial_source_produces_valid_json():
    """SimulationSerialSource.readline() returns valid JSON with expected fields."""
    module = load_serial_bridge_module()
    source = module.SimulationSerialSource(interval=0.0)

    line = source.readline()
    data = json.loads(line.decode())

    assert data["device_id"] == "simulation_0"
    assert "timestamp" in data
    assert "speed_kmh" in data
    assert "engine_rpm" in data
    assert "coolant_temp_c" in data
    assert "fuel_level_percent" in data
    assert "battery_voltage" in data
    assert source.is_open is True


def test_simulation_serial_source_values_vary():
    """Consecutive reads from SimulationSerialSource should produce different values."""
    module = load_serial_bridge_module()
    source = module.SimulationSerialSource(interval=0.0)

    readings = [json.loads(source.readline().decode()) for _ in range(5)]
    rpms = [r["engine_rpm"] for r in readings]
    assert len(set(rpms)) > 1, "RPM values should vary across reads"


def test_connect_serial_returns_simulation_when_forced(monkeypatch):
    """simulation=True should bypass hardware detection entirely."""
    module = load_serial_bridge_module()
    bridge = module.SerialBridge(simulation=True)

    # Stub pub_socket to capture messages
    sent = []
    bridge.pub_socket = type("FakeSocket", (), {
        "send_multipart": lambda self, parts: sent.append(parts),
        "bind": lambda self, ep: None,
        "close": lambda self: None,
    })()

    result = bridge._connect_serial()

    assert isinstance(result, module.SimulationSerialSource)
    assert bridge.simulation_mode is True
    assert bridge._adapter_kind == "simulation"
    assert len(sent) == 1
    status = json.loads(sent[0][1])
    assert status["event"] == "connected"
    assert status["simulation"] is True


def test_connect_serial_auto_falls_back_to_simulation(monkeypatch):
    """simulation=None should fall back when no hardware is found."""
    module = load_serial_bridge_module()
    bridge = module.SerialBridge(simulation=None)

    monkeypatch.setattr(module.os.path, "exists", lambda path: False)
    monkeypatch.setattr(module.serial.tools.list_ports, "comports", lambda: [])

    sent = []
    bridge.pub_socket = type("FakeSocket", (), {
        "send_multipart": lambda self, parts: sent.append(parts),
        "bind": lambda self, ep: None,
        "close": lambda self: None,
    })()

    result = bridge._connect_serial()

    assert isinstance(result, module.SimulationSerialSource)
    assert bridge.simulation_mode is True


def test_connect_serial_no_fallback_when_simulation_disabled(monkeypatch):
    """simulation=False should return None when hardware is absent."""
    module = load_serial_bridge_module()
    bridge = module.SerialBridge(simulation=False)

    monkeypatch.setattr(module.os.path, "exists", lambda path: False)
    monkeypatch.setattr(module.serial.tools.list_ports, "comports", lambda: [])

    result = bridge._connect_serial()

    assert result is None
    assert bridge.simulation_mode is False


def test_adapter_metadata_reports_simulation_transport():
    """Adapter metadata should indicate simulation transport when in sim mode."""
    module = load_serial_bridge_module()
    bridge = module.SerialBridge(simulation=True)
    bridge.simulation_mode = True
    bridge._adapter_kind = "simulation"
    bridge._device_path = "simulation"

    meta = bridge._build_adapter_metadata()

    assert meta["transport"] == "simulation"
    assert meta["adapter_kind"] == "simulation"
