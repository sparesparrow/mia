"""
Kernun Proxy MCP Client

Python client for connecting to Kernun proxy MCP server.
Provides traffic analysis, session inspection, TLS policy management,
proxy rules management, and content categorization.

Usage:
    from modules.security.proxy_mcp_client import ProxyMCPClient
    
    async with ProxyMCPClient("localhost", 3000) as client:
        result = await client.analyze_traffic(time_range_seconds=300)
        print(result)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

import aiohttp
from aiohttp import ClientSession, ClientWebSocketResponse

# Configure logging
logger = logging.getLogger(__name__)


class MCPToolError(Exception):
    """Exception raised when an MCP tool call fails."""
    pass


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class TrafficAnalysis:
    """Traffic analysis result."""
    session_id: str
    source_ip: str = ""
    dest_ip: str = ""
    source_port: int = 0
    dest_port: int = 0
    protocol: str = ""
    bytes_sent: int = 0
    bytes_received: int = 0
    detected_threats: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SessionInfo:
    """Session inspection result."""
    session_id: str
    state: str = "unknown"
    client_info: str = ""
    server_info: str = ""
    start_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    tls_version: str = ""
    cipher_suite: str = ""


@dataclass
class TLSPolicy:
    """TLS policy configuration."""
    policy_id: str
    name: str = ""
    allowed_ciphers: List[str] = field(default_factory=list)
    allowed_protocols: List[str] = field(default_factory=list)
    require_client_cert: bool = False
    enable_ocsp_stapling: bool = True


@dataclass
class ProxyRule:
    """Proxy rule definition."""
    rule_id: str
    name: str = ""
    action: str = "allow"  # "allow", "deny", "log", "inspect"
    source_pattern: str = "*"
    dest_pattern: str = "*"
    priority: int = 100
    enabled: bool = True


@dataclass
class ClearwebCategory:
    """Clearweb category entry."""
    domain: str
    category: str
    subcategory: str = ""
    confidence: float = 1.0
    last_updated: Optional[datetime] = None


@dataclass
class ToolResult:
    """MCP tool result wrapper."""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "ToolResult":
        """Create ToolResult from JSON data."""
        return cls(
            success=json_data.get("success", False),
            message=json_data.get("message", ""),
            data=json_data.get("data", {})
        )


# Type for callback functions
T = TypeVar("T")
ToolCallback = Callable[[ToolResult], None]


class ProxyMCPClient:
    """
    Async Python client for Kernun Proxy MCP Server.
    
    Exposes methods for:
    - analyze_traffic: Network traffic analysis
    - inspect_session: Session inspection
    - modify_tls_policy: TLS policy management
    - update_proxy_rules: Firewall rules management
    - update_clearweb_database: Content categorization
    
    Example:
        async with ProxyMCPClient("localhost", 3000) as client:
            # Analyze traffic
            result = await client.analyze_traffic()
            
            # Inspect session
            session = await client.inspect_session("session-123")
            
            # Get TLS policies
            policies = await client.get_tls_policies()
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 3000,
        use_ssl: bool = False,
        timeout: float = 30.0
    ):
        """
        Initialize the MCP client.
        
        Args:
            host: MCP server host
            port: MCP server port
            use_ssl: Use SSL/TLS connection
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.timeout = timeout
        
        self._session: Optional[ClientSession] = None
        self._ws: Optional[ClientWebSocketResponse] = None
        self._state = ConnectionState.DISCONNECTED
        self._message_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None
    
    @property
    def base_url(self) -> str:
        """Get the base URL for HTTP requests."""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"
    
    @property
    def ws_url(self) -> str:
        """Get the WebSocket URL."""
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}:{self.port}/mcp"
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._state == ConnectionState.CONNECTED
    
    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        Returns:
            True if connection successful
        """
        if self._state == ConnectionState.CONNECTED:
            return True
        
        self._state = ConnectionState.CONNECTING
        
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
            
            # Try WebSocket connection first
            try:
                self._ws = await self._session.ws_connect(self.ws_url)
                self._receive_task = asyncio.create_task(self._receive_loop())
                logger.info(f"Connected to MCP server via WebSocket: {self.ws_url}")
            except Exception as ws_error:
                logger.debug(f"WebSocket connection failed, using HTTP: {ws_error}")
                # Fall back to HTTP-only mode
                self._ws = None
            
            self._state = ConnectionState.CONNECTED
            logger.info(f"Connected to Kernun MCP server at {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self._state = ConnectionState.ERROR
            logger.error(f"Failed to connect to MCP server: {e}")
            await self._cleanup()
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        await self._cleanup()
        self._state = ConnectionState.DISCONNECTED
        logger.info("Disconnected from MCP server")
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
    
    async def _receive_loop(self) -> None:
        """Receive messages from WebSocket."""
        if not self._ws:
            return
        
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self._ws.exception()}")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Handle received message."""
        msg_id = data.get("id")
        if msg_id is not None and msg_id in self._pending_requests:
            future = self._pending_requests.pop(msg_id)
            if not future.done():
                future.set_result(data)
    
    def _next_message_id(self) -> int:
        """Get next message ID."""
        self._message_id += 1
        return self._message_id
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if not self.is_connected:
            if not await self.connect():
                raise MCPToolError("Not connected to MCP server")
        
        arguments = arguments or {}
        
        # Try WebSocket if available
        if self._ws and not self._ws.closed:
            return await self._call_tool_ws(tool_name, arguments)
        else:
            return await self._call_tool_http(tool_name, arguments)
    
    async def _call_tool_ws(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Call tool via WebSocket."""
        msg_id = self._next_message_id()
        
        request = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[msg_id] = future
        
        try:
            await self._ws.send_json(request)
            response = await asyncio.wait_for(future, timeout=self.timeout)
            
            if "error" in response:
                return ToolResult(
                    success=False,
                    message=response["error"].get("message", "Unknown error")
                )
            
            result = response.get("result", {})
            return ToolResult(
                success=True,
                message=result.get("message", "Success"),
                data=result.get("data", result)
            )
            
        except asyncio.TimeoutError:
            self._pending_requests.pop(msg_id, None)
            return ToolResult(success=False, message="Request timeout")
    
    async def _call_tool_http(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Call tool via HTTP POST."""
        url = f"{self.base_url}/mcp/tools/{tool_name}"
        
        try:
            async with self._session.post(url, json=arguments) as response:
                if response.status == 200:
                    data = await response.json()
                    return ToolResult.from_json(data)
                else:
                    text = await response.text()
                    return ToolResult(
                        success=False,
                        message=f"HTTP {response.status}: {text}"
                    )
        except Exception as e:
            return ToolResult(success=False, message=str(e))
    
    # MCP Tool Methods
    
    async def analyze_traffic(
        self,
        session_id: Optional[str] = None,
        time_range_seconds: int = 300
    ) -> ToolResult:
        """
        Analyze network traffic.
        
        Args:
            session_id: Optional session ID to filter
            time_range_seconds: Time range to analyze (default: 5 minutes)
            
        Returns:
            Traffic analysis result
        """
        return await self.call_tool("analyze_traffic", {
            "session_id": session_id or "",
            "time_range_seconds": time_range_seconds
        })
    
    async def inspect_session(self, session_id: str) -> ToolResult:
        """
        Inspect a specific network session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session information
        """
        if not session_id:
            return ToolResult(success=False, message="Session ID required")
        
        return await self.call_tool("inspect_session", {
            "session_id": session_id
        })
    
    async def list_sessions(self) -> ToolResult:
        """
        List all active sessions.
        
        Returns:
            List of session information
        """
        return await self.call_tool("list_sessions", {})
    
    async def modify_tls_policy(
        self,
        policy_id: str,
        updates: Dict[str, Any]
    ) -> ToolResult:
        """
        Modify a TLS policy.
        
        Args:
            policy_id: Policy identifier
            updates: Dictionary of updates to apply
            
        Returns:
            Operation result
        """
        return await self.call_tool("modify_tls_policy", {
            "policy_id": policy_id,
            "updates": updates
        })
    
    async def get_tls_policies(self) -> ToolResult:
        """
        Get all TLS policies.
        
        Returns:
            List of TLS policies
        """
        return await self.call_tool("get_tls_policies", {})
    
    async def update_proxy_rules(
        self,
        rules: List[Union[ProxyRule, Dict[str, Any]]]
    ) -> ToolResult:
        """
        Update proxy rules.
        
        Args:
            rules: List of proxy rules to update/add
            
        Returns:
            Operation result
        """
        # Convert ProxyRule objects to dicts
        rule_dicts = []
        for rule in rules:
            if isinstance(rule, ProxyRule):
                rule_dicts.append({
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "action": rule.action,
                    "source_pattern": rule.source_pattern,
                    "dest_pattern": rule.dest_pattern,
                    "priority": rule.priority,
                    "enabled": rule.enabled
                })
            else:
                rule_dicts.append(rule)
        
        return await self.call_tool("update_proxy_rules", {
            "rules": rule_dicts
        })
    
    async def get_proxy_rules(self) -> ToolResult:
        """
        Get all proxy rules.
        
        Returns:
            List of proxy rules
        """
        return await self.call_tool("get_proxy_rules", {})
    
    async def delete_proxy_rule(self, rule_id: str) -> ToolResult:
        """
        Delete a proxy rule.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Operation result
        """
        return await self.call_tool("delete_proxy_rule", {
            "rule_id": rule_id
        })
    
    async def update_clearweb_database(
        self,
        entries: List[Union[ClearwebCategory, Dict[str, Any]]]
    ) -> ToolResult:
        """
        Update clearweb database entries.
        
        Args:
            entries: List of category entries
            
        Returns:
            Operation result
        """
        # Convert ClearwebCategory objects to dicts
        entry_dicts = []
        for entry in entries:
            if isinstance(entry, ClearwebCategory):
                entry_dicts.append({
                    "domain": entry.domain,
                    "category": entry.category,
                    "subcategory": entry.subcategory,
                    "confidence": entry.confidence
                })
            else:
                entry_dicts.append(entry)
        
        return await self.call_tool("update_clearweb_database", {
            "entries": entry_dicts
        })
    
    async def lookup_domain_category(self, domain: str) -> ToolResult:
        """
        Lookup domain category.
        
        Args:
            domain: Domain to lookup
            
        Returns:
            Category information
        """
        return await self.call_tool("lookup_domain_category", {
            "domain": domain
        })
    
    async def get_statistics(self) -> ToolResult:
        """
        Get server statistics.
        
        Returns:
            Server statistics
        """
        return await self.call_tool("get_statistics", {})
    
    async def list_tools(self) -> ToolResult:
        """
        List available MCP tools.
        
        Returns:
            List of available tools
        """
        return await self.call_tool("list_tools", {})
    
    # Context manager support
    
    async def __aenter__(self) -> "ProxyMCPClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


# FastAPI integration helper
def create_fastapi_routes(client: ProxyMCPClient):
    """
    Create FastAPI routes for proxy MCP client.
    
    Args:
        client: ProxyMCPClient instance
        
    Returns:
        FastAPI APIRouter
    """
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    
    router = APIRouter(prefix="/proxy", tags=["Proxy MCP"])
    
    class TrafficAnalysisRequest(BaseModel):
        session_id: Optional[str] = None
        time_range_seconds: int = 300
    
    class ProxyRuleRequest(BaseModel):
        rule_id: str
        name: str = ""
        action: str = "allow"
        source_pattern: str = "*"
        dest_pattern: str = "*"
        priority: int = 100
        enabled: bool = True
    
    class ClearwebEntryRequest(BaseModel):
        domain: str
        category: str
        subcategory: str = ""
        confidence: float = 1.0
    
    @router.post("/analyze-traffic")
    async def analyze_traffic(request: TrafficAnalysisRequest):
        result = await client.analyze_traffic(
            session_id=request.session_id,
            time_range_seconds=request.time_range_seconds
        )
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    
    @router.get("/sessions/{session_id}")
    async def inspect_session(session_id: str):
        result = await client.inspect_session(session_id)
        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)
        return result.data
    
    @router.get("/sessions")
    async def list_sessions():
        result = await client.list_sessions()
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    
    @router.get("/tls-policies")
    async def get_tls_policies():
        result = await client.get_tls_policies()
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    
    @router.put("/tls-policies/{policy_id}")
    async def modify_tls_policy(policy_id: str, updates: dict):
        result = await client.modify_tls_policy(policy_id, updates)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    
    @router.get("/rules")
    async def get_proxy_rules():
        result = await client.get_proxy_rules()
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    
    @router.post("/rules")
    async def update_proxy_rules(rules: List[ProxyRuleRequest]):
        result = await client.update_proxy_rules([r.dict() for r in rules])
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    
    @router.delete("/rules/{rule_id}")
    async def delete_proxy_rule(rule_id: str):
        result = await client.delete_proxy_rule(rule_id)
        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)
        return result.data
    
    @router.post("/clearweb")
    async def update_clearweb(entries: List[ClearwebEntryRequest]):
        result = await client.update_clearweb_database([e.dict() for e in entries])
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    
    @router.get("/clearweb/{domain}")
    async def lookup_domain(domain: str):
        result = await client.lookup_domain_category(domain)
        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)
        return result.data
    
    @router.get("/statistics")
    async def get_statistics():
        result = await client.get_statistics()
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    
    return router


# Example usage
if __name__ == "__main__":
    async def main():
        async with ProxyMCPClient("localhost", 3000) as client:
            # List available tools
            tools = await client.list_tools()
            print("Available tools:", tools)
            
            # Analyze traffic
            analysis = await client.analyze_traffic(time_range_seconds=60)
            print("Traffic analysis:", analysis)
            
            # Get TLS policies
            policies = await client.get_tls_policies()
            print("TLS policies:", policies)
            
            # Get server statistics
            stats = await client.get_statistics()
            print("Server stats:", stats)
    
    asyncio.run(main())
