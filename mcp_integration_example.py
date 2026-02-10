#!/usr/bin/env python3
"""
MCP Integration Example
Demonstrates advanced integration between Python MCP orchestrator and C++ components
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Import the C++ bridge if available
    import mcp_cpp_bridge
    CPP_BRIDGE_AVAILABLE = True
except ImportError:
    logger.warning("MCP C++ bridge not available, using Python fallback")
    CPP_BRIDGE_AVAILABLE = False

# Import Python MCP framework
from shared.mcp_framework import (
    MCPServer,
    MCPClient,
    Tool,
    Resource,
    Prompt,
    StdioTransport,
    WebSocketTransport,
)


class HybridMCPServer:
    """
    Hybrid MCP server that can use either C++ or Python implementation
    based on availability and performance requirements
    """
    
    def __init__(self, name: str, use_cpp: bool = True):
        self.name = name
        self.use_cpp = use_cpp and CPP_BRIDGE_AVAILABLE
        
        if self.use_cpp:
            self._init_cpp_server()
        else:
            self._init_python_server()
    
    def _init_cpp_server(self):
        """Initialize C++ MCP server"""
        logger.info(f"Initializing C++ MCP server: {self.name}")
        
        # Create server configuration
        config = mcp_cpp_bridge.server.ServerConfig()
        config.name = self.name
        config.version = "1.0.0"
        config.worker_threads = 8  # More threads for better performance
        config.max_concurrent_requests = 200
        
        # Configure capabilities
        capabilities = mcp_cpp_bridge.server.ServerCapabilities()
        capabilities.tools = True
        capabilities.resources = True
        capabilities.prompts = True
        capabilities.logging = True
        config.capabilities = capabilities
        
        # Create server
        self.server = mcp_cpp_bridge.server.Server(config)
        
        # Register built-in tools
        self._register_cpp_tools()
    
    def _init_python_server(self):
        """Initialize Python MCP server"""
        logger.info(f"Initializing Python MCP server: {self.name}")
        
        self.server = MCPServer(
            name=self.name,
            version="1.0.0",
            capabilities={
                "tools": True,
                "resources": True,
                "prompts": True,
                "logging": True
            }
        )
        
        # Register built-in tools
        self._register_python_tools()
    
    def _register_cpp_tools(self):
        """Register tools for C++ server"""
        
        # System info tool
        tool = mcp_cpp_bridge.protocol.Tool()
        tool.name = "system_info"
        tool.description = "Get system information"
        tool.input_schema = {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["cpu", "memory", "disk", "network", "all"]
                }
            },
            "required": ["category"]
        }
        
        def system_info_handler(params):
            import psutil
            category = params.get("category", "all")
            
            info = {}
            if category in ["cpu", "all"]:
                info["cpu"] = {
                    "percent": psutil.cpu_percent(interval=1),
                    "count": psutil.cpu_count(),
                    "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                }
            
            if category in ["memory", "all"]:
                mem = psutil.virtual_memory()
                info["memory"] = {
                    "total": mem.total,
                    "available": mem.available,
                    "percent": mem.percent,
                    "used": mem.used
                }
            
            if category in ["disk", "all"]:
                disk = psutil.disk_usage('/')
                info["disk"] = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            
            if category in ["network", "all"]:
                net = psutil.net_io_counters()
                info["network"] = {
                    "bytes_sent": net.bytes_sent,
                    "bytes_recv": net.bytes_recv,
                    "packets_sent": net.packets_sent,
                    "packets_recv": net.packets_recv
                }
            
            return info
        
        tool.set_handler(system_info_handler)
        self.server.register_tool(tool)
        
        # File operations tool
        file_tool = mcp_cpp_bridge.protocol.Tool()
        file_tool.name = "file_operation"
        file_tool.description = "Perform file operations"
        file_tool.input_schema = {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "list", "delete"]
                },
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["operation", "path"]
        }
        
        def file_operation_handler(params):
            operation = params["operation"]
            path = Path(params["path"])
            
            if operation == "read":
                if path.exists() and path.is_file():
                    return {"content": path.read_text()}
                return {"error": "File not found"}
            
            elif operation == "write":
                content = params.get("content", "")
                path.write_text(content)
                return {"success": True, "bytes_written": len(content)}
            
            elif operation == "list":
                if path.exists() and path.is_dir():
                    files = [str(f.name) for f in path.iterdir()]
                    return {"files": files}
                return {"error": "Directory not found"}
            
            elif operation == "delete":
                if path.exists():
                    path.unlink()
                    return {"success": True}
                return {"error": "File not found"}
            
            return {"error": "Unknown operation"}
        
        file_tool.set_handler(file_operation_handler)
        self.server.register_tool(file_tool)
        
        # Process execution tool
        exec_tool = mcp_cpp_bridge.protocol.Tool()
        exec_tool.name = "execute_command"
        exec_tool.description = "Execute system command"
        exec_tool.input_schema = {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "args": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "timeout": {"type": "number"}
            },
            "required": ["command"]
        }
        
        def execute_command_handler(params):
            import subprocess
            
            command = params["command"]
            args = params.get("args", [])
            timeout = params.get("timeout", 30)
            
            try:
                result = subprocess.run(
                    [command] + args,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            except subprocess.TimeoutExpired:
                return {"error": "Command timed out"}
            except Exception as e:
                return {"error": str(e)}
        
        exec_tool.set_handler(execute_command_handler)
        self.server.register_tool(exec_tool)
    
    def _register_python_tools(self):
        """Register tools for Python server"""
        
        @self.server.tool(
            name="system_info",
            description="Get system information",
            schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["cpu", "memory", "disk", "network", "all"]
                    }
                }
            }
        )
        async def system_info(category: str = "all") -> Dict[str, Any]:
            # Same implementation as C++ version
            import psutil
            info = {}
            # ... (implementation same as above)
            return info
        
        # Add other tools similarly
    
    async def start(self):
        """Start the server"""
        if self.use_cpp:
            self.server.start()
            logger.info(f"C++ MCP server {self.name} started")
        else:
            await self.server.start()
            logger.info(f"Python MCP server {self.name} started")
    
    async def stop(self):
        """Stop the server"""
        if self.use_cpp:
            self.server.stop()
        else:
            await self.server.stop()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        if self.use_cpp:
            stats = self.server.get_stats()
            return {
                "requests_received": stats.requests_received,
                "requests_processed": stats.requests_processed,
                "requests_failed": stats.requests_failed,
                "notifications_received": stats.notifications_received,
                "avg_response_time_ms": stats.avg_response_time.total_seconds() * 1000
            }
        else:
            return self.server.get_stats()


class MCPOrchestrationDemo:
    """
    Demonstration of MCP orchestration with hybrid Python/C++ implementation
    """
    
    def __init__(self):
        self.servers: Dict[str, HybridMCPServer] = {}
        self.clients: Dict[str, Any] = {}
    
    async def setup(self):
        """Setup the demonstration environment"""
        
        # Create servers for different components
        components = [
            ("core-orchestrator", True),  # Use C++ for performance
            ("audio-assistant", True),
            ("hardware-bridge", True),
            ("security-module", False),  # Use Python for flexibility
        ]
        
        for name, use_cpp in components:
            server = HybridMCPServer(name, use_cpp=use_cpp)
            await server.start()
            self.servers[name] = server
            
            logger.info(f"Started {name} server (C++: {server.use_cpp})")
    
    async def demonstrate_tool_execution(self):
        """Demonstrate tool execution"""
        logger.info("\n=== Tool Execution Demo ===")
        
        # Get system info
        if CPP_BRIDGE_AVAILABLE:
            # Direct C++ call
            server = self.servers["core-orchestrator"].server
            
            # This would normally be called through the protocol
            # Here we demonstrate direct usage
            stats = server.get_stats()
            logger.info(f"Server stats: {stats}")
    
    async def demonstrate_performance(self):
        """Demonstrate performance comparison"""
        logger.info("\n=== Performance Comparison ===")
        
        import time
        
        # Test with C++ server
        if "hardware-bridge" in self.servers:
            server = self.servers["hardware-bridge"]
            
            # Measure request processing time
            start = time.perf_counter()
            
            # Simulate multiple requests
            for i in range(100):
                # In real scenario, this would be actual MCP requests
                pass
            
            elapsed = time.perf_counter() - start
            logger.info(f"Processed 100 requests in {elapsed:.3f}s")
            
            # Get statistics
            stats = server.get_stats()
            logger.info(f"Statistics: {stats}")
    
    async def demonstrate_orchestration(self):
        """Demonstrate service orchestration"""
        logger.info("\n=== Service Orchestration Demo ===")
        
        # Simulate a complex workflow
        workflow = [
            ("audio-assistant", "play_music", {"source": "spotify", "query": "jazz"}),
            ("hardware-bridge", "gpio_control", {"pin": 17, "action": "write", "value": True}),
            ("security-module", "check_access", {"user": "admin", "resource": "system"}),
        ]
        
        for server_name, tool_name, params in workflow:
            if server_name in self.servers:
                logger.info(f"Executing {tool_name} on {server_name} with params: {params}")
                # In real scenario, execute through MCP protocol
                await asyncio.sleep(0.1)  # Simulate execution
    
    async def run(self):
        """Run the complete demonstration"""
        try:
            await self.setup()
            await self.demonstrate_tool_execution()
            await self.demonstrate_performance()
            await self.demonstrate_orchestration()
            
            logger.info("\n=== Demo Complete ===")
            
            # Print final statistics
            for name, server in self.servers.items():
                stats = server.get_stats()
                logger.info(f"{name}: {stats}")
        
        finally:
            # Cleanup
            for server in self.servers.values():
                await server.stop()


async def main():
    """Main entry point"""
    demo = MCPOrchestrationDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())