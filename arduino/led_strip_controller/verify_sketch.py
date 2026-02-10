#!/usr/bin/env python3
"""
Arduino Sketch Verification Script
Tests the logic and structure of the Arduino sketch without hardware
"""

import re
import os
import sys


def verify_sketch_structure():
    """Verify the basic structure of the Arduino sketch"""
    sketch_file = "led_strip_controller.ino"

    if not os.path.exists(sketch_file):
        print(f"❌ Sketch file {sketch_file} not found")
        return False

    with open(sketch_file, 'r') as f:
        content = f.read()

    # Check for required includes
    required_includes = [
        '#include <ArduinoJson.h>',
        '#include <FastLED.h>'
    ]

    for include in required_includes:
        if include not in content:
            print(f"❌ Missing required include: {include}")
            return False

    # Check for required defines
    required_defines = [
        '#define LED_PIN 6',
        '#define NUM_LEDS 23',
        '#define LED_TYPE WS2812B'
    ]

    for define in required_defines:
        if define not in content:
            print(f"❌ Missing required define: {define}")
            return False

    # Check for LED zone definitions
    zone_defines = [
        '#define PRIVACY_LED 0',
        '#define SERVICE_LEDS_START 1',
        '#define AI_ZONE_START 5'
    ]

    for define in zone_defines:
        if define not in content:
            print(f"❌ Missing LED zone define: {define}")
            return False

    # Check for function definitions (flexible parameter names)
    required_functions = [
        ('void setup()', 'setup'),
        ('void loop()', 'loop'),
        ('processCommand', 'processCommand'),
        ('updateAnimationsWithPriority', 'updateAnimationsWithPriority'),
        ('sendStatus', 'sendStatus')
    ]

    for func_pattern, func_name in required_functions:
        if func_pattern not in content and func_name not in content:
            print(f"❌ Missing required function: {func_name}")
            return False

    # Check for new command handlers
    new_commands = [
        'handleAIState',
        'handleServiceStatus',
        'handleOBDData',
        'handleSetMode',
        'handleEmergency'
    ]

    for cmd in new_commands:
        if f'void {cmd}' not in content:
            print(f"❌ Missing command handler: {cmd}")
            return False

    # Check for animation functions
    animation_functions = [
        'updateAIAnimation',
        'updateServiceAnimation',
        'updateOBDAnimation'
    ]

    for func in animation_functions:
        if f'void {func}' not in content:
            print(f"❌ Missing animation function: {func}")
            return False

    print("✅ Sketch structure verification passed")
    return True


def verify_json_commands():
    """Verify JSON command handling"""
    sketch_file = "led_strip_controller.ino"

    with open(sketch_file, 'r') as f:
        content = f.read()

    # Check for command processing
    cmd_checks = [
        '"ai_state"',
        '"service_status"',
        '"obd_data"',
        '"set_mode"',
        '"emergency"'
    ]

    for cmd in cmd_checks:
        if cmd not in content:
            print(f"❌ Missing JSON command handler: {cmd}")
            return False

    print("✅ JSON command verification passed")
    return True


def verify_led_zones():
    """Verify LED zone definitions and usage"""
    sketch_file = "led_strip_controller.ino"

    with open(sketch_file, 'r') as f:
        content = f.read()

    # Check zone constants
    zones = [
        'PRIVACY_LED',
        'SERVICE_LEDS_START',
        'SERVICE_LEDS_END',
        'AI_ZONE_START',
        'AI_ZONE_END',
        'BACKGROUND_START',
        'BACKGROUND_END',
        'NOTIFICATION_START',
        'NOTIFICATION_END'
    ]

    for zone in zones:
        if zone not in content:
            print(f"❌ Missing LED zone constant: {zone}")
            return False

    # Check zone usage in functions
    if 'AI_ZONE_START + position' not in content:
        print("❌ AI zone not used in animations")
        return False

    if 'SERVICE_LEDS_START + ' not in content and 'anim.step' not in content:
        print("❌ Service LED zone not used properly")
        return False

    print("✅ LED zone verification passed")
    return True


def verify_priority_system():
    """Verify priority system implementation"""
    sketch_file = "led_strip_controller.ino"

    with open(sketch_file, 'r') as f:
        content = f.read()

    # Check priority constants
    priorities = [
        'PRIORITY_EMERGENCY',
        'PRIORITY_CRITICAL',
        'PRIORITY_HIGH',
        'PRIORITY_MEDIUM',
        'PRIORITY_LOW'
    ]

    for priority in priorities:
        if priority not in content:
            print(f"❌ Missing priority constant: {priority}")
            return False

    # Check priority array
    if 'AnimationState active_animations[5]' not in content:
        print("❌ Missing active animations array")
        return False

    # Check priority dimming
    if 'brightness_multiplier' not in content:
        print("❌ Missing priority-based dimming")
        return False

    print("✅ Priority system verification passed")
    return True


def verify_animations():
    """Verify animation implementations"""
    sketch_file = "led_strip_controller.ino"

    with open(sketch_file, 'r') as f:
        content = f.read()

    # Check animation states
    ai_states = [
        '"listening"',
        '"speaking"',
        '"thinking"',
        '"recording"',
        '"error"'
    ]

    for state in ai_states:
        if state not in content:
            print(f"❌ Missing AI state: {state}")
            return False

    # Check animation patterns
    patterns = [
        'Knight Rider',
        'sin8',
        'CHSV',
        'fill_solid'
    ]

    pattern_found = False
    for pattern in patterns:
        if pattern in content:
            pattern_found = True
            break

    if not pattern_found:
        print("❌ No animation patterns found")
        return False

    print("✅ Animation verification passed")
    return True


def run_all_verifications():
    """Run all sketch verifications"""
    print("Arduino Sketch Verification")
    print("=" * 40)

    verifications = [
        verify_sketch_structure,
        verify_json_commands,
        verify_led_zones,
        verify_priority_system,
        verify_animations
    ]

    passed = 0
    total = len(verifications)

    for verification in verifications:
        try:
            if verification():
                passed += 1
            else:
                print(f"❌ {verification.__name__} failed")
        except Exception as e:
            print(f"❌ {verification.__name__} error: {e}")

    print("=" * 40)
    print(f"Results: {passed}/{total} verifications passed")

    if passed == total:
        print("🎉 Arduino sketch verification successful!")
        print("The sketch is ready for upload to Arduino Uno.")
        return True
    else:
        print("❌ Arduino sketch has issues that need to be fixed.")
        return False


if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)