"""
BMP180 Barometric Pressure Sensor Driver

Driver for BMP180 digital pressure sensor.
This sensor provides accurate pressure and temperature measurements.
"""

import time
import board
import adafruit_bmp180
from typing import Optional, Dict, Any
import logging

from .base_sensor import BaseSensor, SensorData, SensorType, SensorReadError

logger = logging.getLogger(__name__)

class BMP180Sensor(BaseSensor):
    """
    BMP180 Barometric Pressure and Temperature Sensor

    The BMP180 provides:
    - Pressure: 300-1100 hPa, ±1 hPa accuracy
    - Temperature: -40-85°C, ±2°C accuracy
    - I2C interface
    - Low power consumption
    """

    def __init__(self, sensor_id: str = "bmp180", config: Dict[str, Any] = None):
        super().__init__(
            sensor_id=sensor_id,
            sensor_type=SensorType.PRESSURE,  # Primary type
            unit="hPa",
            config=config
        )

        self.bmp180 = None

        # BMP180 specific config
        self.sea_level_pressure = self.config.get('sea_level_pressure', 1013.25)  # hPa
        self.oversampling = self.config.get('oversampling', 3)  # 0-3, higher = more accurate but slower

        # Create secondary sensor for temperature
        self.temperature_sensor = BMP180TemperatureSensor(self)

    def _initialize_hardware(self):
        """Initialize BMP180 sensor"""
        try:
            # Initialize I2C
            i2c = board.I2C()

            self.bmp180 = adafruit_bmp180.Adafruit_BMP180_I2C(i2c)

            # Configure oversampling for accuracy vs speed tradeoff
            # 0 = ultra low power, 1 = standard, 2 = high res, 3 = ultra high res
            if hasattr(self.bmp180, 'mode'):
                self.bmp180.mode = self.oversampling

            logger.info(f"Initialized BMP180 pressure sensor (oversampling: {self.oversampling})")
        except Exception as e:
            raise SensorReadError(f"Failed to initialize BMP180: {e}")

    def _read_raw_value(self) -> Optional[float]:
        """Read pressure from BMP180"""
        if not self.bmp180:
            return None

        try:
            pressure = self.bmp180.pressure

            # Validate pressure range
            if 300 <= pressure <= 1100:
                return pressure
            else:
                logger.warning(f"BMP180 returned invalid pressure: {pressure} hPa")
                return None

        except Exception as e:
            logger.error(f"BMP180 pressure read error: {e}")
            return None

    def read_temperature(self) -> Optional[float]:
        """Read temperature from BMP180"""
        if not self.bmp180:
            return None

        try:
            temperature = self.bmp180.temperature

            # Validate temperature range
            if -40 <= temperature <= 85:
                return temperature
            else:
                logger.warning(f"BMP180 returned invalid temperature: {temperature}°C")
                return None

        except Exception as e:
            logger.error(f"BMP180 temperature read error: {e}")
            return None

    def get_altitude(self, pressure: float = None) -> Optional[float]:
        """Calculate altitude from pressure using barometric formula"""
        if pressure is None:
            pressure = self.read_data()
            if pressure:
                pressure = pressure.value
            else:
                return None

        try:
            # Barometric formula: h = (T0/L) * ((P/P0)^(-1/k) - 1)
            # Simplified version for standard conditions
            altitude = 44330 * (1 - (pressure / self.sea_level_pressure) ** (1/5.255))
            return altitude
        except Exception as e:
            logger.error(f"Altitude calculation error: {e}")
            return None

    def _get_metadata(self) -> Dict[str, Any]:
        """Get BMP180 specific metadata"""
        metadata = super()._get_metadata()
        metadata.update({
            "sea_level_pressure": self.sea_level_pressure,
            "oversampling": self.oversampling,
            "altitude_available": True
        })
        return metadata

    def _calculate_quality(self, value: float) -> float:
        """Calculate measurement quality"""
        base_quality = super()._calculate_quality(value)

        # Pressure-based quality - extreme values might indicate issues
        pressure_quality = 1.0
        if value < 800 or value > 1200:
            pressure_quality = 0.5  # Unusual pressure values

        return min(base_quality, pressure_quality)

    def _cleanup_hardware(self):
        """Cleanup BMP180 resources"""
        if self.bmp180:
            try:
                # BMP180 doesn't have explicit cleanup, but we can set to None
                pass
            except:
                pass
            self.bmp180 = None

class BMP180TemperatureSensor(BaseSensor):
    """Temperature sensor component of BMP180"""

    def __init__(self, parent_bmp: BMP180Sensor):
        super().__init__(
            sensor_id=f"{parent_bmp.sensor_id}_temperature",
            sensor_type=SensorType.TEMPERATURE,
            unit="°C",
            config=parent_bmp.config
        )
        self.parent_bmp = parent_bmp

    def _initialize_hardware(self):
        """Temperature sensor uses parent's BMP device"""
        if not self.parent_bmp.initialized:
            self.parent_bmp.initialize()

    def _read_raw_value(self) -> Optional[float]:
        """Read temperature through parent BMP sensor"""
        return self.parent_bmp.read_temperature()