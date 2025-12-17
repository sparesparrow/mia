"""
Sensor Manager
Implements sensor drivers for I2C/SPI sensors and analog inputs.

This module provides abstractions for common sensors like temperature,
humidity, distance, and other environmental sensors.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .gpio import GPIOController, GPIOMode

logger = logging.getLogger(__name__)


class SensorType(Enum):
    """Supported sensor types."""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    DISTANCE = "distance"
    LIGHT = "light"
    MOTION = "motion"
    GAS = "gas"


@dataclass
class SensorReading:
    """Represents a sensor reading with metadata."""
    sensor_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SensorDriver(ABC):
    """Abstract base class for sensor drivers."""

    def __init__(self, sensor_id: str, sensor_type: SensorType):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.last_reading: Optional[SensorReading] = None
        self.last_error: Optional[str] = None

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the sensor. Returns True if successful."""
        pass

    @abstractmethod
    async def read(self) -> Optional[SensorReading]:
        """Read data from the sensor. Returns None if failed."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the sensor."""
        pass

    def is_healthy(self) -> bool:
        """Check if sensor is healthy (no recent errors)."""
        return self.last_error is None

    def get_last_reading(self) -> Optional[SensorReading]:
        """Get the last successful reading."""
        return self.last_reading


class MockTemperatureSensor(SensorDriver):
    """Mock temperature sensor for testing."""

    def __init__(self, sensor_id: str = "mock_temp", initial_temp: float = 25.0):
        super().__init__(sensor_id, SensorType.TEMPERATURE)
        self.temperature = initial_temp

    async def initialize(self) -> bool:
        """Initialize the mock sensor."""
        await asyncio.sleep(0.1)  # Simulate initialization time
        logger.info(f"Mock temperature sensor {self.sensor_id} initialized")
        return True

    async def read(self) -> Optional[SensorReading]:
        """Read temperature data."""
        try:
            # Simulate temperature variation
            self.temperature += (asyncio.get_event_loop().time() % 10 - 5) * 0.1
            self.temperature = max(0, min(50, self.temperature))  # Clamp to reasonable range

            reading = SensorReading(
                sensor_id=self.sensor_id,
                sensor_type=self.sensor_type,
                value=round(self.temperature, 1),
                unit="°C",
                timestamp=time.time(),
                metadata={"quality": "simulated"}
            )

            self.last_reading = reading
            self.last_error = None
            return reading

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error reading mock temperature sensor: {e}")
            return None

    async def shutdown(self) -> None:
        """Shutdown the mock sensor."""
        logger.info(f"Mock temperature sensor {self.sensor_id} shutdown")


class MockHumiditySensor(SensorDriver):
    """Mock humidity sensor for testing."""

    def __init__(self, sensor_id: str = "mock_humidity", initial_humidity: float = 60.0):
        super().__init__(sensor_id, SensorType.HUMIDITY)
        self.humidity = initial_humidity

    async def initialize(self) -> bool:
        """Initialize the mock sensor."""
        await asyncio.sleep(0.1)
        logger.info(f"Mock humidity sensor {self.sensor_id} initialized")
        return True

    async def read(self) -> Optional[SensorReading]:
        """Read humidity data."""
        try:
            # Simulate humidity variation
            self.humidity += (asyncio.get_event_loop().time() % 20 - 10) * 0.5
            self.humidity = max(0, min(100, self.humidity))

            reading = SensorReading(
                sensor_id=self.sensor_id,
                sensor_type=self.sensor_type,
                value=round(self.humidity, 1),
                unit="%",
                timestamp=time.time(),
                metadata={"quality": "simulated"}
            )

            self.last_reading = reading
            self.last_error = None
            return reading

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error reading mock humidity sensor: {e}")
            return None

    async def shutdown(self) -> None:
        """Shutdown the mock sensor."""
        logger.info(f"Mock humidity sensor {self.sensor_id} shutdown")


class DHT22Sensor(SensorDriver):
    """
    DHT22 Temperature and Humidity Sensor driver.

    Note: This is a placeholder for actual DHT22 implementation.
    Real implementation would use GPIO and timing-critical code,
    typically done in C++ for accuracy.
    """

    def __init__(self, sensor_id: str, gpio_pin: int, gpio_controller: GPIOController):
        super().__init__(sensor_id, SensorType.TEMPERATURE)  # Primary type
        self.gpio_pin = gpio_pin
        self.gpio = gpio_controller
        self.secondary_sensor_id = f"{sensor_id}_humidity"

    async def initialize(self) -> bool:
        """Initialize DHT22 sensor."""
        try:
            # Configure GPIO pin for communication
            success = await self.gpio.configure_pin(self.gpio_pin, GPIOMode.INPUT)
            if success:
                logger.info(f"DHT22 sensor {self.sensor_id} initialized on GPIO {self.gpio_pin}")
                return True
            else:
                self.last_error = "Failed to configure GPIO pin"
                return False
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error initializing DHT22 sensor: {e}")
            return False

    async def read(self) -> Optional[SensorReading]:
        """
        Read temperature and humidity from DHT22.

        Note: Real DHT22 communication requires precise timing that can't be
        reliably achieved in Python. This is a placeholder that would delegate
        to the C++ hardware server for actual sensor reading.
        """
        try:
            # In a real implementation, this would send a request to the C++ hardware server
            # For now, return mock data
            temperature = 23.5 + (time.time() % 10 - 5) * 0.2
            humidity = 65.0 + (time.time() % 15 - 7.5) * 0.5

            # Create temperature reading
            temp_reading = SensorReading(
                sensor_id=self.sensor_id,
                sensor_type=SensorType.TEMPERATURE,
                value=round(temperature, 1),
                unit="°C",
                timestamp=time.time(),
                metadata={"sensor": "DHT22", "quality": "placeholder"}
            )

            # Create humidity reading
            humidity_reading = SensorReading(
                sensor_id=self.secondary_sensor_id,
                sensor_type=SensorType.HUMIDITY,
                value=round(max(0, min(100, humidity)), 1),
                unit="%",
                timestamp=time.time(),
                metadata={"sensor": "DHT22", "quality": "placeholder"}
            )

            # For simplicity, return just temperature reading
            # In practice, you'd return both or handle them separately
            self.last_reading = temp_reading
            self.last_error = None
            return temp_reading

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error reading DHT22 sensor: {e}")
            return None

    async def shutdown(self) -> None:
        """Shutdown DHT22 sensor."""
        logger.info(f"DHT22 sensor {self.sensor_id} shutdown")


class SensorManager:
    """
    Sensor Manager for coordinating multiple sensors.

    Features:
    - Sensor registration and management
    - Batch reading operations
    - Health monitoring
    - Configurable polling intervals
    - Async operation support

    Usage:
        manager = SensorManager()
        await manager.add_sensor(MockTemperatureSensor("temp1"))
        await manager.add_sensor(MockHumiditySensor("humid1"))

        readings = await manager.read_all_sensors()
        print(f"Temperature: {readings[0].value}°C")
    """

    def __init__(self, gpio_controller: Optional[GPIOController] = None):
        """
        Initialize sensor manager.

        Args:
            gpio_controller: GPIO controller for sensors that need GPIO access
        """
        self.gpio = gpio_controller
        self.sensors: Dict[str, SensorDriver] = {}
        self._running = False
        self._read_task: Optional[asyncio.Task] = None

    async def add_sensor(self, sensor: SensorDriver) -> bool:
        """
        Add a sensor to the manager.

        Args:
            sensor: Sensor driver instance

        Returns:
            True if sensor was added and initialized successfully
        """
        if sensor.sensor_id in self.sensors:
            logger.warning(f"Sensor {sensor.sensor_id} already exists")
            return False

        # Initialize the sensor
        success = await sensor.initialize()
        if success:
            self.sensors[sensor.sensor_id] = sensor
            logger.info(f"Added sensor {sensor.sensor_id} ({sensor.sensor_type.value})")
            return True
        else:
            logger.error(f"Failed to initialize sensor {sensor.sensor_id}")
            return False

    async def remove_sensor(self, sensor_id: str) -> bool:
        """
        Remove a sensor from the manager.

        Args:
            sensor_id: ID of sensor to remove

        Returns:
            True if sensor was removed successfully
        """
        if sensor_id not in self.sensors:
            return False

        sensor = self.sensors.pop(sensor_id)
        await sensor.shutdown()
        logger.info(f"Removed sensor {sensor_id}")
        return True

    async def read_sensor(self, sensor_id: str) -> Optional[SensorReading]:
        """
        Read data from a specific sensor.

        Args:
            sensor_id: ID of sensor to read

        Returns:
            Sensor reading or None if failed
        """
        sensor = self.sensors.get(sensor_id)
        if not sensor:
            logger.warning(f"Sensor {sensor_id} not found")
            return None

        return await sensor.read()

    async def read_all_sensors(self) -> List[SensorReading]:
        """
        Read data from all sensors.

        Returns:
            List of sensor readings (may be empty if all failed)
        """
        readings = []
        for sensor in self.sensors.values():
            reading = await sensor.read()
            if reading:
                readings.append(reading)

        logger.debug(f"Read {len(readings)} sensor values from {len(self.sensors)} sensors")
        return readings

    async def read_sensors_by_type(self, sensor_type: SensorType) -> List[SensorReading]:
        """
        Read data from all sensors of a specific type.

        Args:
            sensor_type: Type of sensors to read

        Returns:
            List of sensor readings
        """
        readings = []
        for sensor in self.sensors.values():
            if sensor.sensor_type == sensor_type:
                reading = await sensor.read()
                if reading:
                    readings.append(reading)

        return readings

    def get_sensor(self, sensor_id: str) -> Optional[SensorDriver]:
        """Get a sensor by ID."""
        return self.sensors.get(sensor_id)

    def get_sensors_by_type(self, sensor_type: SensorType) -> List[SensorDriver]:
        """Get all sensors of a specific type."""
        return [s for s in self.sensors.values() if s.sensor_type == sensor_type]

    def get_all_sensors(self) -> List[SensorDriver]:
        """Get all registered sensors."""
        return list(self.sensors.values())

    def get_sensor_status(self) -> Dict[str, Dict]:
        """Get status information for all sensors."""
        status = {}
        for sensor_id, sensor in self.sensors.items():
            status[sensor_id] = {
                "type": sensor.sensor_type.value,
                "healthy": sensor.is_healthy(),
                "last_error": sensor.last_error,
                "last_reading": sensor.last_reading.value if sensor.last_reading else None,
                "last_reading_time": sensor.last_reading.timestamp if sensor.last_reading else None
            }
        return status

    async def initialize_all_sensors(self) -> Dict[str, bool]:
        """
        Initialize all registered sensors.

        Returns:
            Dictionary mapping sensor IDs to initialization success
        """
        results = {}
        for sensor_id, sensor in self.sensors.items():
            try:
                success = await sensor.initialize()
                results[sensor_id] = success
            except Exception as e:
                logger.error(f"Error initializing sensor {sensor_id}: {e}")
                results[sensor_id] = False

        return results

    async def shutdown_all_sensors(self) -> None:
        """Shutdown all sensors."""
        for sensor in self.sensors.values():
            try:
                await sensor.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down sensor {sensor.sensor_id}: {e}")

        self.sensors.clear()
        logger.info("All sensors shutdown")

    # Context manager support
    async def __aenter__(self):
        await self.initialize_all_sensors()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown_all_sensors()