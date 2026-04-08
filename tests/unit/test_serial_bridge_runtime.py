"""Focused unit tests for serial bridge runtime helpers."""

import importlib.util
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