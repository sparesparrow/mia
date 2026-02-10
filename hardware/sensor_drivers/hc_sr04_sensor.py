"""
HC-SR04 Ultrasonic Distance Sensor Driver

Driver for HC-SR04 ultrasonic distance sensor.
This sensor uses sound waves to measure distance to objects.
"""

import time
import board
import adafruit_hcsr04
from typing import Optional, Dict, Any
import logging

from .base_sensor import BaseSensor, SensorData, SensorType, SensorReadError

logger = logging.getLogger(__name__)

class HCSR04Sensor(BaseSensor):
    """
    HC-SR04 Ultrasonic Distance Sensor

    The HC-SR04 uses ultrasonic sound waves to measure distance.
    It provides:
    - Range: 2cm to 400cm
    - Accuracy: ±3mm
    - Resolution: 1mm
    - Update rate: Up to 40Hz
    """

    def __init__(self, trigger_pin: int, echo_pin: int,
                 sensor_id: str = None, config: Dict[str, Any] = None):
        if sensor_id is None:
            sensor_id = f"hcsr04_{trigger_pin}_{echo_pin}"

        super().__init__(
            sensor_id=sensor_id,
            sensor_type=SensorType.DISTANCE,
            unit="cm",
            config=config
        )

        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.hcsr04 = None

        # HC-SR04 specific config
        self.timeout = self.config.get('timeout', 0.1)  # seconds
        self.retry_count = self.config.get('retry_count', 3)

        # Valid range
        self.min_distance = self.config.get('min_distance', 2.0)  # cm
        self.max_distance = self.config.get('max_distance', 400.0)  # cm

    def _initialize_hardware(self):
        """Initialize HC-SR04 sensor"""
        try:
            # Map pin numbers to board pins
            trigger_pin_obj = getattr(board, f'D{self.trigger_pin}', None)
            echo_pin_obj = getattr(board, f'D{self.echo_pin}', None)

            if trigger_pin_obj is None or echo_pin_obj is None:
                raise SensorReadError(f"Invalid pins: trigger=D{self.trigger_pin}, echo=D{self.echo_pin}")

            self.hcsr04 = adafruit_hcsr04.HCSR04(trigger_pin_obj, echo_pin_obj)
            self.hcsr04.timeout = self.timeout

            logger.info(f"Initialized HC-SR04: trigger=D{self.trigger_pin}, echo=D{self.echo_pin}")
        except Exception as e:
            raise SensorReadError(f"Failed to initialize HC-SR04: {e}")

    def _read_raw_value(self) -> Optional[float]:
        """Read distance from HC-SR04"""
        if not self.hcsr04:
            return None

        for attempt in range(self.retry_count):
            try:
                distance = self.hcsr04.distance

                # Convert to cm and validate range
                distance_cm = distance * 100  # Convert m to cm

                if self.min_distance <= distance_cm <= self.max_distance:
                    return distance_cm
                else:
                    logger.warning(f"HC-SR04 distance out of range: {distance_cm} cm")

            except RuntimeError as e:
                # HC-SR04 can timeout or fail
                if attempt < self.retry_count - 1:
                    time.sleep(0.01)  # Short delay before retry
                    continue
                else:
                    logger.error(f"HC-SR04 read failed after {self.retry_count} attempts: {e}")
                    return None

        return None

    def _validate_reading(self, value: float) -> bool:
        """Validate distance reading"""
        return self.min_distance <= value <= self.max_distance

    def _get_metadata(self) -> Dict[str, Any]:
        """Get HC-SR04 specific metadata"""
        metadata = super()._get_metadata()
        metadata.update({
            "trigger_pin": self.trigger_pin,
            "echo_pin": self.echo_pin,
            "min_distance": self.min_distance,
            "max_distance": self.max_distance,
            "timeout": self.timeout
        })
        return metadata

    def _calculate_quality(self, value: float) -> float:
        """Calculate measurement quality based on distance and stability"""
        base_quality = super()._calculate_quality(value)

        # Distance-based quality - closer readings are generally more accurate
        distance_quality = 1.0
        if value < 10:
            distance_quality = 0.8  # Very close readings can have more noise
        elif value > 300:
            distance_quality = 0.9  # Far readings can be less reliable

        return min(base_quality, distance_quality)

    def _cleanup_hardware(self):
        """Cleanup HC-SR04 resources"""
        if self.hcsr04:
            try:
                self.hcsr04.deinit()
            except:
                pass
            self.hcsr04 = None