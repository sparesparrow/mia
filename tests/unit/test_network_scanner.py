"""Focused tests for the network scanner script."""

import importlib.util
import sys
import urllib.request
from pathlib import Path


def load_network_scanner_module():
    """Import the scanner script module for unit testing."""
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "network_scanner.py"
    spec = importlib.util.spec_from_file_location("network_scanner", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_get_local_subnet_falls_back_when_ip_command_fails(monkeypatch):
    """Subnet discovery should fall back instead of crashing when ip route is unavailable."""
    module = load_network_scanner_module()
    scanner = module.MIANetworkScanner()

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ip command missing")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert scanner.get_local_subnet() == "192.168.1"


def test_parse_json_payload_rejects_invalid_json():
    """Malformed device responses should be ignored cleanly."""
    module = load_network_scanner_module()

    assert module.MIANetworkScanner._parse_json_payload("not-json", "device") is None


def test_scan_known_ip_counts_scanned_host_when_device_found(monkeypatch):
    """Direct known-IP scans should always report one scanned host."""
    module = load_network_scanner_module()
    scanner = module.MIANetworkScanner()

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"status": "ok", "uptime": 123, "heap": 456}'

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse())

    result = scanner.scan_known_ip("192.168.1.10")

    assert result.devices_scanned == 1
    assert result.esp32_devices[0]["ip"] == "192.168.1.10"
