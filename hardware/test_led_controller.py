#!/usr/bin/env python3
"""
Test script for AI Service LED Controller
Tests serial communication, JSON commands, and basic functionality
"""

import json
import time
import logging
import sys
import os
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from led_controller import AIServiceLEDController

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockSerialController(AIServiceLEDController):
    """
    Mock controller for testing without hardware
    Simulates Arduino responses for testing
    """

    def __init__(self):
        super().__init__(port="mock", baud_rate=115200)
        self.connected = True
        self.mock_responses = {
            "status": {
                "status": "ok",
                "message": "Status request",
                "brightness": 128,
                "mode": "drive",
                "emergency_override": False,
                "num_leds": 23,
                "active_animations": []
            },
            "ai_state": {
                "status": "ai_state_set",
                "message": "AI state set to: listening (priority 1)"
            },
            "service_status": {
                "status": "service_status_set",
                "message": "Service obd status: error (priority 0)"
            },
            "obd_data": {
                "status": "obd_data_set",
                "message": "OBD rpm data: 50/100"
            },
            "set_mode": {
                "status": "mode_set",
                "message": "Mode changed to: drive (brightness: 128)"
            },
            "emergency": {
                "status": "emergency_activate",
                "message": "Emergency override activated"
            },
            "emergency_deactivate": {
                "status": "emergency_deactivate",
                "message": "Emergency override deactivated"
            },
            "clear": {
                "status": "cleared",
                "message": "All LEDs cleared"
            },
            "set_brightness": {
                "status": "brightness_set",
                "message": "Brightness set to 128"
            }
        }

    def _send_command(self, cmd_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mock command sending that returns predefined responses"""
        cmd = cmd_dict.get("cmd", "")
        action = cmd_dict.get("action", "")

        # Handle emergency command with action parameter
        if cmd == "emergency":
            if action == "activate":
                response = self.mock_responses.get("emergency_activate", {
                    "status": "emergency_activate",
                    "message": "Emergency override activated"
                })
            elif action == "deactivate":
                response = self.mock_responses.get("emergency_deactivate", {
                    "status": "emergency_deactivate",
                    "message": "Emergency override deactivated"
                })
            else:
                response = {
                    "status": "error",
                    "error_type": "invalid_action",
                    "message": f"Invalid emergency action: {action}"
                }
        else:
            response = self.mock_responses.get(cmd, {
                "status": "error",
                "error_type": "unknown_command",
                "message": f"Unknown command: {cmd}"
            })

        # Simulate serial delay
        time.sleep(0.05)
        logger.debug(f"Mock command: {cmd_dict} -> {response}")
        return response


def test_json_protocol():
    """Test JSON command formatting and parsing"""
    logger.info("Testing JSON protocol...")

    # Test command creation
    test_commands = [
        {"cmd": "ai_state", "state": "listening", "priority": 1},
        {"cmd": "service_status", "service": "obd", "status": "error", "priority": 0},
        {"cmd": "obd_data", "type": "rpm", "value": 75},
        {"cmd": "set_mode", "mode": "drive"},
        {"cmd": "emergency", "action": "activate"}
    ]

    for cmd in test_commands:
        json_str = json.dumps(cmd) + '\n'
        # Verify it's valid JSON
        parsed = json.loads(json_str.strip())
        assert parsed == cmd, f"JSON round-trip failed for {cmd}"

    logger.info("✓ JSON protocol test passed")


def test_ai_state_commands(controller):
    """Test AI state command methods"""
    logger.info("Testing AI state commands...")

    # Test all AI states
    states = ['listening', 'speaking', 'thinking', 'recording', 'error']
    for state in states:
        method_name = f'ai_{state}'
        method = getattr(controller, method_name)
        result = method()
        assert result == True, f"AI state {state} command failed"

        # Verify response
        response = controller.get_status()
        assert response is not None, "Status request failed"
        assert "active_animations" in response, "Active animations not in status"

    # Test idle
    result = controller.ai_idle()
    assert result == True, "AI idle command failed"

    logger.info("✓ AI state commands test passed")


def test_service_status_commands(controller):
    """Test service status command methods"""
    logger.info("Testing service status commands...")

    services = ['api', 'gpio', 'serial', 'obd', 'mqtt', 'camera']
    statuses = ['running', 'warning', 'error', 'stopped']

    for service in services:
        for status in statuses:
            method_name = f'service_{status}'
            method = getattr(controller, method_name)
            result = method(service)
            assert result == True, f"Service {service} {status} command failed"

    logger.info("✓ Service status commands test passed")


def test_obd_data_commands(controller):
    """Test OBD data command methods"""
    logger.info("Testing OBD data commands...")

    # Test RPM
    result = controller.obd_rpm(3500, 8000)
    assert result == True, "OBD RPM command failed"

    # Test speed
    result = controller.obd_speed(120, 200)
    assert result == True, "OBD speed command failed"

    # Test temperature
    result = controller.obd_temperature(85, 120)
    assert result == True, "OBD temperature command failed"

    # Test load
    result = controller.obd_load(75)
    assert result == True, "OBD load command failed"

    logger.info("✓ OBD data commands test passed")


def test_mode_commands(controller):
    """Test mode switching commands"""
    logger.info("Testing mode commands...")

    modes = ['drive', 'parked', 'night', 'service']
    for mode in modes:
        method_name = f'set_mode_{mode}'
        method = getattr(controller, method_name)
        result = method()
        assert result == True, f"Mode {mode} command failed"

    logger.info("✓ Mode commands test passed")


def test_emergency_commands(controller):
    """Test emergency override commands"""
    logger.info("Testing emergency commands...")

    # Test activate
    result = controller.emergency_activate()
    assert result == True, "Emergency activate command failed"

    # Test deactivate
    result = controller.emergency_deactivate()
    assert result == True, "Emergency deactivate command failed"

    logger.info("✓ Emergency commands test passed")


def test_utility_commands(controller):
    """Test utility commands"""
    logger.info("Testing utility commands...")

    # Test clear
    result = controller.clear_all()
    assert result == True, "Clear command failed"

    # Test brightness
    result = controller.set_brightness(200)
    assert result == True, "Brightness command failed"

    # Test status
    status = controller.get_status()
    assert status is not None, "Status command failed"
    assert status.get("status") == "ok", "Status response invalid"

    logger.info("✓ Utility commands test passed")


def test_integration_scenario(controller):
    """Test a realistic integration scenario"""
    logger.info("Testing integration scenario...")

    # Simulate a typical AI service session
    sequence = [
        ("AI starts listening", lambda: controller.ai_listening()),
        ("OBD error occurs", lambda: controller.service_error("obd", 0)),
        ("AI starts speaking", lambda: controller.ai_speaking()),
        ("Show RPM bargraph", lambda: controller.obd_rpm(4200)),
        ("Switch to night mode", lambda: controller.set_mode_night()),
        ("Emergency situation", lambda: controller.emergency_activate()),
        ("Clear emergency", lambda: controller.emergency_deactivate()),
        ("Clear all", lambda: controller.clear_all())
    ]

    for description, action in sequence:
        logger.info(f"  - {description}")
        result = action()
        assert result == True, f"Failed: {description}"
        time.sleep(0.1)  # Small delay between commands

    logger.info("✓ Integration scenario test passed")


def run_all_tests():
    """Run all tests"""
    logger.info("Starting AI Service LED Controller Tests")
    logger.info("=" * 50)

    # Create mock controller for testing
    controller = MockSerialController()

    try:
        # Basic protocol tests
        test_json_protocol()

        # Command method tests
        test_ai_state_commands(controller)
        test_service_status_commands(controller)
        test_obd_data_commands(controller)
        test_mode_commands(controller)
        test_emergency_commands(controller)
        test_utility_commands(controller)

        # Integration test
        test_integration_scenario(controller)

        logger.info("=" * 50)
        logger.info("🎉 All tests passed! AI Service LED Controller is ready.")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)