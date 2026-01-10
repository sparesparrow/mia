"""
Automotive Timing Infrastructure - AUTOSAR OS Timing Services Integration

This module provides automotive-grade timing services with microsecond precision,
monotonic timers, and AUTOSAR OS integration for real-time automotive applications.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import platform

logger = logging.getLogger(__name__)


class TimerType(Enum):
    """Timer types for different use cases"""
    MONOTONIC = "monotonic"       # Monotonic time for duration measurements
    WALL_CLOCK = "wall_clock"     # Wall clock time for absolute timestamps
    CAN_TIMING = "can_timing"     # High-precision for CAN bus timing
    DIAGNOSTIC = "diagnostic"     # For diagnostic timeouts
    SAFETY_CRITICAL = "safety"    # For safety-critical timing


class AUTOSAR_TickType(Enum):
    """AUTOSAR tick types"""
    OS_TICK = "os_tick"           # OS tick counter
    HW_COUNTER = "hw_counter"     # Hardware counter
    SW_COUNTER = "sw_counter"     # Software counter


@dataclass
class TimerSnapshot:
    """Timer snapshot for elapsed time calculations"""
    timer_type: TimerType
    start_time_us: int
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_elapsed_us(self) -> int:
        """Get elapsed time in microseconds"""
        current_time_us = AutomotiveTiming.get_current_time_us(self.timer_type)
        return current_time_us - self.start_time_us

    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds"""
        return self.get_elapsed_us() / 1000.0

    def reset(self) -> None:
        """Reset timer snapshot"""
        self.start_time_us = AutomotiveTiming.get_current_time_us(self.timer_type)


@dataclass
class TimeoutMonitor:
    """Timeout monitor for automotive operations"""
    operation_id: str
    timeout_us: int
    start_time_us: int
    timer_type: TimerType = TimerType.SAFETY_CRITICAL
    callback: Optional[Callable[[str], None]] = None

    def is_expired(self) -> bool:
        """Check if timeout has expired"""
        elapsed = AutomotiveTiming.get_current_time_us(self.timer_type) - self.start_time_us
        return elapsed >= self.timeout_us

    def get_remaining_us(self) -> int:
        """Get remaining time in microseconds"""
        elapsed = AutomotiveTiming.get_current_time_us(self.timer_type) - self.start_time_us
        return max(0, self.timeout_us - elapsed)

    def trigger_callback(self) -> None:
        """Trigger timeout callback"""
        if self.callback:
            try:
                self.callback(self.operation_id)
            except Exception as e:
                logger.error(f"Timeout callback error for {self.operation_id}: {e}")


class AutomotiveTiming:
    """
    Automotive Timing Infrastructure - AUTOSAR OS timing services integration

    Provides microsecond precision timing, monotonic timers, and AUTOSAR OS
    integration for real-time automotive applications.
    """

    # Class variables for timing state
    _initialized = False
    _base_time_ns = 0
    _tick_counter = 0
    _tick_interval_us = 1000  # 1ms default tick interval
    _lock = threading.RLock()

    # Platform-specific timing sources
    _hw_timer_available = False
    _hw_timer_frequency = 0

    # Timeout monitoring
    _active_timeouts: Dict[str, TimeoutMonitor] = {}
    _timeout_thread: Optional[threading.Thread] = None
    _timeout_running = False

    @classmethod
    def initialize(cls, tick_interval_us: int = 1000) -> None:
        """
        Initialize automotive timing system

        Args:
            tick_interval_us: Tick interval in microseconds
        """
        if cls._initialized:
            return

        with cls._lock:
            cls._base_time_ns = time.time_ns()
            cls._tick_counter = 0
            cls._tick_interval_us = tick_interval_us

            # Detect platform capabilities
            cls._detect_platform_capabilities()

            # Start timeout monitoring thread
            cls._start_timeout_monitoring()

            cls._initialized = True
            logger.info(f"Automotive Timing initialized with {tick_interval_us}us tick interval")

    @classmethod
    def shutdown(cls) -> None:
        """Shutdown automotive timing system"""
        if not cls._initialized:
            return

        with cls._lock:
            cls._stop_timeout_monitoring()
            cls._initialized = False
            logger.info("Automotive Timing shutdown")

    @classmethod
    def _detect_platform_capabilities(cls) -> None:
        """Detect platform timing capabilities"""
        try:
            # Check for high-resolution timer
            # In Python, time.perf_counter_ns() provides the best resolution
            test_start = time.perf_counter_ns()
            time.sleep(0.001)  # 1ms
            test_end = time.perf_counter_ns()
            resolution_ns = test_end - test_start

            cls._hw_timer_available = resolution_ns > 0
            cls._hw_timer_frequency = 1_000_000_000 // resolution_ns if resolution_ns > 0 else 0

            logger.info(f"Platform timer resolution: {resolution_ns}ns, frequency: {cls._hw_timer_frequency}Hz")

        except Exception as e:
            logger.warning(f"Failed to detect platform timing capabilities: {e}")
            cls._hw_timer_available = False

    @classmethod
    def get_current_time_us(cls, timer_type: TimerType = TimerType.MONOTONIC) -> int:
        """
        Get current time in microseconds

        Args:
            timer_type: Type of timer to use

        Returns:
            Current time in microseconds
        """
        if not cls._initialized:
            cls.initialize()

        if timer_type == TimerType.WALL_CLOCK:
            return int(time.time() * 1_000_000)
        elif timer_type == TimerType.CAN_TIMING:
            # Use highest precision for CAN timing
            return int(time.perf_counter_ns() // 1000)
        elif timer_type == TimerType.SAFETY_CRITICAL:
            # Use monotonic clock for safety-critical timing
            return int(time.monotonic() * 1_000_000)
        else:  # MONOTONIC or DIAGNOSTIC
            return int((time.time_ns() - cls._base_time_ns) // 1000)

    @classmethod
    def get_elapsed_time_us(cls, start_time_us: int,
                           timer_type: TimerType = TimerType.MONOTONIC) -> int:
        """
        Get elapsed time since start time (AUTOSAR Os_GetElapsedTime equivalent)

        Args:
            start_time_us: Start time in microseconds
            timer_type: Timer type used

        Returns:
            Elapsed time in microseconds
        """
        current_time_us = cls.get_current_time_us(timer_type)
        return current_time_us - start_time_us

    @classmethod
    def create_timer_snapshot(cls, timer_type: TimerType = TimerType.MONOTONIC,
                             description: str = "") -> TimerSnapshot:
        """
        Create a timer snapshot for elapsed time measurements

        Args:
            timer_type: Type of timer to use
            description: Description of the timer

        Returns:
            TimerSnapshot object
        """
        return TimerSnapshot(
            timer_type=timer_type,
            start_time_us=cls.get_current_time_us(timer_type),
            description=description
        )

    @classmethod
    def tick(cls) -> int:
        """
        Automotive tick function (replaces OMS tick())

        Returns:
            Current tick count
        """
        if not cls._initialized:
            cls.initialize()

        with cls._lock:
            current_time_us = cls.get_current_time_us()
            ticks_elapsed = current_time_us // cls._tick_interval_us

            if ticks_elapsed > cls._tick_counter:
                cls._tick_counter = ticks_elapsed

            return cls._tick_counter

    @classmethod
    def get_tick_duration_us(cls) -> int:
        """Get tick duration in microseconds"""
        return cls._tick_interval_us

    @classmethod
    def set_timeout(cls, operation_id: str, timeout_us: int,
                   timer_type: TimerType = TimerType.SAFETY_CRITICAL,
                   callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Set a timeout for an operation

        Args:
            operation_id: Unique operation identifier
            timeout_us: Timeout in microseconds
            timer_type: Timer type to use
            callback: Callback function when timeout expires
        """
        if not cls._initialized:
            cls.initialize()

        monitor = TimeoutMonitor(
            operation_id=operation_id,
            timeout_us=timeout_us,
            start_time_us=cls.get_current_time_us(timer_type),
            timer_type=timer_type,
            callback=callback
        )

        with cls._lock:
            cls._active_timeouts[operation_id] = monitor

    @classmethod
    def cancel_timeout(cls, operation_id: str) -> None:
        """
        Cancel a timeout

        Args:
            operation_id: Operation identifier
        """
        with cls._lock:
            cls._active_timeouts.pop(operation_id, None)

    @classmethod
    def get_timeout_status(cls, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get timeout status for an operation

        Args:
            operation_id: Operation identifier

        Returns:
            Timeout status dictionary or None if not found
        """
        with cls._lock:
            monitor = cls._active_timeouts.get(operation_id)
            if monitor:
                return {
                    'operation_id': monitor.operation_id,
                    'timeout_us': monitor.timeout_us,
                    'elapsed_us': monitor.get_remaining_us(),
                    'remaining_us': monitor.get_remaining_us(),
                    'is_expired': monitor.is_expired()
                }
        return None

    @classmethod
    def _start_timeout_monitoring(cls) -> None:
        """Start background timeout monitoring thread"""
        if cls._timeout_running:
            return

        cls._timeout_running = True
        cls._timeout_thread = threading.Thread(target=cls._timeout_monitor_loop, daemon=True)
        cls._timeout_thread.start()

    @classmethod
    def _stop_timeout_monitoring(cls) -> None:
        """Stop timeout monitoring thread"""
        cls._timeout_running = False
        if cls._timeout_thread and cls._timeout_thread.is_alive():
            cls._timeout_thread.join(timeout=1.0)

    @classmethod
    def _timeout_monitor_loop(cls) -> None:
        """Background thread for timeout monitoring"""
        logger.info("Timeout monitoring thread started")

        while cls._timeout_running:
            try:
                current_time = time.time()

                # Check for expired timeouts
                expired_timeouts = []
                with cls._lock:
                    for operation_id, monitor in cls._active_timeouts.items():
                        if monitor.is_expired():
                            expired_timeouts.append(operation_id)

                # Process expired timeouts
                for operation_id in expired_timeouts:
                    with cls._lock:
                        monitor = cls._active_timeouts.pop(operation_id, None)

                    if monitor:
                        logger.warning(f"Timeout expired for operation: {operation_id}")
                        monitor.trigger_callback()

                # Sleep for short interval
                time.sleep(0.001)  # 1ms resolution

            except Exception as e:
                logger.error(f"Error in timeout monitoring: {e}")
                time.sleep(0.01)  # Longer sleep on error

        logger.info("Timeout monitoring thread stopped")

    @classmethod
    def wait_us(cls, microseconds: int, timer_type: TimerType = TimerType.SAFETY_CRITICAL) -> None:
        """
        Busy-wait for specified microseconds (for precise timing)

        Args:
            microseconds: Time to wait in microseconds
            timer_type: Timer type to use for precision
        """
        start_time = cls.get_current_time_us(timer_type)
        end_time = start_time + microseconds

        while cls.get_current_time_us(timer_type) < end_time:
            pass  # Busy wait

    @classmethod
    def get_timing_capabilities(cls) -> Dict[str, Any]:
        """Get timing system capabilities"""
        return {
            'initialized': cls._initialized,
            'tick_interval_us': cls._tick_interval_us,
            'current_tick': cls._tick_counter,
            'hw_timer_available': cls._hw_timer_available,
            'hw_timer_frequency': cls._hw_timer_frequency,
            'platform': platform.system(),
            'active_timeouts': len(cls._active_timeouts)
        }

    @classmethod
    def benchmark_timing_precision(cls, samples: int = 100) -> Dict[str, Any]:
        """
        Benchmark timing precision

        Args:
            samples: Number of samples to collect

        Returns:
            Benchmark results
        """
        results = {
            'samples': samples,
            'timer_types': {},
            'platform_info': cls.get_timing_capabilities()
        }

        for timer_type in TimerType:
            measurements = []

            for _ in range(samples):
                start = cls.get_current_time_us(timer_type)
                # Small operation
                end = cls.get_current_time_us(timer_type)
                measurements.append(end - start)

            measurements.sort()
            results['timer_types'][timer_type.value] = {
                'min_us': measurements[0],
                'max_us': measurements[-1],
                'median_us': measurements[samples // 2],
                'avg_us': sum(measurements) / len(measurements)
            }

        return results


# AUTOSAR OS Interface Functions (for compatibility)
def Os_GetElapsedTime(start_time_us: int, timer_type: TimerType = TimerType.MONOTONIC) -> int:
    """
    AUTOSAR OS GetElapsedTime equivalent

    Args:
        start_time_us: Start time in microseconds
        timer_type: Timer type to use

    Returns:
        Elapsed time in microseconds
    """
    return AutomotiveTiming.get_elapsed_time_us(start_time_us, timer_type)


def Os_GetCurrentTime(timer_type: TimerType = TimerType.MONOTONIC) -> int:
    """
    AUTOSAR OS GetCurrentTime equivalent

    Args:
        timer_type: Timer type to use

    Returns:
        Current time in microseconds
    """
    return AutomotiveTiming.get_current_time_us(timer_type)


def Os_SetTimeout(operation_id: str, timeout_us: int,
                 timer_type: TimerType = TimerType.SAFETY_CRITICAL,
                 callback: Optional[Callable[[str], None]] = None) -> None:
    """
    AUTOSAR OS SetTimeout equivalent

    Args:
        operation_id: Operation identifier
        timeout_us: Timeout in microseconds
        timer_type: Timer type to use
        callback: Timeout callback function
    """
    AutomotiveTiming.set_timeout(operation_id, timeout_us, timer_type, callback)


def Os_CancelTimeout(operation_id: str) -> None:
    """
    AUTOSAR OS CancelTimeout equivalent

    Args:
        operation_id: Operation identifier
    """
    AutomotiveTiming.cancel_timeout(operation_id)


# Convenience functions for common automotive timing patterns
def can_timing_wait(bit_time_us: int = 4) -> None:
    """
    Wait for CAN bit timing (default 250kbps = 4us per bit)

    Args:
        bit_time_us: Bit time in microseconds
    """
    AutomotiveTiming.wait_us(bit_time_us)


def diagnostic_timeout_ms(operation_id: str, timeout_ms: int,
                         callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Set diagnostic timeout in milliseconds

    Args:
        operation_id: Operation identifier
        timeout_ms: Timeout in milliseconds
        callback: Timeout callback function
    """
    AutomotiveTiming.set_timeout(operation_id, timeout_ms * 1000,
                                TimerType.DIAGNOSTIC, callback)


def safety_critical_delay_us(microseconds: int) -> None:
    """
    Safety-critical delay with high precision

    Args:
        microseconds: Delay in microseconds
    """
    AutomotiveTiming.wait_us(microseconds)


# Initialize timing system on module import
AutomotiveTiming.initialize()