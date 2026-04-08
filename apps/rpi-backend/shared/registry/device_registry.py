"""Compatibility wrapper for the shared device registry surface."""

from __future__ import annotations

import sys
from pathlib import Path


_PY_API_ROOT = Path(__file__).resolve().parents[2] / "py-api"
if str(_PY_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_API_ROOT))

from core.registry.device_registry import DeviceRegistry, get_registry, init_registry


__all__ = ["DeviceRegistry", "get_registry", "init_registry"]