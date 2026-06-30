#!/usr/bin/env python3
"""
VehicleTelemetryServer - MCP server for real-time vehicle telemetry and diagnostics.

Exposes OBD-II data, DTC management, and live sensor readings through the MCP protocol.
Designed for Citroen C4 PSA but supports generic OBD-II as fallback.
"""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from mcp_framework import MCPServer, Resource, Tool  # noqa: E402


logger = logging.getLogger(__name__)


@dataclass
class TelemetrySnapshot:
    """Point-in-time vehicle telemetry reading."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    speed_kmh: float = 0.0
    engine_rpm: float = 0.0
    coolant_temp_c: float = 0.0
    battery_voltage: float = 0.0
    fuel_level_pct: float = 0.0
    intake_air_temp_c: float = 0.0
    throttle_pct: float = 0.0
    dpf_soot_mass_g: Optional[float] = None
    eolys_level_l: Optional[float] = None
    dpf_differential_pressure_kpa: Optional[float] = None


@dataclass
class DTC:
    """Diagnostic Trouble Code."""

    code: str
    description: str
    severity: str
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    freeze_frame: Optional[Dict[str, Any]] = None


class VehicleTelemetryServer(MCPServer):
    """MCP server exposing vehicle telemetry and DTC management tools."""

    def __init__(
        self,
        name: str = "vehicle-telemetry",
        version: str = "0.1.0",
        obd_source: Optional[Any] = None,
    ):
        super().__init__(name, version)
        self.obd_source = obd_source
        self._latest_telemetry = TelemetrySnapshot()
        self._stored_dtcs: List[DTC] = []
        self._polling_task: Optional[asyncio.Task] = None

        self._register_tools()
        self._register_resources()

        logger.info("VehicleTelemetryServer initialized: %s v%s", name, version)

    def _register_tools(self) -> None:
        self.add_tool(
            Tool(
                name="get_telemetry",
                description="Get current vehicle telemetry snapshot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of telemetry fields to return.",
                        }
                    },
                    "required": [],
                },
                handler=self.handle_get_telemetry,
            )
        )

        self.add_tool(
            Tool(
                name="get_dtc",
                description="Read stored diagnostic trouble codes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "severity_filter": {
                            "type": "string",
                            "enum": ["info", "warning", "critical", "all"],
                            "description": "Filter DTCs by severity. Defaults to all.",
                        }
                    },
                    "required": [],
                },
                handler=self.handle_get_dtc,
            )
        )

        self.add_tool(
            Tool(
                name="clear_dtc",
                description="Clear stored diagnostic trouble codes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "confirm": {
                            "type": "boolean",
                            "description": "Must be true to clear stored DTCs.",
                        }
                    },
                    "required": ["confirm"],
                },
                handler=self.handle_clear_dtc,
            )
        )

    def _register_resources(self) -> None:
        self.add_resource(
            Resource(
                uri="vehicle://telemetry/live",
                name="Live Telemetry",
                description="Real-time vehicle telemetry stream",
                mimeType="application/json",
            )
        )
        self.add_resource(
            Resource(
                uri="vehicle://dtc/stored",
                name="Stored DTCs",
                description="Currently stored diagnostic trouble codes",
                mimeType="application/json",
            )
        )

    async def handle_get_telemetry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the current telemetry snapshot, optionally filtered by field name."""
        requested_pids = arguments.get("pids", [])
        snapshot = await self._read_telemetry()

        data = {
            "timestamp": snapshot.timestamp,
            "speed_kmh": snapshot.speed_kmh,
            "engine_rpm": snapshot.engine_rpm,
            "coolant_temp_c": snapshot.coolant_temp_c,
            "battery_voltage": snapshot.battery_voltage,
            "fuel_level_pct": snapshot.fuel_level_pct,
            "intake_air_temp_c": snapshot.intake_air_temp_c,
            "throttle_pct": snapshot.throttle_pct,
        }

        if snapshot.dpf_soot_mass_g is not None:
            data["dpf_soot_mass_g"] = snapshot.dpf_soot_mass_g
        if snapshot.eolys_level_l is not None:
            data["eolys_level_l"] = snapshot.eolys_level_l
        if snapshot.dpf_differential_pressure_kpa is not None:
            data["dpf_differential_pressure_kpa"] = snapshot.dpf_differential_pressure_kpa

        if requested_pids:
            data = {key: value for key, value in data.items() if key in requested_pids or key == "timestamp"}

        return {"status": "ok", "telemetry": data}

    async def handle_get_dtc(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return stored DTCs, optionally filtered by severity."""
        severity_filter = arguments.get("severity_filter", "all")
        dtcs = self._stored_dtcs
        if severity_filter != "all":
            dtcs = [dtc for dtc in dtcs if dtc.severity == severity_filter]

        return {
            "status": "ok",
            "count": len(dtcs),
            "dtcs": [
                {
                    "code": dtc.code,
                    "description": dtc.description,
                    "severity": dtc.severity,
                    "first_seen": dtc.first_seen,
                    "freeze_frame": dtc.freeze_frame,
                }
                for dtc in dtcs
            ],
        }

    async def handle_clear_dtc(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Clear stored DTCs only when explicit confirmation is present."""
        if not arguments.get("confirm"):
            return {"status": "error", "message": "confirm must be true to clear DTCs"}

        cleared_count = len(self._stored_dtcs)

        if self.obd_source:
            # TODO: Send Mode 04 clear to a real ECU or digital twin backend.
            pass

        self._stored_dtcs.clear()
        logger.info("Cleared %s DTCs", cleared_count)
        return {"status": "ok", "cleared_count": cleared_count}

    async def _read_telemetry(self) -> TelemetrySnapshot:
        """Read telemetry from a backing source or return the simulation snapshot."""
        if self.obd_source:
            # TODO: Wire this into the obd_worker or Citroen bridge when the live source is ready.
            pass

        self._latest_telemetry.timestamp = datetime.now().isoformat()
        return self._latest_telemetry

    async def start_polling(self, interval_s: float = 1.0) -> None:
        """Start a background polling loop for refreshing telemetry."""
        if self._polling_task and not self._polling_task.done():
            return

        async def _poll() -> None:
            while True:
                try:
                    self._latest_telemetry = await self._read_telemetry()
                except Exception as exc:
                    logger.error("Telemetry poll error: %s", exc)
                await asyncio.sleep(interval_s)

        self._polling_task = asyncio.create_task(_poll())
        logger.info("Telemetry polling started (%ss interval)", interval_s)

    async def stop_polling(self) -> None:
        """Stop the background polling loop."""
        if self._polling_task:
            self._polling_task.cancel()
            self._polling_task = None


async def main() -> None:
    server = VehicleTelemetryServer()
    await server.start_polling()

    telemetry = await server.handle_get_telemetry({})
    logger.info("Self-test telemetry: %s", telemetry)

    dtcs = await server.handle_get_dtc({"severity_filter": "all"})
    logger.info("Self-test DTCs: %s", dtcs)

    await server.stop_polling()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())