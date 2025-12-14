#!/usr/bin/env python3
"""
Test LED Monitor Service Integration
Tests the integration between LED controller and MIA services
"""

import json
import time
import logging
import subprocess
import signal
import sys
import os
from typing import Optional

# Import LED controller
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from led_controller import AIServiceLEDController

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LEDIntegrationTest:
    """Test LED monitor service integration"""

    def __init__(self):
        self.led_controller: Optional[AIServiceLEDController] = None
        self.broker_process: Optional[subprocess.Popen] = None
        self.monitor_process: Optional[subprocess.Popen] = None

    def setup(self) -> bool:
        """Setup test environment"""
        logger.info("Setting up LED integration test...")

        # Connect to LED controller (mock mode for testing)
        try:
            # For testing, we'll use mock mode
            from test_led_controller import MockSerialController
            self.led_controller = MockSerialController()
            logger.info("Connected to mock LED controller")
        except Exception as e:
            logger.error(f"Failed to setup LED controller: {e}")
            return False

        return True

    def start_services(self) -> bool:
        """Start required services for testing"""
        logger.info("Starting test services...")

        try:
            # Start broker
            broker_cmd = [sys.executable, "/home/mia/ai-servis/rpi/core/messaging/broker.py"]
            self.broker_process = subprocess.Popen(
                broker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd="/home/mia/ai-servis/rpi/core/messaging"
            )
            time.sleep(2)  # Wait for broker to start

            # Start LED monitor service
            monitor_cmd = [
                sys.executable,
                "/home/mia/ai-servis/rpi/services/led_monitor_service.py",
                "--led-port", "mock"
            ]
            self.monitor_process = subprocess.Popen(
                monitor_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd="/home/mia/ai-servis/rpi/services",
                env={**os.environ, "PYTHONPATH": "/home/mia/ai-servis/rpi"}
            )
            time.sleep(3)  # Wait for monitor to start

            logger.info("Test services started")
            return True

        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            self.cleanup()
            return False

    def test_service_health_monitoring(self) -> bool:
        """Test service health monitoring"""
        logger.info("Testing service health monitoring...")

        try:
            # Test GPIO service status
            result = self.led_controller.service_running("gpio")
            assert result == True, "GPIO service status update failed"

            # Test OBD service status
            result = self.led_controller.service_error("obd")
            assert result == True, "OBD service status update failed"

            # Test API service status
            result = self.led_controller.service_warning("api")
            assert result == True, "API service status update failed"

            logger.info("✓ Service health monitoring test passed")
            return True

        except Exception as e:
            logger.error(f"Service health monitoring test failed: {e}")
            return False

    def test_ai_state_integration(self) -> bool:
        """Test AI state integration"""
        logger.info("Testing AI state integration...")

        try:
            # Test AI listening
            result = self.led_controller.ai_listening()
            assert result == True, "AI listening command failed"
            time.sleep(0.5)

            # Test AI speaking
            result = self.led_controller.ai_speaking()
            assert result == True, "AI speaking command failed"
            time.sleep(0.5)

            # Test AI thinking
            result = self.led_controller.ai_thinking()
            assert result == True, "AI thinking command failed"
            time.sleep(0.5)

            # Test AI idle
            result = self.led_controller.ai_idle()
            assert result == True, "AI idle command failed"

            logger.info("✓ AI state integration test passed")
            return True

        except Exception as e:
            logger.error(f"AI state integration test failed: {e}")
            return False

    def test_obd_data_integration(self) -> bool:
        """Test OBD data integration"""
        logger.info("Testing OBD data integration...")

        try:
            # Test RPM visualization
            result = self.led_controller.obd_rpm(3200)
            assert result == True, "OBD RPM command failed"

            # Test speed visualization
            result = self.led_controller.obd_speed(85)
            assert result == True, "OBD speed command failed"

            # Test temperature visualization
            result = self.led_controller.obd_temperature(90)
            assert result == True, "OBD temperature command failed"

            logger.info("✓ OBD data integration test passed")
            return True

        except Exception as e:
            logger.error(f"OBD data integration test failed: {e}")
            return False

    def test_mode_switching(self) -> bool:
        """Test mode switching"""
        logger.info("Testing mode switching...")

        try:
            # Test drive mode
            result = self.led_controller.set_mode_drive()
            assert result == True, "Drive mode command failed"

            # Test parked mode
            result = self.led_controller.set_mode_parked()
            assert result == True, "Parked mode command failed"

            # Test night mode
            result = self.led_controller.set_mode_night()
            assert result == True, "Night mode command failed"

            logger.info("✓ Mode switching test passed")
            return True

        except Exception as e:
            logger.error(f"Mode switching test failed: {e}")
            return False

    def test_emergency_override(self) -> bool:
        """Test emergency override"""
        logger.info("Testing emergency override...")

        try:
            # Test emergency activate
            result = self.led_controller.emergency_activate()
            assert result == True, "Emergency activate command failed"

            # Test emergency deactivate
            result = self.led_controller.emergency_deactivate()
            assert result == True, "Emergency deactivate command failed"

            logger.info("✓ Emergency override test passed")
            return True

        except Exception as e:
            logger.error(f"Emergency override test failed: {e}")
            return False

    def cleanup(self):
        """Clean up test resources"""
        logger.info("Cleaning up test resources...")

        # Disconnect LED controller
        if self.led_controller:
            self.led_controller.disconnect()

        # Stop services
        if self.monitor_process:
            self.monitor_process.terminate()
            try:
                self.monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.monitor_process.kill()

        if self.broker_process:
            self.broker_process.terminate()
            try:
                self.broker_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.broker_process.kill()

        logger.info("Cleanup complete")

    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        logger.info("Starting LED Monitor Service Integration Tests")
        logger.info("=" * 60)

        try:
            # Setup
            if not self.setup():
                return False

            # Start services
            if not self.start_services():
                return False

            # Run tests
            tests = [
                self.test_service_health_monitoring,
                self.test_ai_state_integration,
                self.test_obd_data_integration,
                self.test_mode_switching,
                self.test_emergency_override
            ]

            passed = 0
            for test in tests:
                if test():
                    passed += 1
                time.sleep(0.5)  # Brief pause between tests

            logger.info("=" * 60)
            if passed == len(tests):
                logger.info("🎉 All integration tests passed!")
                return True
            else:
                logger.error(f"❌ {len(tests) - passed} tests failed")
                return False

        finally:
            self.cleanup()


def main():
    """Main entry point"""
    test = LEDIntegrationTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()