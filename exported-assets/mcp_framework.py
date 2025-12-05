"""
MIA Universal: Model Context Protocol (MCP) Framework
Core library for implementing MCP servers and clients
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
from enum import Enum
import websockets
import aiohttp
from pydantic import BaseModel, validator


# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """MCP message types"""
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    SHUTDOWN = "shutdown"
    PING = "ping"
    PONG = "pong"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    NOTIFICATION = "notification"
    LOG = "log"


class LogLevel(str, Enum):
    """Log levels for MCP logging"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class MCPMessage:
    """Base MCP message structure"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = {}
        if self.id is not None:
            data["id"] = self.id
        if self.method is not None:
            data["method"] = self.method
        if self.params is not None:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        data["jsonrpc"] = self.jsonrpc
        return data

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Create message from dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error")
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """Create message from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Tool:
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    handler: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema
        }


@dataclass
class Resource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mimeType: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert resource to dictionary"""
        data = {
            "uri": self.uri,
            "name": self.name,
            "description": self.description
        }
        if self.mimeType:
            data["mimeType"] = self.mimeType
        return data


@dataclass
class Prompt:
    """MCP Prompt definition"""
    name: str
    description: str
    arguments: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt to dictionary"""
        data = {
            "name": self.name,
            "description": self.description
        }
        if self.arguments:
            data["arguments"] = self.arguments
        return data


class MCPError(Exception):
    """Base MCP error"""
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        error = {"code": self.code, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error


class MCPTransport(ABC):
    """Abstract base class for MCP transport layers"""

    @abstractmethod
    async def send(self, message: MCPMessage) -> None:
        """Send a message"""
        pass

    @abstractmethod
    async def receive(self) -> MCPMessage:
        """Receive a message"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport"""
        pass


class WebSocketTransport(MCPTransport):
    """WebSocket transport for MCP"""

    def __init__(self, websocket):
        self.websocket = websocket

    async def send(self, message: MCPMessage) -> None:
        """Send message via WebSocket"""
        await self.websocket.send(message.to_json())

    async def receive(self) -> MCPMessage:
        """Receive message via WebSocket"""
        data = await self.websocket.recv()
        return MCPMessage.from_json(data)

    async def close(self) -> None:
        """Close WebSocket connection"""
        await self.websocket.close()


class HTTPTransport(MCPTransport):
    """HTTP transport for MCP"""

    def __init__(self, session: aiohttp.ClientSession, url: str):
        self.session = session
        self.url = url

    async def send(self, message: MCPMessage) -> None:
        """Send message via HTTP POST"""
        async with self.session.post(self.url, json=message.to_dict()) as response:
            if response.status != 200:
                raise MCPError(-32603, f"HTTP error: {response.status}")

    async def receive(self) -> MCPMessage:
        """HTTP transport doesn't support receiving (request/response only)"""
        raise NotImplementedError("HTTP transport doesn't support receiving")

    async def close(self) -> None:
        """Close HTTP session"""
        await self.session.close()


class MCPServer:
    """MCP Server implementation"""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, Tool] = {}
        self.resources: Dict[str, Resource] = {}
        self.prompts: Dict[str, Prompt] = {}
        self.transport: Optional[MCPTransport] = None
        self.initialized = False
        self.running = False

    def add_tool(self, tool: Tool) -> None:
        """Add a tool to the server"""
        self.tools[tool.name] = tool
        logger.info(f"Added tool: {tool.name}")

    def add_resource(self, resource: Resource) -> None:
        """Add a resource to the server"""
        self.resources[resource.uri] = resource
        logger.info(f"Added resource: {resource.uri}")

    def add_prompt(self, prompt: Prompt) -> None:
        """Add a prompt to the server"""
        self.prompts[prompt.name] = prompt
        logger.info(f"Added prompt: {prompt.name}")

    async def handle_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Handle incoming MCP message"""
        try:
            if message.method == MessageType.INITIALIZE:
                return await self._handle_initialize(message)
            elif message.method == MessageType.TOOLS_LIST:
                return await self._handle_tools_list(message)
            elif message.method == MessageType.TOOLS_CALL:
                return await self._handle_tools_call(message)
            elif message.method == MessageType.RESOURCES_LIST:
                return await self._handle_resources_list(message)
            elif message.method == MessageType.RESOURCES_READ:
                return await self._handle_resources_read(message)
            elif message.method == MessageType.PROMPTS_LIST:
                return await self._handle_prompts_list(message)
            elif message.method == MessageType.PROMPTS_GET:
                return await self._handle_prompts_get(message)
            elif message.method == MessageType.PING:
                return await self._handle_ping(message)
            elif message.method == MessageType.SHUTDOWN:
                return await self._handle_shutdown(message)
            else:
                return MCPMessage(
                    id=message.id,
                    error=MCPError(-32601, f"Method not found: {message.method}").to_dict()
                )
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return MCPMessage(
                id=message.id,
                error=MCPError(-32603, f"Internal error: {str(e)}").to_dict()
            )

    async def _handle_initialize(self, message: MCPMessage) -> MCPMessage:
        """Handle initialize request"""
        self.initialized = True
        return MCPMessage(
            id=message.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": True, "listChanged": True},
                    "prompts": {"listChanged": True},
                    "logging": {}
                },
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                }
            }
        )

    async def _handle_tools_list(self, message: MCPMessage) -> MCPMessage:
        """Handle tools/list request"""
        tools_list = [tool.to_dict() for tool in self.tools.values()]
        return MCPMessage(
            id=message.id,
            result={"tools": tools_list}
        )

    async def _handle_tools_call(self, message: MCPMessage) -> MCPMessage:
        """Handle tools/call request"""
        if not message.params:
            return MCPMessage(
                id=message.id,
                error=MCPError(-32602, "Missing parameters").to_dict()
            )

        tool_name = message.params.get("name")
        tool_arguments = message.params.get("arguments", {})

        if tool_name not in self.tools:
            return MCPMessage(
                id=message.id,
                error=MCPError(-32602, f"Tool not found: {tool_name}").to_dict()
            )

        tool = self.tools[tool_name]
        if not tool.handler:
            return MCPMessage(
                id=message.id,
                error=MCPError(-32603, f"Tool handler not implemented: {tool_name}").to_dict()
            )

        try:
            # Execute tool handler
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**tool_arguments)
            else:
                result = tool.handler(**tool_arguments)

            return MCPMessage(
                id=message.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                }
            )
        except Exception as e:
            return MCPMessage(
                id=message.id,
                error=MCPError(-32603, f"Tool execution error: {str(e)}").to_dict()
            )

    async def _handle_resources_list(self, message: MCPMessage) -> MCPMessage:
        """Handle resources/list request"""
        resources_list = [resource.to_dict() for resource in self.resources.values()]
        return MCPMessage(
            id=message.id,
            result={"resources": resources_list}
        )

    async def _handle_resources_read(self, message: MCPMessage) -> MCPMessage:
        """Handle resources/read request"""
        if not message.params:
            return MCPMessage(
                id=message.id,
                error=MCPError(-32602, "Missing parameters").to_dict()
            )

        uri = message.params.get("uri")
        if uri not in self.resources:
            return MCPMessage(
                id=message.id,
                error=MCPError(-32602, f"Resource not found: {uri}").to_dict()
            )

        # In a real implementation, you would read the actual resource content
        return MCPMessage(
            id=message.id,
            result={
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": self.resources[uri].mimeType or "text/plain",
                        "text": f"Resource content for {uri}"
                    }
                ]
            }
        )

    async def _handle_prompts_list(self, message: MCPMessage) -> MCPMessage:
        """Handle prompts/list request"""
        prompts_list = [prompt.to_dict() for prompt in self.prompts.values()]
        return MCPMessage(
            id=message.id,
            result={"prompts": prompts_list}
        )

    async def _handle_prompts_get(self, message: MCPMessage) -> MCPMessage:
        """Handle prompts/get request"""
        if not message.params:
            return MCPMessage(
                id=message.id,
                error=MCPError(-32602, "Missing parameters").to_dict()
            )

        name = message.params.get("name")
        if name not in self.prompts:
            return MCPMessage(
                id=message.id,
                error=MCPError(-32602, f"Prompt not found: {name}").to_dict()
            )

        return MCPMessage(
            id=message.id,
            result={
                "description": self.prompts[name].description,
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Prompt: {name}"
                        }
                    }
                ]
            }
        )

    async def _handle_ping(self, message: MCPMessage) -> MCPMessage:
        """Handle ping request"""
        return MCPMessage(
            id=message.id,
            result={}
        )

    async def _handle_shutdown(self, message: MCPMessage) -> MCPMessage:
        """Handle shutdown request"""
        self.running = False
        return MCPMessage(
            id=message.id,
            result={}
        )

    async def serve(self, transport: MCPTransport) -> None:
        """Serve MCP requests using the provided transport"""
        self.transport = transport
        self.running = True
        logger.info(f"MCP Server '{self.name}' started")

        try:
            while self.running:
                try:
                    message = await transport.receive()
                    response = await self.handle_message(message)
                    if response:
                        await transport.send(response)
                except websockets.exceptions.ConnectionClosed:
                    logger.info("Connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error in serve loop: {e}")
                    break
        finally:
            await transport.close()
            logger.info(f"MCP Server '{self.name}' stopped")


class MCPClient:
    """MCP Client implementation"""

    def __init__(self):
        self.transport: Optional[MCPTransport] = None
        self.request_id = 0
        self.pending_requests: Dict[Union[str, int], asyncio.Future] = {}

    def _next_id(self) -> int:
        """Generate next request ID"""
        self.request_id += 1
        return self.request_id

    async def connect(self, transport: MCPTransport) -> None:
        """Connect to MCP server"""
        self.transport = transport
        await self.initialize()

    async def initialize(self) -> Dict[str, Any]:
        """Initialize connection with server"""
        if not self.transport:
            raise MCPError(-32603, "Not connected to transport")

        request = MCPMessage(
            id=self._next_id(),
            method=MessageType.INITIALIZE,
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "mia-client",
                    "version": "1.0.0"
                }
            }
        )

        response = await self._send_request(request)
        return response.result

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        request = MCPMessage(
            id=self._next_id(),
            method=MessageType.TOOLS_LIST
        )
        response = await self._send_request(request)
        return response.result.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool"""
        request = MCPMessage(
            id=self._next_id(),
            method=MessageType.TOOLS_CALL,
            params={
                "name": name,
                "arguments": arguments
            }
        )
        response = await self._send_request(request)
        return response.result

    async def _send_request(self, request: MCPMessage) -> MCPMessage:
        """Send request and wait for response"""
        if not self.transport:
            raise MCPError(-32603, "Not connected to transport")

        future = asyncio.Future()
        self.pending_requests[request.id] = future

        await self.transport.send(request)
        response = await future

        if response.error:
            raise MCPError(
                response.error.get("code", -32603),
                response.error.get("message", "Unknown error"),
                response.error.get("data")
            )

        return response

    async def _handle_response(self, message: MCPMessage) -> None:
        """Handle response message"""
        if message.id in self.pending_requests:
            future = self.pending_requests.pop(message.id)
            future.set_result(message)

    async def close(self) -> None:
        """Close client connection"""
        if self.transport:
            await self.transport.close()


# Utility functions
def create_tool(name: str, description: str, schema: Dict[str, Any], 
                handler: Callable) -> Tool:
    """Helper function to create a tool"""
    return Tool(
        name=name,
        description=description,
        inputSchema=schema,
        handler=handler
    )


def create_resource(uri: str, name: str, description: str, 
                   mime_type: Optional[str] = None) -> Resource:
    """Helper function to create a resource"""
    return Resource(
        uri=uri,
        name=name,
        description=description,
        mimeType=mime_type
    )


def create_prompt(name: str, description: str, 
                 arguments: Optional[List[Dict[str, Any]]] = None) -> Prompt:
    """Helper function to create a prompt"""
    return Prompt(
        name=name,
        description=description,
        arguments=arguments
    )


# Example usage and testing
if __name__ == "__main__":
    async def example_tool_handler(query: str, max_results: int = 10) -> str:
        """Example tool handler"""
        return f"Processed query '{query}' with max_results={max_results}"

    # Create server
    server = MCPServer("example-server", "1.0.0")
    
    # Add example tool
    tool = create_tool(
        name="search",
        description="Search for information",
        schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 10}
            },
            "required": ["query"]
        },
        handler=example_tool_handler
    )
    server.add_tool(tool)

    print("MCP Framework loaded successfully!")
    print(f"Server: {server.name} v{server.version}")
    print(f"Tools: {list(server.tools.keys())}")