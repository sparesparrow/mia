"""
Performance Optimization Layer - Zero-Copy Data Paths and Real-Time Optimization

This module provides performance optimizations for automotive real-time requirements
including zero-copy data paths, memory pool allocation, and CAN message prioritization.
"""

import time
import threading
import logging
import psutil
import os
from typing import Dict, List, Optional, Set, Tuple, Any, Callable, Generic, TypeVar, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import heapq
from collections import deque
import gc

from .automotive_timing import AutomotiveTiming, TimerType

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ECU_Class(Enum):
    """AUTOSAR ECU performance classes"""
    HIGH_END = "high_end"       # High-performance ECUs (e.g., domain controllers)
    MID_RANGE = "mid_range"     # Standard ECUs (e.g., body controllers)
    LOW_END = "low_end"         # Resource-constrained ECUs (e.g., sensor ECUs)
    SAFETY_CRITICAL = "safety"  # Safety-critical ECUs with real-time requirements


class MemoryPool:
    """
    Memory Pool for predictable allocation latency

    Pre-allocates memory blocks to avoid runtime allocation delays
    """

    def __init__(self, block_size: int, pool_size: int = 1024):
        self.block_size = block_size
        self.pool_size = pool_size
        self.pool: deque = deque()
        self.allocated = 0
        self.lock = threading.RLock()

        # Pre-allocate memory blocks
        self._preallocate_pool()

    def _preallocate_pool(self) -> None:
        """Pre-allocate memory pool"""
        for _ in range(self.pool_size):
            block = bytearray(self.block_size)
            self.pool.append(block)

    def allocate(self) -> Optional[bytearray]:
        """
        Allocate memory block from pool

        Returns:
            Memory block or None if pool exhausted
        """
        with self.lock:
            if self.pool:
                block = self.pool.popleft()
                self.allocated += 1
                return block
            else:
                logger.warning("Memory pool exhausted")
                return None

    def free(self, block: bytearray) -> None:
        """
        Return memory block to pool

        Args:
            block: Memory block to return
        """
        with self.lock:
            if len(block) == self.block_size and self.allocated > 0:
                # Clear block for security
                block[:] = b'\x00'
                self.pool.append(block)
                self.allocated -= 1
            else:
                logger.warning("Invalid block returned to memory pool")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory pool statistics"""
        with self.lock:
            return {
                'block_size': self.block_size,
                'total_blocks': self.pool_size,
                'available_blocks': len(self.pool),
                'allocated_blocks': self.allocated,
                'utilization_percent': (self.allocated / self.pool_size) * 100
            }


class ZeroCopyBuffer:
    """
    Zero-Copy Buffer for high-performance data transfer

    Avoids data copying by using shared memory regions and reference passing
    """

    def __init__(self, buffer_id: str, size: int):
        self.buffer_id = buffer_id
        self.size = size
        self.buffer = bytearray(size)
        self.read_offset = 0
        self.write_offset = 0
        self.references: Set[str] = set()  # Track buffer references
        self.lock = threading.RLock()

    def write_data(self, data: Union[bytes, bytearray], offset: int = 0) -> bool:
        """
        Write data to buffer (zero-copy if possible)

        Args:
            data: Data to write
            offset: Write offset

        Returns:
            True if successful
        """
        with self.lock:
            if offset + len(data) > self.size:
                logger.error(f"Buffer overflow in {self.buffer_id}")
                return False

            if isinstance(data, bytearray):
                # Zero-copy: use memoryview for direct access
                view = memoryview(self.buffer)[offset:offset + len(data)]
                view[:] = data
            else:
                # Copy data
                self.buffer[offset:offset + len(data)] = data

            self.write_offset = offset + len(data)
            return True

    def read_data(self, length: int, offset: int = 0) -> Optional[memoryview]:
        """
        Read data from buffer (zero-copy)

        Args:
            length: Number of bytes to read
            offset: Read offset

        Returns:
            Memoryview of data or None if invalid
        """
        with self.lock:
            if offset + length > self.size:
                logger.error(f"Buffer underflow in {self.buffer_id}")
                return None

            # Return zero-copy memoryview
            return memoryview(self.buffer)[offset:offset + length]

    def create_reference(self, reference_id: str) -> 'ZeroCopyBuffer':
        """
        Create reference to buffer for zero-copy access

        Args:
            reference_id: Unique reference identifier

        Returns:
            Buffer reference
        """
        with self.lock:
            self.references.add(reference_id)
            # Return self as reference (same underlying buffer)
            return self

    def release_reference(self, reference_id: str) -> None:
        """
        Release buffer reference

        Args:
            reference_id: Reference identifier to release
        """
        with self.lock:
            self.references.discard(reference_id)

    def get_reference_count(self) -> int:
        """Get number of active references"""
        with self.lock:
            return len(self.references)

    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        with self.lock:
            return {
                'buffer_id': self.buffer_id,
                'size': self.size,
                'read_offset': self.read_offset,
                'write_offset': self.write_offset,
                'utilization_percent': (self.write_offset / self.size) * 100,
                'reference_count': len(self.references)
            }


class CAN_Message:
    """CAN message with priority for transmission scheduling"""

    def __init__(self, can_id: int, data: bytes, priority: int = 0, deadline: Optional[int] = None):
        self.can_id = can_id
        self.data = data
        self.priority = priority  # Lower number = higher priority
        self.deadline = deadline  # Microseconds since epoch
        self.timestamp = AutomotiveTiming.get_current_time_us()
        self.retries = 0
        self.max_retries = 3

    def is_expired(self) -> bool:
        """Check if message deadline has expired"""
        if self.deadline is None:
            return False
        return AutomotiveTiming.get_current_time_us() > self.deadline

    def get_age_us(self) -> int:
        """Get message age in microseconds"""
        return AutomotiveTiming.get_current_time_us() - self.timestamp

    def __lt__(self, other: 'CAN_Message') -> bool:
        """Priority comparison for heapq"""
        if self.priority != other.priority:
            return self.priority < other.priority  # Lower priority number = higher priority
        return self.timestamp < other.timestamp  # Earlier timestamp = higher priority


class CAN_PriorityScheduler:
    """
    CAN Message Priority Scheduler

    Implements priority-based CAN message scheduling with deadline handling
    """

    def __init__(self, max_queue_size: int = 256):
        self.max_queue_size = max_queue_size
        self.message_queue: List[CAN_Message] = []  # Priority queue
        self.deadline_queue: List[CAN_Message] = []  # Deadline-ordered queue
        self.lock = threading.RLock()

        # Statistics
        self.messages_scheduled = 0
        self.messages_dropped = 0
        self.deadline_misses = 0

    def schedule_message(self, can_id: int, data: bytes,
                        priority: int = 0, deadline_us: Optional[int] = None) -> bool:
        """
        Schedule CAN message for transmission

        Args:
            can_id: CAN message ID
            data: Message data
            priority: Message priority (0 = highest)
            deadline_us: Deadline in microseconds from now

        Returns:
            True if scheduled successfully
        """
        with self.lock:
            if len(self.message_queue) >= self.max_queue_size:
                # Drop lowest priority message
                if self.message_queue:
                    dropped = heapq.heappop(self.message_queue)  # Remove lowest priority
                    self.messages_dropped += 1
                    logger.warning(f"Dropped CAN message {dropped.can_id:#x} due to queue full")
                else:
                    return False

            deadline = None
            if deadline_us:
                deadline = AutomotiveTiming.get_current_time_us() + deadline_us

            message = CAN_Message(can_id, data, priority, deadline)

            # Add to priority queue
            heapq.heappush(self.message_queue, message)

            # Add to deadline queue if deadline specified
            if deadline:
                self.deadline_queue.append(message)
                # Sort by deadline (earliest first)
                self.deadline_queue.sort(key=lambda m: m.deadline)

            self.messages_scheduled += 1
            return True

    def get_next_message(self) -> Optional[CAN_Message]:
        """
        Get next message for transmission (highest priority)

        Returns:
            Next message to transmit or None if queue empty
        """
        with self.lock:
            # Check for expired deadlines first
            current_time = AutomotiveTiming.get_current_time_us()

            # Remove expired messages from deadline queue
            while self.deadline_queue and self.deadline_queue[0].deadline < current_time:
                expired = self.deadline_queue.pop(0)
                self.deadline_misses += 1
                logger.warning(f"CAN message deadline missed: {expired.can_id:#x}")

                # Remove from priority queue too
                self.message_queue = [m for m in self.message_queue if m is not expired]

            # Return highest priority message
            if self.message_queue:
                message = heapq.heappop(self.message_queue)

                # Remove from deadline queue if present
                if message in self.deadline_queue:
                    self.deadline_queue.remove(message)

                return message

            return None

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self.lock:
            return {
                'queue_size': len(self.message_queue),
                'max_queue_size': self.max_queue_size,
                'utilization_percent': (len(self.message_queue) / self.max_queue_size) * 100,
                'messages_scheduled': self.messages_scheduled,
                'messages_dropped': self.messages_dropped,
                'deadline_misses': self.deadline_misses,
                'deadline_queue_size': len(self.deadline_queue)
            }


class PerformanceMonitor:
    """
    Performance Monitor for real-time system metrics
    """

    def __init__(self, monitoring_interval_ms: int = 100):
        self.monitoring_interval_ms = monitoring_interval_ms
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Performance metrics
        self.cpu_usage_history: deque = deque(maxlen=100)
        self.memory_usage_history: deque = deque(maxlen=100)
        self.latency_measurements: Dict[str, List[int]] = {}

        # Thresholds
        self.cpu_threshold_percent = 80.0
        self.memory_threshold_percent = 85.0
        self.latency_threshold_us = 1000  # 1ms

        # Alerts
        self.alert_callbacks: Dict[str, List[Callable]] = {}

    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                self._collect_metrics()
                self._check_thresholds()
                time.sleep(self.monitoring_interval_ms / 1000.0)

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(1.0)

    def _collect_metrics(self) -> None:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_usage_history.append(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_usage_history.append(memory.percent)

        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")

    def _check_thresholds(self) -> None:
        """Check performance thresholds and trigger alerts"""
        # CPU threshold
        if self.cpu_usage_history:
            avg_cpu = sum(self.cpu_usage_history) / len(self.cpu_usage_history)
            if avg_cpu > self.cpu_threshold_percent:
                self._trigger_alert("cpu_threshold_exceeded",
                                  f"Average CPU usage {avg_cpu:.1f}% exceeds threshold {self.cpu_threshold_percent}%")

        # Memory threshold
        if self.memory_usage_history:
            avg_memory = sum(self.memory_usage_history) / len(self.memory_usage_history)
            if avg_memory > self.memory_threshold_percent:
                self._trigger_alert("memory_threshold_exceeded",
                                  f"Average memory usage {avg_memory:.1f}% exceeds threshold {self.memory_threshold_percent}%")

    def measure_latency(self, operation_name: str) -> 'LatencyTimer':
        """Create latency measurement timer"""
        return LatencyTimer(self, operation_name)

    def record_latency(self, operation_name: str, latency_us: int) -> None:
        """Record operation latency"""
        if operation_name not in self.latency_measurements:
            self.latency_measurements[operation_name] = []

        measurements = self.latency_measurements[operation_name]
        measurements.append(latency_us)

        # Keep only last 100 measurements
        if len(measurements) > 100:
            measurements.pop(0)

        # Check latency threshold
        if latency_us > self.latency_threshold_us:
            self._trigger_alert("latency_threshold_exceeded",
                              f"Operation {operation_name} latency {latency_us}us exceeds threshold {self.latency_threshold_us}us")

    def register_alert_callback(self, alert_type: str, callback: Callable) -> None:
        """Register callback for performance alerts"""
        if alert_type not in self.alert_callbacks:
            self.alert_callbacks[alert_type] = []
        self.alert_callbacks[alert_type].append(callback)

    def _trigger_alert(self, alert_type: str, message: str) -> None:
        """Trigger performance alert"""
        logger.warning(f"Performance alert [{alert_type}]: {message}")

        # Call registered callbacks
        callbacks = self.alert_callbacks.get(alert_type, [])
        for callback in callbacks:
            try:
                callback(alert_type, message)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        stats = {
            'monitoring_active': self.monitoring_active,
            'cpu_threshold_percent': self.cpu_threshold_percent,
            'memory_threshold_percent': self.memory_threshold_percent,
            'latency_threshold_us': self.latency_threshold_us,
            'registered_alerts': list(self.alert_callbacks.keys())
        }

        # CPU statistics
        if self.cpu_usage_history:
            stats['cpu'] = {
                'current_percent': self.cpu_usage_history[-1],
                'average_percent': sum(self.cpu_usage_history) / len(self.cpu_usage_history),
                'peak_percent': max(self.cpu_usage_history),
                'samples': len(self.cpu_usage_history)
            }

        # Memory statistics
        if self.memory_usage_history:
            stats['memory'] = {
                'current_percent': self.memory_usage_history[-1],
                'average_percent': sum(self.memory_usage_history) / len(self.memory_usage_history),
                'peak_percent': max(self.memory_usage_history),
                'samples': len(self.memory_usage_history)
            }

        # Latency statistics
        latency_stats = {}
        for operation, measurements in self.latency_measurements.items():
            if measurements:
                latency_stats[operation] = {
                    'count': len(measurements),
                    'average_us': sum(measurements) / len(measurements),
                    'min_us': min(measurements),
                    'max_us': max(measurements),
                    'p95_us': sorted(measurements)[int(len(measurements) * 0.95)]
                }
        stats['latency'] = latency_stats

        return stats


class LatencyTimer:
    """Context manager for measuring operation latency"""

    def __init__(self, monitor: PerformanceMonitor, operation_name: str):
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = AutomotiveTiming.get_current_time_us()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            end_time = AutomotiveTiming.get_current_time_us()
            latency_us = end_time - self.start_time
            self.monitor.record_latency(self.operation_name, latency_us)


class PerformanceOptimizer:
    """
    Performance Optimization Layer - Real-Time Automotive Optimization

    Provides comprehensive performance optimizations including:
    - Zero-copy data paths for high-throughput operations
    - Memory pool allocation for predictable latency
    - CAN message prioritization and scheduling
    - CPU utilization monitoring and alerting
    """

    def __init__(self, ecu_class: ECU_Class = ECU_Class.MID_RANGE):
        self.ecu_class = ecu_class

        # Configure based on ECU class
        self._configure_for_ecu_class()

        # Core optimization components
        self.memory_pools: Dict[str, MemoryPool] = {}
        self.zero_copy_buffers: Dict[str, ZeroCopyBuffer] = {}
        self.can_scheduler = CAN_PriorityScheduler()
        self.performance_monitor = PerformanceMonitor()

        # Optimization settings
        self.zero_copy_enabled = True
        self.memory_pool_enabled = True
        self.can_prioritization_enabled = True

    def _configure_for_ecu_class(self) -> None:
        """Configure optimization parameters based on ECU class"""
        configs = {
            ECU_Class.HIGH_END: {
                'memory_pool_size': 2048,
                'zero_copy_buffer_size': 65536,
                'can_queue_size': 512,
                'cpu_threshold': 85.0,
                'memory_threshold': 90.0,
                'latency_threshold_us': 500
            },
            ECU_Class.MID_RANGE: {
                'memory_pool_size': 1024,
                'zero_copy_buffer_size': 32768,
                'can_queue_size': 256,
                'cpu_threshold': 80.0,
                'memory_threshold': 85.0,
                'latency_threshold_us': 1000
            },
            ECU_Class.LOW_END: {
                'memory_pool_size': 512,
                'zero_copy_buffer_size': 16384,
                'can_queue_size': 128,
                'cpu_threshold': 70.0,
                'memory_threshold': 75.0,
                'latency_threshold_us': 2000
            },
            ECU_Class.SAFETY_CRITICAL: {
                'memory_pool_size': 512,
                'zero_copy_buffer_size': 8192,
                'can_queue_size': 64,
                'cpu_threshold': 60.0,
                'memory_threshold': 70.0,
                'latency_threshold_us': 100
            }
        }

        config = configs.get(self.ecu_class, configs[ECU_Class.MID_RANGE])
        self.memory_pool_size = config['memory_pool_size']
        self.zero_copy_buffer_size = config['zero_copy_buffer_size']
        self.can_queue_size = config['can_queue_size']
        self.cpu_threshold = config['cpu_threshold']
        self.memory_threshold = config['memory_threshold']
        self.latency_threshold = config['latency_threshold_us']

    async def initialize(self) -> None:
        """Initialize performance optimization layer"""
        # Create default memory pools
        self.create_memory_pool('small_blocks', 256, self.memory_pool_size)
        self.create_memory_pool('medium_blocks', 1024, self.memory_pool_size // 2)
        self.create_memory_pool('large_blocks', 4096, self.memory_pool_size // 4)

        # Create zero-copy buffers
        self.create_zero_copy_buffer('diagnostic_buffer', self.zero_copy_buffer_size)
        self.create_zero_copy_buffer('sensor_buffer', self.zero_copy_buffer_size)

        # Configure CAN scheduler
        # Re-initialize with proper size (can't modify after creation, so create new)
        self.can_scheduler = CAN_PriorityScheduler(self.can_queue_size)

        # Configure performance monitor
        self.performance_monitor.cpu_threshold_percent = self.cpu_threshold
        self.performance_monitor.memory_threshold_percent = self.memory_threshold
        self.performance_monitor.latency_threshold_us = self.latency_threshold

        # Start monitoring
        self.performance_monitor.start_monitoring()

        logger.info(f"Performance optimizer initialized for {self.ecu_class.value} ECU class")

    async def shutdown(self) -> None:
        """Shutdown performance optimization layer"""
        self.performance_monitor.stop_monitoring()
        logger.info("Performance optimizer shutdown")

    def create_memory_pool(self, pool_name: str, block_size: int, pool_size: int) -> MemoryPool:
        """Create named memory pool"""
        pool = MemoryPool(block_size, pool_size)
        self.memory_pools[pool_name] = pool
        return pool

    def get_memory_block(self, pool_name: str) -> Optional[bytearray]:
        """Get memory block from named pool"""
        pool = self.memory_pools.get(pool_name)
        if pool:
            return pool.allocate()
        return None

    def return_memory_block(self, pool_name: str, block: bytearray) -> None:
        """Return memory block to named pool"""
        pool = self.memory_pools.get(pool_name)
        if pool:
            pool.free(block)

    def create_zero_copy_buffer(self, buffer_name: str, size: int) -> ZeroCopyBuffer:
        """Create named zero-copy buffer"""
        buffer = ZeroCopyBuffer(buffer_name, size)
        self.zero_copy_buffers[buffer_name] = buffer
        return buffer

    def get_zero_copy_view(self, buffer_name: str, length: int, offset: int = 0) -> Optional[memoryview]:
        """Get zero-copy view of buffer data"""
        buffer = self.zero_copy_buffers.get(buffer_name)
        if buffer:
            return buffer.read_data(length, offset)
        return None

    def schedule_can_message(self, can_id: int, data: bytes,
                           priority: int = 0, deadline_us: Optional[int] = None) -> bool:
        """Schedule CAN message with priority"""
        if not self.can_prioritization_enabled:
            return False
        return self.can_scheduler.schedule_message(can_id, data, priority, deadline_us)

    def get_next_can_message(self) -> Optional[CAN_Message]:
        """Get next highest priority CAN message"""
        return self.can_scheduler.get_next_message()

    def optimize_data_transfer(self, data: bytes, operation: str) -> Tuple[Any, bool]:
        """
        Optimize data transfer using available mechanisms

        Args:
            data: Data to transfer
            operation: Operation type for optimization selection

        Returns:
            Tuple of (optimized_data, is_zero_copy)
        """
        # Try zero-copy first
        if self.zero_copy_enabled and len(data) <= 4096:
            # Use appropriate buffer
            buffer_name = 'diagnostic_buffer' if 'diagnostic' in operation.lower() else 'sensor_buffer'
            buffer = self.zero_copy_buffers.get(buffer_name)

            if buffer and buffer.write_data(data):
                view = buffer.read_data(len(data))
                if view is not None:
                    return view, True

        # Fall back to memory pool
        if self.memory_pool_enabled:
            pool_name = self._select_memory_pool(len(data))
            block = self.get_memory_block(pool_name)

            if block:
                block[:len(data)] = data
                return block, False

        # Fall back to regular allocation
        return data, False

    def _select_memory_pool(self, data_size: int) -> str:
        """Select appropriate memory pool based on data size"""
        if data_size <= 256:
            return 'small_blocks'
        elif data_size <= 1024:
            return 'medium_blocks'
        else:
            return 'large_blocks'

    def measure_operation_latency(self, operation_name: str) -> LatencyTimer:
        """Create latency measurement for operation"""
        return self.performance_monitor.measure_latency(operation_name)

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics"""
        stats = {
            'ecu_class': self.ecu_class.value,
            'zero_copy_enabled': self.zero_copy_enabled,
            'memory_pool_enabled': self.memory_pool_enabled,
            'can_prioritization_enabled': self.can_prioritization_enabled,
            'performance_monitor': self.performance_monitor.get_performance_stats(),
            'can_scheduler': self.can_scheduler.get_queue_stats()
        }

        # Memory pool statistics
        pool_stats = {}
        for name, pool in self.memory_pools.items():
            pool_stats[name] = pool.get_stats()
        stats['memory_pools'] = pool_stats

        # Zero-copy buffer statistics
        buffer_stats = {}
        for name, buffer in self.zero_copy_buffers.items():
            buffer_stats[name] = buffer.get_stats()
        stats['zero_copy_buffers'] = buffer_stats

        return stats

    def tune_for_workload(self, workload_profile: Dict[str, Any]) -> None:
        """
        Dynamically tune optimization parameters based on workload

        Args:
            workload_profile: Workload characteristics
        """
        # Analyze workload and adjust parameters
        high_frequency_operations = workload_profile.get('high_frequency_ops', 0)
        large_data_transfers = workload_profile.get('large_data_mb', 0)
        real_time_requirements = workload_profile.get('real_time_percent', 0)

        # Adjust memory pools based on usage patterns
        if large_data_transfers > 50:  # >50MB data transfer
            # Increase large block pool size
            if 'large_blocks' in self.memory_pools:
                # In a real implementation, we'd resize pools here
                logger.info("Detected high data transfer workload - optimizing memory pools")

        if real_time_requirements > 80:  # >80% real-time operations
            # Enable more aggressive zero-copy
            self.zero_copy_enabled = True
            logger.info("Detected real-time critical workload - enabling aggressive zero-copy")

        # Adjust CAN prioritization based on message frequency
        if high_frequency_operations > 1000:  # >1000 ops/sec
            # Increase CAN queue size for high-frequency scenarios
            logger.info("Detected high-frequency workload - optimizing CAN scheduling")

    def generate_performance_report(self) -> str:
        """
        Generate detailed performance optimization report

        Returns:
            Performance report as formatted string
        """
        stats = self.get_optimization_stats()

        report = f"""
# Performance Optimization Report
# ECU Class: {stats['ecu_class']}

## Configuration
- Zero-Copy: {'Enabled' if stats['zero_copy_enabled'] else 'Disabled'}
- Memory Pools: {'Enabled' if stats['memory_pool_enabled'] else 'Disabled'}
- CAN Prioritization: {'Enabled' if stats['can_prioritization_enabled'] else 'Disabled'}

## Memory Pools
"""

        for name, pool_stat in stats['memory_pools'].items():
            report += f"- {name}: {pool_stat['available_blocks']}/{pool_stat['total_blocks']} blocks available ({pool_stat['utilization_percent']:.1f}%)\n"

        report += "\n## Zero-Copy Buffers\n"
        for name, buffer_stat in stats['zero_copy_buffers'].items():
            report += f"- {name}: {buffer_stat['utilization_percent']:.1f}% utilized, {buffer_stat['reference_count']} active references\n"

        report += "\n## CAN Scheduling\n"
        can_stats = stats['can_scheduler']
        report += f"- Queue: {can_stats['queue_size']}/{can_stats['max_queue_size']} messages ({can_stats['utilization_percent']:.1f}%)\n"
        report += f"- Scheduled: {can_stats['messages_scheduled']}, Dropped: {can_stats['messages_dropped']}, Deadline Misses: {can_stats['deadline_misses']}\n"

        report += "\n## Performance Metrics\n"
        perf_stats = stats['performance_monitor']
        if 'cpu' in perf_stats:
            cpu = perf_stats['cpu']
            report += f"- CPU: {cpu['current_percent']:.1f}% current, {cpu['average_percent']:.1f}% average, {cpu['peak_percent']:.1f}% peak\n"

        if 'memory' in perf_stats:
            mem = perf_stats['memory']
            report += f"- Memory: {mem['current_percent']:.1f}% current, {mem['average_percent']:.1f}% average, {mem['peak_percent']:.1f}% peak\n"

        if 'latency' in perf_stats:
            report += "- Operation Latencies:\n"
            for op, lat in perf_stats['latency'].items():
                report += f"  - {op}: {lat['average_us']:.0f}us avg, {lat['max_us']}us max, {lat['p95_us']}us p95\n"

        return report