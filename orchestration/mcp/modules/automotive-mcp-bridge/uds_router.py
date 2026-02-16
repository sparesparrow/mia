"""
UDS Diagnostic Router - MsgBroker Adaptation for UDS Diagnostic Services

This module provides UDS (Unified Diagnostic Services) routing capabilities
with service-ID based dispatch, session management, and timeout handling
for automotive diagnostic communication.
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


class UDSSession(Enum):
    """UDS diagnostic session types (ISO 14229-1)"""
    DEFAULT = 0x01         # Default session
    PROGRAMMING = 0x02     # Programming session
    EXTENDED = 0x03        # Extended diagnostic session
    SAFETY_SYSTEM = 0x04   # Safety system diagnostic session


class UDSService(Enum):
    """UDS service identifiers (ISO 14229-1)"""
    DIAGNOSTIC_SESSION_CONTROL = 0x10
    ECU_RESET = 0x11
    CLEAR_DIAGNOSTIC_INFORMATION = 0x14
    READ_DTC_INFORMATION = 0x19
    READ_DATA_BY_IDENTIFIER = 0x22
    READ_MEMORY_BY_ADDRESS = 0x23
    READ_SCALING_DATA_BY_IDENTIFIER = 0x24
    SECURITY_ACCESS = 0x27
    COMMUNICATION_CONTROL = 0x28
    READ_DATA_BY_PERIODIC_IDENTIFIER = 0x2A
    DYNAMICALLY_DEFINE_DATA_IDENTIFIER = 0x2C
    WRITE_DATA_BY_IDENTIFIER = 0x2E
    INPUT_OUTPUT_CONTROL_BY_IDENTIFIER = 0x2F
    ROUTINE_CONTROL = 0x31
    REQUEST_DOWNLOAD = 0x34
    REQUEST_UPLOAD = 0x35
    TRANSFER_DATA = 0x36
    REQUEST_TRANSFER_EXIT = 0x37
    REQUEST_FILE_TRANSFER = 0x38
    WRITE_MEMORY_BY_ADDRESS = 0x3D
    TESTER_PRESENT = 0x3E
    ACCESS_TIMING_PARAMETER = 0x83
    SECURED_DATA_TRANSMISSION = 0x84
    CONTROL_DTC_SETTING = 0x85
    RESPONSE_ON_EVENT = 0x86
    LINK_CONTROL = 0x87


class UDSNRC(Enum):
    """UDS Negative Response Codes (ISO 14229-1)"""
    POSITIVE_RESPONSE = 0x00
    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUBFUNCTION_NOT_SUPPORTED = 0x12
    INCORRECT_MESSAGE_LENGTH_OR_INVALID_FORMAT = 0x13
    RESPONSE_TOO_LONG = 0x14
    BUSY_REPEAT_REQUEST = 0x21
    CONDITIONS_NOT_CORRECT = 0x22
    REQUEST_SEQUENCE_ERROR = 0x24
    NO_RESPONSE_FROM_SUBNET_COMPONENT = 0x25
    FAILURE_PREVENTS_EXECUTION_OF_REQUESTED_ACTION = 0x26
    REQUEST_OUT_OF_RANGE = 0x31
    SECURITY_ACCESS_DENIED = 0x33
    INVALID_KEY = 0x35
    EXCEED_NUMBER_OF_ATTEMPTS = 0x36
    REQUIRED_TIME_DELAY_NOT_EXPIRED = 0x37
    UPLOAD_DOWNLOAD_NOT_ACCEPTED = 0x70
    TRANSFER_DATA_SUSPENDED = 0x71
    GENERAL_PROGRAMMING_FAILURE = 0x72
    WRONG_BLOCK_SEQUENCE_COUNTER = 0x73
    REQUEST_CORRECTLY_RECEIVED_RESPONSE_PENDING = 0x78
    SUBFUNCTION_NOT_SUPPORTED_IN_ACTIVE_SESSION = 0x7E
    SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION = 0x7F
    RPM_TOO_HIGH = 0x81
    RPM_TOO_LOW = 0x82
    ENGINE_IS_RUNNING = 0x83
    ENGINE_IS_NOT_RUNNING = 0x84
    ENGINE_RUN_TIME_TOO_LOW = 0x85
    TEMPERATURE_TOO_HIGH = 0x86
    TEMPERATURE_TOO_LOW = 0x87
    VEHICLE_SPEED_TOO_HIGH = 0x88
    VEHICLE_SPEED_TOO_LOW = 0x89
    THROTTLE_PEDAL_TOO_HIGH = 0x8A
    THROTTLE_PEDAL_TOO_LOW = 0x8B
    TRANSMISSION_RANGE_NOT_IN_NEUTRAL = 0x8C
    TRANSMISSION_RANGE_NOT_IN_GEAR = 0x8D
    BRAKE_SWITCH_NOT_CLOSED = 0x8E
    SHIFTER_LEVER_NOT_IN_PARK = 0x8F
    TORQUE_CONVERTER_CLUTCH_LOCKED = 0x90
    VOLTAGE_TOO_HIGH = 0x91
    VOLTAGE_TOO_LOW = 0x92


class ApplicationState(Enum):
    """ECU application states for diagnostic access control"""
    STARTUP = "startup"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DIAGNOSTIC = "diagnostic"
    MAINTENANCE = "maintenance"


@dataclass
class UDSRequest:
    """UDS request structure"""
    service_id: int
    subfunction: Optional[int] = None
    data: bytes = field(default_factory=bytes)
    source_address: Optional[int] = None
    target_address: Optional[int] = None
    is_functional: bool = False  # Functional vs physical addressing
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))  # ms precision

    def to_bytes(self) -> bytes:
        """Convert request to byte array"""
        if self.subfunction is not None:
            return bytes([self.service_id, self.subfunction]) + self.data
        else:
            return bytes([self.service_id]) + self.data

    @classmethod
    def from_bytes(cls, data: bytes, source_address: Optional[int] = None,
                   target_address: Optional[int] = None, is_functional: bool = False) -> 'UDSRequest':
        """Create request from byte array"""
        if len(data) == 0:
            raise ValueError("Empty request data")

        service_id = data[0]
        subfunction = data[1] if len(data) > 1 else None
        request_data = data[2:] if len(data) > 2 else b''

        return cls(
            service_id=service_id,
            subfunction=subfunction,
            data=request_data,
            source_address=source_address,
            target_address=target_address,
            is_functional=is_functional
        )


@dataclass
class UDSResponse:
    """UDS response structure"""
    service_id: int
    response_code: int  # 0x00 for positive, NRC for negative
    data: bytes = field(default_factory=bytes)
    is_pending: bool = False

    def to_bytes(self) -> bytes:
        """Convert response to byte array"""
        if self.response_code == 0x00:  # Positive response
            return bytes([self.service_id + 0x40]) + self.data
        else:  # Negative response
            return bytes([0x7F, self.service_id, self.response_code]) + self.data

    @classmethod
    def positive_response(cls, service_id: int, data: bytes = b'') -> 'UDSResponse':
        """Create positive response"""
        return cls(service_id=service_id, response_code=0x00, data=data)

    @classmethod
    def negative_response(cls, service_id: int, nrc: UDSNRC) -> 'UDSResponse':
        """Create negative response"""
        return cls(service_id=service_id, response_code=nrc.value)

    @classmethod
    def response_pending(cls, service_id: int) -> 'UDSResponse':
        """Create response pending response"""
        return cls(service_id=service_id, response_code=UDSNRC.REQUEST_CORRECTLY_RECEIVED_RESPONSE_PENDING.value,
                   is_pending=True)


@dataclass
class UDSSessionState:
    """UDS session state information"""
    current_session: UDSSession = UDSSession.DEFAULT
    session_start_time: int = field(default_factory=lambda: int(time.time() * 1000))
    p2_timeout_ms: int = 5000   # 5 seconds default P2
    p2_star_timeout_ms: int = 5000  # 5 seconds default P2*
    s3_timeout_ms: int = 5000   # 5 seconds default S3
    security_level: int = 0     # 0 = unlocked
    tester_present_active: bool = False
    last_tester_present: int = field(default_factory=lambda: int(time.time() * 1000))


class UDSServiceHandler:
    """Base class for UDS service handlers"""

    def __init__(self, service_id: int):
        self.service_id = service_id
        self.supported_sessions: Set[UDSSession] = {UDSSession.EXTENDED}
        self.security_required: int = 0  # 0 = no security required

    def is_supported_in_session(self, session: UDSSession) -> bool:
        """Check if service is supported in current session"""
        return session in self.supported_sessions

    def is_security_satisfied(self, current_security: int) -> bool:
        """Check if security requirements are met"""
        return current_security >= self.security_required

    async def handle_request(self, request: UDSRequest, session_state: UDSSessionState) -> UDSResponse:
        """Handle UDS request - override in subclasses"""
        raise NotImplementedError("Service handler must implement handle_request")

    def get_supported_subfunctions(self) -> List[int]:
        """Get list of supported subfunctions"""
        return []


class UDSRouter:
    """
    UDS Diagnostic Router - MsgBroker adaptation for UDS services

    Provides service-ID based dispatch, session management, and timeout handling
    for automotive diagnostic communication over ISO-TP transport layer.
    """

    def __init__(self):
        # Session management
        self._session_state = UDSSessionState()
        self._session_lock = threading.RLock()

        # Service handlers registry
        self._service_handlers: Dict[int, UDSServiceHandler] = {}

        # Application state
        self._application_state = ApplicationState.STARTUP
        self._state_lock = threading.RLock()

        # Pending operations (for ResponsePending handling)
        self._pending_operations: Dict[int, asyncio.Task] = {}
        self._pending_lock = asyncio.Lock()

        # Transport abstraction
        self._transport_sender: Optional[Callable[[bytes], Awaitable[None]]] = None

        # Event callbacks
        self._session_change_callback: Optional[Callable[[UDSSession, UDSSession], None]] = None
        self._security_change_callback: Optional[Callable[[int, int], None]] = None

        # Statistics
        self._total_requests = 0
        self._total_responses = 0
        self._total_timeouts = 0
        self._total_nrcs = 0

        # Register default service handlers
        self._register_default_handlers()

    def set_transport_sender(self, sender: Callable[[bytes], Awaitable[None]]) -> None:
        """Set the transport layer sender function"""
        self._transport_sender = sender

    def register_service_handler(self, handler: UDSServiceHandler) -> None:
        """Register a UDS service handler"""
        self._service_handlers[handler.service_id] = handler
        logger.info(f"Registered UDS service handler: 0x{handler.service_id:02X}")

    def _register_default_handlers(self) -> None:
        """Register default UDS service handlers"""
        # These will be implemented as needed
        pass

    async def process_request(self, request_data: bytes,
                             source_address: Optional[int] = None,
                             is_functional: bool = False) -> Optional[UDSResponse]:
        """
        Process incoming UDS request

        Args:
            request_data: Raw request bytes
            source_address: Source ECU address (for physical addressing)
            is_functional: Whether this is functional addressing

        Returns:
            Response to send, or None if no response needed
        """
        try:
            request = UDSRequest.from_bytes(request_data, source_address=source_address, is_functional=is_functional)
            self._total_requests += 1

            logger.debug(f"UDS Request: SID=0x{request.service_id:02X}, "
                        f"Subfunc={request.subfunction}, Data={request.data.hex()}")

            # Handle functional addressing (broadcast)
            if is_functional and not self._is_functional_service(request.service_id):
                return None  # Ignore functional requests for non-functional services

            # Process the request
            response = await self._dispatch_request(request)

            if response:
                self._total_responses += 1
                logger.debug(f"UDS Response: SID=0x{response.service_id:02X}, "
                           f"NRC=0x{response.response_code:02X}, Data={response.data.hex()}")

            return response

        except Exception as e:
            logger.error(f"Error processing UDS request: {e}")
            # Return general reject for malformed requests
            return UDSResponse.negative_response(0x00, UDSNRC.GENERAL_REJECT)

    async def _dispatch_request(self, request: UDSRequest) -> Optional[UDSResponse]:
        """Dispatch request to appropriate service handler"""
        with self._session_lock:
            # Check session support
            if not self._is_service_supported_in_session(request.service_id):
                return UDSResponse.negative_response(request.service_id,
                                                   UDSNRC.SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION)

            # Get service handler
            handler = self._service_handlers.get(request.service_id)
            if not handler:
                return UDSResponse.negative_response(request.service_id,
                                                   UDSNRC.SERVICE_NOT_SUPPORTED)

            # Check security requirements
            if not handler.is_security_satisfied(self._session_state.security_level):
                return UDSResponse.negative_response(request.service_id,
                                                   UDSNRC.SECURITY_ACCESS_DENIED)

            # Check application state
            if not self._is_service_allowed_in_state(request.service_id):
                return UDSResponse.negative_response(request.service_id,
                                                   UDSNRC.CONDITIONS_NOT_CORRECT)

        # Handle the request (potentially long-running)
        try:
            response = await handler.handle_request(request, self._session_state)

            # Handle ResponsePending
            if response.is_pending:
                # Start background task for long-running operation
                task = asyncio.create_task(self._handle_pending_operation(request, handler))
                async with self._pending_lock:
                    self._pending_operations[request.service_id] = task

            return response

        except Exception as e:
            logger.error(f"Service handler error: {e}")
            return UDSResponse.negative_response(request.service_id,
                                               UDSNRC.FAILURE_PREVENTS_EXECUTION_OF_REQUESTED_ACTION)

    async def _handle_pending_operation(self, request: UDSRequest, handler: UDSServiceHandler) -> None:
        """Handle long-running operation with ResponsePending"""
        try:
            # Send initial ResponsePending
            pending_response = UDSResponse.response_pending(request.service_id)
            if self._transport_sender:
                await self._transport_sender(pending_response.to_bytes())

            # Wait a bit before starting actual work (P2 timeout handling)
            await asyncio.sleep(self._session_state.p2_timeout_ms / 2000)  # Half of P2

            # Perform the actual work
            final_response = await handler.handle_request(request, self._session_state)

            # Send final response
            if self._transport_sender:
                await self._transport_sender(final_response.to_bytes())

        except asyncio.TimeoutError:
            self._total_timeouts += 1
            logger.warning(f"Pending operation timeout for service 0x{request.service_id:02X}")
        except Exception as e:
            logger.error(f"Pending operation error: {e}")
            # Send negative response
            nrc_response = UDSResponse.negative_response(request.service_id,
                                                       UDSNRC.FAILURE_PREVENTS_EXECUTION_OF_REQUESTED_ACTION)
            if self._transport_sender:
                await self._transport_sender(nrc_response.to_bytes())
        finally:
            # Clean up pending operation
            async with self._pending_lock:
                self._pending_operations.pop(request.service_id, None)

    def _is_service_supported_in_session(self, service_id: int) -> bool:
        """Check if service is supported in current session"""
        handler = self._service_handlers.get(service_id)
        if not handler:
            return False
        return handler.is_supported_in_session(self._session_state.current_session)

    def _is_service_allowed_in_state(self, service_id: int) -> bool:
        """Check if service is allowed in current application state"""
        with self._state_lock:
            # Define state restrictions
            restricted_services = {
                ApplicationState.STARTUP: [sid for sid in UDSService],
                ApplicationState.DEGRADED: [],  # Allow all in degraded mode
                ApplicationState.MAINTENANCE: [],  # Allow all in maintenance
            }

            if self._application_state in restricted_services:
                return service_id not in restricted_services[self._application_state]

            return True

    def _is_functional_service(self, service_id: int) -> bool:
        """Check if service supports functional addressing"""
        # Services that typically support functional addressing
        functional_services = {
            UDSService.DIAGNOSTIC_SESSION_CONTROL.value,
            UDSService.ECU_RESET.value,
            UDSService.COMMUNICATION_CONTROL.value,
            UDSService.TESTER_PRESENT.value,
        }
        return service_id in functional_services

    async def change_session(self, new_session: UDSSession) -> bool:
        """
        Change diagnostic session

        Args:
            new_session: New session to activate

        Returns:
            True if session change successful
        """
        old_session = self._session_state.current_session

        with self._session_lock:
            # Validate session transition
            if not self._is_valid_session_transition(old_session, new_session):
                return False

            # Update session state
            self._session_state.current_session = new_session
            self._session_state.session_start_time = int(time.time() * 1000)

            # Reset security level on session change
            old_security = self._session_state.security_level
            self._session_state.security_level = 0

            # Update timeouts based on session
            self._update_session_timeouts(new_session)

        # Notify callback
        if self._session_change_callback:
            try:
                self._session_change_callback(old_session, new_session)
            except Exception as e:
                logger.error(f"Session change callback error: {e}")

        if self._security_change_callback and old_security != 0:
            try:
                self._security_change_callback(old_security, 0)
            except Exception as e:
                logger.error(f"Security change callback error: {e}")

        logger.info(f"Session changed: {old_session.name} -> {new_session.name}")
        return True

    def _is_valid_session_transition(self, old_session: UDSSession, new_session: UDSSession) -> bool:
        """Validate session transition"""
        # Allow all transitions for now - can be made more restrictive
        return True

    def _update_session_timeouts(self, session: UDSSession) -> None:
        """Update timeouts based on session type"""
        if session == UDSSession.PROGRAMMING:
            # Longer timeouts for programming
            self._session_state.p2_timeout_ms = 25000   # 25s
            self._session_state.p2_star_timeout_ms = 25000
            self._session_state.s3_timeout_ms = 5000
        elif session == UDSSession.EXTENDED:
            # Standard extended session timeouts
            self._session_state.p2_timeout_ms = 5000    # 5s
            self._session_state.p2_star_timeout_ms = 5000
            self._session_state.s3_timeout_ms = 5000
        else:
            # Default session timeouts
            self._session_state.p2_timeout_ms = 5000
            self._session_state.p2_star_timeout_ms = 5000
            self._session_state.s3_timeout_ms = 5000

    def set_application_state(self, new_state: ApplicationState) -> None:
        """Set current application state"""
        with self._state_lock:
            old_state = self._application_state
            self._application_state = new_state
            logger.info(f"Application state changed: {old_state.name} -> {new_state.name}")

    async def handle_tester_present(self, suppress_response: bool = False) -> Optional[UDSResponse]:
        """Handle TesterPresent service"""
        current_time = int(time.time() * 1000)
        self._session_state.last_tester_present = current_time
        self._session_state.tester_present_active = True

        if not suppress_response:
            return UDSResponse.positive_response(UDSService.TESTER_PRESENT.value)
        return None

    def check_s3_timeout(self) -> bool:
        """
        Check if S3 (session timeout) has expired

        Returns:
            True if session should be terminated due to timeout
        """
        if not self._session_state.tester_present_active:
            return False

        current_time = int(time.time() * 1000)
        time_since_last_tp = current_time - self._session_state.last_tester_present

        return time_since_last_tp > self._session_state.s3_timeout_ms

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        with self._session_lock:
            return {
                'current_session': self._session_state.current_session.name,
                'session_start_time': self._session_state.session_start_time,
                'p2_timeout_ms': self._session_state.p2_timeout_ms,
                'p2_star_timeout_ms': self._session_state.p2_star_timeout_ms,
                's3_timeout_ms': self._session_state.s3_timeout_ms,
                'security_level': self._session_state.security_level,
                'tester_present_active': self._session_state.tester_present_active,
                'application_state': self._application_state.name
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get UDS router statistics"""
        return {
            'total_requests': self._total_requests,
            'total_responses': self._total_responses,
            'total_timeouts': self._total_timeouts,
            'total_nrcs': self._total_nrcs,
            'registered_services': len(self._service_handlers),
            'pending_operations': len(self._pending_operations)
        }

    def set_session_change_callback(self, callback: Callable[[UDSSession, UDSSession], None]) -> None:
        """Set callback for session changes"""
        self._session_change_callback = callback

    def set_security_change_callback(self, callback: Callable[[int, int], None]) -> None:
        """Set callback for security level changes"""
        self._security_change_callback = callback