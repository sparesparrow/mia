"""
MIA Universal: Linux Platform Controller MCP Server
Handles system operations on Linux platforms
"""

import asyncio
import logging
import os
import subprocess
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
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
class ProcessInfo:
    """Process information"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_mb: float


class SystemManager:
    """Linux system management"""

    def __init__(self):
        self.platform = "linux"

    async def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute system command safely"""
        try:
            logger.info(f"Executing command: {command}")

            # Run command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "stdout": stdout.decode().strip(),
                    "stderr": stderr.decode().strip(),
                    "command": command
                }

            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "command": command
                }

        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }

    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            # Get CPU info
            cpu_result = await self.execute_command("nproc")
            cpu_count = int(cpu_result.get("stdout", "1")) if cpu_result["success"] else 1

            # Get memory info
            mem_result = await self.execute_command("free -m | grep '^Mem:' | awk '{print $2}'")
            total_memory = int(mem_result.get("stdout", "1024")) if mem_result["success"] else 1024

            # Get disk usage
            disk_result = await self.execute_command("df -h / | tail -1 | awk '{print $5}'")
            disk_usage = disk_result.get("stdout", "unknown") if disk_result["success"] else "unknown"

            # Get uptime
            uptime_result = await self.execute_command("uptime -p")
            uptime = uptime_result.get("stdout", "unknown") if uptime_result["success"] else "unknown"

            return {
                "platform": self.platform,
                "cpu_count": cpu_count,
                "total_memory_mb": total_memory,
                "disk_usage": disk_usage,
                "uptime": uptime,
                "hostname": os.uname().nodename
            }

        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}

    async def list_processes(self, filter_name: Optional[str] = None) -> List[ProcessInfo]:
        """List running processes"""
        try:
            # Use ps command to get process info
            cmd = "ps aux --no-headers"
            if filter_name:
                cmd += f" | grep {filter_name}"

            result = await self.execute_command(cmd)

            if not result["success"]:
                return []

            processes = []
            lines = result["stdout"].split('\n')

            for line in lines:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 11:
                    try:
                        pid = int(parts[1])
                        cpu = float(parts[2])
                        memory = float(parts[3])
                        name = ' '.join(parts[10:])

                        processes.append(ProcessInfo(
                            pid=pid,
                            name=name,
                            status="running",
                            cpu_percent=cpu,
                            memory_mb=memory
                        ))
                    except (ValueError, IndexError):
                        continue

            return processes

        except Exception as e:
            logger.error(f"Error listing processes: {e}")
            return []

    async def kill_process(self, pid: int) -> bool:
        """Kill a process by PID"""
        try:
            result = await self.execute_command(f"kill {pid}")
            return result["success"]
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
            return False

    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file/directory information"""
        try:
            # Check if path exists
            stat_result = await self.execute_command(f"stat -c '%s %Y %a' '{path}'")

            if not stat_result["success"]:
                return {"exists": False, "path": path}

            stat_parts = stat_result["stdout"].split()
            size = int(stat_parts[0]) if len(stat_parts) > 0 else 0
            mtime = int(stat_parts[1]) if len(stat_parts) > 1 else 0
            permissions = stat_parts[2] if len(stat_parts) > 2 else "unknown"

            # Check if directory
            ls_result = await self.execute_command(f"ls -la '{path}' | head -1")
            is_dir = "total" in ls_result.get("stdout", "") if ls_result["success"] else False

            return {
                "exists": True,
                "path": path,
                "is_directory": is_dir,
                "size_bytes": size,
                "permissions": permissions,
                "modified_time": datetime.fromtimestamp(mtime).isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting file info for {path}: {e}")
            return {"error": str(e), "path": path}


class LinuxPlatformMCP(MCPServer):
    """Linux Platform Controller MCP Server"""

    def __init__(self):
        super().__init__("ai-platform-linux", "1.0.0")
        self.system_manager = SystemManager()
        self.setup_tools()

    def setup_tools(self):
        """Setup Linux platform tools"""

        # System command execution
        execute_tool = create_tool(
            name="execute_command",
            description="Execute a system command on Linux",
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "integer", "default": 30, "description": "Command timeout in seconds"}
                },
                "required": ["command"]
            },
            handler=self.handle_execute_command
        )
        self.add_tool(execute_tool)

        # System information
        sysinfo_tool = create_tool(
            name="get_system_info",
            description="Get system information and status",
            schema={"type": "object", "properties": {}},
            handler=self.handle_get_system_info
        )
        self.add_tool(sysinfo_tool)

        # Process management
        list_processes_tool = create_tool(
            name="list_processes",
            description="List running processes",
            schema={
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "Filter processes by name"}
                }
            },
            handler=self.handle_list_processes
        )
        self.add_tool(list_processes_tool)

        kill_process_tool = create_tool(
            name="kill_process",
            description="Kill a process by PID",
            schema={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID to kill"}
                },
                "required": ["pid"]
            },
            handler=self.handle_kill_process
        )
        self.add_tool(kill_process_tool)

        # File operations
        file_info_tool = create_tool(
            name="get_file_info",
            description="Get information about a file or directory",
            schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File or directory path"}
                },
                "required": ["path"]
            },
            handler=self.handle_get_file_info
        )
        self.add_tool(file_info_tool)

    async def handle_execute_command(self, command: str, timeout: int = 30) -> str:
        """Handle command execution"""
        try:
            # Security check - prevent dangerous commands
            dangerous_commands = ["rm", "dd", "mkfs", "fdisk", "format"]
            if any(cmd in command.lower() for cmd in dangerous_commands):
                return "Command blocked for security reasons"

            result = await self.system_manager.execute_command(command, timeout)

            if result["success"]:
                response = f"Command executed successfully\n"
                if result.get("stdout"):
                    response += f"Output: {result['stdout']}\n"
                return response.strip()
            else:
                error = result.get("error", "Unknown error")
                if result.get("stderr"):
                    error += f"\nStderr: {result['stderr']}"
                return f"Command failed: {error}"

        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return f"Error executing command: {str(e)}"

    async def handle_get_system_info(self) -> Dict[str, Any]:
        """Handle system info request"""
        try:
            return await self.system_manager.get_system_info()
        except Exception as e:
            return {"error": str(e)}

    async def handle_list_processes(self, filter: Optional[str] = None) -> Dict[str, Any]:
        """Handle process listing"""
        try:
            processes = await self.system_manager.list_processes(filter)
            return {
                "processes": [
                    {
                        "pid": p.pid,
                        "name": p.name,
                        "status": p.status,
                        "cpu_percent": p.cpu_percent,
                        "memory_mb": p.memory_mb
                    }
                    for p in processes
                ],
                "count": len(processes)
            }
        except Exception as e:
            return {"error": str(e)}

    async def handle_kill_process(self, pid: int) -> str:
        """Handle process killing"""
        try:
            success = await self.system_manager.kill_process(pid)
            if success:
                return f"Process {pid} killed successfully"
            else:
                return f"Failed to kill process {pid}"
        except Exception as e:
            return f"Error killing process: {str(e)}"

    async def handle_get_file_info(self, path: str) -> Dict[str, Any]:
        """Handle file info request"""
        try:
            return await self.system_manager.get_file_info(path)
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point for Linux platform controller"""
    logger.info("Starting Linux Platform Controller MCP Server")

    # Create platform controller server
    platform_server = LinuxPlatformMCP()

    # Start WebSocket server for MCP connections
    async def handle_websocket(websocket, path):
        """Handle WebSocket connections"""
        logger.info(f"New WebSocket connection: {websocket.remote_address}")
        transport = WebSocketTransport(websocket)

        try:
            await platform_server.serve(transport)
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")

    # Start WebSocket server
    port = int(os.getenv('MCP_SERVER_PORT', 8083))
    start_server = websockets.serve(handle_websocket, "0.0.0.0", port)

    logger.info(f"Linux Platform Controller MCP Server listening on port {port}")

    try:
        await start_server
        # Keep the server running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Shutting down Linux Platform Controller MCP Server")


if __name__ == "__main__":
    asyncio.run(main())