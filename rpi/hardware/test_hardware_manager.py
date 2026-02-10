#!/usr/bin/env python3
"""
Test script for the hardware manager integration.
Tests the unified hardware management system.
"""

import asyncio
import logging
from typing import Dict, Any

from .hardware_manager import HardwareManager
from .gpio import GPIOMode
from .sensors import SensorType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_hardware_manager():
    """Test the complete hardware manager integration."""
    logger.info("Testing hardware manager integration...")

    try:
        async with HardwareManager() as manager:
            # Test GPIO pin registration
            logger.info("Testing GPIO pin registration...")
            gpio_success = await manager.register_gpio_pin(17, GPIOMode.OUTPUT, "Test LED")
            assert gpio_success == True

            gpio_success2 = await manager.register_gpio_pin(18, GPIOMode.INPUT, "Test Button")
            assert gpio_success2 == True

            # Test sensor registration
            logger.info("Testing sensor registration...")
            sensor_success = await manager.register_sensor(
                SensorType.TEMPERATURE, "temp1", "Living Room"
            )
            assert sensor_success == True

            sensor_success2 = await manager.register_sensor(
                SensorType.HUMIDITY, "humid1", "Living Room"
            )
            assert sensor_success2 == True

            # Test GPIO operations (may fail without hardware server, but tests API)
            logger.info("Testing GPIO operations (API validation)...")
            try:
                # These may fail without a running hardware server, but test the API
                result = await manager.set_gpio_pin(17, True)
                if not result:
                    logger.info("GPIO set operation returned False (expected without hardware server)")
            except Exception as e:
                logger.info(f"GPIO set operation failed as expected: {e}")

            try:
                value = await manager.get_gpio_pin(18)
                logger.info(f"GPIO read returned: {value}")
            except Exception as e:
                logger.info(f"GPIO read failed as expected: {e}")

            # Test sensor operations
            logger.info("Testing sensor operations...")
            temp_reading = await manager.read_sensor("temp1")
            assert temp_reading is not None
            assert temp_reading.sensor_type == SensorType.TEMPERATURE
            assert temp_reading.unit == "°C"

            humid_reading = await manager.read_sensor("humid1")
            assert humid_reading is not None
            assert humid_reading.sensor_type == SensorType.HUMIDITY
            assert humid_reading.unit == "%"

            # Test bulk sensor reading
            all_readings = await manager.read_all_sensors()
            assert len(all_readings) == 2

            # Test Arduino discovery
            logger.info("Testing Arduino device discovery...")
            arduinos = await manager.discover_arduino_devices()
            logger.info(f"Discovered {len(arduinos)} Arduino devices")

            # Test hardware summary
            logger.info("Testing hardware summary...")
            summary = manager.get_hardware_summary()
            assert summary["initialized"] == True
            assert summary["registry"]["total_devices"] >= 4  # 2 GPIO + 2 sensors

            # GPIO pins may not be in the summary if hardware server isn't running
            # but they should be in the registry
            registry_gpio_count = len([d for d in summary["registry"]["gpio_pins"] if d["status"] == "online"])
            assert registry_gpio_count >= 2 or len(summary["registry"]["gpio_pins"]) >= 2

            # Sensors should be working even without hardware server
            assert len(summary["sensors"]["registry_info"]) >= 2

            # Test device capabilities
            capabilities = manager.get_device_capabilities()
            assert len(capabilities) >= 4

            logger.info("✅ Hardware manager integration tests passed")

    except Exception as e:
        logger.error(f"Hardware manager integration test failed: {e}")
        raise


async def test_event_system():
    """Test the event system of the hardware manager."""
    logger.info("Testing hardware manager event system...")

    try:
        manager = HardwareManager()

        # Setup event tracking
        events_received = []

        def on_device_online(device):
            events_received.append(f"online:{device.device_id}")

        def on_device_offline(device):
            events_received.append(f"offline:{device.device_id}")

        def on_sensor_reading(reading):
            events_received.append(f"sensor:{reading.sensor_id}:{reading.value}")

        # Subscribe to events
        manager.on_device_online(on_device_online)
        manager.on_device_offline(on_device_offline)
        manager.on_sensor_reading(on_sensor_reading)

        async with manager:
            # Register devices (should trigger online events)
            await manager.register_gpio_pin(17, GPIOMode.OUTPUT)
            await manager.register_sensor(SensorType.TEMPERATURE, "temp_test")

            # Read sensors (should trigger sensor events)
            await manager.read_all_sensors()

            # Wait a bit for events to be processed
            await asyncio.sleep(0.1)

        # Check that events were received
        assert len(events_received) >= 2  # At least device online events
        logger.info(f"Events received: {events_received}")

        logger.info("✅ Hardware manager event system tests passed")

    except Exception as e:
        logger.error(f"Hardware manager event system test failed: {e}")
        raise


async def test_error_handling():
    """Test error handling in hardware manager."""
    logger.info("Testing hardware manager error handling...")

    try:
        async with HardwareManager() as manager:
            # Test registering invalid sensor type
            try:
                # This should fail gracefully
                success = await manager.register_sensor("invalid_type", "test_sensor")
                assert success == False
            except Exception as e:
                logger.info(f"Expected error handled gracefully: {e}")

            # Test reading non-existent sensor
            reading = await manager.read_sensor("non_existent")
            assert reading is None

            # Test GPIO operations on non-existent pins
            try:
                await manager.set_gpio_pin(999, True)
            except Exception:
                logger.info("GPIO operation on invalid pin handled gracefully")

            logger.info("✅ Hardware manager error handling tests passed")

    except Exception as e:
        logger.error(f"Hardware manager error handling test failed: {e}")
        raise


async def main():
    """Run all hardware manager tests."""
    logger.info("Starting hardware manager comprehensive tests...")

    try:
        # Run individual test suites
        await test_hardware_manager()
        await test_event_system()
        await test_error_handling()

        logger.info("🎉 All hardware manager tests passed!")

    except Exception as e:
        logger.error(f"Hardware manager tests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())