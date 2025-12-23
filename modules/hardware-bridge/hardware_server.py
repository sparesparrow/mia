"""
MIA Hardware MCP Server

Exposes hardware control capabilities to Cursor MCP.
Provides tools for GPIO control, OBD diagnostics, and RF communication.
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from tinymcp import MCPServer
from .hardware_tools import HardwareTools

logger = logging.getLogger(__name__)


class MIAHardwareMCPServer:
    """MCP Server for MIA hardware control"""

    def __init__(self):
        self.tools = HardwareTools()
        self.mcp_server = MCPServer("mia-hardware")
        self._setup_tools()

        # Set up logging
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(level=getattr(logging, log_level))

    def _setup_tools(self):
        """Set up MCP tools"""

        @self.mcp_server.tool("set_gpio_pin")
        async def set_gpio_pin(pin: int, state: bool, mode: str = "OUTPUT") -> Dict[str, Any]:
            """Control GPIO pins - LED lights, relays, sensors"""
            return await self.tools.set_gpio_pin(pin, state, mode)

        @self.mcp_server.tool("query_obd")
        async def query_obd(pid: str, service: str = "CURRENT_DATA") -> Dict[str, Any]:
            """Query vehicle diagnostics - speed, engine data, DTCs"""
            return await self.tools.query_obd(pid, service)

        @self.mcp_server.tool("start_rf_capture")
        async def start_rf_capture(frequency: int = 433920000,
                                 modulation: str = "FSK",
                                 duration_ms: int = 10000) -> Dict[str, Any]:
            """Capture RF signals - remote controls, sensors"""
            return await self.tools.start_rf_capture(frequency, modulation, duration_ms)

        @self.mcp_server.tool("replay_rf_signal")
        async def replay_rf_signal(frame_data: list,
                                 frequency: int = 433920000,
                                 modulation: str = "FSK") -> Dict[str, Any]:
            """Replay RF signals - garage doors, car remotes"""
            return await self.tools.replay_rf_signal(frame_data, frequency, modulation)

        @self.mcp_server.tool("get_vehicle_status")
        async def get_vehicle_status() -> Dict[str, Any]:
            """Get comprehensive vehicle status including speed, RPM, temperature, and fuel level"""
            return await self.tools.get_vehicle_status()

        @self.mcp_server.tool("control_interior_lights")
        async def control_interior_lights(state: bool) -> Dict[str, Any]:
            """Control interior cabin lighting"""
            return await self.tools.control_interior_lights(state)

        @self.mcp_server.tool("check_engine_diagnostics")
        async def check_engine_diagnostics() -> Dict[str, Any]:
            """Check for engine trouble codes and diagnostic information"""
            return await self.tools.check_engine_diagnostics()

    async def serve(self):
        """Start the MCP server"""
        logger.info("Starting MIA Hardware MCP Server")
        try:
            await self.mcp_server.serve()
        except KeyboardInterrupt:
            logger.info("MIA Hardware MCP Server shutting down")
        finally:
            self.tools.cleanup()


async def main():
    """Main entry point"""
    server = MIAHardwareMCPServer()
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())