"""
AUTOSAR Integration Layer - OMS to AUTOSAR Component Mapping

This module provides AUTOSAR abstraction layer mapping OMS components to
standard AUTOSAR services (Dcm, Dem, BswM, PduR, Os) for seamless integration.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from .uds_router import UDSRouter, UDSResponse, UDSNRC, UDSSession
from .dtc_manager import DTCManager, DTCEntry
from .ecu_client import ECU_StateManager, ECU_State
from .isotp_queue import ISOTP_Queue
from .automotive_timing import AutomotiveTiming, TimerType

logger = logging.getLogger(__name__)


class AUTOSAR_Module(Enum):
    """AUTOSAR modules being integrated"""
    DCM = "dcm"         # Diagnostic Communication Manager
    DEM = "dem"         # Diagnostic Event Manager
    BSWM = "bswm"       # Basic Software Mode Manager
    PDUR = "pdu_r"      # PDU Router
    OS = "os"           # Operating System
    COM = "com"         # Communication
    CANIF = "can_if"    # CAN Interface


class Dcm_StatusType(Enum):
    """DCM status types"""
    DCM_E_OK = "ok"
    DCM_E_PENDING = "pending"
    DCM_E_COMPARE_KEY_FAILED = "compare_key_failed"
    DCM_E_NOT_OK = "not_ok"


class Dem_EventStatusType(Enum):
    """DEM event status types"""
    DEM_EVENT_STATUS_PASSED = "passed"
    DEM_EVENT_STATUS_FAILED = "failed"
    DEM_EVENT_STATUS_PREPASSED = "prepassed"
    DEM_EVENT_STATUS_PREFAILED = "prefailed"


class BswM_ModeType(Enum):
    """BSWM mode types"""
    BSWM_STARTUP = "startup"
    BSWM_RUN = "run"
    BSWM_POST_RUN = "post_run"
    BSWM_WAKEUP = "wakeup"
    BSWM_SHUTDOWN = "shutdown"


@dataclass
class AUTOSAR_ServiceInterface:
    """AUTOSAR service interface definition"""
    module: AUTOSAR_Module
    service_name: str
    parameters: Dict[str, Any]
    return_type: str
    description: str


class AUTOSAR_DcmInterface:
    """
    AUTOSAR DCM (Diagnostic Communication Manager) Interface

    Maps OMS MsgBroker to DCM service dispatcher
    """

    def __init__(self, uds_router: UDSRouter):
        self.uds_router = uds_router
        self.dcm_services: Dict[int, Callable] = {}
        self._register_dcm_services()

    def _register_dcm_services(self) -> None:
        """Register DCM service handlers"""
        # Map UDS services to DCM interfaces
        self.dcm_services = {
            0x10: self._dcm_diagnostic_session_control,
            0x11: self._dcm_ecu_reset,
            0x14: self._dcm_clear_diagnostic_information,
            0x19: self._dcm_read_dtc_information,
            0x22: self._dcm_read_data_by_identifier,
            0x23: self._dcm_read_memory_by_address,
            0x27: self._dcm_security_access,
            0x2E: self._dcm_write_data_by_identifier,
            0x31: self._dcm_routine_control,
            0x34: self._dcm_request_download,
            0x3E: self._dcm_tester_present,
        }

    async def dcm_process_request(self, service_id: int, request_data: bytes,
                                 source_address: Optional[int] = None) -> Tuple[Dcm_StatusType, Optional[bytes]]:
        """
        Process DCM request (AUTOSAR DCM main interface)

        Args:
            service_id: UDS service ID
            request_data: Request data
            source_address: Source ECU address

        Returns:
            Tuple of (status, response_data)
        """
        try:
            # Route through UDS router
            response = await self.uds_router.process_request(request_data, source_address)

            if response:
                if response.response_code == 0x00:  # Positive response
                    return Dcm_StatusType.DCM_E_OK, response.data
                else:  # Negative response
                    return Dcm_StatusType.DCM_E_NOT_OK, bytes([response.response_code])
            else:
                return Dcm_StatusType.DCM_E_NOT_OK, None

        except Exception as e:
            logger.error(f"DCM request processing error: {e}")
            return Dcm_StatusType.DCM_E_NOT_OK, None

    def _dcm_diagnostic_session_control(self, subfunction: int, data: bytes) -> None:
        """DCM DiagnosticSessionControl service"""
        # Map subfunction to session type
        session_map = {
            0x01: UDSSession.DEFAULT,
            0x02: UDSSession.PROGRAMMING,
            0x03: UDSSession.EXTENDED,
        }
        # Implementation handled by UDS router
        pass

    def _dcm_ecu_reset(self, subfunction: int, data: bytes) -> None:
        """DCM EcuReset service"""
        pass

    def _dcm_clear_diagnostic_information(self, subfunction: int, data: bytes) -> None:
        """DCM ClearDiagnosticInformation service"""
        pass

    def _dcm_read_dtc_information(self, subfunction: int, data: bytes) -> None:
        """DCM ReadDTCInformation service"""
        pass

    def _dcm_read_data_by_identifier(self, subfunction: int, data: bytes) -> None:
        """DCM ReadDataByIdentifier service"""
        pass

    def _dcm_read_memory_by_address(self, subfunction: int, data: bytes) -> None:
        """DCM ReadMemoryByAddress service"""
        pass

    def _dcm_security_access(self, subfunction: int, data: bytes) -> None:
        """DCM SecurityAccess service"""
        pass

    def _dcm_write_data_by_identifier(self, subfunction: int, data: bytes) -> None:
        """DCM WriteDataByIdentifier service"""
        pass

    def _dcm_routine_control(self, subfunction: int, data: bytes) -> None:
        """DCM RoutineControl service"""
        pass

    def _dcm_request_download(self, subfunction: int, data: bytes) -> None:
        """DCM RequestDownload service"""
        pass

    def _dcm_tester_present(self, subfunction: int, data: bytes) -> None:
        """DCM TesterPresent service"""
        pass


class AUTOSAR_DemInterface:
    """
    AUTOSAR DEM (Diagnostic Event Manager) Interface

    Maps OMS LogManager/DTC Manager to DEM event manager
    """

    def __init__(self, dtc_manager: DTCManager):
        self.dtc_manager = dtc_manager
        self.event_mappings: Dict[str, str] = {}  # DTC code -> DEM event ID
        self.dem_events: Dict[str, Dict[str, Any]] = {}
        self.event_callbacks: Dict[str, Callable] = {}

    def dem_set_event_status(self, event_id: str, event_status: Dem_EventStatusType) -> bool:
        """
        Set DEM event status (AUTOSAR DEM main interface)

        Args:
            event_id: DEM event identifier
            event_status: Event status

        Returns:
            True if successful
        """
        try:
            # Map DEM event to DTC
            dtc_code = self._dem_event_to_dtc(event_id)
            if not dtc_code:
                logger.warning(f"No DTC mapping for DEM event {event_id}")
                return False

            # Update DTC based on event status
            if event_status == Dem_EventStatusType.DEM_EVENT_STATUS_FAILED:
                return self.dtc_manager.report_failure(dtc_code, dtc_format=self.dtc_manager.dtc_format)
            elif event_status == Dem_EventStatusType.DEM_EVENT_STATUS_PASSED:
                return self.dtc_manager.clear_fault(str(dtc_code))

            return True

        except Exception as e:
            logger.error(f"DEM set event status error: {e}")
            return False

    def dem_get_event_status(self, event_id: str) -> Optional[Dem_EventStatusType]:
        """Get DEM event status"""
        dtc_code = self._dem_event_to_dtc(event_id)
        if dtc_code:
            dtc_entry = self.dtc_manager.get_dtc_status(dtc_code)
            if dtc_entry:
                if dtc_entry.is_active():
                    return Dem_EventStatusType.DEM_EVENT_STATUS_FAILED
                else:
                    return Dem_EventStatusType.DEM_EVENT_STATUS_PASSED
        return None

    def register_event_mapping(self, dtc_code: int, dem_event_id: str) -> None:
        """Register DTC to DEM event mapping"""
        self.event_mappings[str(dtc_code)] = dem_event_id

    def _dem_event_to_dtc(self, event_id: str) -> Optional[int]:
        """Convert DEM event ID to DTC code"""
        for dtc_str, dem_id in self.event_mappings.items():
            if dem_id == event_id:
                return int(dtc_str)
        return None

    def get_event_memory(self) -> List[Dict[str, Any]]:
        """Get DEM event memory (mapped DTCs)"""
        events = []
        for dtc_entry in self.dtc_manager.get_all_dtcs():
            event_id = self.event_mappings.get(str(dtc_entry.dtc_code), f"DTC_{dtc_entry.dtc_code}")
            events.append({
                'event_id': event_id,
                'dtc_code': dtc_entry.dtc_code,
                'status': dtc_entry.get_status_byte(),
                'occurrence_count': dtc_entry.occurrence_count,
                'last_failed': dtc_entry.last_failed_time,
                'last_confirmed': dtc_entry.last_confirmed_time
            })
        return events


class AUTOSAR_BswMInterface:
    """
    AUTOSAR BSWM (Basic Software Mode Manager) Interface

    Maps OMS MspClient/ECU State Manager to BSWM mode manager
    """

    def __init__(self, ecu_manager: ECU_StateManager):
        self.ecu_manager = ecu_manager
        self.mode_request_callbacks: Dict[BswM_ModeType, Callable] = {}

    async def bswm_request_mode(self, mode: BswM_ModeType) -> bool:
        """
        Request BSWM mode change (AUTOSAR BSWM main interface)

        Args:
            mode: Requested mode

        Returns:
            True if mode change successful
        """
        try:
            # Map BSWM mode to ECU state
            state_mapping = {
                BswM_ModeType.BSWM_STARTUP: ECU_State.STARTUP,
                BswM_ModeType.BSWM_RUN: ECU_State.NORMAL,
                BswM_ModeType.BSWM_POST_RUN: ECU_State.LIMP_HOME,
                BswM_ModeType.BSWM_WAKEUP: ECU_State.NORMAL,
                BswM_ModeType.BSWM_SHUTDOWN: ECU_State.SHUTDOWN,
            }

            target_state = state_mapping.get(mode)
            if target_state:
                return await self.ecu_manager.request_state_transition(
                    target_state, f"BSWM mode request: {mode.value}"
                )

            return False

        except Exception as e:
            logger.error(f"BSWM request mode error: {e}")
            return False

    def register_mode_callback(self, mode: BswM_ModeType, callback: Callable) -> None:
        """Register callback for mode changes"""
        self.mode_request_callbacks[mode] = callback

    def get_current_mode(self) -> BswM_ModeType:
        """Get current BSWM mode"""
        current_state = self.ecu_manager.get_current_state()[0]

        # Map ECU state to BSWM mode
        mode_mapping = {
            ECU_State.OFF: BswM_ModeType.BSWM_SHUTDOWN,
            ECU_State.STARTUP: BswM_ModeType.BSWM_STARTUP,
            ECU_State.NORMAL: BswM_ModeType.BSWM_RUN,
            ECU_State.LIMP_HOME: BswM_ModeType.BSWM_POST_RUN,
            ECU_State.DIAGNOSTIC: BswM_ModeType.BSWM_RUN,
            ECU_State.FAULT: BswM_ModeType.BSWM_POST_RUN,
            ECU_State.SHUTDOWN: BswM_ModeType.BSWM_SHUTDOWN,
        }

        return mode_mapping.get(current_state, BswM_ModeType.BSWM_RUN)


class AUTOSAR_PduRInterface:
    """
    AUTOSAR PDU Router Interface

    Maps OMS MessageQueue to PDU Router transport protocol
    """

    def __init__(self, isotp_queue: ISOTP_Queue):
        self.isotp_queue = isotp_queue
        self.pdu_mappings: Dict[int, Dict[str, Any]] = {}

    async def pdur_transmit(self, pdu_id: int, data: bytes) -> bool:
        """
        Transmit PDU (AUTOSAR PduR main interface)

        Args:
            pdu_id: PDU identifier
            data: PDU data

        Returns:
            True if transmission successful
        """
        try:
            # Map PDU ID to CAN ID
            can_id = self._pdu_to_can_id(pdu_id)
            if can_id is None:
                logger.warning(f"No CAN ID mapping for PDU {pdu_id}")
                return False

            # Send through ISO-TP queue
            return await self.isotp_queue.send_message(can_id, data)

        except Exception as e:
            logger.error(f"PduR transmit error: {e}")
            return False

    def pdur_receive(self, pdu_id: int, data: bytes) -> None:
        """Receive PDU (callback from transport layer)"""
        # Forward to registered handlers
        pass

    def register_pdu_mapping(self, pdu_id: int, can_id: int, **metadata) -> None:
        """Register PDU to CAN ID mapping"""
        self.pdu_mappings[pdu_id] = {
            'can_id': can_id,
            **metadata
        }

    def _pdu_to_can_id(self, pdu_id: int) -> Optional[int]:
        """Convert PDU ID to CAN ID"""
        mapping = self.pdu_mappings.get(pdu_id)
        return mapping.get('can_id') if mapping else None


class AUTOSAR_OsInterface:
    """
    AUTOSAR OS Interface

    Maps OMS timing to OS elapsed time services
    """

    def __init__(self):
        self.timers: Dict[int, int] = {}  # Timer ID -> start time
        self.timer_counter = 0

    def os_get_elapsed_time(self, timer_id: int) -> Tuple[bool, int]:
        """
        Get elapsed time for timer (AUTOSAR Os_GetElapsedTime)

        Args:
            timer_id: Timer identifier

        Returns:
            Tuple of (success, elapsed_time_us)
        """
        try:
            start_time = self.timers.get(timer_id)
            if start_time is None:
                return False, 0

            elapsed = AutomotiveTiming.get_elapsed_time_us(start_time)
            return True, elapsed

        except Exception as e:
            logger.error(f"OS get elapsed time error: {e}")
            return False, 0

    def os_start_timer(self) -> int:
        """Start a new timer"""
        timer_id = self.timer_counter
        self.timer_counter += 1
        self.timers[timer_id] = AutomotiveTiming.get_current_time_us()
        return timer_id

    def os_stop_timer(self, timer_id: int) -> bool:
        """Stop a timer"""
        if timer_id in self.timers:
            del self.timers[timer_id]
            return True
        return False

    def os_get_current_time(self) -> int:
        """Get current OS time (microseconds)"""
        return AutomotiveTiming.get_current_time_us()


class AUTOSAR_IntegrationLayer:
    """
    AUTOSAR Integration Layer - Complete OMS to AUTOSAR Mapping

    Provides unified interface to all AUTOSAR services with OMS component mappings:
    - MsgBroker → DCM service dispatcher
    - LogManager → DEM event manager
    - MspClient → BSWM mode manager
    - MessageQueue → PduR transport protocol
    - Timing → OS elapsed time services
    """

    def __init__(self):
        # Core OMS components (to be injected)
        self.uds_router: Optional[UDSRouter] = None
        self.dtc_manager: Optional[DTCManager] = None
        self.ecu_manager: Optional[ECU_StateManager] = None
        self.isotp_queue: Optional[ISOTP_Queue] = None

        # AUTOSAR interfaces
        self.dcm: Optional[AUTOSAR_DcmInterface] = None
        self.dem: Optional[AUTOSAR_DemInterface] = None
        self.bswm: Optional[AUTOSAR_BswMInterface] = None
        self.pdur: Optional[AUTOSAR_PduRInterface] = None
        self.os: AUTOSAR_OsInterface = AUTOSAR_OsInterface()

        # Integration status
        self.initialized = False

    def initialize(self, uds_router: UDSRouter, dtc_manager: DTCManager,
                   ecu_manager: ECU_StateManager, isotp_queue: ISOTP_Queue) -> bool:
        """
        Initialize AUTOSAR integration layer

        Args:
            uds_router: UDS diagnostic router instance
            dtc_manager: DTC manager instance
            ecu_manager: ECU state manager instance
            isotp_queue: ISO-TP transport queue instance

        Returns:
            True if initialization successful
        """
        try:
            self.uds_router = uds_router
            self.dtc_manager = dtc_manager
            self.ecu_manager = ecu_manager
            self.isotp_queue = isotp_queue

            # Create AUTOSAR interfaces
            self.dcm = AUTOSAR_DcmInterface(uds_router)
            self.dem = AUTOSAR_DemInterface(dtc_manager)
            self.bswm = AUTOSAR_BswMInterface(ecu_manager)
            self.pdur = AUTOSAR_PduRInterface(isotp_queue)

            # Set up callbacks
            self._setup_callbacks()

            self.initialized = True
            logger.info("AUTOSAR Integration Layer initialized successfully")
            return True

        except Exception as e:
            logger.error(f"AUTOSAR integration initialization error: {e}")
            return False

    def _setup_callbacks(self) -> None:
        """Set up callbacks between components"""
        if self.ecu_manager and self.bswm:
            self.ecu_manager.set_bswm_callback(self.bswm.bswm_request_mode)

        if self.dtc_manager and self.dem:
            self.dtc_manager.set_dem_callbacks(
                report_callback=self._dem_report_callback,
                clear_callback=self._dem_clear_callback
            )

    def _dem_report_callback(self, dtc_code: int, event_name: str) -> None:
        """DEM report callback"""
        if self.dem:
            self.dem.dem_set_event_status(str(dtc_code), Dem_EventStatusType.DEM_EVENT_STATUS_FAILED)

    def _dem_clear_callback(self, dtc_code: int) -> None:
        """DEM clear callback"""
        if self.dem:
            self.dem.dem_set_event_status(str(dtc_code), Dem_EventStatusType.DEM_EVENT_STATUS_PASSED)

    # Public AUTOSAR API methods

    async def process_diagnostic_request(self, service_id: int, data: bytes,
                                       source_address: Optional[int] = None) -> Tuple[Dcm_StatusType, Optional[bytes]]:
        """
        Process diagnostic request through DCM interface

        Args:
            service_id: UDS service ID
            data: Request data
            source_address: Source address

        Returns:
            DCM status and response data
        """
        if not self.dcm:
            return Dcm_StatusType.DCM_E_NOT_OK, None
        return await self.dcm.dcm_process_request(service_id, data, source_address)

    def get_dem_event_memory(self) -> List[Dict[str, Any]]:
        """Get DEM event memory"""
        if not self.dem:
            return []
        return self.dem.get_event_memory()

    async def request_bswm_mode(self, mode: BswM_ModeType) -> bool:
        """Request BSWM mode change"""
        if not self.bswm:
            return False
        return await self.bswm.bswm_request_mode(mode)

    def get_current_bswm_mode(self) -> BswM_ModeType:
        """Get current BSWM mode"""
        if not self.bswm:
            return BswM_ModeType.BSWM_RUN
        return self.bswm.get_current_mode()

    async def transmit_pdu(self, pdu_id: int, data: bytes) -> bool:
        """Transmit PDU through PduR"""
        if not self.pdur:
            return False
        return await self.pdur.pdur_transmit(pdu_id, data)

    def get_os_elapsed_time(self, timer_id: int) -> Tuple[bool, int]:
        """Get OS elapsed time"""
        return self.os.os_get_elapsed_time(timer_id)

    def start_os_timer(self) -> int:
        """Start OS timer"""
        return self.os.os_start_timer()

    def get_os_current_time(self) -> int:
        """Get OS current time"""
        return self.os.os_get_current_time()

    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration layer status"""
        return {
            'initialized': self.initialized,
            'dcm_available': self.dcm is not None,
            'dem_available': self.dem is not None,
            'bswm_available': self.bswm is not None,
            'pdur_available': self.pdur is not None,
            'os_available': True,
            'uds_router_connected': self.uds_router is not None,
            'dtc_manager_connected': self.dtc_manager is not None,
            'ecu_manager_connected': self.ecu_manager is not None,
            'isotp_queue_connected': self.isotp_queue is not None
        }

    def get_service_interfaces(self) -> List[AUTOSAR_ServiceInterface]:
        """Get list of available AUTOSAR service interfaces"""
        interfaces = []

        if self.dcm:
            interfaces.extend([
                AUTOSAR_ServiceInterface(
                    module=AUTOSAR_Module.DCM,
                    service_name="Dcm_ProcessRequest",
                    parameters={"service_id": "int", "request_data": "bytes", "source_address": "int"},
                    return_type="Tuple[Dcm_StatusType, Optional[bytes]]",
                    description="Process diagnostic request"
                )
            ])

        if self.dem:
            interfaces.extend([
                AUTOSAR_ServiceInterface(
                    module=AUTOSAR_Module.DEM,
                    service_name="Dem_SetEventStatus",
                    parameters={"event_id": "str", "event_status": "Dem_EventStatusType"},
                    return_type="bool",
                    description="Set DEM event status"
                )
            ])

        if self.bswm:
            interfaces.extend([
                AUTOSAR_ServiceInterface(
                    module=AUTOSAR_Module.BSWM,
                    service_name="BswM_RequestMode",
                    parameters={"mode": "BswM_ModeType"},
                    return_type="bool",
                    description="Request BSWM mode change"
                )
            ])

        if self.pdur:
            interfaces.extend([
                AUTOSAR_ServiceInterface(
                    module=AUTOSAR_Module.PDUR,
                    service_name="PduR_Transmit",
                    parameters={"pdu_id": "int", "data": "bytes"},
                    return_type="bool",
                    description="Transmit PDU"
                )
            ])

        interfaces.extend([
            AUTOSAR_ServiceInterface(
                module=AUTOSAR_Module.OS,
                service_name="Os_GetElapsedTime",
                parameters={"timer_id": "int"},
                return_type="Tuple[bool, int]",
                description="Get elapsed time"
            )
        ])

        return interfaces