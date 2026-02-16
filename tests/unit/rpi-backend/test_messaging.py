#!/usr/bin/env python3
"""
Test script for the ZeroMQ messaging layer.
Tests the integration between MessagingClient and ZeroMQBroker.
"""

import asyncio
import json
import logging
import threading
import time
from typing import Dict, Any

from .client import MessagingClient
from .broker import ZeroMQBroker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockHardwareWorker:
    """Mock hardware worker that responds to GPIO requests."""

    def __init__(self, broker_url: str = "tcp://localhost:5555"):
        self.broker_url = broker_url
        self.running = False
        self.thread = None

    def start(self):
        """Start the mock worker in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run_worker)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Mock hardware worker started")

    def stop(self):
        """Stop the mock worker."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("Mock hardware worker stopped")

    def _run_worker(self):
        """Run the worker loop."""
        import zmq

        context = zmq.Context()
        socket = context.socket(zmq.DEALER)
        socket.setsockopt_string(zmq.IDENTITY, "mock-hardware-worker")
        socket.connect(self.broker_url)

        # Register as worker
        register_msg = {
            "type": "WORKER_REGISTER",
            "worker_type": "hardware",
            "capabilities": ["gpio"]
        }
        socket.send_multipart([b"", json.dumps(register_msg).encode('utf-8')])
        logger.info("Worker registered with broker")

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(1000))  # 1 second timeout
                if socket in socks:
                    # Receive request: [empty][message]
                    parts = socket.recv_multipart()
                    if len(parts) < 2:
                        continue

                    _, message_data = parts[0], parts[1]

                    try:
                        request = json.loads(message_data.decode('utf-8'))
                        logger.info(f"Worker received request: {request}")

                        # Handle different request types
                        response = self._handle_request(request)

                        # Send response back with same request_id
                        socket.send_multipart([b"", json.dumps(response).encode('utf-8')])
                        logger.info(f"Worker sent response: {response}")

                    except Exception as e:
                        logger.error(f"Error handling request: {e}")

            except zmq.ZMQError as e:
                if self.running:
                    logger.error(f"ZMQ error in worker: {e}")
                break

        socket.close()
        context.term()

    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a request and return a response."""
        request_type = request.get("type", "")
        request_id = request.get("request_id", "")

        if request_type == "GPIO_CONFIGURE_REQUEST":
            return {
                "type": "GPIO_CONFIGURE_RESPONSE",
                "request_id": request_id,
                "success": True,
                "pin": request.get("pin", 0),
                "message": f"GPIO pin {request.get('pin')} configured as {request.get('direction')}"
            }

        elif request_type == "GPIO_SET_REQUEST":
            return {
                "type": "GPIO_SET_RESPONSE",
                "request_id": request_id,
                "success": True,
                "pin": request.get("pin", 0),
                "message": f"GPIO pin {request.get('pin')} set to {request.get('value')}"
            }

        elif request_type == "GPIO_GET_REQUEST":
            return {
                "type": "GPIO_GET_RESPONSE",
                "request_id": request_id,
                "success": True,
                "pin": request.get("pin", 0),
                "value": True  # Mock value
            }

        elif request_type == "GPIO_STATUS_REQUEST":
            return {
                "type": "GPIO_STATUS_RESPONSE",
                "request_id": request_id,
                "pins": [
                    {"pin": 17, "direction": "output", "value": True},
                    {"pin": 18, "direction": "input", "value": False}
                ]
            }

        elif request_type == "SYSTEM_STATUS_REQUEST":
            return {
                "type": "SYSTEM_STATUS_RESPONSE",
                "request_id": request_id,
                "uptime_seconds": 3600,
                "memory_used_mb": 256,
                "memory_total_mb": 1024,
                "cpu_usage_percent": 15.5,
                "active_devices": 2,
                "timestamp": int(time.time() * 1000)
            }

        else:
            return {
                "type": "ERROR",
                "request_id": request_id,
                "error": f"Unknown request type: {request_type}"
            }


async def test_messaging():
    """Test the messaging layer integration."""
    logger.info("Starting messaging layer test...")

    # Start the broker
    broker = ZeroMQBroker(router_port=5557)  # Use different port for testing
    broker.start()

    # Start mock hardware worker
    worker = MockHardwareWorker("tcp://localhost:5557")
    worker.start()

    # Give them time to start
    await asyncio.sleep(1.0)

    try:
        # Test client connection and requests
        async with MessagingClient("tcp://localhost:5557") as client:
            logger.info("Testing GPIO configure request...")
            response = await client.send_gpio_configure_request(17, "output")
            logger.info(f"Response: {response}")
            assert response.get("success") == True

            logger.info("Testing GPIO set request...")
            response = await client.send_gpio_set_request(17, True)
            logger.info(f"Response: {response}")
            assert response.get("success") == True

            logger.info("Testing GPIO get request...")
            response = await client.send_gpio_get_request(17)
            logger.info(f"Response: {response}")
            assert response.get("success") == True

            logger.info("Testing GPIO status request...")
            response = await client.send_gpio_status_request()
            logger.info(f"Response: {response}")
            assert "pins" in response

            logger.info("Testing system status request...")
            response = await client.send_system_status_request()
            logger.info(f"Response: {response}")
            assert "uptime_seconds" in response

        logger.info("✅ All messaging tests passed!")

    finally:
        # Clean up
        worker.stop()
        broker.stop()


if __name__ == "__main__":
    asyncio.run(test_messaging())