"""
MIA Universal: Core Orchestrator
Main MCP host that coordinates all AI modules
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiohttp
import websockets
from datetime import datetime

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
class ServiceInfo:
    """Information about a registered service"""
    name: str
    host: str
    port: int
    capabilities: List[str]
    health_status: str = "unknown"
    last_seen: Optional[datetime] = None


class NLPProcessor:
    """Simple NLP processor for intent recognition"""
    
    def __init__(self):
        self.intent_patterns = {
            "play_music": ["play", "music", "song", "track", "album", "artist"],
            "control_volume": ["volume", "loud", "quiet", "mute", "unmute"],
            "switch_audio": ["switch", "change", "output", "headphones", "speakers", "bluetooth"],
            "system_control": ["open", "close", "launch", "run", "execute", "kill"],
            "smart_home": ["lights", "temperature", "thermostat", "lock", "unlock", "dim"],
            "communication": ["send", "call", "message", "text", "email", "whatsapp"],
            "navigation": ["directions", "navigate", "route", "map", "location", "traffic"]
        }
    
    async def parse_command(self, text: str) -> Dict[str, Any]:
        """Parse natural language command into intent and parameters"""
        text_lower = text.lower()
        words = text_lower.split()
        
        # Simple intent classification
        intent_scores = {}
        for intent, keywords in self.intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "parameters": {},
                "original_text": text
            }
        
        # Get highest scoring intent
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent] / len(words)
        
        # Extract parameters based on intent
        parameters = self._extract_parameters(text_lower, best_intent, words)
        
        return {
            "intent": best_intent,
            "confidence": confidence,
            "parameters": parameters,
            "original_text": text
        }
    
    def _extract_parameters(self, text: str, intent: str, words: List[str]) -> Dict[str, Any]:
        """Extract parameters from text based on intent"""
        params = {}
        
        if intent == "play_music":
            # Look for artist, song, genre patterns
            if "artist" in text or "by" in text:
                # Simple artist extraction
                by_index = next((i for i, word in enumerate(words) if word == "by"), -1)
                if by_index != -1 and by_index + 1 < len(words):
                    params["artist"] = " ".join(words[by_index + 1:])
            
            # Genre detection
            genres = ["jazz", "rock", "classical", "pop", "electronic", "ambient", "folk"]
            for genre in genres:
                if genre in text:
                    params["genre"] = genre
                    break
            
            # Default query
            if not params:
                params["query"] = " ".join([w for w in words if w not in ["play", "music", "song"]])
        
        elif intent == "control_volume":
            # Volume level extraction
            volume_words = ["up", "down", "high", "low", "max", "min"]
            for word in volume_words:
                if word in words:
                    params["action"] = word
                    break
            
            # Numeric volume
            for word in words:
                if word.isdigit():
                    params["level"] = int(word)
                    break
        
        elif intent == "switch_audio":
            # Audio device detection
            devices = ["headphones", "speakers", "bluetooth", "rtsp"]
            for device in devices:
                if device in text:
                    params["device"] = device
                    break
        
        elif intent == "system_control":
            # Application name extraction
            action_words = ["open", "close", "launch", "run", "execute", "kill"]
            for i, word in enumerate(words):
                if word in action_words and i + 1 < len(words):
                    params["action"] = word
                    params["target"] = " ".join(words[i + 1:])
                    break
        
        elif intent == "smart_home":
            # Device and action extraction
            if "lights" in text:
                params["device_type"] = "lights"
                if "dim" in text or "brightness" in text:
                    params["action"] = "dim"
                elif "on" in text:
                    params["action"] = "on"
                elif "off" in text:
                    params["action"] = "off"
        
        return params


class CoreOrchestrator(MCPServer):
    """Main orchestrator that coordinates all AI modules"""
    
    def __init__(self):
        super().__init__("ai-servis-core", "1.0.0")
        self.services: Dict[str, ServiceInfo] = {}
        self.mcp_clients: Dict[str, MCPClient] = {}
        self.nlp_processor = NLPProcessor()
        self.setup_tools()
    
    def setup_tools(self):
        """Setup core orchestrator tools"""
        
        # Voice command processing tool
        voice_command_tool = create_tool(
            name="process_voice_command",
            description="Process natural language voice command and route to appropriate services",
            schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The voice command text to process"
                    },
                    "context": {
                        "type": "object",
                        "description": "Optional context information",
                        "properties": {
                            "user_id": {"type": "string"},
                            "location": {"type": "string"},
                            "time": {"type": "string"}
                        }
                    }
                },
                "required": ["text"]
            },
            handler=self.handle_voice_command
        )
        self.add_tool(voice_command_tool)
        
        # Service management tools
        list_services_tool = create_tool(
            name="list_services",
            description="List all registered services and their status",
            schema={
                "type": "object",
                "properties": {}
            },
            handler=self.handle_list_services
        )
        self.add_tool(list_services_tool)
        
        # Health check tool
        health_check_tool = create_tool(
            name="health_check",
            description="Check health of all services",
            schema={
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Optional specific service to check"
                    }
                }
            },
            handler=self.handle_health_check
        )
        self.add_tool(health_check_tool)
    
    async def handle_voice_command(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Handle voice command processing"""
        logger.info(f"Processing voice command: {text}")
        
        try:
            # Parse the command
            parsed = await self.nlp_processor.parse_command(text)
            logger.info(f"Parsed command: {parsed}")
            
            # Route to appropriate service based on intent
            result = await self._route_command(parsed, context)
            
            return f"Command processed successfully: {result}"
            
        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            return f"Error processing command: {str(e)}"
    
    async def handle_list_services(self) -> Dict[str, Any]:
        """List all registered services"""
        return {
            "services": {
                name: {
                    "host": service.host,
                    "port": service.port,
                    "capabilities": service.capabilities,
                    "health_status": service.health_status,
                    "last_seen": service.last_seen.isoformat() if service.last_seen else None
                }
                for name, service in self.services.items()
            },
            "total_services": len(self.services)
        }
    
    async def handle_health_check(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Check health of services"""
        results = {}
        
        services_to_check = [service_name] if service_name else list(self.services.keys())
        
        for name in services_to_check:
            if name in self.services:
                try:
                    # Check service health via MCP client
                    client = self.mcp_clients.get(name)
                    if client and client.connected:
                        # Try to ping the service
                        try:
                            # Simple health check - could be replaced with actual ping
                            results[name] = "healthy"
                            self.services[name].health_status = "healthy"
                            self.services[name].last_seen = datetime.now()
                        except Exception as ping_error:
                            logger.warning(f"Health check ping failed for {name}: {ping_error}")
                            results[name] = "ping_failed"
                            self.services[name].health_status = "unhealthy"
                    else:
                        results[name] = "disconnected"
                        self.services[name].health_status = "disconnected"
                except Exception as e:
                    results[name] = f"error: {str(e)}"
                    self.services[name].health_status = "error"
            else:
                results[name] = "not_found"
        
        return {"health_check_results": results}
    
    async def _route_command(self, parsed_command: Dict[str, Any], context: Optional[Dict[str, Any]]) -> str:
        """Route parsed command to appropriate service"""
        intent = parsed_command["intent"]
        parameters = parsed_command["parameters"]
        
        if intent == "play_music":
            return await self._call_service("ai-audio-assistant", "play_music", parameters)
        
        elif intent == "control_volume":
            return await self._call_service("ai-audio-assistant", "set_volume", parameters)
        
        elif intent == "switch_audio":
            return await self._call_service("ai-audio-assistant", "switch_audio_output", parameters)
        
        elif intent == "system_control":
            # Determine which platform controller to use
            platform = os.name  # Simple platform detection
            service_name = f"ai-platform-{platform}"
            return await self._call_service(service_name, "execute_command", parameters)
        
        elif intent == "smart_home":
            return await self._call_service("ai-home-automation", "control_device", parameters)
        
        elif intent == "communication":
            return await self._call_service("ai-communications", "send_message", parameters)
        
        elif intent == "navigation":
            return await self._call_service("ai-maps-navigation", "get_directions", parameters)
        
        else:
            return f"Unknown intent: {intent}. Available intents: {list(self.nlp_processor.intent_patterns.keys())}"
    
    async def _call_service(self, service_name: str, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Call a tool on a specific service"""
        if service_name not in self.mcp_clients:
            return f"Service {service_name} not available"

        client = self.mcp_clients[service_name]
        if not client.connected:
            return f"Service {service_name} is not connected"

        try:
            result = await client.call_tool(tool_name, parameters)
            return f"Service {service_name} responded: {result}"
        except Exception as e:
            logger.error(f"Error calling service {service_name}: {e}")
            # Check if this is a connection error and mark service as unhealthy
            if "Connection closed" in str(e) or "timeout" in str(e).lower():
                if service_name in self.services:
                    self.services[service_name].health_status = "disconnected"
            return f"Error calling service {service_name}: {str(e)}"
    
    async def register_service(self, service_name: str, host: str, port: int, capabilities: List[str]):
        """Register a new service"""
        service_info = ServiceInfo(
            name=service_name,
            host=host,
            port=port,
            capabilities=capabilities,
            health_status="connecting",
            last_seen=datetime.now()
        )

        self.services[service_name] = service_info
        logger.info(f"Registered service: {service_name} at {host}:{port}")

        # Try to connect to the service
        try:
            client = MCPClient(max_reconnect_attempts=5, reconnect_delay=3.0)

            # Create WebSocket transport factory for reconnection
            async def create_transport():
                try:
                    websocket = await websockets.connect(f"ws://{host}:{port}")
                    return WebSocketTransport(websocket)
                except Exception as e:
                    logger.error(f"Failed to create WebSocket transport to {host}:{port}: {e}")
                    raise

            # Connect with transport factory for reconnection support
            transport = await create_transport()
            await client.connect(transport, create_transport, timeout=15.0)

            self.mcp_clients[service_name] = client
            service_info.health_status = "healthy"
            logger.info(f"Successfully connected to service: {service_name}")

        except Exception as e:
            logger.error(f"Failed to connect to service {service_name}: {e}")
            service_info.health_status = "disconnected"
    
    async def start_http_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start HTTP server for REST API"""
        from aiohttp import web, web_request
        
        app = web.Application()
        
        async def handle_voice_command_http(request: web_request.Request) -> web.Response:
            """HTTP handler for voice commands"""
            data = await request.json()
            text = data.get("text", "")
            context = data.get("context", {})
            
            result = await self.handle_voice_command(text, context)
            
            return web.json_response({
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
        
        async def handle_health_http(request: web_request.Request) -> web.Response:
            """HTTP handler for health checks"""
            service_name = request.query.get("service")
            result = await self.handle_health_check(service_name)
            return web.json_response(result)
        
        async def handle_services_http(request: web_request.Request) -> web.Response:
            """HTTP handler for listing services"""
            result = await self.handle_list_services()
            return web.json_response(result)
        
        # Routes
        app.router.add_post("/api/voice", handle_voice_command_http)
        app.router.add_get("/api/health", handle_health_http)
        app.router.add_get("/api/services", handle_services_http)
        
        # CORS support
        async def add_cors_headers(request, response):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        
        app.middlewares.append(add_cors_headers)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"HTTP server started on {host}:{port}")
        return runner


async def main():
    """Main entry point"""
    logger.info("Starting MIA Core Orchestrator")
    
    # Create orchestrator
    orchestrator = CoreOrchestrator()
    
    # Register some example services (in real implementation, these would register themselves)
    await orchestrator.register_service("ai-audio-assistant", "localhost", 8082, ["audio", "music", "voice"])
    await orchestrator.register_service("ai-platform-linux", "localhost", 8083, ["system", "process", "file"])
    
    # Start HTTP server
    runner = await orchestrator.start_http_server()
    
    try:
        # Keep running
        logger.info("Core Orchestrator is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
            
            # Periodic health checks
            await orchestrator.handle_health_check()
            await asyncio.sleep(30)  # Check every 30 seconds
            
    except KeyboardInterrupt:
        logger.info("Shutting down Core Orchestrator")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())