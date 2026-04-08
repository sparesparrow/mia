"""Focused tests for the Citroen bridge helper parsing functions."""

import importlib.util
import sys
from pathlib import Path


def load_citroen_bridge_module():
    """Import the bridge script module for unit testing."""
    module_path = Path(__file__).resolve().parents[2] / "orchestration" / "mia-agents" / "agents" / "citroen_bridge.py"
    spec = importlib.util.spec_from_file_location("mia_citroen_bridge", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_decode_hex_measurement_parses_valid_payload():
    """Valid OBD payloads should be decoded into engineering units."""
    module = load_citroen_bridge_module()

    rpm = module.decode_hex_measurement("41 0C 1F40", "410C", "rpm", lambda value: value / 4.0)

    assert rpm == 2000.0


def test_decode_hex_measurement_returns_zero_on_invalid_hex(caplog):
    """Malformed payloads should return the existing zero default and emit a warning."""
    module = load_citroen_bridge_module()

    with caplog.at_level("WARNING"):
        coolant = module.decode_hex_measurement("41 05 GG", "4105", "coolant", lambda value: float(value - 40))

    assert coolant == 0.0
    assert "Failed to parse coolant" in caplog.text