"""
MCP Client for Hardware Control

Python MCP client that communicates with the C++ MCP server
for hardware control operations.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import socket

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPResult:
    """MCP Tool execution result"""
    content: List[Dict[str, Any]]
    is_error: bool = False


class MCPClient:
    """MCP Client for communicating with C++ MCP server"""

    def __init__(self, host: str = "localhost", port: int = 8082):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False

        # MCP Tools available from the C++ server
        self.tools = {
            "download_file": MCPTool(
                name="download_file",
                description="Download a file from URL to local path",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to download from"},
                        "output_path": {"type": "string", "description": "Local path to save file"},
                        "session_id": {"type": "integer", "description": "Session ID for tracking"}
                    },
                    "required": ["url", "output_path", "session_id"]
                }
            ),
            "abort_download": MCPTool(
                name="abort_download",
                description="Abort an ongoing download operation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "integer", "description": "Session ID to abort"}
                    },
                    "required": ["session_id"]
                }
            ),
            "get_download_status": MCPTool(
                name="get_download_status",
                description="Get status of download operations",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "integer", "description": "Session ID to check"}
                    },
                    "required": ["session_id"]
                }
            ),
            "gpio_task": MCPTool(
                name="gpio_task",
                description="Execute GPIO control task",
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["configure", "set", "get"], "description": "GPIO action"},
                        "pin": {"type": "integer", "description": "GPIO pin number"},
                        "direction": {"type": "string", "enum": ["input", "output"], "description": "Pin direction"},
                        "value": {"type": "integer", "enum": [0, 1], "description": "Pin value"}
                    },
                    "required": ["action", "pin"]
                }
            )
        }

    def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to MCP server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from MCP server"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            self.socket = None
        self.connected = False

    def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send MCP request and receive response"""
        if not self.connected or not self.socket:
            logger.error("Not connected to MCP server")
            return None

        try:
            # Send request as JSON
            message = json.dumps(request) + "\n"
            self.socket.send(message.encode('utf-8'))

            # Receive response
            response_data = self.socket.recv(4096)
            if not response_data:
                logger.error("No response from MCP server")
                return None

            response = json.loads(response_data.decode('utf-8'))
            return response

        except Exception as e:
            logger.error(f"Error communicating with MCP server: {e}")
            return None

    def get_available_tools(self) -> List[MCPTool]:
        """Get list of available MCP tools"""
        return list(self.tools.values())

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResult:
        """Execute MCP tool"""
        try:
            if tool_name == "download_file":
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "download_file",
                        "arguments": arguments
                    }
                }

                response = self._send_request(request)
                if response and "result" in response:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": f"Download started: {arguments['url']} -> {arguments['output_path']}"
                        }]
                    )
                else:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": "Failed to start download"
                        }],
                        is_error=True
                    )

            elif tool_name == "abort_download":
                request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "abort_download",
                        "arguments": arguments
                    }
                }

                response = self._send_request(request)
                if response and "result" in response:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": f"Download aborted for session {arguments['session_id']}"
                        }]
                    )
                else:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": "Failed to abort download"
                        }],
                        is_error=True
                    )

            elif tool_name == "get_download_status":
                request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "get_download_status",
                        "arguments": arguments
                    }
                }

                response = self._send_request(request)
                if response and "result" in response:
                    status = response["result"]
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": f"Download status for session {arguments['session_id']}: {status}"
                        }]
                    )
                else:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": "Failed to get download status"
                        }],
                        is_error=True
                    )

            elif tool_name == "gpio_task":
                request = {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "gpio_task",
                        "arguments": arguments
                    }
                }

                response = self._send_request(request)
                if response and "result" in response:
                    result = response["result"]
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": f"GPIO task completed: {result}"
                        }]
                    )
                else:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": "Failed to execute GPIO task"
                        }],
                        is_error=True
                    )

            else:
                return MCPResult(
                    content=[{
                        "type": "text",
                        "text": f"Unknown tool: {tool_name}"
                    }],
                    is_error=True
                )

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return MCPResult(
                content=[{
                    "type": "text",
                    "text": f"Error executing {tool_name}: {str(e)}"
                }],
                is_error=True
            )

    async def initialize(self) -> bool:
        """Initialize MCP connection"""
        if not self.connect():
            return False

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "ai-servis-hardware-bridge",
                    "version": "1.0.0"
                }
            }
        }

        response = self._send_request(init_request)
        if response and "result" in response:
            logger.info("MCP client initialized successfully")
            return True
        else:
            logger.error("Failed to initialize MCP client")
            return False

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()