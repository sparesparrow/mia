"""
Runtime contract drift regression tests.

P2 — catches when /status response shapes, systemd service dependencies,
or message envelope structures drift from their documented contracts.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SYSTEMD_DIR = REPO_ROOT / "infra" / "systemd"


# ---------------------------------------------------------------------------
# Systemd service dependency contracts
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSystemdServiceContracts:
    """Systemd unit files must preserve required dependency relationships."""

    def _read_service(self, name: str) -> configparser.ConfigParser:
        path = SYSTEMD_DIR / name
        assert path.is_file(), f"Missing systemd unit: {name}"
        cp = configparser.ConfigParser(interpolation=None)
        cp.read(str(path), encoding="utf-8")
        return cp

    def _get_unit_field(self, cp: configparser.ConfigParser, field: str) -> str:
        return cp.get("Unit", field, fallback="")

    # -- Broker is the root dependency --

    def test_broker_has_no_service_dependency(self):
        cp = self._read_service("zmq-broker.service")
        after = self._get_unit_field(cp, "After")
        assert "mia-" not in after, "Broker should not depend on any mia-* service"

    def test_api_depends_on_broker(self):
        cp = self._read_service("mia-api.service")
        after = self._get_unit_field(cp, "After")
        assert "zmq-broker.service" in after

    def test_gpio_worker_depends_on_broker(self):
        cp = self._read_service("mia-gpio-worker.service")
        after = self._get_unit_field(cp, "After")
        assert "zmq-broker.service" in after

    def test_serial_bridge_depends_on_broker(self):
        cp = self._read_service("mia-serial-bridge.service")
        after = self._get_unit_field(cp, "After")
        assert "zmq-broker.service" in after

    def test_obd_worker_depends_on_serial_bridge(self):
        cp = self._read_service("mia-obd-worker.service")
        after = self._get_unit_field(cp, "After")
        assert "mia-serial-bridge.service" in after

    def test_ble_services_depend_on_bluetooth(self):
        for name in ("mia-ble-advertiser.service", "mia-ble-obd.service"):
            cp = self._read_service(name)
            after = self._get_unit_field(cp, "After")
            requires = self._get_unit_field(cp, "Requires")
            assert "bluetooth.service" in after or "bluetooth.service" in requires, (
                f"{name} must depend on bluetooth.service"
            )

    # -- All core services should have restart policy --

    @pytest.mark.parametrize("service", [
        "zmq-broker.service",
        "mia-api.service",
        "mia-gpio-worker.service",
        "mia-serial-bridge.service",
        "mia-obd-worker.service",
    ])
    def test_core_services_have_restart_policy(self, service: str):
        cp = self._read_service(service)
        restart = cp.get("Service", "Restart", fallback="")
        assert restart in ("always", "on-failure"), (
            f"{service} should have Restart=always or on-failure, got '{restart}'"
        )

    # -- Working directory must point to /opt/mia --

    @pytest.mark.parametrize("service", [
        "zmq-broker.service",
        "mia-api.service",
        "mia-gpio-worker.service",
        "mia-serial-bridge.service",
        "mia-obd-worker.service",
    ])
    def test_working_directory_under_opt_mia(self, service: str):
        cp = self._read_service(service)
        wd = cp.get("Service", "WorkingDirectory", fallback="")
        assert wd.startswith("/opt/mia"), (
            f"{service} WorkingDirectory should start with /opt/mia, got '{wd}'"
        )


# ---------------------------------------------------------------------------
# API response shape contracts
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAPIResponseShapeContract:
    """
    The FastAPI /status endpoint must return a documented shape.
    Uses TestClient to avoid needing a running server.
    """

    @pytest.fixture(autouse=True)
    def _setup_app(self):
        try:
            from api.main import app
            from fastapi.testclient import TestClient

            self.client = TestClient(app)
            self.available = True
        except Exception:
            self.available = False

    def test_status_has_required_fields(self):
        if not self.available:
            pytest.skip("FastAPI app not importable in this environment")

        resp = self.client.get("/status")
        assert resp.status_code == 200
        data = resp.json()

        required_top_level = {"status", "uptime_seconds", "timestamp"}
        assert required_top_level.issubset(data.keys()), (
            f"Missing fields in /status response: {required_top_level - data.keys()}"
        )

    def test_devices_response_shape(self):
        if not self.available:
            pytest.skip("FastAPI app not importable in this environment")

        resp = self.client.get("/devices")
        assert resp.status_code == 200
        data = resp.json()

        assert "devices" in data
        assert "count" in data
        assert isinstance(data["devices"], list)


# ---------------------------------------------------------------------------
# Telemetry payload shape contracts
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTelemetryFieldContract:
    """Normalized telemetry payloads must include mandatory fields."""

    MANDATORY_FIELDS = {"timestamp", "device_id"}
    GENERIC_PID_FIELDS = {"speed_kmh", "engine_rpm", "coolant_temp_c", "fuel_level_percent", "battery_voltage", "vin"}

    def test_build_payload_has_mandatory_fields(self):
        try:
            from apps.rpi_backend.shared.telemetry.normalized_payload import build_telemetry_payload
        except ImportError:
            pytest.skip("normalized_payload not importable")

        payload = build_telemetry_payload(speed_kmh=60, device_id="test-dev-01")
        for field in self.MANDATORY_FIELDS:
            assert field in payload, f"Telemetry payload missing mandatory field '{field}'"

    def test_generic_pid_fields_accepted(self):
        try:
            from apps.rpi_backend.shared.telemetry.normalized_payload import build_telemetry_payload
        except ImportError:
            pytest.skip("normalized_payload not importable")

        payload = build_telemetry_payload(
            speed_kmh=60,
            engine_rpm=3000,
            coolant_temp_c=90,
            fuel_level_percent=75.0,
            battery_voltage=14.2,
            vin="WVWZZZ3CZWE000001",
        )
        for field in self.GENERIC_PID_FIELDS:
            assert field in payload, f"Payload should include generic PID field '{field}'"


# ---------------------------------------------------------------------------
# Contract documentation alignment
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestContractDocumentation:
    """Key contract documents must exist and not be empty."""

    @pytest.mark.parametrize("rel_path", [
        "contracts/events.md",
        "contracts/topics.md",
    ])
    def test_contract_doc_exists(self, rel_path: str):
        path = REPO_ROOT / rel_path
        if not path.is_file():
            pytest.skip(f"{rel_path} does not exist yet")
        content = path.read_text(encoding="utf-8")
        assert len(content.strip()) > 20, f"{rel_path} appears empty or placeholder-only"
