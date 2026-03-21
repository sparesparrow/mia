"""
FlatBuffers-to-JSON-RPC Translation Gateway

Bridges MQTT (FlatBuffers binary) with MCP servers (JSON-RPC 2.0).
Also connects to the ZeroMQ broker for internal message routing.

Architecture:
  MQTT (ESP32/devices) ↔ Gateway ↔ ZMQ Broker (port 5555)
                                  ↔ MCP Servers (JSON-RPC)
"""

import asyncio
import json
import logging
import os
import sys
import uuid

import zmq
import zmq.asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.mcp_framework import MCPServer
from shared.topics import (
    SUBSCRIBE_ALL, TOPIC_PREFIX, build_topic, parse_topic,
)

from .fb_to_jsonrpc import translate_fb_to_jsonrpc
from .jsonrpc_to_fb import translate_jsonrpc_to_fb
from .topic_router import route_topic, LAYER_TO_SERVICE

logger = logging.getLogger(__name__)

# Configuration defaults
DEFAULT_MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
DEFAULT_MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
DEFAULT_ZMQ_BROKER = os.environ.get("ZMQ_BROKER", "tcp://localhost:5555")
DEFAULT_GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8085"))


class FlatBuffersGateway(MCPServer):
    """Gateway that translates between FlatBuffers/MQTT and JSON-RPC/MCP."""

    def __init__(self, name="flatbuffers-gateway", port=DEFAULT_GATEWAY_PORT):
        super().__init__(name=name, port=port)
        self.mqtt_client = None
        self.zmq_context = None
        self.zmq_socket = None
        self._running = False
        self._tasks = []

        # Register MCP tools
        self._register_tools()

    def _register_tools(self):
        """Register gateway-specific MCP tools."""
        self.register_tool(
            name="get_gateway_status",
            description="Get the status of the FlatBuffers gateway",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_get_status,
        )
        self.register_tool(
            name="publish_to_device",
            description="Publish a message to a device via MQTT",
            input_schema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string"},
                    "layer": {"type": "string"},
                    "data_type": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["device_id", "layer", "data_type", "payload"],
            },
            handler=self._handle_publish_to_device,
        )
        self.register_tool(
            name="list_cognitive_routes",
            description="List all registered cognitive layer to MCP service routes",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_list_routes,
        )

    async def initialize(self):
        """Initialize MQTT and ZMQ connections."""
        logger.info("Initializing FlatBuffers Gateway...")

        # Initialize ZMQ DEALER socket to connect to broker
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.DEALER)
        self.zmq_socket.setsockopt_string(zmq.IDENTITY, f"fb-gateway-{uuid.uuid4().hex[:8]}")
        self.zmq_socket.connect(DEFAULT_ZMQ_BROKER)
        logger.info("Connected to ZMQ broker at %s", DEFAULT_ZMQ_BROKER)

        # Initialize MQTT client
        try:
            from asyncio_mqtt import Client as AsyncMQTTClient
            self.mqtt_client = AsyncMQTTClient(DEFAULT_MQTT_HOST, DEFAULT_MQTT_PORT)
            await self.mqtt_client.connect()
            logger.info("Connected to MQTT broker at %s:%d", DEFAULT_MQTT_HOST, DEFAULT_MQTT_PORT)
        except ImportError:
            logger.warning("asyncio-mqtt not available, MQTT disabled")
            self.mqtt_client = None
        except Exception as e:
            logger.warning("Failed to connect to MQTT broker: %s", e)
            self.mqtt_client = None

        self._running = True

        # Start background tasks
        if self.mqtt_client:
            self._tasks.append(asyncio.create_task(self._mqtt_listener()))
        self._tasks.append(asyncio.create_task(self._zmq_listener()))

        logger.info("FlatBuffers Gateway initialized")

    async def shutdown(self):
        """Clean shutdown of all connections."""
        logger.info("Shutting down FlatBuffers Gateway...")
        self._running = False

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if self.mqtt_client:
            try:
                await self.mqtt_client.disconnect()
            except Exception:
                pass

        if self.zmq_socket:
            self.zmq_socket.close()
        if self.zmq_context:
            self.zmq_context.term()

        logger.info("FlatBuffers Gateway shut down")

    async def _mqtt_listener(self):
        """Listen for MQTT messages and translate to MCP calls."""
        try:
            async with self.mqtt_client.filtered_messages(SUBSCRIBE_ALL) as messages:
                await self.mqtt_client.subscribe(SUBSCRIBE_ALL)
                logger.info("Subscribed to MQTT topic: %s", SUBSCRIBE_ALL)

                async for message in messages:
                    if not self._running:
                        break
                    try:
                        await self._handle_mqtt_message(
                            message.topic, message.payload
                        )
                    except Exception as e:
                        logger.error("Error handling MQTT message on %s: %s",
                                     message.topic, e)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("MQTT listener error: %s", e)

    async def _zmq_listener(self):
        """Listen for ZMQ messages from the broker."""
        try:
            while self._running:
                try:
                    frames = await asyncio.wait_for(
                        self.zmq_socket.recv_multipart(), timeout=1.0
                    )
                    await self._handle_zmq_message(frames)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error("Error receiving ZMQ message: %s", e)
        except asyncio.CancelledError:
            pass

    async def _handle_mqtt_message(self, topic: str, payload: bytes):
        """Process an incoming MQTT message."""
        route = route_topic(topic)
        if not route:
            logger.debug("Unroutable MQTT topic: %s", topic)
            return

        # Translate FlatBuffers → JSON-RPC
        jsonrpc_request = translate_fb_to_jsonrpc(topic, payload)
        if not jsonrpc_request:
            return

        logger.debug("Routing %s -> %s.%s", topic, route["service"], route["tool"])

        # Forward to ZMQ broker for internal routing
        await self.zmq_socket.send_multipart([
            route["service"].encode("utf-8"),
            json.dumps(jsonrpc_request).encode("utf-8"),
        ])

    async def _handle_zmq_message(self, frames: list):
        """Process a ZMQ message from the broker (response path)."""
        if len(frames) < 2:
            return

        try:
            response = json.loads(frames[-1])
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        # If the response contains routing info, publish back to MQTT
        if self.mqtt_client and "result" in response:
            result = response["result"]
            if isinstance(result, dict) and "reply_topic" in result:
                reply_topic = result.pop("reply_topic")
                fb_bytes = translate_jsonrpc_to_fb(response)
                await self.mqtt_client.publish(reply_topic, fb_bytes)

    # ---- MCP Tool Handlers ----

    async def _handle_get_status(self, params: dict) -> dict:
        return {
            "status": "running" if self._running else "stopped",
            "mqtt_connected": self.mqtt_client is not None,
            "zmq_connected": self.zmq_socket is not None and not self.zmq_socket.closed,
        }

    async def _handle_publish_to_device(self, params: dict) -> dict:
        if not self.mqtt_client:
            return {"status": "error", "message": "MQTT not connected"}

        topic = build_topic(
            params["device_id"], params["layer"], params["data_type"]
        )
        payload = json.dumps(params["payload"]).encode("utf-8")
        await self.mqtt_client.publish(topic, payload)
        return {"status": "success", "topic": topic}

    async def _handle_list_routes(self, params: dict) -> dict:
        return {"routes": {k: v for k, v in LAYER_TO_SERVICE.items()}}


async def main():
    """Entry point for the FlatBuffers gateway."""
    logging.basicConfig(level=logging.INFO)
    gateway = FlatBuffersGateway()
    await gateway.initialize()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await gateway.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
