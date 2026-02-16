"""
Diagnostic Gateway - MessageGate Adaptation for Automotive Transport Protocols

This module provides diagnostic gateway functionality for automotive communication,
supporting CAN ID filtering, physical/functional addressing, and multi-protocol
transport integration for diagnostic services.
"""

import time
import asyncio
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import ipaddress

logger = logging.getLogger(__name__)


class TransportProtocol(Enum):
    """Supported transport protocols"""
    CAN = "can"               # CAN bus
    DOIP = "doip"            # DoIP (Diagnostics over IP)
    ETHERNET = "ethernet"    # Raw Ethernet
    LIN = "lin"              # LIN bus


class AddressingMode(Enum):
    """Addressing modes for diagnostic communication"""
    PHYSICAL = "physical"     # Specific ECU addressing (0x7E0-0x7E7)
    FUNCTIONAL = "functional" # Broadcast addressing (0x7DF)


class ConnectionState(Enum):
    """Connection states for diagnostic sessions"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DIAGNOSTIC_SESSION = "diagnostic_session"


@dataclass
class TransportChannel:
    """Transport channel configuration"""
    protocol: TransportProtocol
    channel_id: str
    local_address: Any  # CAN ID, IP address, etc.
    remote_address: Any  # CAN ID, IP address, etc.
    addressing_mode: AddressingMode
    max_bandwidth: int = 500000  # bps
    timeout_ms: int = 5000
    active: bool = True

    def get_response_address(self, request_address: Any) -> Any:
        """Calculate response address based on protocol"""
        if self.protocol == TransportProtocol.CAN:
            if isinstance(request_address, int):
                return request_address + 8  # Standard CAN response ID
        elif self.protocol in [TransportProtocol.DOIP, TransportProtocol.ETHERNET]:
            # For IP-based protocols, response comes from same address
            return request_address
        return request_address

    def is_diagnostic_address(self, address: Any) -> bool:
        """Check if address is a diagnostic address"""
        if self.protocol == TransportProtocol.CAN:
            if isinstance(address, int):
                # Standard diagnostic addresses
                return 0x7E0 <= address <= 0x7E7 or address == 0x7DF
        return True  # Accept all for other protocols


@dataclass
class DiagnosticConnection:
    """Active diagnostic connection"""
    connection_id: str
    channel: TransportChannel
    client_address: Any
    server_address: Any
    state: ConnectionState = ConnectionState.CONNECTED
    created_time: int = field(default_factory=lambda: int(time.time() * 1000))
    last_activity: int = field(default_factory=lambda: int(time.time() * 1000))
    session_data: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    error_count: int = 0

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = int(time.time() * 1000)

    def is_timed_out(self, timeout_ms: int) -> bool:
        """Check if connection has timed out"""
        current_time = int(time.time() * 1000)
        return (current_time - self.last_activity) > timeout_ms

    def increment_message_count(self) -> None:
        """Increment message counter"""
        self.message_count += 1

    def increment_error_count(self) -> None:
        """Increment error counter"""
        self.error_count += 1


@dataclass
class CAN_Filter:
    """CAN message filter configuration"""
    filter_id: int
    mask: int
    description: str = ""
    enabled: bool = True

    def matches(self, can_id: int) -> bool:
        """Check if CAN ID matches this filter"""
        if not self.enabled:
            return False
        return (can_id & self.mask) == (self.filter_id & self.mask)


class DiagnosticFilter:
    """Multi-protocol filter for diagnostic messages"""

    def __init__(self):
        self.can_filters: List[CAN_Filter] = []
        self.ip_filters: Set[str] = set()  # IP address ranges
        self.protocol_filters: Set[TransportProtocol] = set()
        self.service_filters: Set[int] = set()  # UDS service IDs

        # Default diagnostic filters
        self._setup_default_filters()

    def _setup_default_filters(self) -> None:
        """Set up default diagnostic message filters"""
        # Standard CAN diagnostic addresses
        self.can_filters.extend([
            CAN_Filter(0x7E0, 0x7F8, "Physical diagnostic addressing (ECU 0)"),
            CAN_Filter(0x7E1, 0x7F8, "Physical diagnostic addressing (ECU 1)"),
            CAN_Filter(0x7E2, 0x7F8, "Physical diagnostic addressing (ECU 2)"),
            CAN_Filter(0x7E3, 0x7F8, "Physical diagnostic addressing (ECU 3)"),
            CAN_Filter(0x7E4, 0x7F8, "Physical diagnostic addressing (ECU 4)"),
            CAN_Filter(0x7E5, 0x7F8, "Physical diagnostic addressing (ECU 5)"),
            CAN_Filter(0x7E6, 0x7F8, "Physical diagnostic addressing (ECU 6)"),
            CAN_Filter(0x7E7, 0x7F8, "Physical diagnostic addressing (ECU 7)"),
            CAN_Filter(0x7DF, 0x7FF, "Functional diagnostic addressing (broadcast)"),
        ])

        # Common diagnostic services
        self.service_filters.update([
            0x10,  # DiagnosticSessionControl
            0x11,  # ECUReset
            0x14,  # ClearDiagnosticInformation
            0x19,  # ReadDTCInformation
            0x22,  # ReadDataByIdentifier
            0x23,  # ReadMemoryByAddress
            0x24,  # ReadScalingDataByIdentifier
            0x27,  # SecurityAccess
            0x28,  # CommunicationControl
            0x2A,  # ReadDataByPeriodicIdentifier
            0x2C,  # DynamicallyDefineDataIdentifier
            0x2E,  # WriteDataByIdentifier
            0x2F,  # InputOutputControlByIdentifier
            0x31,  # RoutineControl
            0x34,  # RequestDownload
            0x35,  # RequestUpload
            0x36,  # TransferData
            0x37,  # RequestTransferExit
            0x38,  # RequestFileTransfer
            0x3D,  # WriteMemoryByAddress
            0x3E,  # TesterPresent
        ])

    def add_can_filter(self, filter_id: int, mask: int, description: str = "") -> None:
        """Add CAN message filter"""
        self.can_filters.append(CAN_Filter(filter_id, mask, description))

    def add_service_filter(self, service_id: int) -> None:
        """Add service ID filter"""
        self.service_filters.add(service_id)

    def should_accept_message(self, protocol: TransportProtocol, address: Any,
                             data: bytes) -> bool:
        """
        Check if message should be accepted based on filters

        Args:
            protocol: Transport protocol
            address: Source address (CAN ID, IP, etc.)
            data: Message data

        Returns:
            True if message should be accepted
        """
        # Protocol filter
        if self.protocol_filters and protocol not in self.protocol_filters:
            return False

        # Transport-specific filtering
        if protocol == TransportProtocol.CAN:
            if not isinstance(address, int):
                return False

            # Check CAN filters
            can_accepted = any(f.matches(address) for f in self.can_filters)
            if not can_accepted:
                return False

        elif protocol in [TransportProtocol.DOIP, TransportProtocol.ETHERNET]:
            # IP address filtering (future implementation)
            pass

        # Service ID filtering (if data is available)
        if data and len(data) > 0:
            service_id = data[0]
            if self.service_filters and service_id not in self.service_filters:
                return False

        return True


class DiagnosticGateway:
    """
    Diagnostic Gateway - MessageGate adaptation for automotive transport protocols

    Provides CAN ID filtering, channel management, and multi-protocol support
    for automotive diagnostic communication with physical and functional addressing.
    """

    def __init__(self, max_connections: int = 32):
        """
        Initialize Diagnostic Gateway

        Args:
            max_connections: Maximum number of concurrent diagnostic connections
        """
        self.max_connections = max_connections

        # Channel management
        self._channels: Dict[str, TransportChannel] = {}
        self._channel_lock = threading.RLock()

        # Connection management
        self._connections: Dict[str, DiagnosticConnection] = {}
        self._connection_lock = threading.RLock()

        # Message filtering
        self._filter = DiagnosticFilter()

        # Transport handlers
        self._transport_receivers: Dict[TransportProtocol, Callable] = {}
        self._transport_senders: Dict[TransportProtocol, Callable] = {}

        # Message routing
        self._message_router: Optional[Callable[[bytes, TransportChannel, Any], Awaitable[None]]] = None

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self._messages_received = 0
        self._messages_sent = 0
        self._messages_filtered = 0
        self._connections_created = 0
        self._connections_closed = 0

    def add_channel(self, channel: TransportChannel) -> None:
        """Add transport channel"""
        with self._channel_lock:
            self._channels[channel.channel_id] = channel
            logger.info(f"Added channel {channel.channel_id} for {channel.protocol.value}")

    def remove_channel(self, channel_id: str) -> None:
        """Remove transport channel"""
        with self._channel_lock:
            if channel_id in self._channels:
                del self._channels[channel_id]
                logger.info(f"Removed channel {channel_id}")

    def set_transport_receiver(self, protocol: TransportProtocol,
                              receiver: Callable[[TransportChannel, Any, bytes], Awaitable[None]]) -> None:
        """Set transport receiver for a protocol"""
        self._transport_receivers[protocol] = receiver

    def set_transport_sender(self, protocol: TransportProtocol,
                            sender: Callable[[TransportChannel, Any, bytes], Awaitable[None]]) -> None:
        """Set transport sender for a protocol"""
        self._transport_senders[protocol] = sender

    def set_message_router(self, router: Callable[[bytes, TransportChannel, Any], Awaitable[None]]) -> None:
        """Set message router function"""
        self._message_router = router

    async def start(self) -> None:
        """Start the diagnostic gateway"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_connections())

        logger.info("Diagnostic Gateway started")

    async def stop(self) -> None:
        """Stop the diagnostic gateway"""
        if not self._running:
            return

        self._running = False

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        with self._connection_lock:
            for connection in list(self._connections.values()):
                await self._close_connection(connection.connection_id)

        logger.info("Diagnostic Gateway stopped")

    async def receive_message(self, protocol: TransportProtocol, channel_id: str,
                             source_address: Any, data: bytes) -> None:
        """
        Receive message from transport layer

        Args:
            protocol: Transport protocol
            channel_id: Channel identifier
            source_address: Source address
            data: Message data
        """
        try:
            self._messages_received += 1

            # Get channel
            channel = self._channels.get(channel_id)
            if not channel:
                logger.warning(f"Unknown channel {channel_id}")
                return

            # Apply filters
            if not self._filter.should_accept_message(protocol, source_address, data):
                self._messages_filtered += 1
                logger.debug(f"Message filtered: {protocol.value} {source_address}")
                return

            # Find or create connection
            connection = await self._get_or_create_connection(channel, source_address)

            if connection:
                connection.update_activity()
                connection.increment_message_count()

                # Route message
                if self._message_router:
                    await self._message_router(data, channel, source_address)

        except Exception as e:
            logger.error(f"Error receiving message: {e}")

    async def send_message(self, protocol: TransportProtocol, channel_id: str,
                          target_address: Any, data: bytes,
                          source_address: Optional[Any] = None) -> bool:
        """
        Send message through transport layer

        Args:
            protocol: Transport protocol
            channel_id: Channel identifier
            target_address: Target address
            data: Message data
            source_address: Source address (for connection lookup)

        Returns:
            True if sent successfully
        """
        try:
            # Get channel
            channel = self._channels.get(channel_id)
            if not channel:
                logger.warning(f"Unknown channel {channel_id}")
                return False

            # Get transport sender
            sender = self._transport_senders.get(protocol)
            if not sender:
                logger.warning(f"No sender for protocol {protocol.value}")
                return False

            # Send message
            await sender(channel, target_address, data)
            self._messages_sent += 1

            # Update connection activity if applicable
            if source_address:
                connection_id = f"{channel_id}_{source_address}"
                with self._connection_lock:
                    connection = self._connections.get(connection_id)
                    if connection:
                        connection.update_activity()

            return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def _get_or_create_connection(self, channel: TransportChannel,
                                       client_address: Any) -> Optional[DiagnosticConnection]:
        """Get existing connection or create new one"""
        connection_id = f"{channel.channel_id}_{client_address}"

        with self._connection_lock:
            # Check existing connection
            connection = self._connections.get(connection_id)
            if connection:
                return connection

            # Check connection limit
            if len(self._connections) >= self.max_connections:
                logger.warning("Maximum connections reached")
                return None

            # Create new connection
            response_address = channel.get_response_address(client_address)

            connection = DiagnosticConnection(
                connection_id=connection_id,
                channel=channel,
                client_address=client_address,
                server_address=response_address
            )

            self._connections[connection_id] = connection
            self._connections_created += 1

            logger.info(f"Created connection {connection_id}")
            return connection

    async def _close_connection(self, connection_id: str) -> None:
        """Close a diagnostic connection"""
        with self._connection_lock:
            connection = self._connections.get(connection_id)
            if connection:
                # Perform any cleanup
                connection.state = ConnectionState.DISCONNECTED
                del self._connections[connection_id]
                self._connections_closed += 1
                logger.info(f"Closed connection {connection_id}")

    async def _cleanup_connections(self) -> None:
        """Background task to clean up timed out connections"""
        logger.info("Connection cleanup task started")

        while self._running:
            try:
                current_time = int(time.time() * 1000)
                timed_out_connections = []

                with self._connection_lock:
                    for connection_id, connection in self._connections.items():
                        if connection.is_timed_out(connection.channel.timeout_ms):
                            timed_out_connections.append(connection_id)

                # Close timed out connections
                for connection_id in timed_out_connections:
                    await self._close_connection(connection_id)

                # Run cleanup every 30 seconds
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")
                await asyncio.sleep(30)

        logger.info("Connection cleanup task stopped")

    def get_channel_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all channels"""
        with self._channel_lock:
            return {
                channel_id: {
                    'protocol': channel.protocol.value,
                    'addressing_mode': channel.addressing_mode.value,
                    'local_address': str(channel.local_address),
                    'remote_address': str(channel.remote_address),
                    'active': channel.active,
                    'max_bandwidth': channel.max_bandwidth
                }
                for channel_id, channel in self._channels.items()
            }

    def get_connection_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all connections"""
        with self._connection_lock:
            return {
                conn_id: {
                    'channel_id': connection.channel.channel_id,
                    'client_address': str(connection.client_address),
                    'server_address': str(connection.server_address),
                    'state': connection.state.value,
                    'created_time': connection.created_time,
                    'last_activity': connection.last_activity,
                    'message_count': connection.message_count,
                    'error_count': connection.error_count
                }
                for conn_id, connection in self._connections.items()
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        return {
            'messages_received': self._messages_received,
            'messages_sent': self._messages_sent,
            'messages_filtered': self._messages_filtered,
            'active_connections': len(self._connections),
            'total_connections_created': self._connections_created,
            'total_connections_closed': self._connections_closed,
            'active_channels': len(self._channels)
        }

    def configure_filter(self, config: Dict[str, Any]) -> None:
        """
        Configure message filtering

        Args:
            config: Filter configuration
        """
        # Add CAN filters
        if 'can_filters' in config:
            for filter_config in config['can_filters']:
                self._filter.add_can_filter(
                    filter_config['id'],
                    filter_config['mask'],
                    filter_config.get('description', '')
                )

        # Add service filters
        if 'service_filters' in config:
            for service_id in config['service_filters']:
                self._filter.add_service_filter(service_id)

    def is_diagnostic_address(self, protocol: TransportProtocol, address: Any) -> bool:
        """Check if address is a valid diagnostic address"""
        channel = None
        for ch in self._channels.values():
            if ch.protocol == protocol:
                channel = ch
                break

        if channel:
            return channel.is_diagnostic_address(address)

        return False