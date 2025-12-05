"""
MIA Universal: Service Discovery MCP Server
Handles automatic service registration and health checking
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import websockets

# Import our MCP framework
from mcp_framework import (
    MCPServer, MCPClient, MCPMessage, MCPTransport,
    WebSocketTransport, Tool, create_tool
)


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceEntry:
    """Service registration entry"""
    name: str
    host: str
    port: int
    capabilities: List[str]
    health_endpoint: Optional[str] = None
    last_heartbeat: datetime = None
    status: str = "unknown"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class ServiceRegistry:
    """Service registry for automatic discovery"""

    def __init__(self):
        self.services: Dict[str, ServiceEntry] = {}
        self.heartbeat_timeout = timedelta(seconds=30)  # Services must heartbeat every 30s

    def register_service(self, name: str, host: str, port: int,
                        capabilities: List[str], health_endpoint: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register a new service"""
        if name in self.services:
            logger.warning(f"Service {name} already registered, updating...")
            return False

        entry = ServiceEntry(
            name=name,
            host=host,
            port=port,
            capabilities=capabilities,
            health_endpoint=health_endpoint,
            metadata=metadata or {}
        )

        self.services[name] = entry
        logger.info(f"Registered service: {name} at {host}:{port}")
        return True

    def update_service(self, name: str, **kwargs) -> bool:
        """Update service information"""
        if name not in self.services:
            return False

        entry = self.services[name]
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.last_heartbeat = datetime.now()
        return True

    def unregister_service(self, name: str) -> bool:
        """Unregister a service"""
        if name in self.services:
            del self.services[name]
            logger.info(f"Unregistered service: {name}")
            return True
        return False

    def get_service(self, name: str) -> Optional[ServiceEntry]:
        """Get service information"""
        return self.services.get(name)

    def list_services(self, capability_filter: Optional[str] = None) -> List[ServiceEntry]:
        """List all registered services"""
        services = list(self.services.values())

        if capability_filter:
            services = [s for s in services if capability_filter in s.capabilities]

        return services

    def check_health(self) -> Dict[str, str]:
        """Check health of all services"""
        results = {}
        now = datetime.now()

        for name, service in self.services.items():
            if now - service.last_heartbeat > self.heartbeat_timeout:
                service.status = "unhealthy"
            else:
                service.status = "healthy"
            results[name] = service.status

        return results

    async def heartbeat(self, name: str) -> bool:
        """Process heartbeat from service"""
        if name in self.services:
            self.services[name].last_heartbeat = datetime.now()
            self.services[name].status = "healthy"
            return True
        return False

    def cleanup_stale_services(self):
        """Remove services that haven't sent heartbeats"""
        now = datetime.now()
        stale_services = []

        for name, service in self.services.items():
            if now - service.last_heartbeat > self.heartbeat_timeout * 2:
                stale_services.append(name)

        for name in stale_services:
            logger.warning(f"Removing stale service: {name}")
            del self.services[name]


class ServiceDiscoveryMCP(MCPServer):
    """Service Discovery MCP Server"""

    def __init__(self):
        super().__init__("service-discovery", "1.0.0")
        self.registry = ServiceRegistry()
        self.setup_tools()
        self._start_cleanup_task()

    def setup_tools(self):
        """Setup service discovery tools"""

        # Service registration
        register_tool = create_tool(
            name="register_service",
            description="Register a new service with the discovery system",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Service name"},
                    "host": {"type": "string", "description": "Service host"},
                    "port": {"type": "integer", "description": "Service port"},
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of service capabilities"
                    },
                    "health_endpoint": {"type": "string", "description": "Health check endpoint"},
                    "metadata": {"type": "object", "description": "Additional metadata"}
                },
                "required": ["name", "host", "port", "capabilities"]
            },
            handler=self.handle_register_service
        )
        self.add_tool(register_tool)

        # Service discovery
        discover_tool = create_tool(
            name="discover_services",
            description="Discover available services",
            schema={
                "type": "object",
                "properties": {
                    "capability": {"type": "string", "description": "Filter by capability"}
                }
            },
            handler=self.handle_discover_services
        )
        self.add_tool(discover_tool)

        # Service heartbeat
        heartbeat_tool = create_tool(
            name="service_heartbeat",
            description="Send heartbeat to keep service alive",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Service name"}
                },
                "required": ["name"]
            },
            handler=self.handle_heartbeat
        )
        self.add_tool(heartbeat_tool)

        # Health check
        health_tool = create_tool(
            name="check_service_health",
            description="Check health status of all services",
            schema={"type": "object", "properties": {}},
            handler=self.handle_health_check
        )
        self.add_tool(health_tool)

    async def handle_register_service(self, name: str, host: str, port: int,
                                    capabilities: List[str], health_endpoint: Optional[str] = None,
                                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Handle service registration"""
        try:
            success = self.registry.register_service(name, host, port, capabilities,
                                                   health_endpoint, metadata)
            if success:
                return f"Service {name} registered successfully"
            else:
                return f"Service {name} already exists"
        except Exception as e:
            logger.error(f"Error registering service: {e}")
            return f"Registration failed: {str(e)}"

    async def handle_discover_services(self, capability: Optional[str] = None) -> Dict[str, Any]:
        """Handle service discovery"""
        try:
            services = self.registry.list_services(capability)
            return {
                "services": [
                    {
                        "name": s.name,
                        "host": s.host,
                        "port": s.port,
                        "capabilities": s.capabilities,
                        "status": s.status,
                        "last_heartbeat": s.last_heartbeat.isoformat(),
                        "metadata": s.metadata
                    }
                    for s in services
                ],
                "total": len(services)
            }
        except Exception as e:
            logger.error(f"Error discovering services: {e}")
            return {"error": str(e)}

    async def handle_heartbeat(self, name: str) -> str:
        """Handle service heartbeat"""
        try:
            success = await self.registry.heartbeat(name)
            if success:
                return f"Heartbeat received for {name}"
            else:
                return f"Service {name} not found"
        except Exception as e:
            logger.error(f"Error processing heartbeat: {e}")
            return f"Heartbeat failed: {str(e)}"

    async def handle_health_check(self) -> Dict[str, Any]:
        """Handle health check request"""
        try:
            health_status = self.registry.check_health()
            return {
                "health_status": health_status,
                "total_services": len(self.registry.services),
                "healthy_count": sum(1 for s in health_status.values() if s == "healthy")
            }
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            return {"error": str(e)}

    def _start_cleanup_task(self):
        """Start periodic cleanup task"""
        asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        """Periodic cleanup of stale services"""
        while True:
            try:
                self.registry.cleanup_stale_services()
                await asyncio.sleep(60)  # Clean up every minute
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)


async def main():
    """Main entry point for service discovery"""
    logger.info("Starting Service Discovery MCP Server")

    # Create service discovery server
    discovery_server = ServiceDiscoveryMCP()

    # Start WebSocket server for MCP connections
    async def handle_websocket(websocket, path):
        """Handle WebSocket connections"""
        logger.info(f"New WebSocket connection: {websocket.remote_address}")
        transport = WebSocketTransport(websocket)

        try:
            await discovery_server.serve(transport)
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")

    # Start WebSocket server
    port = int(os.getenv('DISCOVERY_PORT', 8090))
    start_server = websockets.serve(handle_websocket, "0.0.0.0", port)

    logger.info(f"Service Discovery MCP Server listening on port {port}")

    try:
        await start_server
        # Keep the server running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Shutting down Service Discovery MCP Server")


if __name__ == "__main__":
    asyncio.run(main())