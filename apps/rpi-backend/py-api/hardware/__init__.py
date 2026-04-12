"""
Hardware Abstraction Layer
Phase 2.2: GPIO Control & Sensor Integration

This module provides Python abstractions for hardware control,
communicating with the C++ hardware server via ZeroMQ messaging.
"""

from importlib import import_module

__all__ = ["GPIOController", "SensorManager", "ArduinoController", "HardwareManager"]

_EXPORT_MODULES = {
	"GPIOController": ".gpio",
	"SensorManager": ".sensors",
	"ArduinoController": ".arduino",
	"HardwareManager": ".hardware_manager",
}


def __getattr__(name):
	module_name = _EXPORT_MODULES.get(name)
	if module_name is None:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

	module = import_module(module_name, __name__)
	return getattr(module, name)