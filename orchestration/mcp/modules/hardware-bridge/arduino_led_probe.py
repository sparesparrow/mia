#!/usr/bin/env python3
"""
Test script for Arduino LED Controller

Tests basic functionality of the Arduino LED controller.
Requires Arduino to be connected and LED strip controller code uploaded.
"""

import sys
import time
import logging
from arduino_led_controller import ArduinoLEDController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_operations(controller: ArduinoLEDController):
    """Test basic LED operations"""
    logger.info("Testing basic operations...")
    
    # Test 1: Set color
    logger.info("Test 1: Setting all LEDs to red")
    assert controller.set_color(255, 0, 0), "Failed to set color"
    time.sleep(1)
    
    # Test 2: Set brightness
    logger.info("Test 2: Setting brightness to 64")
    assert controller.set_brightness(64), "Failed to set brightness"
    time.sleep(1)
    
    # Test 3: Set individual LED
    logger.info("Test 3: Setting LED 5 to yellow")
    assert controller.set_led(5, 255, 255, 0), "Failed to set individual LED"
    time.sleep(1)
    
    # Test 4: Clear
    logger.info("Test 4: Clearing all LEDs")
    assert controller.clear(), "Failed to clear LEDs"
    time.sleep(1)
    
    logger.info("✓ Basic operations test passed")


def test_animations(controller: ArduinoLEDController):
    """Test animations"""
    logger.info("Testing animations...")
    
    # Test rainbow
    logger.info("Test: Starting rainbow animation")
    assert controller.start_rainbow(speed=20), "Failed to start rainbow"
    time.sleep(3)
    
    # Test chase
    logger.info("Test: Starting chase animation")
    assert controller.start_chase(0, 255, 0, speed=100), "Failed to start chase"
    time.sleep(3)
    
    # Test blink
    logger.info("Test: Starting blink animation")
    assert controller.start_animation("blink", speed=500), "Failed to start blink"
    time.sleep(3)
    
    # Clear
    controller.clear()
    logger.info("✓ Animations test passed")


def test_status(controller: ArduinoLEDController):
    """Test status retrieval"""
    logger.info("Testing status retrieval...")
    
    status = controller.get_status()
    assert status is not None, "Failed to get status"
    assert "brightness" in status, "Status missing brightness"
    assert "current_color" in status, "Status missing current_color"
    assert "num_leds" in status, "Status missing num_leds"
    
    logger.info(f"Status: {status}")
    logger.info("✓ Status test passed")


def main():
    """Main test function"""
    serial_port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    
    logger.info(f"Connecting to Arduino on {serial_port}...")
    controller = ArduinoLEDController(serial_port=serial_port)
    
    if not controller.connect():
        logger.error("Failed to connect to Arduino")
        sys.exit(1)
    
    try:
        logger.info("Connected! Starting tests...")
        
        # Run tests
        test_basic_operations(controller)
        test_animations(controller)
        test_status(controller)
        
        logger.info("\n✓ All tests passed!")
        
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        controller.clear()
        controller.disconnect()
        logger.info("Disconnected from Arduino")


if __name__ == "__main__":
    main()
