"""
Hardware Abstraction Layer
Phase 2.2: GPIO Control & Sensor Integration

This module provides Python abstractions for hardware control,
communicating with the C++ hardware server via ZeroMQ messaging.
"""

from .gpio import GPIOController
from .sensors import SensorManager
from .arduino import ArduinoController
from .hardware_manager import HardwareManager

__all__ = ['GPIOController', 'SensorManager', 'ArduinoController', 'HardwareManager']