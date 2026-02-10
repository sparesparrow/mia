#!/usr/bin/env python3
"""
Integration test for hardware bridge components

Tests communication between Python clients and C++ servers.
"""

import asyncio
import logging
import time
from hardware_client import HardwareClient
from mcp_client import MCPClient
from gpio_controller import GPIOController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_hardware_client():
    """Test basic hardware client TCP communication"""
    logger.info("Testing Hardware Client...")

    client = HardwareClient()

    # Test GPIO operations (these will fail without hardware, but test connectivity)
    try:
        # Configure pin as output
        success = client.configure_gpio(17, "output")
        logger.info(f"GPIO configure result: {success}")

        # Try to set pin high
        success = client.set_gpio_value(17, 1)
        logger.info(f"GPIO set result: {success}")

        # Try to read pin value
        value = client.get_gpio_value(17)
        logger.info(f"GPIO read result: {value}")

        # Get status
        status = client.get_gpio_status()
        logger.info(f"GPIO status: {status}")

    except Exception as e:
        logger.error(f"Hardware client test failed: {e}")

    client.disconnect()


async def test_mcp_client():
    """Test MCP client communication with C++ MCP server"""
    logger.info("Testing MCP Client...")

    client = MCPClient()

    try:
        # Initialize MCP connection
        success = await client.initialize()
        if not success:
            logger.error("Failed to initialize MCP client")
            return

        # Get available tools
        tools = client.get_available_tools()
        logger.info(f"Available tools: {[t.name for t in tools]}")

        # Test download tool (will fail without real server, but tests protocol)
        result = client.execute_tool("download_file", {
            "url": "http://example.com/test.txt",
            "output_path": "/tmp/test.txt",
            "session_id": 12345
        })
        logger.info(f"Download result: {result}")

        # Test GPIO tool
        result = client.execute_tool("gpio_task", {
            "action": "configure",
            "pin": 17,
            "direction": "output"
        })
        logger.info(f"GPIO task result: {result}")

    except Exception as e:
        logger.error(f"MCP client test failed: {e}")

    client.disconnect()


async def test_gpio_controller():
    """Test high-level GPIO controller"""
    logger.info("Testing GPIO Controller...")

    controller = GPIOController()

    try:
        # Test output pin setup
        success = controller.setup_output_pin(17, 1)
        logger.info(f"Setup output pin: {success}")

        # Test pin toggle
        value = controller.toggle_pin(17)
        logger.info(f"Toggle pin result: {value}")

        # Test LED control
        success = controller.control_led(17, True)
        logger.info(f"LED control: {success}")

        # Test status
        status = controller.get_all_pins_status()
        logger.info(f"Pins status: {status}")

    except Exception as e:
        logger.error(f"GPIO controller test failed: {e}")


async def main():
    """Run all integration tests"""
    logger.info("Starting hardware bridge integration tests...")

    # Note: These tests assume the C++ servers are running
    # In a real environment, you would start the servers first

    logger.info("Note: These tests require C++ servers to be running")
    logger.info("Start hardware-server and mcp-server before running tests")

    try:
        await test_hardware_client()
        await asyncio.sleep(1)

        await test_mcp_client()
        await asyncio.sleep(1)

        await test_gpio_controller()

    except KeyboardInterrupt:
        logger.info("Tests interrupted")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")

    logger.info("Integration tests completed")


if __name__ == "__main__":
    asyncio.run(main())