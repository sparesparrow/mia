"""Tests for HardwareManager simulation fallback and component isolation."""

import asyncio
import sys
import types

import pytest


def _build_hardware_manager_module():
    """
    Build a standalone version of hardware_manager by stubbing out package imports.
    This mirrors the approach used in test_gpio_simulation.py.
    """
    # Create stub modules for the relative imports
    core_registry = types.ModuleType("core_registry")

    class DeviceRegistry:
        def start(self):
            pass

        def get_hardware_summary(self):
            return {"devices": []}

    class DeviceType:
        GPIO = "gpio"
        SENSOR = "sensor"
        SERIAL = "serial"

    class DeviceStatus:
        ONLINE = "online"
        OFFLINE = "offline"

    core_registry.DeviceRegistry = DeviceRegistry
    core_registry.DeviceType = DeviceType
    core_registry.DeviceStatus = DeviceStatus

    # Read actual gpio.py, arduino.py source for their simulation classes
    import pathlib

    hw_dir = pathlib.Path(__file__).resolve().parents[2] / "apps" / "rpi-backend" / "py-api" / "hardware"
    manager_source = (hw_dir / "hardware_manager.py").read_text(encoding="utf-8")

    # Replace relative imports with absolute stubs
    manager_source = manager_source.replace(
        "from ..core.registry import DeviceRegistry, DeviceType, DeviceStatus",
        ""
    )
    manager_source = manager_source.replace(
        "from .gpio import GPIOController, GPIOMode",
        ""
    )
    manager_source = manager_source.replace(
        "from .sensors import SensorManager, SensorReading, SensorType",
        ""
    )
    manager_source = manager_source.replace(
        "from .arduino import ArduinoController, ArduinoInfo",
        ""
    )

    # Build stub classes to inject
    stub_preamble = '''
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class DeviceRegistry:
    def start(self):
        pass
    def get_hardware_summary(self):
        return {"devices": []}


class DeviceType:
    GPIO = "gpio"


class DeviceStatus:
    ONLINE = "online"


class GPIOMode:
    OUTPUT = "output"
    INPUT = "input"


class GPIOController:
    def __init__(self, broker_url="tcp://localhost:5555", simulation=None):
        self.broker_url = broker_url
        self._simulation = simulation
        self.simulation_mode = False
        self._pin_configs = {}

    async def connect(self):
        self.simulation_mode = True
        logger.info("GPIOController: simulation mode (stub)")

    def get_configured_pins(self):
        return self._pin_configs


class SensorReading:
    pass


class SensorType:
    TEMPERATURE = "temperature"


class SensorManager:
    def __init__(self, gpio_controller):
        self.gpio_controller = gpio_controller

    def get_all_readings(self):
        return []

    def get_sensor_status(self):
        return {}


class ArduinoInfo:
    pass


class ArduinoController:
    def __init__(self, baudrate=115200, timeout=1.0, simulation=None):
        self._simulation = simulation
        self.simulation_mode = False
        self._devices = []

    async def start(self):
        self.simulation_mode = True
        logger.info("ArduinoController: simulation mode (stub)")

    def get_connected_devices(self):
        return self._devices

'''
    # Compile the module
    ns = {}
    exec(stub_preamble, ns)
    # Now exec the manager source, but skip module-level imports (already replaced)
    exec(manager_source, ns)
    return ns


@pytest.fixture
def hw_ns():
    return _build_hardware_manager_module()


@pytest.mark.unit
class TestHardwareManagerSimulation:
    """Verify HardwareManager initializes with simulation fallback."""

    @pytest.mark.asyncio
    async def test_initialize_all_simulation(self, hw_ns):
        HardwareManager = hw_ns["HardwareManager"]
        mgr = HardwareManager(simulation=True)
        result = await mgr.initialize()
        assert result is True
        assert mgr._initialized is True
        assert mgr._component_status["registry"] == "ok"
        assert mgr._component_status["gpio"] == "simulation"
        assert mgr._component_status["arduino"] == "simulation"

    @pytest.mark.asyncio
    async def test_initialize_returns_component_status(self, hw_ns):
        HardwareManager = hw_ns["HardwareManager"]
        mgr = HardwareManager(simulation=True)
        await mgr.initialize()
        summary = mgr.get_hardware_summary()
        assert "component_status" in summary
        assert summary["initialized"] is True
        assert summary["component_status"]["gpio"] == "simulation"

    @pytest.mark.asyncio
    async def test_partial_failure_still_initializes(self, hw_ns):
        """If one component throws, the manager still starts."""
        HardwareManager = hw_ns["HardwareManager"]
        mgr = HardwareManager(simulation=True)

        # Make arduino.start() raise
        async def bad_start():
            raise RuntimeError("Arduino exploded")
        mgr.arduino_controller.start = bad_start

        result = await mgr.initialize()
        assert result is True  # registry + gpio still work
        assert "failed" in mgr._component_status["arduino"]
        assert mgr._component_status["gpio"] == "simulation"

    @pytest.mark.asyncio
    async def test_all_components_fail_returns_false(self, hw_ns):
        """If every component fails, initialize returns False."""
        HardwareManager = hw_ns["HardwareManager"]
        mgr = HardwareManager(simulation=True)

        # Break everything
        def bad_registry_start():
            raise RuntimeError("registry boom")

        async def bad_connect():
            raise RuntimeError("gpio boom")

        async def bad_start():
            raise RuntimeError("arduino boom")

        mgr.registry.start = bad_registry_start
        mgr.gpio_controller.connect = bad_connect
        mgr.arduino_controller.start = bad_start

        result = await mgr.initialize()
        assert result is False
        assert mgr._initialized is False

    @pytest.mark.asyncio
    async def test_simulation_flag_passed_to_gpio(self, hw_ns):
        HardwareManager = hw_ns["HardwareManager"]
        mgr = HardwareManager(simulation=True)
        assert mgr.gpio_controller._simulation is True

    @pytest.mark.asyncio
    async def test_simulation_flag_passed_to_arduino(self, hw_ns):
        HardwareManager = hw_ns["HardwareManager"]
        mgr = HardwareManager(simulation=True)
        assert mgr.arduino_controller._simulation is True
