"""
ZeroMQ Message Broker with Enhanced Features
Implements Phase 1.3: ZeroMQ Core Messaging Layer with Enhancements

This broker sits between:
- FastAPI clients (DEALER sockets)
- GPIO / hardware workers (DEALER sockets)

Features:
- Message queuing and persistence
- Comprehensive logging and message tracing
- Enhanced error handling and reconnection logic
- Worker health monitoring
- Message retry mechanisms

It provides a request/response routing mechanism using a
`request_id` field that is added to client requests and echoed by
workers in their responses.
"""
import json
import logging
import threading
import time
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any
from collections import defaultdict
import queue

import zmq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessagePersistence:
    """Handles message persistence using SQLite."""

    def __init__(self, db_path: str = "/var/lib/mia/broker_messages.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_messages (
                    request_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    worker_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    direction TEXT, -- 'inbound' or 'outbound'
                    peer_type TEXT, -- 'client' or 'worker'
                    peer_id TEXT,
                    message_type TEXT,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def store_pending_message(self, request_id: str, client_id: bytes, message: Dict, worker_type: Optional[str] = None):
        """Store a pending message for retry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO pending_messages (request_id, client_id, message, worker_type, created_at) VALUES (?, ?, ?, ?, ?)",
                (request_id, client_id.hex(), json.dumps(message), worker_type, datetime.now().isoformat())
            )
            conn.commit()

    def get_pending_messages(self, worker_type: Optional[str] = None, limit: int = 50) -> List[Tuple[str, bytes, Dict]]:
        """Retrieve pending messages, optionally filtered by worker type."""
        with sqlite3.connect(self.db_path) as conn:
            if worker_type:
                rows = conn.execute(
                    "SELECT request_id, client_id, message FROM pending_messages WHERE worker_type = ? AND status = 'pending' ORDER BY created_at LIMIT ?",
                    (worker_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT request_id, client_id, message FROM pending_messages WHERE status = 'pending' ORDER BY created_at LIMIT ?",
                    (limit,)
                ).fetchall()

            return [(row[0], bytes.fromhex(row[1]), json.loads(row[2])) for row in rows]

    def mark_message_completed(self, request_id: str):
        """Mark a message as completed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE pending_messages SET status = 'completed' WHERE request_id = ?", (request_id,))
            conn.commit()

    def increment_retry_count(self, request_id: str) -> int:
        """Increment retry count and return new count."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE pending_messages SET retry_count = retry_count + 1, last_attempt = ? WHERE request_id = ?",
                (datetime.now().isoformat(), request_id)
            )
            row = conn.execute("SELECT retry_count FROM pending_messages WHERE request_id = ?", (request_id,)).fetchone()
            conn.commit()
            return row[0] if row else 0

    def log_message(self, request_id: Optional[str], direction: str, peer_type: str, peer_id: bytes, message_type: str, message: Dict):
        """Log a message for tracing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO message_log (request_id, direction, peer_type, peer_id, message_type, message) VALUES (?, ?, ?, ?, ?, ?)",
                (request_id, direction, peer_type, peer_id.hex()[:16], message_type, json.dumps(message))
            )
            conn.commit()


class WorkerHealthMonitor:
    """Monitors worker health and handles reconnections."""

    def __init__(self, heartbeat_timeout: int = 30):
        self.heartbeat_timeout = heartbeat_timeout
        self.worker_last_seen: Dict[bytes, datetime] = {}
        self.worker_types: Dict[bytes, str] = {}
        self.unhealthy_workers: set = set()

    def register_worker(self, worker_id: bytes, worker_type: str):
        """Register or update a worker."""
        self.worker_last_seen[worker_id] = datetime.now()
        self.worker_types[worker_id] = worker_type
        self.unhealthy_workers.discard(worker_id)

    def update_heartbeat(self, worker_id: bytes):
        """Update worker heartbeat."""
        if worker_id in self.worker_last_seen:
            self.worker_last_seen[worker_id] = datetime.now()
            self.unhealthy_workers.discard(worker_id)

    def check_health(self) -> List[bytes]:
        """Check for unhealthy workers and return their IDs."""
        now = datetime.now()
        unhealthy = []

        for worker_id, last_seen in self.worker_last_seen.items():
            if (now - last_seen).seconds > self.heartbeat_timeout:
                if worker_id not in self.unhealthy_workers:
                    unhealthy.append(worker_id)
                    self.unhealthy_workers.add(worker_id)

        return unhealthy

    def get_healthy_workers(self, worker_type: Optional[str] = None) -> List[bytes]:
        """Get list of healthy workers, optionally filtered by type."""
        healthy = []
        now = datetime.now()

        for worker_id, last_seen in self.worker_last_seen.items():
            if (now - last_seen).seconds <= self.heartbeat_timeout:
                if worker_type is None or self.worker_types.get(worker_id) == worker_type:
                    healthy.append(worker_id)

        return healthy

    def remove_worker(self, worker_id: bytes):
        """Remove a worker."""
        self.worker_last_seen.pop(worker_id, None)
        self.worker_types.pop(worker_id, None)
        self.unhealthy_workers.discard(worker_id)


class ZeroMQBroker:
    """
    Enhanced ZeroMQ ROUTER-based message broker.

    Features:
    - Message queuing and persistence
    - Comprehensive logging and message tracing
    - Enhanced error handling and reconnection logic
    - Worker health monitoring
    - Message retry mechanisms

    Responsibilities:
    - Accept requests from API clients (DEALER)
    - Forward requests to available workers (DEALER)
    - Route responses from workers back to the originating client
      using a `request_id` correlation id.
    """

    def __init__(self, router_port: int = 5555, persistence_path: str = "/var/lib/mia/broker_messages.db"):
        self.router_port = router_port
        self.context = zmq.Context()
        self.router: Optional[zmq.Socket] = None
        self.running: bool = False

        # Enhanced components
        self.persistence = MessagePersistence(persistence_path)
        self.health_monitor = WorkerHealthMonitor()
        self.message_queue = queue.Queue()

        # Legacy attributes for compatibility
        self.workers: Dict[bytes, bool] = {}

        # request_id -> client_identity
        self.pending_requests: Dict[str, bytes] = {}

        # Worker load balancing
        self.worker_load: Dict[bytes, int] = defaultdict(int)

        # Configuration
        self.max_retry_attempts = 3
        self.retry_delay_seconds = 5

    def start(self) -> bool:
        """Start the broker and background threads."""
        self.router = self.context.socket(zmq.ROUTER)
        self.router.bind(f"tcp://*:{self.router_port}")
        self.running = True

        logger.info("Enhanced ZeroMQ broker started on port %s", self.router_port)
        logger.info("Message persistence enabled at %s", self.persistence.db_path)

        # Start background threads
        threads = [
            threading.Thread(target=self._process_messages, daemon=True, name="message_processor"),
            threading.Thread(target=self._process_message_queue, daemon=True, name="queue_processor"),
            threading.Thread(target=self._health_check_worker, daemon=True, name="health_monitor"),
            threading.Thread(target=self._retry_failed_messages, daemon=True, name="retry_handler"),
        ]

        for thread in threads:
            thread.start()

        # Load any pending messages from persistence
        self._load_pending_messages()

        return True

    def stop(self) -> None:
        """Stop the broker and clean up resources."""
        self.running = False
        if self.router is not None:
            self.router.close()
        self.context.term()
        logger.info("Enhanced ZeroMQ broker stopped")

    def _load_pending_messages(self):
        """Load pending messages from persistence on startup."""
        try:
            pending = self.persistence.get_pending_messages(limit=1000)
            for request_id, client_id, message in pending:
                self.pending_requests[request_id] = client_id
                self.message_queue.put((client_id, message))
            logger.info("Loaded %d pending messages from persistence", len(pending))
        except Exception as e:
            logger.error("Failed to load pending messages: %s", e)

    def _process_message_queue(self):
        """Process queued messages in background."""
        while self.running:
            try:
                client_id, message = self.message_queue.get(timeout=1.0)
                self._route_request_to_worker(client_id, message)
                self.message_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Error processing queued message: %s", e)

    def _health_check_worker(self):
        """Monitor worker health in background."""
        while self.running:
            try:
                unhealthy_workers = self.health_monitor.check_health()
                for worker_id in unhealthy_workers:
                    logger.warning("Worker %s marked as unhealthy", worker_id.hex()[:8])
                    self.workers.pop(worker_id, None)
                    self.worker_load.pop(worker_id, None)

                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error("Error in health check: %s", e)
                time.sleep(5)

    def _retry_failed_messages(self):
        """Retry failed messages in background."""
        while self.running:
            try:
                # Get messages that need retry
                failed_messages = self.persistence.get_pending_messages(limit=10)

                for request_id, client_id, message in failed_messages:
                    retry_count = self.persistence.increment_retry_count(request_id)

                    if retry_count >= self.max_retry_attempts:
                        logger.error("Message %s exceeded max retries (%d), marking as failed", request_id, self.max_retry_attempts)
                        continue

                    logger.info("Retrying message %s (attempt %d/%d)", request_id, retry_count, self.max_retry_attempts)
                    time.sleep(self.retry_delay_seconds)
                    self.message_queue.put((client_id, message))

                time.sleep(30)  # Retry check every 30 seconds
            except Exception as e:
                logger.error("Error in retry handler: %s", e)
                time.sleep(10)

    # ------------------------------------------------------------------
    # Core message loop
    # ------------------------------------------------------------------
    def _process_messages(self) -> None:
        """Process incoming messages from all peers with enhanced error handling."""
        assert self.router is not None, "Broker router socket not initialized"

        poller = zmq.Poller()
        poller.register(self.router, zmq.POLLIN)

        consecutive_errors = 0
        max_consecutive_errors = 10

        while self.running:
            try:
                socks = dict(poller.poll(100))  # 100ms timeout
                if self.router in socks and socks[self.router] == zmq.POLLIN:
                    try:
                        # ROUTER receives: [identity][empty][message]
                        parts = self.router.recv_multipart()
                        if len(parts) < 3:
                            logger.warning(
                                "Received malformed message with %d parts (expected 3+), parts: %s",
                                len(parts), [p.hex()[:16] if isinstance(p, bytes) else str(p) for p in parts[:3]]
                            )
                            consecutive_errors = 0
                            continue

                        peer_id, _, message_data = parts[0], parts[1], parts[2]

                        try:
                            message_str = message_data.decode("utf-8")
                            message = json.loads(message_str)
                        except UnicodeDecodeError as exc:
                            logger.error("Failed to decode message data as UTF-8: %s", exc)
                            consecutive_errors += 1
                            continue
                        except json.JSONDecodeError as exc:
                            logger.error("Failed to parse message JSON: %s", exc)
                            logger.debug("Raw message data: %s", message_data.hex()[:100])
                            consecutive_errors += 1
                            continue

                        # Reset error counter on successful message processing
                        consecutive_errors = 0
                        self._handle_message(peer_id, message)

                    except zmq.ZMQError as msg_exc:
                        logger.error("ZMQ error processing individual message: %s", msg_exc)
                        consecutive_errors += 1

                # Check for too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors (%d), entering recovery mode", consecutive_errors)
                    time.sleep(5)  # Brief pause to prevent tight error loops
                    consecutive_errors = 0

            except zmq.ZMQError as exc:
                if self.running:
                    logger.error("ZMQ error in broker message loop: %s", exc)
                    consecutive_errors += 1
                    time.sleep(1)  # Brief pause before retry
                else:
                    break
            except Exception as exc:
                logger.error("Unexpected error in message processing loop: %s", exc)
                consecutive_errors += 1
                time.sleep(1)

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------
    def _handle_message(self, peer_id: bytes, message: Dict) -> None:
        """
        Handle a message from either a client (FastAPI DEALER) or a worker.

        We distinguish them using message type and presence of `request_id`.
        """
        message_type = message.get("type", "UNKNOWN")
        request_id = message.get("request_id")

        # Determine peer type
        is_worker_message = self._is_worker_message(message)
        peer_type = "worker" if is_worker_message else "client"

        # Log incoming message
        self.persistence.log_message(
            request_id, "inbound", peer_type, peer_id, message_type, message
        )

        # Worker heartbeat
        if message_type == "WORKER_HEARTBEAT":
            self.health_monitor.update_heartbeat(peer_id)
            return

        # Worker registration
        if message_type == "WORKER_REGISTER":
            worker_type = message.get("worker_type", "unknown")
            self._register_worker(peer_id, message, worker_type)
            return

        # Worker response (must contain request_id)
        if request_id and (
            str(message_type).endswith("_RESPONSE") or message_type == "ERROR"
        ):
            self._route_response_to_client(request_id, message)
            return

        # Otherwise treat as client request
        self._route_request_to_worker(peer_id, message)

    def _is_worker_message(self, message: Dict) -> bool:
        """Determine if message is from a worker."""
        message_type = message.get("type", "")
        return message_type in ["WORKER_REGISTER", "WORKER_HEARTBEAT"] or "RESPONSE" in message_type

    def _register_worker(self, worker_id: bytes, message: Dict, worker_type: str) -> None:
        """Register a new worker with the broker."""
        if worker_id not in self.workers:
            self.workers[worker_id] = True
            self.health_monitor.register_worker(worker_id, worker_type)
            logger.info(
                "Registered new worker %s (type=%s)",
                worker_id.hex()[:8],
                worker_type,
            )

    def _route_request_to_worker(self, client_id: bytes, message: Dict) -> None:
        """Forward a client request to an available worker with load balancing."""
        message_type = message.get("type", "UNKNOWN")
        request_id = message.get("request_id")

        # Determine required worker type based on message type
        worker_type = self._get_worker_type_for_message(message_type)

        # Get healthy workers of the required type
        available_workers = self.health_monitor.get_healthy_workers(worker_type)

        if not available_workers:
            logger.warning("No healthy workers available for type %s, queuing message", worker_type)

            # Generate request ID if not present
            if not request_id:
                import uuid
                request_id = str(uuid.uuid4())
                message["request_id"] = request_id

            # Store for later retry
            self.persistence.store_pending_message(request_id, client_id, message, worker_type)
            self.pending_requests[request_id] = client_id

            # Send immediate response to client
            self._send_to_peer(
                client_id,
                {
                    "type": "QUEUED",
                    "request_id": request_id,
                    "message": "Request queued - no workers currently available",
                    "timestamp": datetime.now().isoformat(),
                },
            )
            return

        # Load balancing: choose worker with least load
        worker_id = min(available_workers, key=lambda w: self.worker_load.get(w, 0))
        self.worker_load[worker_id] += 1

        # Attach correlation id if not present
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())
            message["request_id"] = request_id

        # Remember which client to route the response back to
        self.pending_requests[request_id] = client_id

        logger.info(
            "Routing request %s (type=%s) from client %s to worker %s (load: %d)",
            request_id,
            message_type,
            client_id.hex()[:8],
            worker_id.hex()[:8],
            self.worker_load[worker_id],
        )

        # Log outbound message
        self.persistence.log_message(
            request_id, "outbound", "worker", worker_id, message_type, message
        )

        try:
            self._send_to_peer(worker_id, message)
        except Exception as e:
            logger.error("Failed to send message to worker: %s", e)
            self.worker_load[worker_id] -= 1  # Decrement load on failure

    def _get_worker_type_for_message(self, message_type: str) -> Optional[str]:
        """Determine the worker type needed for a message type."""
        # Map message types to worker types
        worker_mapping = {
            "GPIO_CONFIGURE": "gpio",
            "GPIO_SET": "gpio",
            "GPIO_GET": "gpio",
            "SENSOR_READ": "sensor",
            "OBD_COMMAND": "obd",
            "LED_AI_STATE": "led",
            "LED_SERVICE_STATUS": "led",
            "LED_OBD_DATA": "led",
            "LED_MODE": "led",
            "LED_EMERGENCY": "led",
        }
        return worker_mapping.get(message_type)

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

        # Decrement worker load if we can determine which worker sent this
        # In a ROUTER socket, we don't know the worker ID from the response
        # This is a limitation - we'd need DEALER socket tracking for better load balancing

        # Mark message as completed in persistence
        self.persistence.mark_message_completed(request_id)

        # Log outbound message
        self.persistence.log_message(
            request_id, "outbound", "client", client_id, message.get("type", "RESPONSE"), message
        )

        logger.info(
            "Routing response for request %s back to client %s",
            request_id,
            client_id.hex()[:8],
        )

        self._send_to_peer(client_id, message)

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
        """Send a JSON message to a specific ROUTER peer with enhanced error handling."""
        assert self.router is not None, "Broker router socket not initialized"

        try:
            payload = json.dumps(message, default=str).encode("utf-8")
            self.router.send_multipart([peer_id, b"", payload])
            logger.debug("Sent message to peer %s: %s", peer_id.hex()[:8], message.get("type"))
        except zmq.ZMQError as exc:
            logger.error("ZMQ error sending message to peer %s: %s", peer_id.hex()[:8], exc)
            # Could implement retry logic here for transient errors
        except Exception as exc:
            logger.error("Unexpected error sending message to peer %s: %s", peer_id.hex()[:8], exc)


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
