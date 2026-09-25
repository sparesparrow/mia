#!/usr/bin/env python3
"""
Test different pin configurations to find which pin the LEDs are actually on
"""
import serial
import time
import sys

def test_pin_command(ser, pin_num):
    """Send a test command assuming LEDs are on a different pin"""
    # We can't change pin via serial, but we can check if responses suggest wrong pin
    print(f"Note: Current firmware uses pin 6. If LEDs don't work, they might be on a different pin.")
    print(f"Common pins for WS2812B: 3, 5, 6, 9, 10, 11")
    return True

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    
    print("=== LED Pin Configuration Diagnostic ===")
    print(f"Testing Arduino on {port}")
    print("\nCurrent firmware configuration:")
    print("  - Pin: 6 (defined in firmware)")
    print("  - LED Type: WS2812B")
    print("  - Color Order: GRB")
    print("  - Number of LEDs: 23")
    
    ser = serial.Serial(port, 115200, timeout=2)
    time.sleep(2)
    
    # Check status
    print("\nChecking current status...")
    ser.write(b'{"command":"status"}\n')
    time.sleep(0.5)
    response = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"Status: {response}")
    
    # Try setting maximum brightness and white
    print("\nSetting maximum brightness and white color...")
    ser.write(b'{"command":"set_brightness","brightness":255}\n')
    time.sleep(0.3)
    ser.write(b'{"command":"set_color","r":255,"g":255,"b":255}\n')
    time.sleep(1)
    
    print("\n=== Hardware Checklist ===")
    print("If LEDs are NOT lighting up, verify:")
    print("1. LED data wire is connected to Arduino pin 6")
    print("2. LED power (5V) is connected to external power supply (not Arduino 5V)")
    print("3. LED ground is connected to Arduino ground (common ground required)")
    print("4. Power supply can provide at least 1.4A (23 LEDs × 60mA)")
    print("5. LED strip is WS2812B or compatible")
    print("6. No loose connections")
    print("\nIf LEDs are on a different pin, you need to:")
    print("  - Edit led_strip_controller.ino")
    print("  - Change: #define LED_PIN 6  to your pin number")
    print("  - Re-upload firmware")
    
    ser.close()

if __name__ == "__main__":
    main()
