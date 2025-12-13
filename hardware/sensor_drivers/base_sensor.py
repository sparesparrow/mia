"""
Base Sensor Interface

This module defines the base classes and interfaces for all MIA sensor drivers.
It provides common functionality for sensor management, data handling, and calibration.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SensorType(Enum):
    """Sensor types supported by MIA"""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    DISTANCE = "distance"
    PRESSURE = "pressure"
    LIGHT = "light"
    MOTION = "motion"
    VOLTAGE = "voltage"
    CURRENT = "current"
    ACCELERATION = "acceleration"
    GYROSCOPE = "gyroscope"
    MAGNETOMETER = "magnetometer"
    GPS = "gps"
    CUSTOM = "custom"

@dataclass
class SensorData:
    """Container for sensor measurement data"""
    sensor_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: float
    metadata: Dict[str, Any] = None
    quality: float = 1.0  # 0.0 to 1.0, where 1.0 is best quality

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
            "quality": self.quality
        }

class SensorError(Exception):
    """Base exception for sensor errors"""
    pass

class SensorTimeoutError(SensorError):
    """Raised when sensor operation times out"""
    pass

class SensorReadError(SensorError):
    """Raised when sensor read fails"""
    pass

class SensorConfigError(SensorError):
    """Raised when sensor configuration is invalid"""
    pass

class BaseSensor:
    """
    Base class for all MIA sensor drivers

    Provides common functionality for:
    - Sensor initialization and configuration
    - Data reading and validation
    - Calibration and scaling
    - Error handling and recovery
    - Background sampling
    """

    def __init__(self, sensor_id: str, sensor_type: SensorType,
                 unit: str, config: Dict[str, Any] = None):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.unit = unit
        self.config = config or {}

        # Sensor state
        self.initialized = False
        self.last_reading: Optional[SensorData] = None
        self.last_error: Optional[Exception] = None

        # Calibration
        self.calibration_offset = self.config.get('calibration_offset', 0.0)
        self.calibration_scale = self.config.get('calibration_scale', 1.0)

        # Sampling configuration
        self.sample_interval = self.config.get('sample_interval', 1.0)  # seconds
        self.max_age = self.config.get('max_age', 30.0)  # seconds

        # Background sampling
        self._sampling_thread: Optional[threading.Thread] = None
        self._sampling_active = False
        self._sample_lock = threading.Lock()

        # Callbacks
        self.data_callbacks: List[Callable[[SensorData], None]] = []
        self.error_callbacks: List[Callable[[Exception], None]] = []

    def initialize(self) -> bool:
        """
        Initialize the sensor

        This method should be overridden by subclasses to perform
        sensor-specific initialization (e.g., I2C setup, pin configuration).

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._initialize_hardware()
            self.initialized = True
            logger.info(f"Sensor {self.sensor_id} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize sensor {self.sensor_id}: {e}")
            self.last_error = e
            self._call_error_callbacks(e)
            return False

    def _initialize_hardware(self):
        """Hardware-specific initialization - override in subclasses"""
        raise NotImplementedError("Subclasses must implement _initialize_hardware")

    def read_data(self) -> Optional[SensorData]:
        """
        Read data from the sensor

        Returns:
            SensorData object if successful, None if failed
        """
        if not self.initialized:
            logger.warning(f"Sensor {self.sensor_id} not initialized")
            return None

        try:
            with self._sample_lock:
                raw_value = self._read_raw_value()

                if raw_value is not None:
                    # Apply calibration
                    calibrated_value = (raw_value * self.calibration_scale) + self.calibration_offset

                    # Validate reading
                    if self._validate_reading(calibrated_value):
                        data = SensorData(
                            sensor_id=self.sensor_id,
                            sensor_type=self.sensor_type,
                            value=round(calibrated_value, 3),
                            unit=self.unit,
                            timestamp=time.time(),
                            metadata=self._get_metadata(),
                            quality=self._calculate_quality(calibrated_value)
                        )

                        self.last_reading = data
                        self.last_error = None

                        # Call data callbacks
                        self._call_data_callbacks(data)

                        return data
                    else:
                        raise SensorReadError(f"Invalid reading: {calibrated_value}")
                else:
                    raise SensorReadError("Failed to read raw value")

        except Exception as e:
            logger.error(f"Error reading sensor {self.sensor_id}: {e}")
            self.last_error = e
            self._call_error_callbacks(e)
            return None

    def _read_raw_value(self) -> Optional[float]:
        """Read raw value from sensor - override in subclasses"""
        raise NotImplementedError("Subclasses must implement _read_raw_value")

    def _validate_reading(self, value: float) -> bool:
        """Validate sensor reading - can be overridden"""
        # Basic validation - check for NaN/inf
        return not (value != value or abs(value) == float('inf'))

    def _get_metadata(self) -> Dict[str, Any]:
        """Get sensor-specific metadata - can be overridden"""
        return {
            "calibration_offset": self.calibration_offset,
            "calibration_scale": self.calibration_scale,
            "sample_interval": self.sample_interval
        }

    def _calculate_quality(self, value: float) -> float:
        """Calculate data quality (0.0-1.0) - can be overridden"""
        # Basic quality calculation based on recency and validity
        if self.last_reading:
            age = time.time() - self.last_reading.timestamp
            age_quality = max(0.0, 1.0 - (age / self.max_age))
            return age_quality
        return 1.0

    def start_sampling(self):
        """Start background sampling thread"""
        if self._sampling_active:
            return

        self._sampling_active = True
        self._sampling_thread = threading.Thread(target=self._sampling_loop, daemon=True)
        self._sampling_thread.start()
        logger.info(f"Started background sampling for sensor {self.sensor_id}")

    def stop_sampling(self):
        """Stop background sampling thread"""
        self._sampling_active = False
        if self._sampling_thread and self._sampling_thread.is_alive():
            self._sampling_thread.join(timeout=2.0)
        logger.info(f"Stopped background sampling for sensor {self.sensor_id}")

    def _sampling_loop(self):
        """Background sampling loop"""
        while self._sampling_active:
            self.read_data()
            time.sleep(self.sample_interval)

    def calibrate(self, reference_value: float, measured_value: float):
        """Calibrate sensor using reference measurement"""
        # Simple linear calibration
        if measured_value != 0:
            self.calibration_scale = reference_value / measured_value
            self.calibration_offset = 0.0
            logger.info(f"Calibrated sensor {self.sensor_id}: scale={self.calibration_scale}")

    def get_last_reading(self) -> Optional[SensorData]:
        """Get the last successful reading"""
        return self.last_reading

    def is_data_fresh(self, max_age: float = None) -> bool:
        """Check if we have fresh data"""
        if not self.last_reading:
            return False

        max_age = max_age or self.max_age
        return (time.time() - self.last_reading.timestamp) < max_age

    def add_data_callback(self, callback: Callable[[SensorData], None]):
        """Add callback for new data readings"""
        self.data_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[Exception], None]):
        """Add callback for errors"""
        self.error_callbacks.append(callback)

    def _call_data_callbacks(self, data: SensorData):
        """Call all data callbacks"""
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in data callback: {e}")

    def _call_error_callbacks(self, error: Exception):
        """Call all error callbacks"""
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")

    def cleanup(self):
        """Cleanup sensor resources"""
        self.stop_sampling()
        self._cleanup_hardware()
        logger.info(f"Cleaned up sensor {self.sensor_id}")

    def _cleanup_hardware(self):
        """Hardware-specific cleanup - override in subclasses"""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.sensor_id}, type={self.sensor_type.value}, unit={self.unit})"