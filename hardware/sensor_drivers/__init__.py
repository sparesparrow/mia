"""
MIA Sensor Drivers

This package provides sensor drivers for various I2C/SPI sensors
used in the MIA (Modular IoT Assistant) system.

Supported sensors:
- DHT11/DHT22: Temperature and humidity
- HC-SR04: Ultrasonic distance sensor
- BMP180: Barometric pressure and temperature
- Generic I2C/SPI abstraction for custom sensors
"""

from .base_sensor import BaseSensor, SensorData, SensorType
from .dht_sensor import DHT11Sensor, DHT22Sensor
from .hc_sr04_sensor import HCSR04Sensor
from .bmp180_sensor import BMP180Sensor
from .analog_sensor import AnalogSensor
from .sensor_manager import SensorManager

__all__ = [
    'BaseSensor', 'SensorData', 'SensorType',
    'DHT11Sensor', 'DHT22Sensor',
    'HCSR04Sensor',
    'BMP180Sensor',
    'AnalogSensor',
    'SensorManager'
]