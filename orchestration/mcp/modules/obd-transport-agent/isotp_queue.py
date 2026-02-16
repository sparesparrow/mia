"""
ISO-TP Transport Layer - MessageQueue Adaptation for ISO 15765-2 Transport

This module provides ISO-TP (ISO 15765-2) transport protocol implementation
with segmentation/reassembly, flow control, and CAN frame handling for
automotive diagnostic communication.
"""

import time
import asyncio
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import struct

logger = logging.getLogger(__name__)


class ISO_TP_FrameType(Enum):
    """ISO-TP frame types (ISO 15765-2)"""
    SINGLE_FRAME = 0x00       # Single frame (up to 7 bytes)
    FIRST_FRAME = 0x01        # First frame of multi-frame message
    CONSECUTIVE_FRAME = 0x02  # Consecutive frame
    FLOW_CONTROL = 0x03       # Flow control frame


class ISO_TP_FlowStatus(Enum):
    """Flow control status"""
    CONTINUE_TO_SEND = 0x00   # Continue sending
    WAIT = 0x01              # Wait
    OVERFLOW = 0x02          # Overflow/abort


@dataclass
class ISO_TP_Frame:
    """ISO-TP frame structure"""
    frame_type: ISO_TP_FrameType
    data: bytes
    sequence_number: int = 0  # For consecutive frames
    flow_status: ISO_TP_FlowStatus = ISO_TP_FlowStatus.CONTINUE_TO_SEND
    block_size: int = 0       # Flow control block size
    separation_time: int = 0  # Flow control separation time (ms)
    can_id: int = 0          # CAN message ID
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    @classmethod
    def from_can_data(cls, can_id: int, data: bytes) -> 'ISO_TP_Frame':
        """Create ISO-TP frame from CAN data"""
        if len(data) == 0:
            raise ValueError("Empty CAN data")

        frame_type = ISO_TP_FrameType(data[0] >> 4)  # Upper 4 bits

        if frame_type == ISO_TP_FrameType.SINGLE_FRAME:
            # Single frame: [TYPE|DL] [DATA...]
            data_length = data[0] & 0x0F
            frame_data = data[1:1+data_length]
            return cls(frame_type=frame_type, data=frame_data, can_id=can_id)

        elif frame_type == ISO_TP_FrameType.FIRST_FRAME:
            # First frame: [TYPE|DL_HIGH] [DL_LOW] [DATA...]
            data_length = ((data[0] & 0x0F) << 8) | data[1]
            frame_data = data[2:]
            return cls(frame_type=frame_type, data=frame_data, can_id=can_id)

        elif frame_type == ISO_TP_FrameType.CONSECUTIVE_FRAME:
            # Consecutive frame: [TYPE|SN] [DATA...]
            sequence_number = data[0] & 0x0F
            frame_data = data[1:]
            return cls(frame_type=frame_type, data=frame_data,
                      sequence_number=sequence_number, can_id=can_id)

        elif frame_type == ISO_TP_FrameType.FLOW_CONTROL:
            # Flow control: [TYPE|FS] [BS] [ST] [DATA...]
            flow_status = ISO_TP_FlowStatus(data[0] & 0x0F)
            block_size = data[1] if len(data) > 1 else 0
            separation_time = data[2] if len(data) > 2 else 0
            frame_data = data[3:] if len(data) > 3 else b''
            return cls(frame_type=frame_type, data=frame_data,
                      flow_status=flow_status, block_size=block_size,
                      separation_time=separation_time, can_id=can_id)

        else:
            raise ValueError(f"Unknown frame type: {frame_type}")

    def to_can_data(self) -> bytes:
        """Convert frame to CAN data bytes"""
        if self.frame_type == ISO_TP_FrameType.SINGLE_FRAME:
            # Single frame: [TYPE|DL] [DATA...]
            data_length = len(self.data)
            if data_length > 7:
                raise ValueError("Single frame data too long")
            return bytes([self.frame_type.value << 4 | data_length]) + self.data

        elif self.frame_type == ISO_TP_FrameType.FIRST_FRAME:
            # First frame: [TYPE|DL_HIGH] [DL_LOW] [DATA...]
            total_length = len(self.data)
            if total_length > 4095:  # 12-bit length field
                raise ValueError("Message too long for ISO-TP")
            dl_high = (total_length >> 8) & 0x0F
            dl_low = total_length & 0xFF
            header = bytes([self.frame_type.value << 4 | dl_high, dl_low])
            # First frame carries up to 6 bytes of data
            frame_data = self.data[:6]
            return header + frame_data

        elif self.frame_type == ISO_TP_FrameType.CONSECUTIVE_FRAME:
            # Consecutive frame: [TYPE|SN] [DATA...]
            if self.sequence_number > 15:
                raise ValueError("Invalid sequence number")
            header = bytes([self.frame_type.value << 4 | self.sequence_number])
            return header + self.data

        elif self.frame_type == ISO_TP_FrameType.FLOW_CONTROL:
            # Flow control: [TYPE|FS] [BS] [ST] [DATA...]
            header = bytes([self.frame_type.value << 4 | self.flow_status.value,
                           self.block_size, self.separation_time])
            return header + self.data

        else:
            raise ValueError(f"Unsupported frame type: {self.frame_type}")


@dataclass
class ISO_TP_Message:
    """Complete ISO-TP message being assembled/reassembled"""
    can_id: int
    total_length: int
    received_data: bytearray = field(default_factory=bytearray)
    expected_sequence: int = 1  # Next expected sequence number
    first_frame_time: int = field(default_factory=lambda: int(time.time() * 1000))
    last_frame_time: int = field(default_factory=lambda: int(time.time() * 1000))
    completed: bool = False

    def add_frame(self, frame: ISO_TP_Frame) -> bool:
        """
        Add a frame to the message

        Returns:
            True if message is now complete
        """
        self.last_frame_time = frame.timestamp

        if frame.frame_type == ISO_TP_FrameType.FIRST_FRAME:
            # First frame - initialize message
            self.total_length = ((frame.data[0] & 0x0F) << 8) | frame.data[1]  # From CAN data
            self.received_data.clear()
            self.received_data.extend(frame.data[2:])  # First frame data starts after length
            self.expected_sequence = 1

        elif frame.frame_type == ISO_TP_FrameType.CONSECUTIVE_FRAME:
            # Consecutive frame - check sequence and add data
            if frame.sequence_number != self.expected_sequence:
                logger.warning(f"Sequence error: expected {self.expected_sequence}, got {frame.sequence_number}")
                return False

            self.received_data.extend(frame.data)
            self.expected_sequence = (self.expected_sequence + 1) % 16

        else:
            logger.warning(f"Unexpected frame type for message assembly: {frame.frame_type}")
            return False

        # Check if message is complete
        if len(self.received_data) >= self.total_length:
            self.completed = True
            # Trim to exact length
            if len(self.received_data) > self.total_length:
                self.received_data = self.received_data[:self.total_length]
            return True

        return False

    def get_message_data(self) -> bytes:
        """Get complete message data"""
        return bytes(self.received_data)

    def is_timed_out(self, timeout_ms: int = 1000) -> bool:
        """Check if message assembly has timed out"""
        current_time = int(time.time() * 1000)
        return (current_time - self.last_frame_time) > timeout_ms


class ISO_TP_Connection:
    """ISO-TP connection state for a CAN ID pair"""

    def __init__(self, tx_id: int, rx_id: int, block_size: int = 8, separation_time: int = 0):
        self.tx_id = tx_id  # Transmit CAN ID
        self.rx_id = rx_id  # Receive CAN ID
        self.block_size = block_size  # Flow control block size
        self.separation_time = separation_time  # Separation time between frames (ms)

        # Transmission state
        self.tx_message: Optional[bytes] = None
        self.tx_offset: int = 0
        self.tx_sequence: int = 0
        self.tx_block_count: int = 0
        self.tx_waiting_for_fc: bool = False
        self.tx_last_sent_time: int = 0

        # Reception state
        self.rx_message: Optional[ISO_TP_Message] = None
        self.rx_waiting_for_cf: bool = False  # Waiting for consecutive frames

        # Flow control state
        self.last_fc_sent_time: int = 0
        self.fc_block_counter: int = 0

    def start_transmission(self, data: bytes) -> Optional[ISO_TP_Frame]:
        """Start transmission of a message"""
        self.tx_message = data
        self.tx_offset = 0
        self.tx_sequence = 0
        self.tx_block_count = 0
        self.tx_waiting_for_fc = len(data) > 7  # Multi-frame if > 7 bytes

        if len(data) <= 7:
            # Single frame
            return ISO_TP_Frame(
                frame_type=ISO_TP_FrameType.SINGLE_FRAME,
                data=data,
                can_id=self.tx_id
            )
        else:
            # First frame
            frame = ISO_TP_Frame(
                frame_type=ISO_TP_FrameType.FIRST_FRAME,
                data=data,
                can_id=self.tx_id
            )
            self.tx_offset = 6  # First frame carries 6 bytes
            self.tx_waiting_for_fc = True
            return frame

    def handle_flow_control(self, fc_frame: ISO_TP_Frame) -> Optional[ISO_TP_Frame]:
        """Handle received flow control frame"""
        if not self.tx_waiting_for_fc or not self.tx_message:
            return None

        if fc_frame.flow_status == ISO_TP_FlowStatus.CONTINUE_TO_SEND:
            # Update flow control parameters
            self.block_size = fc_frame.block_size
            self.separation_time = fc_frame.separation_time
            self.tx_waiting_for_fc = False
            self.tx_block_count = 0

            # Send next consecutive frame
            return self._get_next_consecutive_frame()

        elif fc_frame.flow_status == ISO_TP_FlowStatus.WAIT:
            # Wait - do nothing, keep waiting
            logger.debug("Flow control: WAIT")
            return None

        elif fc_frame.flow_status == ISO_TP_FlowStatus.OVERFLOW:
            # Overflow - abort transmission
            logger.warning("Flow control: OVERFLOW - aborting transmission")
            self.tx_message = None
            self.tx_waiting_for_fc = False
            return None

        return None

    def _get_next_consecutive_frame(self) -> Optional[ISO_TP_Frame]:
        """Get next consecutive frame to send"""
        if not self.tx_message or self.tx_offset >= len(self.tx_message):
            return None

        # Check separation time
        current_time = int(time.time() * 1000)
        if self.separation_time > 0 and self.tx_last_sent_time > 0:
            if current_time - self.tx_last_sent_time < self.separation_time:
                return None  # Too soon

        # Get next chunk of data (up to 7 bytes)
        chunk_size = min(7, len(self.tx_message) - self.tx_offset)
        chunk = self.tx_message[self.tx_offset:self.tx_offset + chunk_size]

        frame = ISO_TP_Frame(
            frame_type=ISO_TP_FrameType.CONSECUTIVE_FRAME,
            data=chunk,
            sequence_number=self.tx_sequence,
            can_id=self.tx_id
        )

        self.tx_offset += chunk_size
        self.tx_sequence = (self.tx_sequence + 1) % 16
        self.tx_block_count += 1
        self.tx_last_sent_time = current_time

        # Check if we need to wait for next flow control
        if self.block_size > 0 and self.tx_block_count >= self.block_size:
            self.tx_waiting_for_fc = True

        return frame

    def get_next_frame_to_send(self) -> Optional[ISO_TP_Frame]:
        """Get next frame that should be sent"""
        if self.tx_waiting_for_fc:
            return None  # Waiting for flow control

        if self.tx_message and self.tx_offset < len(self.tx_message):
            return self._get_next_consecutive_frame()

        return None

    def send_flow_control(self, flow_status: ISO_TP_FlowStatus = ISO_TP_FlowStatus.CONTINUE_TO_SEND,
                         block_size: Optional[int] = None, separation_time: Optional[int] = None) -> ISO_TP_Frame:
        """Send flow control frame"""
        if block_size is None:
            block_size = self.block_size
        if separation_time is None:
            separation_time = self.separation_time

        frame = ISO_TP_Frame(
            frame_type=ISO_TP_FlowStatus.FLOW_CONTROL,
            data=b'',
            flow_status=flow_status,
            block_size=block_size,
            separation_time=separation_time,
            can_id=self.rx_id  # Flow control goes to receiver's ID
        )

        self.last_fc_sent_time = int(time.time() * 1000)
        return frame

    def receive_frame(self, frame: ISO_TP_Frame) -> Optional[bytes]:
        """
        Receive and process an ISO-TP frame

        Returns:
            Complete message data if message is complete, None otherwise
        """
        if frame.frame_type == ISO_TP_FrameType.SINGLE_FRAME:
            # Single frame - message is complete
            return frame.data

        elif frame.frame_type == ISO_TP_FrameType.FIRST_FRAME:
            # Start of multi-frame message
            self.rx_message = ISO_TP_Message(
                can_id=frame.can_id,
                total_length=((frame.data[0] & 0x0F) << 8) | frame.data[1]
            )
            self.rx_message.add_frame(frame)
            self.rx_waiting_for_cf = True

            # Send flow control to continue
            # Note: Flow control is sent by the queue manager
            return None

        elif frame.frame_type == ISO_TP_FrameType.CONSECUTIVE_FRAME:
            # Consecutive frame
            if not self.rx_waiting_for_cf or not self.rx_message:
                logger.warning("Received consecutive frame without active message")
                return None

            if self.rx_message.add_frame(frame):
                # Message complete
                self.rx_waiting_for_cf = False
                message_data = self.rx_message.get_message_data()
                self.rx_message = None
                return message_data

        elif frame.frame_type == ISO_TP_FrameType.FLOW_CONTROL:
            # Handle flow control for transmission
            return self.handle_flow_control(frame)

        return None


class ISOTP_Queue:
    """
    ISO-TP Transport Layer - MessageQueue adaptation for ISO 15765-2

    Provides segmentation/reassembly, flow control, and CAN frame handling
    for automotive diagnostic communication over CAN bus.
    """

    def __init__(self, max_connections: int = 16, reassembly_timeout_ms: int = 1000):
        """
        Initialize ISO-TP Queue

        Args:
            max_connections: Maximum number of concurrent ISO-TP connections
            reassembly_timeout_ms: Timeout for message reassembly
        """
        self.max_connections = max_connections
        self.reassembly_timeout_ms = reassembly_timeout_ms

        # Connection management
        self._connections: Dict[Tuple[int, int], ISO_TP_Connection] = {}  # (tx_id, rx_id) -> connection
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=32)

        # CAN transport abstraction
        self._can_sender: Optional[Callable[[int, bytes], Awaitable[None]]] = None
        self._message_handler: Optional[Callable[[bytes, int], Awaitable[None]]] = None

        # Background tasks
        self._processing_task: Optional[asyncio.Task] = None
        self._timeout_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self._frames_received = 0
        self._frames_sent = 0
        self._messages_assembled = 0
        self._messages_segmented = 0
        self._timeouts = 0
        self._errors = 0

    def set_can_sender(self, sender: Callable[[int, bytes], Awaitable[None]]) -> None:
        """Set CAN frame sender function"""
        self._can_sender = sender

    def set_message_handler(self, handler: Callable[[bytes, int], Awaitable[None]]) -> None:
        """Set complete message handler function"""
        self._message_handler = handler

    async def start(self) -> None:
        """Start the ISO-TP queue processor"""
        if self._running:
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._process_frames())
        self._timeout_task = asyncio.create_task(self._check_timeouts())

        logger.info("ISO-TP Queue started")

    async def stop(self) -> None:
        """Stop the ISO-TP queue processor"""
        if not self._running:
            return

        self._running = False

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass

        logger.info("ISO-TP Queue stopped")

    async def send_message(self, can_id: int, data: bytes, response_id: Optional[int] = None) -> bool:
        """
        Send a message using ISO-TP segmentation

        Args:
            can_id: CAN ID to send on
            data: Message data to send
            response_id: Expected response CAN ID (for connection setup)

        Returns:
            True if transmission started successfully
        """
        try:
            # Determine connection IDs
            if response_id is None:
                response_id = can_id + 8  # Standard response ID calculation

            conn_key = (can_id, response_id)

            # Get or create connection
            if conn_key not in self._connections:
                if len(self._connections) >= self.max_connections:
                    logger.warning("Maximum connections reached")
                    return False
                self._connections[conn_key] = ISO_TP_Connection(can_id, response_id)

            connection = self._connections[conn_key]

            # Start transmission
            first_frame = connection.start_transmission(data)
            if first_frame and self._can_sender:
                await self._can_sender(first_frame.can_id, first_frame.to_can_data())
                self._frames_sent += 1
                self._messages_segmented += 1

                # If multi-frame, start transmission loop
                if len(data) > 7:
                    asyncio.create_task(self._continue_transmission(connection))

                return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self._errors += 1

        return False

    async def _continue_transmission(self, connection: ISO_TP_Connection) -> None:
        """Continue multi-frame transmission"""
        try:
            while self._running:
                frame = connection.get_next_frame_to_send()
                if frame is None:
                    break

                if self._can_sender:
                    await self._can_sender(frame.can_id, frame.to_can_data())
                    self._frames_sent += 1

                    # Respect separation time
                    if connection.separation_time > 0:
                        await asyncio.sleep(connection.separation_time / 1000.0)

        except Exception as e:
            logger.error(f"Error in transmission continuation: {e}")
            self._errors += 1

    async def receive_can_frame(self, can_id: int, data: bytes) -> None:
        """
        Receive a CAN frame for ISO-TP processing

        Args:
            can_id: CAN message ID
            data: CAN message data
        """
        try:
            self._frames_received += 1

            # Parse ISO-TP frame
            frame = ISO_TP_Frame.from_can_data(can_id, data)

            # Find connection for this frame
            connection = None
            for conn in self._connections.values():
                if conn.tx_id == can_id or conn.rx_id == can_id:
                    connection = conn
                    break

            # Create new connection if needed (for received messages)
            if connection is None and frame.frame_type in [ISO_TP_FrameType.SINGLE_FRAME, ISO_TP_FrameType.FIRST_FRAME]:
                # Assume this is a request, create connection with response ID
                tx_id = can_id + 8  # Response ID
                connection = ISO_TP_Connection(tx_id, can_id)
                self._connections[(tx_id, can_id)] = connection

            if connection:
                # Process frame through connection
                message_data = connection.receive_frame(frame)

                if message_data:
                    # Message complete
                    self._messages_assembled += 1
                    if self._message_handler:
                        await self._message_handler(message_data, can_id)

                elif frame.frame_type == ISO_TP_FrameType.FIRST_FRAME:
                    # Received first frame, send flow control
                    fc_frame = connection.send_flow_control()
                    if self._can_sender:
                        await self._can_sender(fc_frame.can_id, fc_frame.to_can_data())
                        self._frames_sent += 1

        except Exception as e:
            logger.error(f"Error processing CAN frame: {e}")
            self._errors += 1

    async def _process_frames(self) -> None:
        """Process frames from the queue"""
        logger.info("Frame processing loop started")

        while self._running:
            try:
                # Process any pending transmissions
                for connection in list(self._connections.values()):
                    frame = connection.get_next_frame_to_send()
                    if frame and self._can_sender:
                        await self._can_sender(frame.can_id, frame.to_can_data())
                        self._frames_sent += 1

                await asyncio.sleep(0.01)  # Small delay

            except Exception as e:
                logger.error(f"Error in frame processing: {e}")
                await asyncio.sleep(0.1)

        logger.info("Frame processing loop stopped")

    async def _check_timeouts(self) -> None:
        """Check for reassembly timeouts"""
        logger.info("Timeout checking loop started")

        while self._running:
            try:
                current_time = int(time.time() * 1000)
                timed_out_connections = []

                for conn_key, connection in self._connections.items():
                    if connection.rx_message and connection.rx_message.is_timed_out(self.reassembly_timeout_ms):
                        logger.warning(f"Reassembly timeout for connection {conn_key}")
                        connection.rx_message = None
                        connection.rx_waiting_for_cf = False
                        self._timeouts += 1
                        timed_out_connections.append(conn_key)

                # Clean up timed out connections
                for conn_key in timed_out_connections:
                    if conn_key in self._connections:
                        del self._connections[conn_key]

                await asyncio.sleep(0.1)  # Check every 100ms

            except Exception as e:
                logger.error(f"Error in timeout checking: {e}")
                await asyncio.sleep(0.1)

        logger.info("Timeout checking loop stopped")

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self._connections)

    def get_statistics(self) -> Dict[str, Any]:
        """Get ISO-TP queue statistics"""
        return {
            'frames_received': self._frames_received,
            'frames_sent': self._frames_sent,
            'messages_assembled': self._messages_assembled,
            'messages_segmented': self._messages_segmented,
            'timeouts': self._timeouts,
            'errors': self._errors,
            'active_connections': len(self._connections),
            'max_connections': self.max_connections
        }

    def clear_statistics(self) -> None:
        """Clear statistics counters"""
        self._frames_received = 0
        self._frames_sent = 0
        self._messages_assembled = 0
        self._messages_segmented = 0
        self._timeouts = 0
        self._errors = 0