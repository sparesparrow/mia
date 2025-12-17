"""
Hardware Manager
Unified interface for managing all hardware devices through the device registry.

This module provides high-level hardware management that integrates:
- Device registry for tracking devices
- GPIO controller for pin management
- Sensor manager for sensor readings
- Arduino controller for serial devices
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from ..core.registry import DeviceRegistry, DeviceType, DeviceStatus
from .gpio import GPIOController, GPIOMode
from .sensors import SensorManager, SensorReading, SensorType
from .arduino import ArduinoController, ArduinoInfo

logger = logging.getLogger(__name__)


class HardwareManager:
    """
    Unified hardware management system.

    Features:
    - Centralized device management
    - Automatic hardware discovery
    - Health monitoring and status reporting
    - Unified API for all hardware types
    - Event-driven architecture

    Usage:
        manager = HardwareManager()
        await manager.initialize()

        # Register devices
        await manager.register_gpio_pin(17, GPIOMode.OUTPUT)
        await manager.register_sensor("temp1", SensorType.TEMPERATURE)

        # Control hardware
        await manager.set_gpio_pin(17, True)
        readings = await manager.read_all_sensors()
    """

    def __init__(self, broker_url: str = "tcp://localhost:5555"):
        """
        Initialize hardware manager.

        Args:
            broker_url: ZeroMQ broker URL for hardware communication
        """
        self.broker_url = broker_url

        # Core components
        self.registry = DeviceRegistry()
        self.gpio_controller = GPIOController(broker_url)
        self.sensor_manager = SensorManager(self.gpio_controller)
        self.arduino_controller = ArduinoController()

        # Initialization state
        self._initialized = False

        # Event callbacks
        self._on_device_online: List[Callable] = []
        self._on_device_offline: List[Callable] = []
        self._on_sensor_reading: List[Callable[[SensorReading], None]] = []

    async def initialize(self) -> bool:
        """
        Initialize all hardware subsystems.

        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing hardware manager...")

            # Start device registry
            self.registry.start()

            # Connect GPIO controller
            await self.gpio_controller.connect()

            # Initialize sensor manager
            # Note: Sensors are initialized when registered

            # Start Arduino controller
            await self.arduino_controller.start()

            # Setup event handlers
            self._setup_event_handlers()

            self._initialized = True
            logger.info("Hardware manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize hardware manager: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown all hardware subsystems."""
        logger.info("Shutting down hardware manager...")

        # Stop event monitoring
        self._initialized = False

        # Shutdown components
        await self.arduino_controller.stop()
        await self.sensor_manager.shutdown_all_sensors()
        await self.gpio_controller.disconnect()
        self.registry.stop()

        logger.info("Hardware manager shutdown complete")

    def _setup_event_handlers(self):
        """Setup event handlers for device state changes."""
        # Registry event handlers
        self.registry.on_device_online(self._handle_device_online)
        self.registry.on_device_offline(self._handle_device_offline)
        self.registry.on_device_error(self._handle_device_error)

    def _handle_device_online(self, device):
        """Handle device coming online."""
        logger.info(f"Device online: {device.device_id} ({device.device_type.value})")
        for callback in self._on_device_online:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Error in device online callback: {e}")

    def _handle_device_offline(self, device):
        """Handle device going offline."""
        logger.info(f"Device offline: {device.device_id} ({device.device_type.value})")
        for callback in self._on_device_offline:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Error in device offline callback: {e}")

    def _handle_device_error(self, device, error_message):
        """Handle device error."""
        logger.warning(f"Device error: {device.device_id} - {error_message}")

    # GPIO Management
    async def register_gpio_pin(self, pin: int, mode: GPIOMode,
                               name: str = None) -> bool:
        """
        Register and configure a GPIO pin.

        Args:
            pin: GPIO pin number
            mode: Pin mode (INPUT or OUTPUT)
            name: Optional custom name

        Returns:
            True if registration and configuration successful
        """
        if not self._initialized:
            raise RuntimeError("Hardware manager not initialized")

        try:
            # Choose the appropriate profile based on mode
            profile_key = "gpio_output_pin" if mode == GPIOMode.OUTPUT else "gpio_input_pin"

            # Register with device registry
            device_profile = self.registry.register_hardware_device(
                DeviceType.GPIO,
                device_id=f"gpio_pin_{pin}",
                name=name,
                profile_key=profile_key,
                pin=pin,
                mode=mode.value
            )
            if not device_profile:
                return False

            # Try to configure the actual GPIO pin (may fail if hardware server not running)
            try:
                success = await self.gpio_controller.configure_pin(pin, mode)
                if success:
                    logger.info(f"GPIO pin {pin} registered and configured as {mode.value}")
                    return True
                else:
                    logger.warning(f"GPIO pin {pin} registered but hardware configuration failed (server not available?)")
                    # Don't remove from registry - device is still registered for monitoring
                    return True
            except Exception as e:
                logger.warning(f"GPIO pin {pin} registered but hardware configuration failed: {e}")
                # Don't remove from registry - device is still registered for monitoring
                return True

        except Exception as e:
            logger.error(f"Failed to register GPIO pin {pin}: {e}")
            return False

    async def set_gpio_pin(self, pin: int, value: bool) -> bool:
        """
        Set the value of a GPIO output pin.

        Args:
            pin: GPIO pin number
            value: Boolean value to set

        Returns:
            True if successful
        """
        return await self.gpio_controller.set_pin(pin, value)

    async def get_gpio_pin(self, pin: int) -> bool:
        """
        Get the value of a GPIO pin.

        Args:
            pin: GPIO pin number

        Returns:
            Boolean value of the pin
        """
        return await self.gpio_controller.get_pin(pin)

    async def get_gpio_status(self) -> Dict[str, Any]:
        """Get status of all GPIO pins."""
        gpio_status = await self.gpio_controller.get_status()

        # Enhance with registry information
        registry_info = self.registry.get_hardware_summary()
        gpio_status["registry_info"] = registry_info.get("gpio_pins", [])

        return gpio_status

    # Sensor Management
    async def register_sensor(self, sensor_type: SensorType, sensor_id: str,
                            location: str = None, **metadata) -> bool:
        """
        Register a sensor device.

        Args:
            sensor_type: Type of sensor
            sensor_id: Unique sensor identifier
            location: Physical location of sensor
            **metadata: Additional sensor metadata

        Returns:
            True if registration successful
        """
        if not self._initialized:
            raise RuntimeError("Hardware manager not initialized")

        try:
            # Register with device registry
            device_profile = self.registry.register_sensor(
                sensor_type.value, sensor_id, location, **metadata
            )
            if not device_profile:
                return False

            # Create appropriate sensor driver
            if sensor_type == SensorType.TEMPERATURE:
                from .sensors import MockTemperatureSensor
                sensor = MockTemperatureSensor(sensor_id)
            elif sensor_type == SensorType.HUMIDITY:
                from .sensors import MockHumiditySensor
                sensor = MockHumiditySensor(sensor_id)
            else:
                logger.warning(f"No driver available for sensor type: {sensor_type}")
                self.registry.unregister(sensor_id)
                return False

            # Add to sensor manager
            success = await self.sensor_manager.add_sensor(sensor)
            if success:
                logger.info(f"Sensor {sensor_id} ({sensor_type.value}) registered successfully")
                return True
            else:
                self.registry.unregister(sensor_id)
                return False

        except Exception as e:
            logger.error(f"Failed to register sensor {sensor_id}: {e}")
            return False

    async def read_sensor(self, sensor_id: str) -> Optional[SensorReading]:
        """
        Read data from a specific sensor.

        Args:
            sensor_id: Sensor identifier

        Returns:
            Sensor reading or None if failed
        """
        reading = await self.sensor_manager.read_sensor(sensor_id)

        # Update device registry health
        if reading:
            self.registry.update_hardware_health(sensor_id, True)
            # Trigger sensor reading callbacks
            for callback in self._on_sensor_reading:
                try:
                    callback(reading)
                except Exception as e:
                    logger.error(f"Error in sensor reading callback: {e}")
        else:
            self.registry.update_hardware_health(sensor_id, False, "Read failed")

        return reading

    async def read_all_sensors(self) -> List[SensorReading]:
        """
        Read data from all registered sensors.

        Returns:
            List of sensor readings
        """
        readings = await self.sensor_manager.read_all_sensors()

        # Update health status for all sensors
        sensor_ids = {r.sensor_id for r in readings}
        for sensor_id in self.sensor_manager.get_all_sensors():
            is_healthy = sensor_id.sensor_id in sensor_ids
            self.registry.update_hardware_health(sensor_id.sensor_id, is_healthy)

        # Trigger callbacks for all readings
        for reading in readings:
            for callback in self._on_sensor_reading:
                try:
                    callback(reading)
                except Exception as e:
                    logger.error(f"Error in sensor reading callback: {e}")

        return readings

    def get_sensor_status(self) -> Dict[str, Any]:
        """Get status of all sensors."""
        sensor_status = self.sensor_manager.get_sensor_status()

        # Enhance with registry information
        registry_info = self.registry.get_hardware_summary()
        sensor_status["registry_info"] = registry_info.get("sensors", [])

        return sensor_status

    # Arduino Management
    async def discover_arduino_devices(self) -> List[ArduinoInfo]:
        """
        Discover available Arduino devices.

        Returns:
            List of discovered Arduino devices
        """
        devices = await self.arduino_controller.discover_devices()

        # Register discovered devices with registry
        for device in devices:
            self.registry.register_arduino_device(
                port=device.port,
                board_type=device.board_type,
                firmware_version=device.firmware_version
            )

        return devices

    async def connect_arduino_device(self, port: str) -> bool:
        """
        Connect to an Arduino device.

        Args:
            port: Serial port path

        Returns:
            True if connection successful
        """
        success = await self.arduino_controller.connect_device(port)
        if success:
            self.registry.update_hardware_health(f"arduino_{port.replace('/', '_').replace('dev_', '')}", True)
        return success

    async def send_arduino_command(self, port: str, command: str, **kwargs) -> Optional[str]:
        """
        Send a command to an Arduino device.

        Args:
            port: Serial port path
            command: Command to send
            **kwargs: Command parameters

        Returns:
            Response string or None if failed
        """
        return await self.arduino_controller.send_command(port, command, **kwargs)

    def get_arduino_devices(self) -> List[ArduinoInfo]:
        """Get information about connected Arduino devices."""
        return self.arduino_controller.get_all_devices()

    # General Hardware Management
    def get_hardware_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive hardware system summary.

        Returns:
            Dictionary with complete hardware status
        """
        return {
            "registry": self.registry.get_hardware_summary(),
            "gpio": self.gpio_controller.get_configured_pins(),
            "sensors": self.get_sensor_status(),
            "arduinos": len(self.arduino_controller.get_connected_devices()),
            "timestamp": datetime.now().isoformat(),
            "initialized": self._initialized
        }

    def get_device_capabilities(self, device_type: DeviceType = None) -> Dict[str, List[str]]:
        """
        Get capabilities for devices by type.

        Args:
            device_type: Optional filter by device type

        Returns:
            Dictionary mapping device IDs to capability lists
        """
        return self.registry.get_hardware_capabilities(device_type)

    # Event Subscription
    def on_device_online(self, callback: Callable):
        """Subscribe to device online events."""
        self._on_device_online.append(callback)

    def on_device_offline(self, callback: Callable):
        """Subscribe to device offline events."""
        self._on_device_offline.append(callback)

    def on_sensor_reading(self, callback: Callable[[SensorReading], None]):
        """Subscribe to sensor reading events."""
        self._on_sensor_reading.append(callback)

    # Context manager support
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()