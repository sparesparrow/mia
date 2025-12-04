"""
ZeroMQ Message Broker
Implements Phase 1.3: ZeroMQ Core Messaging Layer

This broker sits between:
- FastAPI clients (DEALER sockets)
- GPIO / hardware workers (DEALER sockets)

It provides a simple request/response routing mechanism using a
`request_id` field that is added to client requests and echoed by
workers in their responses.
"""
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Optional

import zmq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ZeroMQBroker:
    """
    ZeroMQ ROUTER-based message broker.

    Responsibilities:
    - Accept requests from API clients (DEALER)
    - Forward requests to available workers (DEALER)
    - Route responses from workers back to the originating client
      using a `request_id` correlation id.
    """

    def __init__(self, router_port: int = 5555):
        self.router_port = router_port
        self.context = zmq.Context()
        self.router: Optional[zmq.Socket] = None
        self.running: bool = False

        # Worker identities connected to the broker
        self.workers: Dict[bytes, bool] = {}

        # request_id -> client_identity
        self.pending_requests: Dict[str, bytes] = {}

    def start(self) -> bool:
        """Start the broker and background polling thread."""
        self.router = self.context.socket(zmq.ROUTER)
        self.router.bind(f"tcp://*:{self.router_port}")
        self.running = True

        logger.info("ZeroMQ broker started on port %s", self.router_port)

        thread = threading.Thread(target=self._process_messages, daemon=True)
        thread.start()

        return True

    def stop(self) -> None:
        """Stop the broker and clean up resources."""
        self.running = False
        if self.router is not None:
            self.router.close()
        self.context.term()
        logger.info("ZeroMQ broker stopped")

    # ------------------------------------------------------------------
    # Core message loop
    # ------------------------------------------------------------------
    def _process_messages(self) -> None:
        """Process incoming messages from all peers."""
        assert self.router is not None, "Broker router socket not initialized"

        poller = zmq.Poller()
        poller.register(self.router, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(100))  # 100ms timeout
                if self.router in socks and socks[self.router] == zmq.POLLIN:
                    # ROUTER receives: [identity][empty][message]
                    parts = self.router.recv_multipart()
                    if len(parts) < 3:
                        logger.warning(
                            "Received malformed message with %d parts", len(parts)
                        )
                        continue

                    peer_id, _, message_data = parts[0], parts[1], parts[2]

                    try:
                        message = json.loads(message_data.decode("utf-8"))
                    except json.JSONDecodeError as exc:
                        logger.error("Failed to decode message: %s", exc)
                        continue

                    self._handle_message(peer_id, message)
            except zmq.ZMQError as exc:
                if self.running:
                    logger.error("ZMQ error in broker loop: %s", exc)
                break

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------
    def _handle_message(self, peer_id: bytes, message: Dict) -> None:
        """
        Handle a message from either a client (FastAPI DEALER) or a worker.

        We distinguish them using message type and presence of `request_id`.
        """
        message_type = message.get("type")
        request_id = message.get("request_id")

        # Worker registration
        if message_type == "WORKER_REGISTER":
            self._register_worker(peer_id, message)
            return

        # Worker response (must contain request_id)
        if request_id and (
            str(message_type).endswith("_RESPONSE") or message_type == "ERROR"
        ):
            self._route_response_to_client(request_id, message)
            return

        # Otherwise treat as client request
        self._route_request_to_worker(peer_id, message)

    def _register_worker(self, worker_id: bytes, message: Dict) -> None:
        """Register a new worker with the broker."""
        if worker_id not in self.workers:
            self.workers[worker_id] = True
            logger.info(
                "Registered new worker %s (type=%s)",
                worker_id.hex()[:8],
                message.get("worker_type"),
            )

    def _route_request_to_worker(self, client_id: bytes, message: Dict) -> None:
        """Forward a client request to an available worker."""
        if not self.workers:
            logger.warning("No workers connected, cannot handle request")
            self._send_to_peer(
                client_id,
                {
                    "type": "ERROR",
                    "error": "No workers available to handle request",
                    "timestamp": datetime.now().isoformat(),
                },
            )
            return

        # Choose the first available worker (simple strategy for now)
        # Future: round-robin or worker-type based routing.
        worker_id = next(iter(self.workers.keys()))

        # Attach correlation id
        request_id = message.get("request_id")
        if not request_id:
            # Lazy import to avoid global dependency
            import uuid

            request_id = str(uuid.uuid4())
            message["request_id"] = request_id

        # Remember which client to route the response back to
        self.pending_requests[request_id] = client_id

        logger.debug(
            "Routing request %s (type=%s) from client %s to worker %s",
            request_id,
            message.get("type"),
            client_id.hex()[:8],
            worker_id.hex()[:8],
        )
        self._send_to_peer(worker_id, message)

    def _route_response_to_client(self, request_id: str, message: Dict) -> None:
        """Forward a worker response back to the originating client."""
        client_id = self.pending_requests.pop(request_id, None)
        if not client_id:
            logger.warning(
                "No pending client found for request_id=%s (message type=%s)",
                request_id,
                message.get("type"),
            )
            return

        logger.debug(
            "Routing response for request %s back to client %s",
            request_id,
            client_id.hex()[:8],
        )
        self._send_to_peer(client_id, message)

    def _send_to_peer(self, peer_id: bytes, message: Dict) -> None:
        """Send a JSON message to a specific ROUTER peer."""
        assert self.router is not None, "Broker router socket not initialized"

        try:
            payload = json.dumps(message).encode("utf-8")
            self.router.send_multipart([peer_id, b"", payload])
        except Exception as exc:
            logger.error("Error sending message to peer: %s", exc)


def main() -> None:
    """Main entry point for standalone broker service."""
    broker = ZeroMQBroker(router_port=5555)

    try:
        broker.start()

        # Keep running until interrupted
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down broker...")
        broker.stop()


if __name__ == "__main__":
    main()
