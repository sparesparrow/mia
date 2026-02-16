"""
MCP Bridge for Hardware Control

Integrates C++ MCP server with Python MCP orchestrator for
hardware control through the MCP protocol.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import paho.mqtt.client as mqtt

from .gpio_controller import GPIOController

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


class MCPBridge:
    """Bridge between Python MCP orchestrator and C++ hardware MCP server"""

    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883,
                 hardware_host: str = "localhost", hardware_port: int = 8081):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.hardware_host = hardware_host
        self.hardware_port = hardware_port

        self.mqtt_client: Optional[mqtt.Client] = None
        self.gpio_controller = GPIOController(hardware_host, hardware_port)

        # MCP Tools
        self.tools = {
            "gpio_configure": MCPTool(
                name="gpio_configure",
                description="Configure a GPIO pin as input or output",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pin": {"type": "integer", "description": "GPIO pin number"},
                        "direction": {"type": "string", "enum": ["input", "output"], "description": "Pin direction"}
                    },
                    "required": ["pin", "direction"]
                }
            ),
            "gpio_set": MCPTool(
                name="gpio_set",
                description="Set GPIO output pin value",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pin": {"type": "integer", "description": "GPIO pin number"},
                        "value": {"type": "integer", "enum": [0, 1], "description": "Pin value (0 or 1)"}
                    },
                    "required": ["pin", "value"]
                }
            ),
            "gpio_get": MCPTool(
                name="gpio_get",
                description="Read GPIO pin value",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pin": {"type": "integer", "description": "GPIO pin number"}
                    },
                    "required": ["pin"]
                }
            ),
            "gpio_status": MCPTool(
                name="gpio_status",
                description="Get status of all configured GPIO pins",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            )
        }

    def connect_mqtt(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def disconnect_mqtt(self):
        """Disconnect from MQTT broker"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connect callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to hardware control topics
            client.subscribe("hardware/gpio/+")
            client.subscribe("hardware/status")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())

            logger.info(f"Received MQTT message on {topic}: {payload}")

            # Handle hardware control messages
            if topic.startswith("hardware/gpio/"):
                pin = int(topic.split("/")[-1])
                if "configure" in payload:
                    self.gpio_controller.setup_input_pin(pin) if payload["direction"] == "input" \
                        else self.gpio_controller.setup_output_pin(pin, payload.get("value", 0))
                elif "set" in payload:
                    self.gpio_controller.set_pin_high(pin) if payload["value"] else self.gpio_controller.set_pin_low(pin)
                elif "get" in payload:
                    value = self.gpio_controller.get_pin_value(pin)
                    # Publish response
                    response_topic = f"hardware/response/{pin}"
                    client.publish(response_topic, json.dumps({"value": value}))

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def get_available_tools(self) -> List[MCPTool]:
        """Get list of available MCP tools"""
        return list(self.tools.values())

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResult:
        """Execute MCP tool"""
        try:
            if tool_name == "gpio_configure":
                pin = arguments["pin"]
                direction = arguments["direction"]
                success = self.gpio_controller.setup_input_pin(pin) if direction == "input" \
                         else self.gpio_controller.setup_output_pin(pin)
                return MCPResult(
                    content=[{
                        "type": "text",
                        "text": f"GPIO pin {pin} configured as {direction}: {'Success' if success else 'Failed'}"
                    }]
                )

            elif tool_name == "gpio_set":
                pin = arguments["pin"]
                value = arguments["value"]
                success = self.gpio_controller.set_pin_high(pin) if value else self.gpio_controller.set_pin_low(pin)
                return MCPResult(
                    content=[{
                        "type": "text",
                        "text": f"GPIO pin {pin} set to {value}: {'Success' if success else 'Failed'}"
                    }]
                )

            elif tool_name == "gpio_get":
                pin = arguments["pin"]
                value = self.gpio_controller.get_pin_value(pin)
                if value is not None:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": f"GPIO pin {pin} value: {value}"
                        }]
                    )
                else:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": f"Failed to read GPIO pin {pin}"
                        }],
                        is_error=True
                    )

            elif tool_name == "gpio_status":
                status = self.gpio_controller.get_all_pins_status()
                if status is not None:
                    status_text = "\n".join([f"Pin {pin}: {s.direction} = {s.value}" for pin, s in status.items()])
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": f"GPIO Status:\n{status_text}"
                        }]
                    )
                else:
                    return MCPResult(
                        content=[{
                            "type": "text",
                            "text": "Failed to get GPIO status"
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

    async def run(self):
        """Run the MCP bridge"""
        if not self.connect_mqtt():
            raise RuntimeError("Failed to connect to MQTT broker")

        try:
            # Keep running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("MCP Bridge shutting down")
        finally:
            self.disconnect_mqtt()