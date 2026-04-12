"""Compatibility wrapper for the shared device profile surface."""

from __future__ import annotations

import sys
from pathlib import Path


_PY_API_ROOT = Path(__file__).resolve().parents[2] / "py-api"
if str(_PY_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_API_ROOT))

from core.registry.device_profile import DEVICE_PROFILES, DeviceProfile, DeviceStatus, DeviceType


__all__ = ["DEVICE_PROFILES", "DeviceProfile", "DeviceStatus", "DeviceType"]