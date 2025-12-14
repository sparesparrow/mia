"""
DHT Sensor Driver

Driver for DHT11 and DHT22 temperature and humidity sensors.
These sensors use a single-wire protocol and are commonly used in IoT projects.
"""

import time
import board
import adafruit_dht
from typing import Optional, Dict, Any
import logging

from .base_sensor import BaseSensor, SensorData, SensorType, SensorReadError

logger = logging.getLogger(__name__)

class DHT11Sensor(BaseSensor):
    """
    DHT11 Temperature and Humidity Sensor

    The DHT11 is a basic digital temperature and humidity sensor.
    It provides:
    - Temperature: 0-50°C, ±2°C accuracy
    - Humidity: 20-90% RH, ±5% accuracy
    - Sampling rate: 1Hz maximum
    """

    def __init__(self, pin: int, sensor_id: str = None, config: Dict[str, Any] = None):
        if sensor_id is None:
            sensor_id = f"dht11_{pin}"

        super().__init__(
            sensor_id=sensor_id,
            sensor_type=SensorType.TEMPERATURE,  # Primary type
            unit="°C",
            config=config
        )

        self.pin = pin
        self.dht_device = None

        # DHT11 specific config
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_delay = self.config.get('retry_delay', 0.1)

        # Create secondary sensor for humidity
        self.humidity_sensor = DHT11HumiditySensor(self)

    def _initialize_hardware(self):
        """Initialize DHT11 sensor"""
        try:
            # Map pin number to board pin
            pin_obj = getattr(board, f'D{self.pin}', None)
            if pin_obj is None:
                raise SensorReadError(f"Invalid pin D{self.pin}")

            self.dht_device = adafruit_dht.DHT11(pin_obj, use_pulseio=False)
            logger.info(f"Initialized DHT11 on pin D{self.pin}")
        except Exception as e:
            raise SensorReadError(f"Failed to initialize DHT11: {e}")

    def _read_raw_value(self) -> Optional[float]:
        """Read temperature from DHT11"""
        if not self.dht_device:
            return None

        for attempt in range(self.retry_count):
            try:
                temperature = self.dht_device.temperature
                if temperature is not None and 0 <= temperature <= 50:
                    return temperature
                else:
                    logger.warning(f"DHT11 returned invalid temperature: {temperature}")
            except RuntimeError as e:
                # DHT sensors can fail occasionally
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise SensorReadError(f"DHT11 read failed after {self.retry_count} attempts: {e}")

        return None

    def read_humidity(self) -> Optional[float]:
        """Read humidity from DHT11"""
        if not self.dht_device:
            return None

        for attempt in range(self.retry_count):
            try:
                humidity = self.dht_device.humidity
                if humidity is not None and 20 <= humidity <= 90:
                    return humidity
                else:
                    logger.warning(f"DHT11 returned invalid humidity: {humidity}")
            except RuntimeError as e:
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"DHT11 humidity read failed: {e}")
                    return None

        return None

    def _cleanup_hardware(self):
        """Cleanup DHT11 resources"""
        if self.dht_device:
            try:
                self.dht_device.exit()
            except:
                pass
            self.dht_device = None

class DHT11HumiditySensor(BaseSensor):
    """Humidity sensor component of DHT11"""

    def __init__(self, parent_dht: DHT11Sensor):
        super().__init__(
            sensor_id=f"{parent_dht.sensor_id}_humidity",
            sensor_type=SensorType.HUMIDITY,
            unit="%",
            config=parent_dht.config
        )
        self.parent_dht = parent_dht

    def _initialize_hardware(self):
        """Humidity sensor uses parent's DHT device"""
        if not self.parent_dht.initialized:
            self.parent_dht.initialize()

    def _read_raw_value(self) -> Optional[float]:
        """Read humidity through parent DHT sensor"""
        return self.parent_dht.read_humidity()

class DHT22Sensor(BaseSensor):
    """
    DHT22 Temperature and Humidity Sensor

    The DHT22 is a more accurate version of the DHT11.
    It provides:
    - Temperature: -40-80°C, ±0.5°C accuracy
    - Humidity: 0-100% RH, ±2-5% accuracy
    - Sampling rate: 2Hz maximum
    """

    def __init__(self, pin: int, sensor_id: str = None, config: Dict[str, Any] = None):
        if sensor_id is None:
            sensor_id = f"dht22_{pin}"

        super().__init__(
            sensor_id=sensor_id,
            sensor_type=SensorType.TEMPERATURE,
            unit="°C",
            config=config
        )

        self.pin = pin
        self.dht_device = None

        # DHT22 specific config
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_delay = self.config.get('retry_delay', 0.1)

        # Create secondary sensor for humidity
        self.humidity_sensor = DHT22HumiditySensor(self)

    def _initialize_hardware(self):
        """Initialize DHT22 sensor"""
        try:
            # Map pin number to board pin
            pin_obj = getattr(board, f'D{self.pin}', None)
            if pin_obj is None:
                raise SensorReadError(f"Invalid pin D{self.pin}")

            self.dht_device = adafruit_dht.DHT22(pin_obj, use_pulseio=False)
            logger.info(f"Initialized DHT22 on pin D{self.pin}")
        except Exception as e:
            raise SensorReadError(f"Failed to initialize DHT22: {e}")

    def _read_raw_value(self) -> Optional[float]:
        """Read temperature from DHT22"""
        if not self.dht_device:
            return None

        for attempt in range(self.retry_count):
            try:
                temperature = self.dht_device.temperature
                if temperature is not None and -40 <= temperature <= 80:
                    return temperature
                else:
                    logger.warning(f"DHT22 returned invalid temperature: {temperature}")
            except RuntimeError as e:
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise SensorReadError(f"DHT22 read failed after {self.retry_count} attempts: {e}")

        return None

    def read_humidity(self) -> Optional[float]:
        """Read humidity from DHT22"""
        if not self.dht_device:
            return None

        for attempt in range(self.retry_count):
            try:
                humidity = self.dht_device.humidity
                if humidity is not None and 0 <= humidity <= 100:
                    return humidity
                else:
                    logger.warning(f"DHT22 returned invalid humidity: {humidity}")
            except RuntimeError as e:
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"DHT22 humidity read failed: {e}")
                    return None

        return None

    def _cleanup_hardware(self):
        """Cleanup DHT22 resources"""
        if self.dht_device:
            try:
                self.dht_device.exit()
            except:
                pass
            self.dht_device = None

class DHT22HumiditySensor(BaseSensor):
    """Humidity sensor component of DHT22"""

    def __init__(self, parent_dht: DHT22Sensor):
        super().__init__(
            sensor_id=f"{parent_dht.sensor_id}_humidity",
            sensor_type=SensorType.HUMIDITY,
            unit="%",
            config=parent_dht.config
        )
        self.parent_dht = parent_dht

    def _initialize_hardware(self):
        """Humidity sensor uses parent's DHT device"""
        if not self.parent_dht.initialized:
            self.parent_dht.initialize()

    def _read_raw_value(self) -> Optional[float]:
        """Read humidity through parent DHT sensor"""
        return self.parent_dht.read_humidity()