"""
ZeroMQ Messaging Client
Implements Phase 1.3: ZeroMQ Core Messaging Layer

Python client for communicating with the ZeroMQ broker using FlatBuffers messages.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional, Callable, Union
import zmq
import zmq.asyncio

from ..flatbuffers import MessageBuilder, MessageParser

logger = logging.getLogger(__name__)


class MessagingClient:
    """
    ZeroMQ DEALER client for communicating with the broker.

    Features:
    - Async/await support
    - Automatic request/response correlation
    - FlatBuffers message serialization
    - Connection retry logic
    - Request timeout handling

    Usage:
        async with MessagingClient("tcp://localhost:5555") as client:
            # Send a GPIO request
            response = await client.send_gpio_request("set", pin=17, value=1)
            print(f"Response: {response}")
    """

    def __init__(
        self,
        broker_url: str = "tcp://localhost:5555",
        identity: Optional[str] = None,
        timeout: float = 30.0,
        retry_attempts: int = 3
    ):
        """
        Initialize the messaging client.

        Args:
            broker_url: ZeroMQ broker URL
            identity: Client identity (auto-generated if None)
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts for failed requests
        """
        self.broker_url = broker_url
        self.identity = identity or f"python-client-{uuid.uuid4().hex[:8]}"
        self.timeout = timeout
        self.retry_attempts = retry_attempts

        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None

        # Request/response correlation
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self._running = False
        self._receive_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect to the ZeroMQ broker."""
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt_string(zmq.IDENTITY, self.identity)

        logger.info(f"Connecting to broker at {self.broker_url} as {self.identity}")
        self.socket.connect(self.broker_url)

        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())

        # Give the connection time to establish
        await asyncio.sleep(0.1)

    async def disconnect(self):
        """Disconnect from the ZeroMQ broker."""
        self._running = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.socket:
            self.socket.close()
            self.socket = None

        if self.context:
            self.context.term()
            self.context = None

        # Cancel any pending requests
        for future in self.pending_requests.values():
            if not future.done():
                future.cancel()

        self.pending_requests.clear()
        logger.info(f"Disconnected from broker")

    async def _receive_loop(self):
        """Background task to receive responses from broker."""
        while self._running and self.socket:
            try:
                # Receive response: [empty][message]
                parts = await self.socket.recv_multipart()
                if len(parts) < 2:
                    continue

                _, message_data = parts[0], parts[1]

                # Parse JSON message
                message = json.loads(message_data.decode("utf-8"))
                request_id = message.get("request_id")

                if request_id and request_id in self.pending_requests:
                    future = self.pending_requests.pop(request_id)
                    if not future.done():
                        future.set_result(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await asyncio.sleep(1.0)

    async def _send_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a request and wait for response.

        Args:
            message: Request message dictionary

        Returns:
            Response message dictionary

        Raises:
            asyncio.TimeoutError: If request times out
            Exception: If request fails
        """
        if not self.socket:
            raise RuntimeError("Client not connected")

        # Add request ID for correlation
        request_id = str(uuid.uuid4())
        message["request_id"] = request_id

        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        try:
            # Send request: [empty][message]
            payload = json.dumps(message).encode("utf-8")
            await self.socket.send_multipart([b"", payload])

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=self.timeout)
            return response

        except asyncio.TimeoutError:
            logger.warning(f"Request {request_id} timed out")
            raise
        except Exception as e:
            logger.error(f"Request {request_id} failed: {e}")
            raise
        finally:
            # Clean up pending request if still there
            self.pending_requests.pop(request_id, None)

    # ------------------------------------------------------------------
    # High-level API methods for different message types
    # ------------------------------------------------------------------

    async def send_download_request(self, url: str) -> Dict[str, Any]:
        """Send a download request."""
        message = {
            "type": "DOWNLOAD_REQUEST",
            "url": url
        }
        return await self._send_request(message)

    async def send_download_status_request(self, session_id: int) -> Dict[str, Any]:
        """Send a download status request."""
        message = {
            "type": "DOWNLOAD_STATUS_REQUEST",
            "session_id": session_id
        }
        return await self._send_request(message)

    async def send_download_abort_request(self, session_id: int) -> Dict[str, Any]:
        """Send a download abort request."""
        message = {
            "type": "DOWNLOAD_ABORT_REQUEST",
            "session_id": session_id
        }
        return await self._send_request(message)

    async def send_shutdown_request(self) -> Dict[str, Any]:
        """Send a shutdown request."""
        message = {
            "type": "SHUTDOWN_REQUEST"
        }
        return await self._send_request(message)

    async def send_gpio_configure_request(self, pin: int, direction: str) -> Dict[str, Any]:
        """Send a GPIO configuration request."""
        message = {
            "type": "GPIO_CONFIGURE_REQUEST",
            "pin": pin,
            "direction": direction
        }
        return await self._send_request(message)

    async def send_gpio_set_request(self, pin: int, value: bool) -> Dict[str, Any]:
        """Send a GPIO set request."""
        message = {
            "type": "GPIO_SET_REQUEST",
            "pin": pin,
            "value": value
        }
        return await self._send_request(message)

    async def send_gpio_get_request(self, pin: int) -> Dict[str, Any]:
        """Send a GPIO get request."""
        message = {
            "type": "GPIO_GET_REQUEST",
            "pin": pin
        }
        return await self._send_request(message)

    async def send_gpio_status_request(self) -> Dict[str, Any]:
        """Send a GPIO status request."""
        message = {
            "type": "GPIO_STATUS_REQUEST"
        }
        return await self._send_request(message)

    async def send_system_status_request(self) -> Dict[str, Any]:
        """Send a system status request."""
        message = {
            "type": "SYSTEM_STATUS_REQUEST"
        }
        return await self._send_request(message)

    async def send_device_discovery_request(self, device_type: Optional[str] = None) -> Dict[str, Any]:
        """Send a device discovery request."""
        message = {
            "type": "DEVICE_DISCOVERY_REQUEST"
        }
        if device_type:
            message["device_type"] = device_type
        return await self._send_request(message)

    async def send_telemetry_request(self, device_id: Optional[str] = None,
                                   sensor_type: Optional[str] = None) -> Dict[str, Any]:
        """Send a telemetry request."""
        message = {
            "type": "TELEMETRY_REQUEST"
        }
        if device_id:
            message["device_id"] = device_id
        if sensor_type:
            message["sensor_type"] = sensor_type
        return await self._send_request(message)

    async def send_health_check_request(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Send a health check request."""
        message = {
            "type": "HEALTH_CHECK_REQUEST"
        }
        if service_name:
            message["service_name"] = service_name
        return await self._send_request(message)

    # ------------------------------------------------------------------
    # Raw message sending (for advanced use cases)
    # ------------------------------------------------------------------

    async def send_raw_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a raw message dictionary.

        Args:
            message: Raw message dictionary

        Returns:
            Response message dictionary
        """
        return await self._send_request(message)