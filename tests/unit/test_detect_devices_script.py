"""Focused tests for the detect_devices script."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def load_detect_devices_module():
    """Import the detect_devices script module for unit testing."""
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "detect_devices.py"
    spec = importlib.util.spec_from_file_location("detect_devices_script", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_summary_counts_platforms():
    """The device summary should recompute per-platform counts accurately."""
    module = load_detect_devices_module()

    summary = module.build_summary(
        [
            {"platform": "esp32"},
            {"platform": "esp32"},
            {"platform": "android"},
            {"platform": "rpi"},
        ]
    )

    assert summary == {
        "total_devices": 4,
        "esp32_devices": 2,
        "android_devices": 1,
        "rpi_devices": 1,
    }


def test_get_android_model_returns_unknown_on_subprocess_error(monkeypatch):
    """ADB model lookup should fall back cleanly when subprocess calls fail."""
    module = load_detect_devices_module()

    def fake_run(*args, **kwargs):
        raise OSError("adb missing")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.get_android_model("device-1") == "Unknown"


@pytest.mark.asyncio
async def test_check_raspberry_pi_returns_none_on_connection_failure(monkeypatch):
    """Host probes should return None when sockets fail instead of raising."""
    module = load_detect_devices_module()

    async def fake_open_connection(*args, **kwargs):
        raise ConnectionRefusedError("unreachable")

    monkeypatch.setattr(module.asyncio, "open_connection", fake_open_connection)

    assert await module.check_raspberry_pi("192.168.1.10") is None
