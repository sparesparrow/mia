"""
Sensor Manager

Manages multiple sensors with configurable polling, priority scheduling,
and background sampling threads.
"""

import time
import threading
import heapq
from typing import Dict, List, Optional, Callable, Any
import logging

from .base_sensor import BaseSensor, SensorData, SensorType

logger = logging.getLogger(__name__)

class SensorTask:
    """Represents a sensor sampling task with priority"""

    def __init__(self, sensor: BaseSensor, priority: int = 1):
        self.sensor = sensor
        self.priority = priority  # Lower number = higher priority
        self.next_run_time = time.time()
        self.task_id = id(sensor)

    def __lt__(self, other):
        # Priority queue comparison: higher priority (lower number) first
        if self.priority != other.priority:
            return self.priority < other.priority
        # If same priority, earlier next_run_time first
        return self.next_run_time < other.next_run_time

    def update_next_run_time(self):
        """Update when this task should run next"""
        self.next_run_time = time.time() + self.sensor.sample_interval

    def is_due(self) -> bool:
        """Check if this task is due to run"""
        return time.time() >= self.next_run_time

class SensorManager:
    """
    Manages multiple sensors with advanced features:

    - Configurable polling intervals per sensor
    - Priority-based scheduling
    - Background sampling threads
    - Sensor health monitoring
    - Data aggregation and filtering
    - Automatic error recovery
    """

    def __init__(self, max_threads: int = 4, config: Dict[str, Any] = None):
        self.config = config or {}

        # Sensor management
        self.sensors: Dict[str, BaseSensor] = {}
        self.sensor_tasks: List[SensorTask] = []
        self.task_lock = threading.Lock()

        # Threading
        self.max_threads = max_threads
        self.active_threads = 0
        self.thread_pool: List[threading.Thread] = []
        self.running = False

        # Data management
        self.data_buffer_size = self.config.get('data_buffer_size', 1000)
        self.data_buffers: Dict[str, List[SensorData]] = {}

        # Callbacks
        self.data_callbacks: List[Callable[[str, SensorData], None]] = []
        self.error_callbacks: List[Callable[[str, Exception], None]] = []

        # Monitoring
        self.stats = {
            'total_readings': 0,
            'errors': 0,
            'last_activity': time.time()
        }

    def add_sensor(self, sensor: BaseSensor, priority: int = 1, start_sampling: bool = True):
        """
        Add a sensor to the manager

        Args:
            sensor: Sensor instance to add
            priority: Sampling priority (lower = higher priority)
            start_sampling: Whether to start background sampling
        """
        if sensor.sensor_id in self.sensors:
            logger.warning(f"Sensor {sensor.sensor_id} already exists, replacing")

        self.sensors[sensor.sensor_id] = sensor
        self.data_buffers[sensor.sensor_id] = []

        # Create sampling task
        task = SensorTask(sensor, priority)
        with self.task_lock:
            heapq.heappush(self.sensor_tasks, task)

        # Add callbacks
        sensor.add_data_callback(self._on_sensor_data)
        sensor.add_error_callback(self._on_sensor_error)

        # Initialize sensor
        if not sensor.initialize():
            logger.error(f"Failed to initialize sensor {sensor.sensor_id}")
            return False

        # Start background sampling if requested
        if start_sampling:
            sensor.start_sampling()

        logger.info(f"Added sensor {sensor.sensor_id} with priority {priority}")
        return True

    def remove_sensor(self, sensor_id: str):
        """Remove a sensor from the manager"""
        if sensor_id not in self.sensors:
            return False

        sensor = self.sensors[sensor_id]

        # Stop sampling
        sensor.stop_sampling()

        # Remove from task queue
        with self.task_lock:
            self.sensor_tasks = [task for task in self.sensor_tasks
                               if task.sensor.sensor_id != sensor_id]

        # Cleanup
        sensor.cleanup()
        del self.sensors[sensor_id]
        del self.data_buffers[sensor_id]

        logger.info(f"Removed sensor {sensor_id}")
        return True

    def get_sensor(self, sensor_id: str) -> Optional[BaseSensor]:
        """Get sensor by ID"""
        return self.sensors.get(sensor_id)

    def list_sensors(self) -> List[str]:
        """List all sensor IDs"""
        return list(self.sensors.keys())

    def read_sensor(self, sensor_id: str) -> Optional[SensorData]:
        """Manually read a sensor"""
        sensor = self.get_sensor(sensor_id)
        if sensor:
            return sensor.read_data()
        return None

    def read_all_sensors(self) -> Dict[str, Optional[SensorData]]:
        """Read all sensors once"""
        results = {}
        for sensor_id, sensor in self.sensors.items():
            results[sensor_id] = sensor.read_data()
        return results

    def start_priority_scheduler(self):
        """Start the priority-based sampling scheduler"""
        if self.running:
            return

        self.running = True
        scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        scheduler_thread.start()
        logger.info("Started priority scheduler")

    def stop_priority_scheduler(self):
        """Stop the priority-based sampling scheduler"""
        self.running = False
        logger.info("Stopped priority scheduler")

    def _scheduler_loop(self):
        """Priority-based scheduler loop"""
        while self.running:
            try:
                current_time = time.time()

                with self.task_lock:
                    # Find due tasks
                    due_tasks = []
                    remaining_tasks = []

                    for task in self.sensor_tasks:
                        if task.is_due():
                            due_tasks.append(task)
                        else:
                            remaining_tasks.append(task)

                    self.sensor_tasks = remaining_tasks

                # Process due tasks by priority
                if due_tasks:
                    # Sort by priority (already handled by heap, but ensure)
                    due_tasks.sort()

                    for task in due_tasks:
                        # Check if we can start a new thread
                        if self.active_threads < self.max_threads:
                            self._start_sampling_task(task)
                        else:
                            # Re-queue high priority tasks
                            if task.priority <= 2:
                                with self.task_lock:
                                    heapq.heappush(self.sensor_tasks, task)
                            # Lower priority tasks get delayed

                # Sleep briefly to prevent busy waiting
                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(0.1)

    def _start_sampling_task(self, task: SensorTask):
        """Start a sampling task in a thread"""
        def sampling_worker():
            try:
                self.active_threads += 1

                # Perform sampling
                data = task.sensor.read_data()

                # Update task timing
                task.update_next_run_time()

                # Re-queue the task
                with self.task_lock:
                    heapq.heappush(self.sensor_tasks, task)

            except Exception as e:
                logger.error(f"Sampling task error for {task.sensor.sensor_id}: {e}")
            finally:
                self.active_threads -= 1

        thread = threading.Thread(target=sampling_worker, daemon=True)
        thread.start()

    def get_recent_data(self, sensor_id: str, count: int = 1) -> List[SensorData]:
        """Get recent data readings for a sensor"""
        buffer = self.data_buffers.get(sensor_id, [])
        return buffer[-count:] if buffer else []

    def get_sensor_stats(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a sensor"""
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            return None

        buffer = self.data_buffers.get(sensor_id, [])

        if not buffer:
            return {
                'sensor_id': sensor_id,
                'readings': 0,
                'last_reading': None,
                'fresh': False
            }

        last_reading = buffer[-1]
        age = time.time() - last_reading.timestamp

        return {
            'sensor_id': sensor_id,
            'readings': len(buffer),
            'last_reading': last_reading,
            'age_seconds': age,
            'fresh': age < sensor.max_age
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all sensors"""
        stats = {}
        for sensor_id in self.sensors.keys():
            sensor_stats = self.get_sensor_stats(sensor_id)
            if sensor_stats:
                stats[sensor_id] = sensor_stats
        return stats

    def clear_data_buffers(self):
        """Clear all data buffers"""
        for buffer in self.data_buffers.values():
            buffer.clear()

    def add_data_callback(self, callback: Callable[[str, SensorData], None]):
        """Add global data callback"""
        self.data_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[str, Exception], None]):
        """Add global error callback"""
        self.error_callbacks.append(callback)

    def _on_sensor_data(self, data: SensorData):
        """Handle sensor data reception"""
        sensor_id = data.sensor_id

        # Add to buffer
        buffer = self.data_buffers.get(sensor_id, [])
        buffer.append(data)

        # Maintain buffer size
        if len(buffer) > self.data_buffer_size:
            buffer.pop(0)

        # Update stats
        self.stats['total_readings'] += 1
        self.stats['last_activity'] = time.time()

        # Call global callbacks
        for callback in self.data_callbacks:
            try:
                callback(sensor_id, data)
            except Exception as e:
                logger.error(f"Data callback error: {e}")

    def _on_sensor_error(self, error: Exception):
        """Handle sensor errors"""
        # Update stats
        self.stats['errors'] += 1

        # Call global error callbacks
        for callback in self.error_callbacks:
            try:
                callback("unknown", error)  # We don't know which sensor
            except Exception as e:
                logger.error(f"Error callback error: {e}")

    def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        return {
            'total_sensors': len(self.sensors),
            'active_threads': self.active_threads,
            'total_readings': self.stats['total_readings'],
            'total_errors': self.stats['errors'],
            'uptime': time.time() - self.stats.get('start_time', time.time()),
            'scheduler_running': self.running
        }

    def __enter__(self):
        """Context manager entry"""
        self.stats['start_time'] = time.time()
        self.start_priority_scheduler()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_priority_scheduler()

        # Cleanup all sensors
        for sensor in list(self.sensors.values()):
            sensor.cleanup()

        self.sensors.clear()
        self.data_buffers.clear()