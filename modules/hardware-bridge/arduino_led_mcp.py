"""
MCP Server for Arduino LED Strip Control

Provides MCP tools for controlling Arduino Uno LED strip via the MCP framework.
Integrates with the core orchestrator for AI-driven LED control.
"""

import logging
import sys
import os
from typing import Dict, Any, Optional, List

# Add parent directory to path to import mcp_framework
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mcp_framework import MCPServer, Tool, create_tool, WebSocketTransport

from .arduino_led_controller import ArduinoLEDController

logger = logging.getLogger(__name__)


class ArduinoLEDMCPServer(MCPServer):
    """MCP Server for Arduino LED strip control"""

    def __init__(self, serial_port: str = "/dev/ttyUSB0", name: str = "arduino-led-controller", version: str = "1.0.0"):
        """
        Initialize Arduino LED MCP Server
        
        Args:
            serial_port: Serial port path for Arduino
            name: MCP server name
            version: MCP server version
        """
        super().__init__(name=name, version=version)
        self.led_controller = ArduinoLEDController(serial_port)
        self._register_tools()

    def _register_tools(self):
        """Register MCP tools for LED control"""
        
        # Set LED color tool
        self.add_tool(create_tool(
            name="arduino_led_set_color",
            description="Set all LEDs on Arduino LED strip to a specific color",
            schema={
                "type": "object",
                "properties": {
                    "r": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Red value (0-255)"},
                    "g": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Green value (0-255)"},
                    "b": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Blue value (0-255)"}
                },
                "required": ["r", "g", "b"]
            },
            handler=self._handle_set_color
        ))

        # Set brightness tool
        self.add_tool(create_tool(
            name="arduino_led_set_brightness",
            description="Set brightness of Arduino LED strip",
            schema={
                "type": "object",
                "properties": {
                    "brightness": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Brightness (0-255)"}
                },
                "required": ["brightness"]
            },
            handler=self._handle_set_brightness
        ))

        # Set individual LED tool
        self.add_tool(create_tool(
            name="arduino_led_set_led",
            description="Set a specific LED on the strip to a color",
            schema={
                "type": "object",
                "properties": {
                    "led": {"type": "integer", "minimum": 0, "maximum": 22, "description": "LED index (0-22)"},
                    "r": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Red value (0-255)"},
                    "g": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Green value (0-255)"},
                    "b": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Blue value (0-255)"}
                },
                "required": ["led", "r", "g", "b"]
            },
            handler=self._handle_set_led
        ))

        # Start animation tool
        self.add_tool(create_tool(
            name="arduino_led_animation",
            description="Start an animation on the LED strip",
            schema={
                "type": "object",
                "properties": {
                    "animation": {
                        "type": "string",
                        "enum": ["blink", "fade", "rainbow", "chase"],
                        "description": "Animation type"
                    },
                    "speed": {"type": "integer", "minimum": 10, "maximum": 5000, "description": "Animation speed in milliseconds"},
                    "r": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Red value for chase animation"},
                    "g": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Green value for chase animation"},
                    "b": {"type": "integer", "minimum": 0, "maximum": 255, "description": "Blue value for chase animation"}
                },
                "required": ["animation"]
            },
            handler=self._handle_animation
        ))

        # Clear LEDs tool
        self.add_tool(create_tool(
            name="arduino_led_clear",
            description="Clear all LEDs (turn off)",
            schema={
                "type": "object",
                "properties": {}
            },
            handler=self._handle_clear
        ))

        # Get status tool
        self.add_tool(create_tool(
            name="arduino_led_status",
            description="Get current status of the LED strip",
            schema={
                "type": "object",
                "properties": {}
            },
            handler=self._handle_status
        ))

    def _handle_set_color(self, **arguments) -> str:
        """Handle set_color tool call"""
        try:
            r = arguments["r"]
            g = arguments["g"]
            b = arguments["b"]
            
            success = self.led_controller.set_color(r, g, b)
            
            if success:
                return f"LED strip color set to RGB({r}, {g}, {b})"
            else:
                raise Exception("Failed to set LED strip color")
        except Exception as e:
            logger.error(f"Error setting LED color: {e}")
            raise

    def _handle_set_brightness(self, **arguments) -> str:
        """Handle set_brightness tool call"""
        try:
            brightness = arguments["brightness"]
            
            success = self.led_controller.set_brightness(brightness)
            
            if success:
                return f"LED strip brightness set to {brightness}"
            else:
                raise Exception("Failed to set LED strip brightness")
        except Exception as e:
            logger.error(f"Error setting LED brightness: {e}")
            raise

    def _handle_set_led(self, **arguments) -> str:
        """Handle set_led tool call"""
        try:
            led_index = arguments["led"]
            r = arguments["r"]
            g = arguments["g"]
            b = arguments["b"]
            
            success = self.led_controller.set_led(led_index, r, g, b)
            
            if success:
                return f"LED {led_index} set to RGB({r}, {g}, {b})"
            else:
                raise Exception(f"Failed to set LED {led_index}")
        except Exception as e:
            logger.error(f"Error setting LED: {e}")
            raise

    def _handle_animation(self, **arguments) -> str:
        """Handle animation tool call"""
        try:
            animation = arguments["animation"]
            speed = arguments.get("speed", 500)
            
            if animation == "rainbow":
                success = self.led_controller.start_rainbow(speed)
            elif animation == "chase":
                r = arguments.get("r", 255)
                g = arguments.get("g", 0)
                b = arguments.get("b", 0)
                success = self.led_controller.start_chase(r, g, b, speed)
            else:
                success = self.led_controller.start_animation(animation, speed=speed)
            
            if success:
                return f"Started {animation} animation with speed {speed}ms"
            else:
                raise Exception(f"Failed to start {animation} animation")
        except Exception as e:
            logger.error(f"Error starting animation: {e}")
            raise

    def _handle_clear(self, **arguments) -> str:
        """Handle clear tool call"""
        try:
            success = self.led_controller.clear()
            
            if success:
                return "All LEDs cleared"
            else:
                raise Exception("Failed to clear LEDs")
        except Exception as e:
            logger.error(f"Error clearing LEDs: {e}")
            raise

    def _handle_status(self, **arguments) -> str:
        """Handle status tool call"""
        try:
            status = self.led_controller.get_status()
            
            if status:
                status_text = f"LED Strip Status:\n"
                status_text += f"  Brightness: {status.get('brightness', 'N/A')}\n"
                status_text += f"  Current Color: RGB({status.get('current_color', {}).get('r', 'N/A')}, "
                status_text += f"{status.get('current_color', {}).get('g', 'N/A')}, "
                status_text += f"{status.get('current_color', {}).get('b', 'N/A')})\n"
                status_text += f"  Animation: {status.get('animation', 'N/A')}\n"
                status_text += f"  Number of LEDs: {status.get('num_leds', 'N/A')}"
                
                return status_text
            else:
                raise Exception("Failed to get LED strip status")
        except Exception as e:
            logger.error(f"Error getting LED status: {e}")
            raise


if __name__ == "__main__":
    import asyncio
    import sys
    import websockets

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    serial_port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    websocket_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8084

    server = ArduinoLEDMCPServer(
        serial_port=serial_port,
        name="arduino-led-controller"
    )

    # Connect to Arduino
    if not server.led_controller.connect():
        logger.error("Failed to connect to Arduino LED controller")
        sys.exit(1)

    async def main():
        async with websockets.serve(
            lambda ws, path: server.serve(WebSocketTransport(ws)),
            "localhost",
            websocket_port
        ):
            logger.info(f"Arduino LED MCP Server listening on ws://localhost:{websocket_port}")
            await asyncio.Future()  # Run forever

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.led_controller.disconnect()
