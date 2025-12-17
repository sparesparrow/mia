#!/usr/bin/env python3
"""
Test script for the hardware abstraction layer.
Tests GPIO controller, sensor manager, and Arduino communication.
"""

import asyncio
import logging
import time
from typing import Dict, Any

from .gpio import GPIOController, GPIOMode
from .sensors import SensorManager, MockTemperatureSensor, MockHumiditySensor, SensorType
from .arduino import ArduinoController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_gpio_controller():
    """Test GPIO controller with mock hardware server."""
    logger.info("Testing GPIO controller...")

    try:
        # Note: This test requires a running hardware server
        # For now, we'll test the client-side logic without actual server
        gpio = GPIOController()

        # Test basic functionality (will fail without server, but tests API)
        logger.info("GPIO controller created successfully")

        # Test pin configuration validation
        assert gpio.is_pin_configured(17) == False
        assert gpio.get_pin_mode(17) is None

        logger.info("✅ GPIO controller tests passed (API validation)")

    except Exception as e:
        logger.error(f"GPIO controller test failed: {e}")
        raise


async def test_sensor_manager():
    """Test sensor manager with mock sensors."""
    logger.info("Testing sensor manager...")

    try:
        # Create sensor manager
        manager = SensorManager()

        # Add mock sensors
        temp_sensor = MockTemperatureSensor("temp1", 22.5)
        humidity_sensor = MockHumiditySensor("humid1", 55.0)

        success1 = await manager.add_sensor(temp_sensor)
        success2 = await manager.add_sensor(humidity_sensor)

        assert success1 == True
        assert success2 == True

        # Test individual sensor reading
        temp_reading = await manager.read_sensor("temp1")
        assert temp_reading is not None
        assert temp_reading.sensor_type == SensorType.TEMPERATURE
        assert temp_reading.unit == "°C"
        assert 0 <= temp_reading.value <= 50  # Reasonable temperature range

        humidity_reading = await manager.read_sensor("humid1")
        assert humidity_reading is not None
        assert humidity_reading.sensor_type == SensorType.HUMIDITY
        assert humidity_reading.unit == "%"
        assert 0 <= humidity_reading.value <= 100  # Valid humidity range

        # Test reading all sensors
        all_readings = await manager.read_all_sensors()
        assert len(all_readings) == 2

        # Test reading by type
        temp_readings = await manager.read_sensors_by_type(SensorType.TEMPERATURE)
        assert len(temp_readings) == 1

        humidity_readings = await manager.read_sensors_by_type(SensorType.HUMIDITY)
        assert len(humidity_readings) == 1

        # Test sensor status
        status = manager.get_sensor_status()
        assert len(status) == 2
        assert status["temp1"]["healthy"] == True
        assert status["humid1"]["healthy"] == True

        # Test sensor removal
        removed = await manager.remove_sensor("temp1")
        assert removed == True
        assert len(manager.get_all_sensors()) == 1

        # Cleanup
        await manager.shutdown_all_sensors()

        logger.info("✅ Sensor manager tests passed")

    except Exception as e:
        logger.error(f"Sensor manager test failed: {e}")
        raise


async def test_arduino_controller():
    """Test Arduino controller device discovery."""
    logger.info("Testing Arduino controller...")

    try:
        controller = ArduinoController()

        # Test device discovery (may find real devices or none)
        devices = await controller.discover_devices()
        logger.info(f"Discovered {len(devices)} Arduino devices")

        # Test device info retrieval
        for device in devices:
            logger.info(f"Device: {device.port} - {device.board_type}")
            assert device.port
            assert device.board_type

        # Test controller lifecycle
        await controller.start()

        # Test getting device status for non-existent device
        status = controller.get_device_status("/dev/ttyACM0")
        logger.info(f"Status for non-existent device: {status}")

        await controller.stop()

        logger.info("✅ Arduino controller tests passed")

    except Exception as e:
        logger.error(f"Arduino controller test failed: {e}")
        raise


async def test_integration():
    """Test integration between components."""
    logger.info("Testing hardware integration...")

    try:
        # Create components
        sensor_manager = SensorManager()

        # Add multiple sensors
        sensors = [
            MockTemperatureSensor("temp1"),
            MockTemperatureSensor("temp2"),
            MockHumiditySensor("humid1"),
            MockHumiditySensor("humid2"),
        ]

        for sensor in sensors:
            success = await sensor_manager.add_sensor(sensor)
            assert success == True

        # Test batch operations
        readings = await sensor_manager.read_all_sensors()
        assert len(readings) == 4

        # Test sensor health
        status = sensor_manager.get_sensor_status()
        healthy_count = sum(1 for s in status.values() if s["healthy"])
        assert healthy_count == 4

        # Test context manager
        async with sensor_manager:
            readings = await sensor_manager.read_all_sensors()
            assert len(readings) == 4

        # After context manager, sensors should be cleaned up
        assert len(sensor_manager.get_all_sensors()) == 0

        logger.info("✅ Hardware integration tests passed")

    except Exception as e:
        logger.error(f"Hardware integration test failed: {e}")
        raise


async def run_performance_test():
    """Run performance test for sensor reading."""
    logger.info("Running performance test...")

    try:
        manager = SensorManager()

        # Add many sensors
        for i in range(10):
            sensor = MockTemperatureSensor(f"temp{i}")
            await manager.add_sensor(sensor)

        # Measure reading performance
        start_time = time.time()

        for _ in range(100):  # 100 batches
            readings = await manager.read_all_sensors()
            assert len(readings) == 10

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_batch = total_time / 100
        readings_per_second = 1000 / avg_time_per_batch

        logger.info(f"Performance: {readings_per_second:.1f} sensor readings/second")
        logger.info(f"Average batch time: {avg_time_per_batch:.3f} seconds")

        await manager.shutdown_all_sensors()

        logger.info("✅ Performance test passed")

    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        raise


async def main():
    """Run all hardware tests."""
    logger.info("Starting hardware abstraction layer tests...")

    try:
        # Run individual component tests
        await test_gpio_controller()
        await test_sensor_manager()
        await test_arduino_controller()

        # Run integration tests
        await test_integration()

        # Run performance tests
        await run_performance_test()

        logger.info("🎉 All hardware tests passed!")

    except Exception as e:
        logger.error(f"Hardware tests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())