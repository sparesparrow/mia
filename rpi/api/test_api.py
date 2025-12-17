#!/usr/bin/env python3
"""
Test script for the FastAPI hardware management API.
Tests REST endpoints and WebSocket functionality.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any
import aiohttp

from ..hardware import HardwareManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIClient:
    """Test client for the FastAPI API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, endpoint: str) -> Dict[str, Any]:
        """GET request"""
        async with self.session.get(f"{self.base_url}{endpoint}") as response:
            return await response.json()

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST request"""
        async with self.session.post(
            f"{self.base_url}{endpoint}",
            json=data,
            headers={"Content-Type": "application/json"}
        ) as response:
            return await response.json()


async def test_rest_api():
    """Test REST API endpoints"""
    logger.info("Testing REST API endpoints...")

    try:
        async with APIClient() as client:
            # Test root endpoint
            response = await client.get("/")
            assert response["service"] == "MIA Hardware Management API"
            logger.info("✓ Root endpoint works")

            # Test health check
            response = await client.get("/health")
            assert "status" in response
            assert "hardware_manager" in response
            logger.info("✓ Health check works")

            # Test hardware status
            response = await client.get("/hardware/status")
            assert "hardware" in response
            assert response["hardware"]["initialized"] == True
            logger.info("✓ Hardware status works")

            # Test GPIO configuration
            gpio_config = {
                "pin": 17,
                "mode": "output",
                "name": "Test LED"
            }
            response = await client.post("/gpio/configure", gpio_config)
            assert response["success"] == True
            assert response["pin"] == 17
            logger.info("✓ GPIO configuration works")

            # Test GPIO set
            gpio_value = {
                "pin": 17,
                "value": True
            }
            response = await client.post("/gpio/set", gpio_value)
            assert response["success"] == True
            logger.info("✓ GPIO set works")

            # Test GPIO get
            response = await client.get("/gpio/17")
            assert response["success"] == True
            assert "value" in response
            logger.info("✓ GPIO get works")

            # Test sensor registration
            sensor_config = {
                "sensor_id": "temp_test",
                "sensor_type": "temperature",
                "location": "Test Lab"
            }
            response = await client.post("/sensors/register", sensor_config)
            assert response["success"] == True
            assert response["sensor_id"] == "temp_test"
            logger.info("✓ Sensor registration works")

            # Test sensor readings
            response = await client.get("/sensors/readings")
            assert "readings" in response
            assert len(response["readings"]) >= 1
            logger.info("✓ Sensor readings work")

            # Test Arduino discovery
            response = await client.get("/arduino/devices")
            assert "devices" in response
            logger.info("✓ Arduino discovery works")

            # Test device listing
            response = await client.get("/devices")
            assert "devices" in response
            assert len(response["devices"]) >= 2  # GPIO + sensor
            logger.info("✓ Device listing works")

        logger.info("✅ REST API tests passed")

    except Exception as e:
        logger.error(f"REST API test failed: {e}")
        raise


async def test_websocket():
    """Test WebSocket functionality"""
    logger.info("Testing WebSocket functionality...")

    try:
        uri = "ws://localhost:8000/ws"
        messages_received = []

        async with websockets.connect(uri) as websocket:
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            logger.info("✓ WebSocket connection established")

            # Listen for messages for a short time
            try:
                async for message in websocket:
                    data = json.loads(message)
                    messages_received.append(data)

                    # We expect to receive some messages
                    if len(messages_received) >= 2:  # hardware status + sensor reading
                        break

            except asyncio.TimeoutError:
                pass

            # Verify we received expected message types
            message_types = {msg.get("type") for msg in messages_received}
            assert "hardware_status" in message_types
            logger.info("✓ WebSocket messages received")

        logger.info("✅ WebSocket tests passed")

    except Exception as e:
        logger.error(f"WebSocket test failed: {e}")
        raise


async def test_integration():
    """Test complete API integration"""
    logger.info("Testing complete API integration...")

    # Start hardware manager (simulated - would be done by the server)
    hardware_manager = HardwareManager()

    try:
        await hardware_manager.initialize()

        # Register some test devices
        await hardware_manager.register_gpio_pin(18, True, "Test Button")
        await hardware_manager.register_sensor("humidity", "humid_test", "Test Room")

        # Test API client interaction
        async with APIClient() as client:
            # Check that devices are registered
            response = await client.get("/devices")
            assert len(response["devices"]) >= 3  # GPIO output + GPIO input + sensor

            # Test GPIO operations
            await client.post("/gpio/configure", {"pin": 18, "mode": "input"})
            response = await client.get("/gpio/18")
            assert response["success"] == True

            # Test sensor operations
            response = await client.get("/sensors/readings")
            assert len(response["readings"]) >= 2  # temperature + humidity

        await hardware_manager.shutdown()

        logger.info("✅ API integration tests passed")

    except Exception as e:
        logger.error(f"API integration test failed: {e}")
        raise


async def main():
    """Run all API tests"""
    logger.info("Starting FastAPI hardware management API tests...")

    try:
        # Note: These tests assume the FastAPI server is running
        # In a real test environment, you'd start the server programmatically

        logger.info("Note: These tests require the FastAPI server to be running on localhost:8000")
        logger.info("Start the server with: python -m rpi.api.server")

        # Test REST API
        await test_rest_api()

        # Test WebSocket
        await test_websocket()

        # Test integration
        await test_integration()

        logger.info("🎉 All API tests passed!")

    except Exception as e:
        logger.error(f"API tests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())