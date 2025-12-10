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
    """WebSocket transport for MCP with connection management"""

    def __init__(self, websocket):
        self.websocket = websocket
        self.closed = False

    async def send(self, message: MCPMessage) -> None:
        """Send message via WebSocket"""
        if self.closed:
            raise MCPError(-32000, "Connection closed")
        try:
            await self.websocket.send(message.to_json())
        except websockets.exceptions.ConnectionClosed:
            self.closed = True
            raise MCPError(-32000, "Connection closed during send")
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            raise MCPError(-32603, f"WebSocket send error: {str(e)}")

    async def receive(self) -> MCPMessage:
        """Receive message via WebSocket"""
        if self.closed:
            raise MCPError(-32000, "Connection closed")
        try:
            data = await self.websocket.recv()
            return MCPMessage.from_json(data)
        except websockets.exceptions.ConnectionClosed:
            self.closed = True
            raise MCPError(-32000, "Connection closed during receive")
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            raise MCPError(-32603, f"WebSocket receive error: {str(e)}")

    async def close(self) -> None:
        """Close WebSocket connection"""
        if not self.closed:
            self.closed = True
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")


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
                except MCPError as e:
                    if e.code == -32000:  # Connection closed
                        logger.info("Connection closed by client")
                        break
                    else:
                        logger.error(f"MCP Error in serve loop: {e}")
                        # Try to send error response if possible
                        try:
                            error_response = MCPMessage(
                                id=getattr(message, 'id', None),
                                error=e.to_dict()
                            )
                            await transport.send(error_response)
                        except Exception:
                            break  # Can't send error, connection likely closed
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in serve loop: {e}")
                    break
        finally:
            self.running = False
            try:
                await transport.close()
            except Exception as e:
                logger.error(f"Error closing transport: {e}")
            logger.info(f"MCP Server '{self.name}' stopped")


class MCPClient:
    """MCP Client implementation with persistent connection and response handling"""

    def __init__(self, max_reconnect_attempts: int = 3, reconnect_delay: float = 5.0):
        self.transport: Optional[MCPTransport] = None
        self.request_id = 0
        self.pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self.connected = False
        self.receive_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.reconnect_task: Optional[asyncio.Task] = None
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.reconnect_attempts = 0
        self.client_info = {
            "name": "ai-servis-client",
            "version": "1.0.0"
        }
        self.transport_factory: Optional[Callable[[], Union[MCPTransport, Awaitable[MCPTransport]]]] = None

    def _next_id(self) -> int:
        """Generate next request ID"""
        self.request_id += 1
        return self.request_id

    async def connect(
        self,
        transport: MCPTransport,
        transport_factory: Optional[Callable[[], Union[MCPTransport, Awaitable[MCPTransport]]]] = None,
        timeout: float = 30.0,
    ) -> None:
        """Connect to MCP server with persistent connection"""
        if transport_factory:
            self.transport_factory = transport_factory
        else:
            async def _default_factory() -> MCPTransport:
                return transport
            self.transport_factory = _default_factory

        await self._establish_connection(timeout)
        self.reconnect_attempts = 0  # Reset on successful connection

        # Start background tasks
        self.receive_task = asyncio.create_task(self._receive_loop())
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.reconnect_task = asyncio.create_task(self._reconnect_loop())

        logger.info("MCP Client connected successfully")

    async def _establish_connection(self, timeout: float = 30.0) -> None:
        """Establish connection to the server"""
        if self.transport_factory is None:
            raise MCPError(-32603, "No transport factory available")

        try:
<<<<<<< HEAD
            transport_candidate = self.transport_factory()
            if asyncio.iscoroutine(transport_candidate):
                self.transport = await transport_candidate
            else:
                self.transport = transport_candidate

            if self.transport is None:
                raise MCPError(-32603, "Transport factory returned None")
=======
            self.transport = await self.transport_factory()
>>>>>>> origin/fix/mcp-errors-and-cloudsmith-bootstrap
            self.connected = True

            # Initialize the connection
            await self.initialize()

        except Exception as e:
            self.connected = False
            logger.error(f"Failed to establish connection: {e}")
            raise

    async def _reconnect_loop(self) -> None:
        """Background task to handle reconnection attempts"""
        while True:
            await asyncio.sleep(1)  # Check connection status periodically

            if not self.connected and self.transport_factory and self.reconnect_attempts < self.max_reconnect_attempts:
                logger.info(f"Attempting reconnection (attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts})")

                try:
                    await asyncio.sleep(self.reconnect_delay)
                    await self._establish_connection()

                    # Restart background tasks
                    if self.receive_task and not self.receive_task.done():
                        self.receive_task.cancel()
                    if self.heartbeat_task and not self.heartbeat_task.done():
                        self.heartbeat_task.cancel()

                    self.receive_task = asyncio.create_task(self._receive_loop())
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    self.reconnect_attempts = 0  # Reset on success
                    logger.info("Reconnection successful")

                except Exception as e:
                    self.reconnect_attempts += 1
                    logger.error(f"Reconnection attempt {self.reconnect_attempts} failed: {e}")

                    if self.reconnect_attempts >= self.max_reconnect_attempts:
                        logger.error("Max reconnection attempts reached, giving up")
                        break
            elif self.connected:
                self.reconnect_attempts = 0  # Reset when connected

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
                "clientInfo": self.client_info
            }
        )

        response = await self._send_request(request, timeout=10.0)
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

    async def _send_request(self, request: MCPMessage, timeout: float = 30.0) -> MCPMessage:
        """Send request and wait for response with timeout"""
        if not self.transport or not self.connected:
            raise MCPError(-32603, "Not connected to transport")

        future = asyncio.Future()
        self.pending_requests[request.id] = future

        try:
            await self.transport.send(request)

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise MCPError(
                    response.error.get("code", -32603),
                    response.error.get("message", "Unknown error"),
                    response.error.get("data")
                )

            return response

        except asyncio.TimeoutError:
            # Clean up the pending request
            if request.id in self.pending_requests:
                del self.pending_requests[request.id]
            raise MCPError(-32000, f"Request timeout after {timeout} seconds")
        except Exception as e:
            # Clean up the pending request
            if request.id in self.pending_requests:
                del self.pending_requests[request.id]
            raise

    async def _receive_loop(self) -> None:
        """Background task to receive and handle incoming messages"""
        logger.info("Starting MCP client receive loop")
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.connected and self.transport:
            try:
                message = await self.transport.receive()
                await self._handle_message(message)
                consecutive_errors = 0  # Reset error counter on success
            except MCPError as e:
                if e.code == -32000:  # Connection closed
                    logger.warning("Connection closed during receive")
                    self.connected = False
                    break
                else:
                    consecutive_errors += 1
                    logger.error(f"MCP Error in receive loop: {e}")
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self.connected = False
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in receive loop: {e}")

                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), disconnecting")
                    self.connected = False
                    break

                if not self.connected:
                    break
                await asyncio.sleep(1)  # Brief pause before retrying

        logger.info("MCP client receive loop stopped")

    async def _heartbeat_loop(self) -> None:
        """Background task to send periodic ping messages"""
        logger.info("Starting MCP client heartbeat loop")
        while self.connected and self.transport:
            try:
                await asyncio.sleep(30)  # Ping every 30 seconds
                if self.connected and self.transport:
                    ping_request = MCPMessage(
                        id=self._next_id(),
                        method=MessageType.PING
                    )
                    # Send ping and wait for pong response
                    try:
                        pong_future = asyncio.Future()
                        self.pending_requests[ping_request.id] = pong_future

                        await asyncio.wait_for(
                            self.transport.send(ping_request),
                            timeout=5.0
                        )

                        # Wait for pong response
                        await asyncio.wait_for(pong_future, timeout=10.0)
                        logger.debug("Heartbeat ping-pong successful")

                    except asyncio.TimeoutError:
                        logger.warning("Heartbeat ping timeout - connection may be unstable")
                        # Don't immediately disconnect, just log the issue
                    except Exception as e:
                        logger.error(f"Heartbeat ping failed: {e}")
                        self.connected = False
                        break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                if not self.connected:
                    break

        logger.info("MCP client heartbeat loop stopped")

    async def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message"""
        try:
            # Check if this is a response to a pending request
            if message.id in self.pending_requests:
                future = self.pending_requests.pop(message.id)
                future.set_result(message)
                return

            # Handle server-initiated messages (notifications, etc.)
            if message.method:
                if message.method == MessageType.NOTIFICATION:
                    logger.debug(f"Received notification: {message.params}")
                elif message.method == MessageType.LOG:
                    logger.info(f"Server log: {message.params}")
                else:
                    logger.warning(f"Unhandled server message: {message.method}")
            else:
                logger.warning(f"Received message without method or matching request ID: {message}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def close(self) -> None:
        """Close client connection and cleanup tasks"""
        logger.info("Closing MCP client connection")
        self.connected = False

        # Cancel background tasks
        tasks_to_cancel = [
            (self.receive_task, "receive_task"),
            (self.heartbeat_task, "heartbeat_task"),
            (self.reconnect_task, "reconnect_task")
        ]

        for task, name in tasks_to_cancel:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error cancelling {name}: {e}")

        # Cancel any pending requests
        for future in self.pending_requests.values():
            if not future.done():
                future.cancel()

        self.pending_requests.clear()

        # Close transport
        if self.transport:
            try:
                await self.transport.close()
            except Exception as e:
                logger.error(f"Error closing transport: {e}")

        logger.info("MCP client connection closed")


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