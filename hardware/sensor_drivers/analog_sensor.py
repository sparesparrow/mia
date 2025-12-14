"""
Analog Sensor Driver

Driver for analog sensors connected to ADC pins.
Provides voltage divider calculations, calibration, and scaling.
"""

import time
from typing import Optional, Dict, Any, Callable
import logging

from .base_sensor import BaseSensor, SensorData, SensorType, SensorReadError

logger = logging.getLogger(__name__)

class AnalogSensor(BaseSensor):
    """
    Generic Analog Sensor Driver

    Supports various analog sensors connected to ADC pins with:
    - Voltage divider calculations
    - Linear and non-linear calibration
    - Multiple sensor types (voltage, current, temperature, etc.)
    - Configurable ADC resolution and reference voltage
    """

    def __init__(self, pin: int, sensor_type: SensorType,
                 sensor_id: str = None, config: Dict[str, Any] = None):
        if sensor_id is None:
            sensor_id = f"analog_{sensor_type.value}_{pin}"

        # Determine unit based on sensor type
        unit_map = {
            SensorType.VOLTAGE: "V",
            SensorType.CURRENT: "A",
            SensorType.TEMPERATURE: "°C",
            SensorType.LIGHT: "lux",
            SensorType.DISTANCE: "cm",
            SensorType.PRESSURE: "hPa",
        }
        unit = unit_map.get(sensor_type, "V")  # Default to volts

        super().__init__(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            unit=unit,
            config=config
        )

        self.pin = pin

        # ADC configuration
        self.adc_resolution = self.config.get('adc_resolution', 10)  # bits (Arduino: 10, ESP32: 12)
        self.reference_voltage = self.config.get('reference_voltage', 5.0)  # V
        self.max_adc_value = (2 ** self.adc_resolution) - 1

        # Voltage divider configuration
        self.voltage_divider = self.config.get('voltage_divider', False)
        self.r1 = self.config.get('r1', 10000)  # ohms (upper resistor)
        self.r2 = self.config.get('r2', 10000)  # ohms (lower resistor to ground)

        # Conversion function
        self.conversion_function = self.config.get('conversion_function')
        if isinstance(self.conversion_function, str):
            # Allow string function definitions for config files
            self.conversion_function = eval(self.conversion_function)

        # Sensor-specific ranges for validation
        self.valid_range = self._get_valid_range()

    def _get_valid_range(self) -> tuple:
        """Get valid range for this sensor type"""
        ranges = {
            SensorType.VOLTAGE: (0, self.reference_voltage),
            SensorType.CURRENT: (0, 10),  # Amps
            SensorType.TEMPERATURE: (-50, 150),  # Celsius
            SensorType.LIGHT: (0, 100000),  # Lux
            SensorType.DISTANCE: (0, 500),  # cm
            SensorType.PRESSURE: (800, 1200),  # hPa
        }
        return ranges.get(self.sensor_type, (0, self.max_adc_value))

    def _initialize_hardware(self):
        """Initialize analog pin"""
        try:
            # For CircuitPython/RPi.GPIO, pin setup is minimal
            # The actual ADC reading will happen in _read_raw_value
            logger.info(f"Initialized analog sensor on pin {self.pin} (ADC{self.adc_resolution}bit, {self.reference_voltage}V ref)")
        except Exception as e:
            raise SensorReadError(f"Failed to initialize analog sensor: {e}")

    def _read_raw_value(self) -> Optional[float]:
        """Read analog value and convert to sensor units"""
        try:
            # Read ADC value (0 to max_adc_value)
            adc_value = self._read_adc_value()

            if adc_value is None:
                return None

            # Convert ADC to voltage
            voltage = (adc_value / self.max_adc_value) * self.reference_voltage

            # Apply voltage divider correction if configured
            if self.voltage_divider:
                # For voltage divider: V_measured = V_actual * (R2 / (R1 + R2))
                # So: V_actual = V_measured / (R2 / (R1 + R2)) = V_measured * ((R1 + R2) / R2)
                divider_ratio = (self.r1 + self.r2) / self.r2
                voltage *= divider_ratio

            # Apply custom conversion function if provided
            if self.conversion_function:
                try:
                    result = self.conversion_function(voltage, adc_value)
                    return result
                except Exception as e:
                    logger.error(f"Conversion function error: {e}")
                    return None

            # Default: return voltage for voltage sensors, ADC value for others
            if self.sensor_type == SensorType.VOLTAGE:
                return voltage
            else:
                # For other sensor types, expect conversion function
                logger.warning(f"No conversion function for {self.sensor_type.value} sensor")
                return voltage

        except Exception as e:
            logger.error(f"Analog sensor read error: {e}")
            return None

    def _read_adc_value(self) -> Optional[int]:
        """Read raw ADC value - platform specific"""
        try:
            # This is a placeholder - actual implementation depends on platform
            # For Arduino/RPi, this would use analogRead() or GPIO library

            # Simulate ADC reading for development
            if hasattr(self, '_mock_adc_value'):
                return self._mock_adc_value
            else:
                # Return middle value as default
                return self.max_adc_value // 2

        except Exception as e:
            logger.error(f"ADC read error: {e}")
            return None

    def set_mock_value(self, adc_value: int):
        """Set mock ADC value for testing"""
        self._mock_adc_value = max(0, min(self.max_adc_value, adc_value))

    def _validate_reading(self, value: float) -> bool:
        """Validate sensor reading against expected range"""
        min_val, max_val = self.valid_range
        return min_val <= value <= max_val

    def _get_metadata(self) -> Dict[str, Any]:
        """Get analog sensor specific metadata"""
        metadata = super()._get_metadata()
        metadata.update({
            "pin": self.pin,
            "adc_resolution": self.adc_resolution,
            "reference_voltage": self.reference_voltage,
            "voltage_divider": self.voltage_divider,
            "r1": self.r1,
            "r2": self.r2,
            "valid_range": self.valid_range,
            "has_conversion_function": self.conversion_function is not None
        })
        return metadata

    def calibrate_voltage_divider(self, measured_voltage: float, actual_voltage: float):
        """Calibrate voltage divider ratios"""
        if not self.voltage_divider:
            logger.warning("Voltage divider not enabled")
            return

        # Calculate required divider ratio
        if measured_voltage > 0:
            required_ratio = actual_voltage / measured_voltage
            total_r = self.r1 + self.r2

            # R2 stays the same, adjust R1
            self.r1 = (required_ratio * self.r2) - self.r2

            if self.r1 < 0:
                logger.error("Calibration resulted in negative R1")
                return

            logger.info(f"Calibrated voltage divider: R1={self.r1:.1f}, R2={self.r2}")

    @staticmethod
    def create_thermistor_converter(r25: float = 10000, beta: float = 3950,
                                   r_series: float = 10000) -> Callable:
        """
        Create conversion function for thermistor sensors

        Args:
            r25: Resistance at 25°C
            beta: Beta value of thermistor
            r_series: Series resistor value

        Returns:
            Conversion function that takes (voltage, adc_value) and returns temperature
        """
        def thermistor_to_temperature(voltage: float, adc_value: int) -> float:
            if voltage <= 0 or voltage >= 5.0:
                return 0.0

            # Calculate thermistor resistance
            r_thermistor = r_series * (voltage / (5.0 - voltage))

            # Steinhart-Hart equation approximation
            if r_thermistor > 0:
                ln_r = math.log(r_thermistor / r25)
                temperature = 1.0 / ((1.0 / 298.15) + (ln_r / beta)) - 273.15
                return temperature
            else:
                return 0.0

        return thermistor_to_temperature

    @staticmethod
    def create_linear_converter(scale: float, offset: float = 0.0) -> Callable:
        """
        Create linear conversion function

        Args:
            scale: Scale factor (output = input * scale + offset)
            offset: Offset value

        Returns:
            Linear conversion function
        """
        def linear_conversion(voltage: float, adc_value: int) -> float:
            return voltage * scale + offset

        return linear_conversion