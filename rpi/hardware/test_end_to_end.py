#!/usr/bin/env python3
"""
End-to-End Test for AI Service LED Monitor
Simulates a complete real-world scenario with all components
"""

import time
import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.led_controller import AIServiceLEDController

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EndToEndTest:
    """Comprehensive end-to-end test scenario"""

    def __init__(self):
        self.controller = None
        self.test_results = []

    def setup(self):
        """Setup test environment"""
        logger.info("Setting up end-to-end test...")
        try:
            from test_led_controller import MockSerialController
            self.controller = MockSerialController()
            logger.info("✅ Mock LED controller initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False

    def test_scenario_1_vehicle_startup(self):
        """Test Scenario 1: Vehicle Startup Sequence"""
        logger.info("\n" + "="*60)
        logger.info("SCENARIO 1: Vehicle Startup Sequence")
        logger.info("="*60)

        steps = [
            ("System boot", lambda: self.controller.clear_all()),
            ("Boot sequence complete", lambda: self.controller.set_mode_drive()),
            ("All services starting", lambda: [
                self.controller.service_running("api"),
                self.controller.service_running("gpio"),
                self.controller.service_running("serial"),
                self.controller.service_running("obd")
            ]),
            ("AI system ready", lambda: self.controller.ai_idle()),
        ]

        for step_name, step_action in steps:
            logger.info(f"  → {step_name}")
            if callable(step_action):
                result = step_action()
            else:
                result = all(step_action)
            
            self.test_results.append(("startup", step_name, result))
            time.sleep(0.2)

        logger.info("✅ Scenario 1 completed")
        return all(r[2] for r in self.test_results if r[0] == "startup")

    def test_scenario_2_ai_conversation(self):
        """Test Scenario 2: AI Conversation Flow"""
        logger.info("\n" + "="*60)
        logger.info("SCENARIO 2: AI Conversation Flow")
        logger.info("="*60)

        steps = [
            ("User speaks - AI listening", lambda: self.controller.ai_listening()),
            ("AI processing - thinking", lambda: self.controller.ai_thinking()),
            ("AI responds - speaking", lambda: self.controller.ai_speaking()),
            ("Conversation ends - idle", lambda: self.controller.ai_idle()),
        ]

        for step_name, step_action in steps:
            logger.info(f"  → {step_name}")
            result = step_action()
            self.test_results.append(("conversation", step_name, result))
            time.sleep(0.5)

        logger.info("✅ Scenario 2 completed")
        return all(r[2] for r in self.test_results if r[0] == "conversation")

    def test_scenario_3_driving_with_obd(self):
        """Test Scenario 3: Driving with OBD Data"""
        logger.info("\n" + "="*60)
        logger.info("SCENARIO 3: Driving with OBD Data Visualization")
        logger.info("="*60)

        # Simulate driving sequence
        rpm_values = [800, 1500, 2500, 3500, 4500, 5500, 6500]
        
        logger.info("  → Vehicle accelerating...")
        for rpm in rpm_values:
            result = self.controller.obd_rpm(rpm)
            self.test_results.append(("driving", f"RPM {rpm}", result))
            time.sleep(0.3)

        logger.info("  → Showing speed")
        speed_values = [0, 30, 60, 90, 120]
        for speed in speed_values:
            result = self.controller.obd_speed(speed)
            self.test_results.append(("driving", f"Speed {speed}", result))
            time.sleep(0.2)

        logger.info("  → Monitoring temperature")
        temp_values = [80, 85, 90, 95, 100]
        for temp in temp_values:
            result = self.controller.obd_temperature(temp)
            self.test_results.append(("driving", f"Temp {temp}", result))
            time.sleep(0.2)

        logger.info("✅ Scenario 3 completed")
        return all(r[2] for r in self.test_results if r[0] == "driving")

    def test_scenario_4_service_health_monitoring(self):
        """Test Scenario 4: Service Health Monitoring"""
        logger.info("\n" + "="*60)
        logger.info("SCENARIO 4: Service Health Monitoring")
        logger.info("="*60)

        services = ["api", "gpio", "serial", "obd", "mqtt", "camera"]
        
        logger.info("  → All services running")
        for service in services:
            result = self.controller.service_running(service)
            self.test_results.append(("health", f"{service} running", result))
        time.sleep(1)

        logger.info("  → API service warning")
        result = self.controller.service_warning("api")
        self.test_results.append(("health", "api warning", result))
        time.sleep(1)

        logger.info("  → OBD service error")
        result = self.controller.service_error("obd")
        self.test_results.append(("health", "obd error", result))
        time.sleep(1)

        logger.info("  → Recovery - services back to normal")
        for service in services:
            result = self.controller.service_running(service)
            self.test_results.append(("health", f"{service} recovered", result))

        logger.info("✅ Scenario 4 completed")
        return all(r[2] for r in self.test_results if r[0] == "health")

    def test_scenario_5_mode_switching(self):
        """Test Scenario 5: Intelligent Mode Switching"""
        logger.info("\n" + "="*60)
        logger.info("SCENARIO 5: Intelligent Mode Switching")
        logger.info("="*60)

        modes = [
            ("Drive mode", lambda: self.controller.set_mode_drive()),
            ("Parked mode", lambda: self.controller.set_mode_parked()),
            ("Night mode", lambda: self.controller.set_mode_night()),
            ("Service mode", lambda: self.controller.set_mode_service()),
            ("Back to drive", lambda: self.controller.set_mode_drive()),
        ]

        for mode_name, mode_action in modes:
            logger.info(f"  → Switching to {mode_name}")
            result = mode_action()
            self.test_results.append(("modes", mode_name, result))
            time.sleep(0.5)

        logger.info("✅ Scenario 5 completed")
        return all(r[2] for r in self.test_results if r[0] == "modes")

    def test_scenario_6_emergency_handling(self):
        """Test Scenario 6: Emergency Handling"""
        logger.info("\n" + "="*60)
        logger.info("SCENARIO 6: Emergency Handling")
        logger.info("="*60)

        steps = [
            ("Normal operation", lambda: self.controller.ai_listening()),
            ("Emergency detected", lambda: self.controller.emergency_activate()),
            ("Emergency cleared", lambda: self.controller.emergency_deactivate()),
            ("System recovery", lambda: self.controller.ai_idle()),
        ]

        for step_name, step_action in steps:
            logger.info(f"  → {step_name}")
            result = step_action()
            self.test_results.append(("emergency", step_name, result))
            time.sleep(0.5)

        logger.info("✅ Scenario 6 completed")
        return all(r[2] for r in self.test_results if r[0] == "emergency")

    def test_scenario_7_complex_interaction(self):
        """Test Scenario 7: Complex Multi-Component Interaction"""
        logger.info("\n" + "="*60)
        logger.info("SCENARIO 7: Complex Multi-Component Interaction")
        logger.info("="*60)

        # Simulate complex real-world scenario
        sequence = [
            ("Driving at highway speed", [
                lambda: self.controller.set_mode_drive(),
                lambda: self.controller.obd_rpm(3000),
                lambda: self.controller.obd_speed(100),
            ]),
            ("AI conversation while driving", [
                lambda: self.controller.ai_listening(),
                lambda: self.controller.ai_thinking(),
                lambda: self.controller.ai_speaking(),
            ]),
            ("Service monitoring active", [
                lambda: self.controller.service_running("api"),
                lambda: self.controller.service_running("obd"),
            ]),
            ("Night mode activation", [
                lambda: self.controller.set_mode_night(),
            ]),
            ("System status check", [
                lambda: self.controller.get_status() is not None,
            ]),
        ]

        for scenario_name, actions in sequence:
            logger.info(f"  → {scenario_name}")
            results = [action() for action in actions]
            all_passed = all(results)
            self.test_results.append(("complex", scenario_name, all_passed))
            time.sleep(0.3)

        logger.info("✅ Scenario 7 completed")
        return all(r[2] for r in self.test_results if r[0] == "complex")

    def generate_report(self):
        """Generate test report"""
        logger.info("\n" + "="*60)
        logger.info("TEST REPORT")
        logger.info("="*60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, _, result in self.test_results if result)
        failed_tests = total_tests - passed_tests

        logger.info(f"Total Test Steps: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        # Group by scenario
        scenarios = {}
        for scenario, step, result in self.test_results:
            if scenario not in scenarios:
                scenarios[scenario] = {"total": 0, "passed": 0}
            scenarios[scenario]["total"] += 1
            if result:
                scenarios[scenario]["passed"] += 1

        logger.info("\nScenario Breakdown:")
        for scenario, stats in scenarios.items():
            rate = (stats["passed"]/stats["total"])*100
            status = "✅" if stats["passed"] == stats["total"] else "❌"
            logger.info(f"  {status} {scenario}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

        if failed_tests == 0:
            logger.info("\n🎉 All end-to-end tests passed!")
            return True
        else:
            logger.error(f"\n❌ {failed_tests} test(s) failed")
            return False

    def run_all_tests(self):
        """Run all end-to-end test scenarios"""
        logger.info("="*60)
        logger.info("AI Service LED Monitor - End-to-End Test Suite")
        logger.info("="*60)

        if not self.setup():
            return False

        scenarios = [
            self.test_scenario_1_vehicle_startup,
            self.test_scenario_2_ai_conversation,
            self.test_scenario_3_driving_with_obd,
            self.test_scenario_4_service_health_monitoring,
            self.test_scenario_5_mode_switching,
            self.test_scenario_6_emergency_handling,
            self.test_scenario_7_complex_interaction,
        ]

        for scenario in scenarios:
            try:
                scenario()
            except Exception as e:
                logger.error(f"Scenario failed with error: {e}")
                return False

        return self.generate_report()


if __name__ == "__main__":
    test = EndToEndTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)