"""
ECU State Manager - MspClient Adaptation for AUTOSAR ECU Operational States

This module provides ECU state management with AUTOSAR BswM integration,
fault reporting through Dem, and state persistence across ignition cycles.
"""

import time
import asyncio
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ECU_State(Enum):
    """AUTOSAR ECU operational states"""
    OFF = "off"                   # ECU powered off
    STARTUP = "startup"          # ECU starting up
    NORMAL = "normal"            # Normal operation
    LIMP_HOME = "limp_home"      # Limp home mode (degraded operation)
    DIAGNOSTIC = "diagnostic"    # Diagnostic session active
    FAULT = "fault"              # Fault condition
    SHUTDOWN = "shutdown"        # ECU shutting down


class ECU_SubState(Enum):
    """ECU sub-states for more detailed state tracking"""
    INITIALIZING = "initializing"
    SELF_TEST = "self_test"
    NETWORK_STARTUP = "network_startup"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DIAGNOSTIC_ACTIVE = "diagnostic_active"
    FAULT_RECOVERY = "fault_recovery"
    SHUTTING_DOWN = "shutting_down"


class BswM_Mode(Enum):
    """AUTOSAR BswM modes"""
    STARTUP = "startup"
    RUN = "run"
    POST_RUN = "post_run"
    WAKEUP = "wakeup"
    SHUTDOWN = "shutdown"


class Dem_EventStatus(Enum):
    """AUTOSAR Dem event status"""
    PASSED = "passed"
    FAILED = "failed"
    PREPASSED = "prepassed"
    PREFAILED = "prefailed"


@dataclass
class ECU_StateTransition:
    """ECU state transition definition"""
    from_state: ECU_State
    to_state: ECU_State
    condition: str
    priority: int = 1
    timeout_ms: Optional[int] = None
    allowed_in_session: bool = True

    def is_allowed(self, current_session_active: bool) -> bool:
        """Check if transition is allowed"""
        if not self.allowed_in_session and current_session_active:
            return False
        return True


@dataclass
class ECU_Fault:
    """ECU fault information"""
    fault_id: str
    description: str
    severity: str
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    active: bool = True
    occurrence_count: int = 1
    dem_event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'fault_id': self.fault_id,
            'description': self.description,
            'severity': self.severity,
            'timestamp': self.timestamp,
            'active': self.active,
            'occurrence_count': self.occurrence_count,
            'dem_event_id': self.dem_event_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ECU_Fault':
        """Create from dictionary"""
        return cls(
            fault_id=data['fault_id'],
            description=data['description'],
            severity=data['severity'],
            timestamp=data['timestamp'],
            active=data.get('active', True),
            occurrence_count=data.get('occurrence_count', 1),
            dem_event_id=data.get('dem_event_id')
        )


@dataclass
class ECU_StateHistory:
    """ECU state transition history"""
    timestamp: int
    from_state: ECU_State
    to_state: ECU_State
    reason: str
    trigger: str = ""  # What triggered the transition

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'from_state': self.from_state.value,
            'to_state': self.to_state.value,
            'reason': self.reason,
            'trigger': self.trigger
        }


class ECU_StateManager:
    """
    ECU State Manager - MspClient adaptation for AUTOSAR ECU operational states

    Provides ECU state management with BswM integration, Dem fault reporting,
    and state persistence across ignition cycles.
    """

    def __init__(self, ecu_id: str, persistence_file: Optional[str] = None):
        """
        Initialize ECU State Manager

        Args:
            ecu_id: Unique ECU identifier
            persistence_file: File for state persistence
        """
        self.ecu_id = ecu_id
        self.persistence_file = persistence_file

        # State management
        self._current_state = ECU_State.OFF
        self._current_sub_state = ECU_SubState.INITIALIZING
        self._state_lock = threading.RLock()

        # State history
        self._state_history: List[ECU_StateHistory] = []
        self._max_history_entries = 100

        # State transitions
        self._transitions = self._setup_state_transitions()

        # Fault management
        self._active_faults: Dict[str, ECU_Fault] = {}
        self._fault_history: List[ECU_Fault] = []

        # AUTOSAR integration
        self._bswm_callback: Optional[Callable[[BswM_Mode], Awaitable[None]]] = None
        self._dem_callback: Optional[Callable[[str, Dem_EventStatus], Awaitable[None]]] = None

        # Diagnostic session state
        self._diagnostic_session_active = False
        self._session_lock = threading.RLock()

        # Health monitoring
        self._startup_time = 0
        self._uptime_seconds = 0
        self._fault_count = 0
        self._state_transition_count = 0

        # Load persisted state
        if persistence_file:
            self._load_persisted_state()

        # Initialize to OFF state
        self._record_state_transition(ECU_State.OFF, ECU_State.OFF, "ECU initialization", "startup")

    def _setup_state_transitions(self) -> List[ECU_StateTransition]:
        """Set up allowed state transitions"""
        return [
            # Power-up sequence
            ECU_StateTransition(ECU_State.OFF, ECU_State.STARTUP, "ECU power on", priority=10),
            ECU_StateTransition(ECU_State.STARTUP, ECU_State.NORMAL, "Startup complete", priority=9),

            # Normal operation transitions
            ECU_StateTransition(ECU_State.NORMAL, ECU_State.LIMP_HOME, "Fault detected", priority=8),
            ECU_StateTransition(ECU_State.NORMAL, ECU_State.DIAGNOSTIC, "Diagnostic session started", priority=7),
            ECU_StateTransition(ECU_State.NORMAL, ECU_State.FAULT, "Critical fault", priority=10),

            # Limp home transitions
            ECU_StateTransition(ECU_State.LIMP_HOME, ECU_State.NORMAL, "Fault cleared", priority=6),
            ECU_StateTransition(ECU_State.LIMP_HOME, ECU_State.DIAGNOSTIC, "Diagnostic session started", priority=5),
            ECU_StateTransition(ECU_State.LIMP_HOME, ECU_State.FAULT, "Additional fault", priority=9),

            # Diagnostic transitions
            ECU_StateTransition(ECU_State.DIAGNOSTIC, ECU_State.NORMAL, "Diagnostic session ended", priority=7),
            ECU_StateTransition(ECU_State.DIAGNOSTIC, ECU_State.LIMP_HOME, "Fault during diagnostic", priority=6),
            ECU_StateTransition(ECU_State.DIAGNOSTIC, ECU_State.FAULT, "Critical fault", priority=8),

            # Fault recovery
            ECU_StateTransition(ECU_State.FAULT, ECU_State.LIMP_HOME, "Fault recovery to limp home", priority=5),
            ECU_StateTransition(ECU_State.FAULT, ECU_State.NORMAL, "Fault cleared", priority=6),

            # Shutdown sequence
            ECU_StateTransition(ECU_State.NORMAL, ECU_State.SHUTDOWN, "ECU shutdown requested", priority=4),
            ECU_StateTransition(ECU_State.LIMP_HOME, ECU_State.SHUTDOWN, "ECU shutdown requested", priority=4),
            ECU_StateTransition(ECU_State.DIAGNOSTIC, ECU_State.SHUTDOWN, "ECU shutdown requested", priority=4),
            ECU_StateTransition(ECU_State.FAULT, ECU_State.SHUTDOWN, "ECU shutdown requested", priority=4),
            ECU_StateTransition(ECU_State.SHUTDOWN, ECU_State.OFF, "Shutdown complete", priority=3),
        ]

    async def startup(self) -> None:
        """Start ECU state manager"""
        logger.info(f"Starting ECU State Manager for {self.ecu_id}")

        # Transition to startup state
        await self.request_state_transition(ECU_State.STARTUP, "ECU startup")

        # Notify BswM of startup
        await self._notify_bswm(BswM_Mode.STARTUP)

        # Simulate startup sequence
        await asyncio.sleep(0.1)  # Brief startup delay

        # Transition to normal operation
        await self.request_state_transition(ECU_State.NORMAL, "Startup complete")

        # Notify BswM of run mode
        await self._notify_bswm(BswM_Mode.RUN)

        self._startup_time = int(time.time() * 1000)

    async def shutdown(self) -> None:
        """Shutdown ECU state manager"""
        logger.info(f"Shutting down ECU State Manager for {self.ecu_id}")

        # Transition to shutdown state
        await self.request_state_transition(ECU_State.SHUTDOWN, "ECU shutdown")

        # Notify BswM of shutdown
        await self._notify_bswm(BswM_Mode.SHUTDOWN)

        # Save state before shutdown
        if self.persistence_file:
            self._persist_state()

        # Transition to off state
        await self.request_state_transition(ECU_State.OFF, "Shutdown complete")

    async def request_state_transition(self, target_state: ECU_State, reason: str,
                                     trigger: str = "") -> bool:
        """
        Request a state transition

        Args:
            target_state: Target ECU state
            reason: Reason for transition
            trigger: What triggered the transition

        Returns:
            True if transition successful
        """
        with self._state_lock:
            current_state = self._current_state

            # Check if transition is allowed
            allowed_transitions = [t for t in self._transitions
                                 if t.from_state == current_state and t.to_state == target_state]

            if not allowed_transitions:
                logger.warning(f"Invalid state transition: {current_state.value} -> {target_state.value}")
                return False

            # Check session restrictions
            with self._session_lock:
                session_active = self._diagnostic_session_active

            valid_transitions = [t for t in allowed_transitions if t.is_allowed(session_active)]
            if not valid_transitions:
                logger.warning(f"State transition blocked by active diagnostic session: "
                             f"{current_state.value} -> {target_state.value}")
                return False

            # Select highest priority transition
            transition = max(valid_transitions, key=lambda t: t.priority)

            # Perform transition
            self._current_state = target_state
            self._state_transition_count += 1

            # Update sub-state based on main state
            self._update_sub_state()

            # Record transition
            self._record_state_transition(current_state, target_state, reason, trigger)

            logger.info(f"ECU state transition: {current_state.value} -> {target_state.value} ({reason})")

            # Handle special transitions
            if target_state == ECU_State.FAULT:
                await self._handle_fault_state()
            elif target_state == ECU_State.DIAGNOSTIC:
                await self._handle_diagnostic_state()
            elif target_state == ECU_State.NORMAL:
                await self._handle_normal_state()

            return True

    def _update_sub_state(self) -> None:
        """Update sub-state based on main state"""
        state_map = {
            ECU_State.OFF: ECU_SubState.INITIALIZING,
            ECU_State.STARTUP: ECU_SubState.SELF_TEST,
            ECU_State.NORMAL: ECU_SubState.OPERATIONAL,
            ECU_State.LIMP_HOME: ECU_SubState.DEGRADED,
            ECU_State.DIAGNOSTIC: ECU_SubState.DIAGNOSTIC_ACTIVE,
            ECU_State.FAULT: ECU_SubState.FAULT_RECOVERY,
            ECU_State.SHUTDOWN: ECU_SubState.SHUTTING_DOWN,
        }
        self._current_sub_state = state_map.get(self._current_state, ECU_SubState.INITIALIZING)

    async def _handle_fault_state(self) -> None:
        """Handle transition to fault state"""
        # Report all active faults to Dem
        for fault in self._active_faults.values():
            if self._dem_callback:
                await self._dem_callback(fault.fault_id, Dem_EventStatus.FAILED)

    async def _handle_diagnostic_state(self) -> None:
        """Handle transition to diagnostic state"""
        with self._session_lock:
            self._diagnostic_session_active = True

    async def _handle_normal_state(self) -> None:
        """Handle transition to normal state"""
        with self._session_lock:
            self._diagnostic_session_active = False

        # Clear non-critical faults
        await self._clear_recovered_faults()

    async def _clear_recovered_faults(self) -> None:
        """Clear faults that have been resolved"""
        # This would integrate with actual fault monitoring
        # For now, clear faults that are no longer active
        pass

    def _record_state_transition(self, from_state: ECU_State, to_state: ECU_State,
                                reason: str, trigger: str) -> None:
        """Record state transition in history"""
        history_entry = ECU_StateHistory(
            timestamp=int(time.time() * 1000),
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            trigger=trigger
        )

        self._state_history.append(history_entry)

        # Maintain history size limit
        if len(self._state_history) > self._max_history_entries:
            self._state_history.pop(0)

    async def _notify_bswm(self, mode: BswM_Mode) -> None:
        """Notify AUTOSAR BswM of mode change"""
        if self._bswm_callback:
            try:
                await self._bswm_callback(mode)
            except Exception as e:
                logger.error(f"BswM callback error: {e}")

    def set_bswm_callback(self, callback: Callable[[BswM_Mode], Awaitable[None]]) -> None:
        """Set BswM notification callback"""
        self._bswm_callback = callback

    def set_dem_callback(self, callback: Callable[[str, Dem_EventStatus], Awaitable[None]]) -> None:
        """Set Dem event reporting callback"""
        self._dem_callback = callback

    async def report_fault(self, fault_id: str, description: str, severity: str = "moderate",
                          dem_event_id: Optional[str] = None) -> None:
        """
        Report a fault to the ECU state manager

        Args:
            fault_id: Unique fault identifier
            description: Fault description
            severity: Fault severity (minor, moderate, major, critical)
            dem_event_id: Associated Dem event ID
        """
        with self._state_lock:
            if fault_id in self._active_faults:
                # Increment occurrence count
                self._active_faults[fault_id].occurrence_count += 1
                self._active_faults[fault_id].timestamp = int(time.time() * 1000)
            else:
                # New fault
                fault = ECU_Fault(
                    fault_id=fault_id,
                    description=description,
                    severity=severity,
                    dem_event_id=dem_event_id
                )
                self._active_faults[fault_id] = fault
                self._fault_history.append(fault)
                self._fault_count += 1

            # Notify Dem
            if self._dem_callback:
                await self._dem_callback(fault_id, Dem_EventStatus.FAILED)

            # Check if state transition needed based on severity
            await self._evaluate_fault_impact(severity)

            logger.info(f"Fault reported: {fault_id} ({severity})")

    async def clear_fault(self, fault_id: str) -> bool:
        """
        Clear a fault

        Args:
            fault_id: Fault identifier to clear

        Returns:
            True if fault was cleared
        """
        with self._state_lock:
            if fault_id not in self._active_faults:
                return False

            fault = self._active_faults[fault_id]
            fault.active = False

            # Notify Dem
            if self._dem_callback:
                await self._dem_callback(fault_id, Dem_EventStatus.PASSED)

            # Keep in history but mark inactive
            del self._active_faults[fault_id]

            # Check if state can return to normal
            await self._evaluate_fault_clearance()

            logger.info(f"Fault cleared: {fault_id}")
            return True

    async def _evaluate_fault_impact(self, severity: str) -> None:
        """Evaluate if fault requires state change"""
        critical_severities = ["major", "critical"]

        if severity in critical_severities and self._current_state != ECU_State.FAULT:
            await self.request_state_transition(
                ECU_State.FAULT, f"Critical fault detected ({severity})", "fault_monitoring"
            )
        elif severity == "moderate" and self._current_state == ECU_State.NORMAL:
            # Consider limp home mode for moderate faults
            if len(self._active_faults) > 2:  # Multiple moderate faults
                await self.request_state_transition(
                    ECU_State.LIMP_HOME, "Multiple faults detected", "fault_monitoring"
                )

    async def _evaluate_fault_clearance(self) -> None:
        """Evaluate if faults have cleared enough to return to normal operation"""
        if not self._active_faults:
            # All faults cleared
            if self._current_state in [ECU_State.LIMP_HOME, ECU_State.FAULT]:
                await self.request_state_transition(
                    ECU_State.NORMAL, "All faults cleared", "fault_monitoring"
                )

    def get_current_state(self) -> Tuple[ECU_State, ECU_SubState]:
        """Get current ECU state"""
        with self._state_lock:
            return (self._current_state, self._current_sub_state)

    def get_active_faults(self) -> List[ECU_Fault]:
        """Get list of active faults"""
        with self._state_lock:
            return list(self._active_faults.values())

    def get_state_history(self, limit: Optional[int] = None) -> List[ECU_StateHistory]:
        """Get state transition history"""
        with self._state_lock:
            history = self._state_history
            if limit:
                history = history[-limit:]
            return history.copy()

    def get_health_status(self) -> Dict[str, Any]:
        """Get ECU health status"""
        with self._state_lock:
            current_time = int(time.time() * 1000)
            uptime = (current_time - self._startup_time) // 1000 if self._startup_time > 0 else 0

            return {
                'ecu_id': self.ecu_id,
                'current_state': self._current_state.value,
                'current_sub_state': self._current_sub_state.value,
                'uptime_seconds': uptime,
                'active_faults': len(self._active_faults),
                'total_faults': self._fault_count,
                'state_transitions': self._state_transition_count,
                'diagnostic_session_active': self._diagnostic_session_active
            }

    def _persist_state(self) -> None:
        """Persist ECU state to file"""
        if not self.persistence_file:
            return

        try:
            state_data = {
                'ecu_id': self.ecu_id,
                'current_state': self._current_state.value,
                'current_sub_state': self._current_sub_state.value,
                'startup_time': self._startup_time,
                'active_faults': [f.to_dict() for f in self._active_faults.values()],
                'state_history': [h.to_dict() for h in self._state_history[-20:]],  # Last 20 transitions
                'diagnostic_session_active': self._diagnostic_session_active
            }

            with open(self.persistence_file, 'w') as f:
                json.dump(state_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to persist ECU state: {e}")

    def _load_persisted_state(self) -> None:
        """Load persisted ECU state from file"""
        if not self.persistence_file:
            return

        try:
            with open(self.persistence_file, 'r') as f:
                state_data = json.load(f)

            # Restore state
            self._current_state = ECU_State(state_data.get('current_state', 'off'))
            self._current_sub_state = ECU_SubState(state_data.get('current_sub_state', 'initializing'))
            self._startup_time = state_data.get('startup_time', 0)
            self._diagnostic_session_active = state_data.get('diagnostic_session_active', False)

            # Restore active faults
            for fault_data in state_data.get('active_faults', []):
                fault = ECU_Fault.from_dict(fault_data)
                self._active_faults[fault.fault_id] = fault

            # Restore state history
            for history_data in state_data.get('state_history', []):
                history = ECU_StateHistory(
                    timestamp=history_data['timestamp'],
                    from_state=ECU_State(history_data['from_state']),
                    to_state=ECU_State(history_data['to_state']),
                    reason=history_data['reason'],
                    trigger=history_data.get('trigger', '')
                )
                self._state_history.append(history)

            logger.info(f"Loaded persisted state for ECU {self.ecu_id}")

        except FileNotFoundError:
            logger.info(f"No persisted state found for ECU {self.ecu_id}")
        except Exception as e:
            logger.error(f"Failed to load persisted ECU state: {e}")

    async def diagnostic_session_start(self) -> None:
        """Handle diagnostic session start"""
        if self._current_state != ECU_State.DIAGNOSTIC:
            await self.request_state_transition(
                ECU_State.DIAGNOSTIC, "Diagnostic session started", "uds_service"
            )

    async def diagnostic_session_end(self) -> None:
        """Handle diagnostic session end"""
        if self._current_state == ECU_State.DIAGNOSTIC:
            # Return to appropriate state based on faults
            target_state = ECU_State.NORMAL if not self._active_faults else ECU_State.LIMP_HOME
            await self.request_state_transition(
                target_state, "Diagnostic session ended", "uds_service"
            )