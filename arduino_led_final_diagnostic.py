#!/usr/bin/env python3
"""
Final LED Diagnostic - Comprehensive hardware test
"""
import serial
import serial.tools.list_ports
import time
import json
import sys
import os

def find_arduino_port():
    """Auto-detect Arduino port"""
    # First check if port was specified
    if len(sys.argv) > 1:
        port = sys.argv[1]
        if os.path.exists(port):
            return port
        else:
            print(f"Specified port {port} does not exist")
    
    # List all available ports
    ports = serial.tools.list_ports.comports()
    if not ports:
        return None
    
    print("Available serial ports:")
    for p in ports:
        print(f"  - {p.device}: {p.description}")
    
    # Try to find Arduino-like port
    arduino_keywords = ["arduino", "uno", "usb", "serial"]
    for p in ports:
        desc_lower = (p.description or "").lower()
        if any(keyword in desc_lower for keyword in arduino_keywords):
            print(f"\nAuto-selected: {p.device} ({p.description})")
            return p.device
    
    # Fallback to first USB serial port
    for p in ports:
        if "ttyUSB" in p.device or "ttyACM" in p.device:
            print(f"\nAuto-selected: {p.device} ({p.description})")
            return p.device
    
    # Last resort: first port
    if ports:
        print(f"\nUsing first available port: {ports[0].device}")
        return ports[0].device
    
    return None

def main():
    port = find_arduino_port()
    
    if not port:
        print("ERROR: No serial port found!")
        print("\nPlease:")
        print("  1. Connect Arduino via USB")
        print("  2. Check: ls -l /dev/ttyUSB* /dev/ttyACM*")
        print("  3. Specify port manually: python arduino_led_final_diagnostic.py /dev/ttyUSB0")
        sys.exit(1)
    
    print("=" * 60)
    print("ARDUINO LED FINAL DIAGNOSTIC")
    print("=" * 60)
    print(f"Using port: {port}")
    print()
    
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        print("Step 1: Checking Arduino communication...")
        ser.write(b'{"command":"status"}\n')
        time.sleep(0.5)
        response = ser.readline().decode('utf-8', errors='ignore').strip()
        try:
            status = json.loads(response)
            print(f"  ✓ Arduino responding")
            print(f"  - Brightness: {status.get('brightness')}")
            print(f"  - LEDs configured: {status.get('num_leds')}")
            print(f"  - Current color: {status.get('current_color')}")
        except:
            print(f"  ✗ Invalid response: {response}")
            ser.close()
            return
        
        print()
        print("Step 2: Setting maximum brightness (255)...")
        ser.write(b'{"command":"set_brightness","brightness":255}\n')
        ser.flush()
        time.sleep(0.5)
        # Read and discard any buffered responses
        while ser.in_waiting > 0:
            response = ser.readline().decode('utf-8', errors='ignore').strip()
            if response:
                try:
                    data = json.loads(response)
                    if data.get('status') == 'brightness_set':
                        print(f"  ✓ Brightness set to: {data.get('brightness')}")
                        break
                except:
                    pass
        
        print()
        print("Step 3: Setting bright RED (255,0,0)...")
        print("  >>> WATCH THE LEDs NOW <<<")
        ser.reset_input_buffer()  # Clear any buffered data
        ser.write(b'{"command":"set_color","r":255,"g":0,"b":0}\n')
        ser.flush()
        time.sleep(1)
        response = ser.readline().decode('utf-8', errors='ignore').strip()
        if response:
            try:
                data = json.loads(response)
                print(f"  ✓ Command acknowledged: {data.get('message', 'OK')}")
            except:
                print(f"  Response: {response[:80]}...")
        print("  Did LEDs light up RED? (y/n)")
        
        print()
        print("Step 4: Setting bright WHITE (255,255,255)...")
        ser.reset_input_buffer()
        ser.write(b'{"command":"set_color","r":255,"g":255,"b":255}\n')
        ser.flush()
        time.sleep(1)
        response = ser.readline().decode('utf-8', errors='ignore').strip()
        if response:
            try:
                data = json.loads(response)
                print(f"  ✓ Command acknowledged: {data.get('message', 'OK')}")
            except:
                print(f"  Response: {response[:80]}...")
        print("  Did LEDs light up WHITE? (y/n)")
        
        print()
        print("Step 5: Running hardware test sequence...")
        print("  >>> WATCH THE LEDs - Should cycle: White->Red->Green->Blue->Chase->Off <<<")
        ser.reset_input_buffer()
        ser.write(b'{"command":"hardware_test"}\n')
        ser.flush()
        time.sleep(4)  # Wait for test sequence to complete
        response = ser.readline().decode('utf-8', errors='ignore').strip()
        if response:
            try:
                data = json.loads(response)
                print(f"  ✓ Test complete: {data.get('message', 'OK')}")
            except:
                print(f"  Response: {response[:80]}...")
        print("  Did you see the LED sequence? (y/n)")
        
        print()
        print("=" * 60)
        print("DIAGNOSIS SUMMARY")
        print("=" * 60)
        print()
        print("If Arduino responds but LEDs DON'T light up:")
        print("  ✗ HARDWARE CONNECTION ISSUE")
        print()
        print("Check:")
        print("  1. LED data wire connected to Arduino PIN 6?")
        print("  2. LED power (5V) connected to EXTERNAL 2A+ supply?")
        print("  3. LED ground connected to Arduino ground?")
        print("  4. Power supply provides sufficient current?")
        print("  5. Try different pin (3, 5, 9, 10, 11) using pin_test.ino")
        print()
        print("If LEDs DO light up:")
        print("  ✓ Hardware is working!")
        print("  ✓ Issue was likely brightness or timing")
        print()
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
        print("  Check: Arduino connected? Port correct? Permissions?")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    main()
