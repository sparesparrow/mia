"""Tests for the vehicle telemetry MCP server skeleton."""

import asyncio
import importlib.util
import os
import sys

import pytest


MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "orchestration",
    "mcp",
    "modules",
    "automotive-mcp-bridge",
    "vehicle_telemetry_server.py",
)

SPEC = importlib.util.spec_from_file_location("vehicle_telemetry_server", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["vehicle_telemetry_server"] = MODULE
assert SPEC is not None
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

VehicleTelemetryServer = MODULE.VehicleTelemetryServer
DTC = MODULE.DTC


class TestVehicleTelemetryServer:
    """Unit tests for VehicleTelemetryServer."""

    def setup_method(self):
        self.server = VehicleTelemetryServer()

    def test_tools_registered(self):
        assert "get_telemetry" in self.server.tools
        assert "get_dtc" in self.server.tools
        assert "clear_dtc" in self.server.tools

    def test_resources_registered(self):
        assert "vehicle://telemetry/live" in self.server.resources
        assert "vehicle://dtc/stored" in self.server.resources

    @pytest.mark.asyncio
    async def test_get_telemetry_returns_snapshot(self):
        result = await self.server.handle_get_telemetry({})
        assert result["status"] == "ok"
        assert "telemetry" in result
        telemetry = result["telemetry"]
        assert "timestamp" in telemetry
        assert "speed_kmh" in telemetry
        assert "engine_rpm" in telemetry

    @pytest.mark.asyncio
    async def test_get_telemetry_pid_filter(self):
        result = await self.server.handle_get_telemetry({"pids": ["speed_kmh"]})
        telemetry = result["telemetry"]
        assert "speed_kmh" in telemetry
        assert "engine_rpm" not in telemetry
        assert "timestamp" in telemetry

    @pytest.mark.asyncio
    async def test_get_dtc_empty(self):
        result = await self.server.handle_get_dtc({"severity_filter": "all"})
        assert result["status"] == "ok"
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_get_dtc_with_codes(self):
        self.server._stored_dtcs = [
            DTC(code="P0420", description="Catalyst efficiency below threshold", severity="warning"),
            DTC(code="P0300", description="Random misfire detected", severity="critical"),
        ]
        result = await self.server.handle_get_dtc({"severity_filter": "all"})
        assert result["count"] == 2

        result = await self.server.handle_get_dtc({"severity_filter": "critical"})
        assert result["count"] == 1
        assert result["dtcs"][0]["code"] == "P0300"

    @pytest.mark.asyncio
    async def test_clear_dtc_requires_confirmation(self):
        self.server._stored_dtcs = [DTC(code="P0420", description="test", severity="info")]
        result = await self.server.handle_clear_dtc({"confirm": False})
        assert result["status"] == "error"
        assert len(self.server._stored_dtcs) == 1

    @pytest.mark.asyncio
    async def test_clear_dtc_confirmed(self):
        self.server._stored_dtcs = [DTC(code="P0420", description="test", severity="info")]
        result = await self.server.handle_clear_dtc({"confirm": True})
        assert result["status"] == "ok"
        assert result["cleared_count"] == 1
        assert len(self.server._stored_dtcs) == 0

    @pytest.mark.asyncio
    async def test_polling_lifecycle(self):
        await self.server.start_polling(interval_s=0.1)
        assert self.server._polling_task is not None
        await asyncio.sleep(0.25)
        await self.server.stop_polling()
        assert self.server._polling_task is None