"""Test harness for service-discovery: ServiceRegistry and ServiceEntry.

Covers register/unregister/get/list, health-check TTL, duplicate registration,
stale service cleanup, and capability filtering.
"""

import importlib.util
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Module loading — mock aiohttp + websockets before load
# ---------------------------------------------------------------------------
sys.modules.setdefault("aiohttp", MagicMock())
sys.modules.setdefault("websockets", MagicMock())

import os

_SD_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "orchestration",
    "mcp",
    "modules",
    "service-discovery",
    "main.py",
)

_sd_spec = importlib.util.spec_from_file_location("service_discovery_main", _SD_PATH)
_sd_module = importlib.util.module_from_spec(_sd_spec)
_sd_module.__package__ = "modules.service_discovery"
sys.modules.setdefault("modules.service_discovery", MagicMock())
_sd_spec.loader.exec_module(_sd_module)

ServiceRegistry = _sd_module.ServiceRegistry
ServiceEntry = _sd_module.ServiceEntry


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestServiceEntry:
    """ServiceEntry dataclass defaults."""

    def test_last_heartbeat_auto_set(self):
        entry = ServiceEntry(name="svc", host="localhost", port=9000, capabilities=["read"])
        assert entry.last_heartbeat is not None
        assert isinstance(entry.last_heartbeat, datetime)

    def test_metadata_defaults_to_empty_dict(self):
        entry = ServiceEntry(name="svc", host="localhost", port=9000, capabilities=[])
        assert entry.metadata == {}

    def test_status_defaults_to_unknown(self):
        entry = ServiceEntry(name="svc", host="localhost", port=9000, capabilities=[])
        assert entry.status == "unknown"


@pytest.mark.unit
class TestServiceRegistryBasicOps:
    """Core register / unregister / get / list operations."""

    def setup_method(self):
        self.registry = ServiceRegistry()

    def test_register_service_returns_true(self):
        result = self.registry.register_service("audio", "localhost", 8001, ["audio", "tts"])
        assert result is True

    def test_registered_service_retrievable(self):
        self.registry.register_service("gpio", "10.0.0.1", 8002, ["gpio"])
        svc = self.registry.get_service("gpio")
        assert svc is not None
        assert svc.host == "10.0.0.1"
        assert svc.port == 8002

    def test_get_unknown_service_returns_none(self):
        assert self.registry.get_service("nonexistent") is None

    def test_duplicate_registration_returns_false(self):
        self.registry.register_service("dup", "localhost", 9999, [])
        result = self.registry.register_service("dup", "localhost", 9999, [])
        assert result is False

    def test_unregister_existing_returns_true(self):
        self.registry.register_service("temp", "localhost", 7777, [])
        assert self.registry.unregister_service("temp") is True
        assert self.registry.get_service("temp") is None

    def test_unregister_missing_returns_false(self):
        assert self.registry.unregister_service("ghost") is False

    def test_list_services_returns_all(self):
        self.registry.register_service("a", "h", 1, ["x"])
        self.registry.register_service("b", "h", 2, ["y"])
        services = self.registry.list_services()
        assert len(services) == 2

    def test_list_services_empty_initially(self):
        assert self.registry.list_services() == []


@pytest.mark.unit
class TestServiceRegistryCapabilityFilter:
    """list_services capability filtering."""

    def setup_method(self):
        self.registry = ServiceRegistry()
        self.registry.register_service("svc_a", "h", 1, ["audio", "tts"])
        self.registry.register_service("svc_b", "h", 2, ["gpio"])
        self.registry.register_service("svc_c", "h", 3, ["audio", "gpio"])

    def test_filter_returns_matching_services(self):
        audio_svcs = self.registry.list_services(capability_filter="audio")
        names = {s.name for s in audio_svcs}
        assert names == {"svc_a", "svc_c"}

    def test_filter_with_no_match_returns_empty(self):
        result = self.registry.list_services(capability_filter="bluetooth")
        assert result == []

    def test_no_filter_returns_all(self):
        assert len(self.registry.list_services()) == 3


@pytest.mark.unit
class TestServiceRegistryHealthCheck:
    """check_health() and TTL-based health state transitions."""

    def setup_method(self):
        self.registry = ServiceRegistry()

    def test_healthy_service_within_ttl(self):
        self.registry.register_service("fresh", "h", 1, [])
        # last_heartbeat was just set by __post_init__ — should be healthy
        health = self.registry.check_health()
        assert health["fresh"] == "healthy"

    def test_unhealthy_service_past_ttl(self):
        self.registry.register_service("old", "h", 2, [])
        # Manually backdate the heartbeat past the 30s TTL
        svc = self.registry.get_service("old")
        svc.last_heartbeat = datetime.now() - timedelta(seconds=60)
        health = self.registry.check_health()
        assert health["old"] == "unhealthy"

    def test_check_health_empty_registry(self):
        assert self.registry.check_health() == {}


@pytest.mark.unit
class TestServiceRegistryStaleCleanup:
    """cleanup_stale_services() removes services past 2× TTL."""

    def setup_method(self):
        self.registry = ServiceRegistry()

    def test_stale_service_removed(self):
        self.registry.register_service("stale", "h", 1, [])
        svc = self.registry.get_service("stale")
        svc.last_heartbeat = datetime.now() - timedelta(seconds=70)  # > 2×30s
        self.registry.cleanup_stale_services()
        assert self.registry.get_service("stale") is None

    def test_fresh_service_not_removed(self):
        self.registry.register_service("fresh", "h", 2, [])
        self.registry.cleanup_stale_services()
        assert self.registry.get_service("fresh") is not None

    @pytest.mark.asyncio
    async def test_heartbeat_marks_service_healthy(self):
        self.registry.register_service("beat", "h", 3, [])
        result = await self.registry.heartbeat("beat")
        assert result is True
        svc = self.registry.get_service("beat")
        assert svc.status == "healthy"

    @pytest.mark.asyncio
    async def test_heartbeat_unknown_service_returns_false(self):
        result = await self.registry.heartbeat("nobody")
        assert result is False
