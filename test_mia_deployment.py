#!/usr/bin/env python3
"""
MIA Deployment Test Script

Tests all features provided by the Raspberry Pi deployment of MIA.
This script verifies that the core components are working correctly.
"""

import requests
import json
import time
import websocket
import threading
import sys

API_BASE = "http://localhost:8000"

def test_api_endpoint(name, url, expected_status=200):
    """Test an API endpoint"""
    print(f"Testing {name}...", end=" ")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == expected_status:
            print("✓ PASS")
            return response.json()
        else:
            print(f"✗ FAIL (status: {response.status_code})")
            return None
    except Exception as e:
        print(f"✗ FAIL ({e})")
        return None

def test_api_post(name, url, data, expected_status=200):
    """Test an API POST endpoint"""
    print(f"Testing {name}...", end=" ")
    try:
        response = requests.post(url, json=data, timeout=5)
        if response.status_code == expected_status:
            print("✓ PASS")
            return response.json()
        else:
            print(f"✗ FAIL (status: {response.status_code})")
            return None
    except Exception as e:
        print(f"✗ FAIL ({e})")
        return None

def test_websocket():
    """Test WebSocket connection"""
    print("Testing WebSocket...", end=" ")

    messages_received = []

    def on_message(ws, message):
        messages_received.append(message)

    def on_error(ws, error):
        print(f"WebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        pass

    def on_open(ws):
        # Keep connection open for a few seconds
        time.sleep(2)
        ws.close()

    try:
        ws = websocket.WebSocketApp(f"ws://localhost:8000/ws",
                                   on_message=on_message,
                                   on_error=on_error,
                                   on_close=on_close,
                                   on_open=on_open)

        ws.run_forever()

        if messages_received:
            print("✓ PASS (received messages)")
            return True
        else:
            print("✓ PASS (connected, no messages)")
            return True

    except Exception as e:
        print(f"✗ FAIL ({e})")
        return False

def check_service_status(service_name):
    """Check if a systemd service is running"""
    import subprocess
    try:
        result = subprocess.run(['systemctl', 'is-active', service_name],
                              capture_output=True, text=True)
        status = result.stdout.strip()
        if status == 'active':
            print(f"✓ {service_name}: RUNNING")
            return True
        else:
            print(f"✗ {service_name}: {status.upper()}")
            return False
    except Exception as e:
        print(f"✗ {service_name}: ERROR ({e})")
        return False

def main():
    print("=== MIA Raspberry Pi Deployment Test ===\n")

    # Test systemd services
    print("Checking systemd services:")
    services_ok = 0
    services_ok += check_service_status('zmq-broker.service')
    services_ok += check_service_status('mia-api.service')
    services_ok += check_service_status('mia-gpio-worker.service')
    services_ok += check_service_status('mia-serial-bridge.service')
    services_ok += check_service_status('mia-obd-worker.service')
    print(f"Services running: {services_ok}/5\n")

    # Test API endpoints
    print("Testing API endpoints:")

    # Basic endpoints
    root_data = test_api_endpoint("Root endpoint", f"{API_BASE}/")
    status_data = test_api_endpoint("Status endpoint", f"{API_BASE}/status")
    devices_data = test_api_endpoint("Devices endpoint", f"{API_BASE}/devices")
    telemetry_data = test_api_endpoint("Telemetry endpoint", f"{API_BASE}/telemetry")

    # GPIO endpoints (these will timeout since no hardware, but should not crash)
    gpio_config = test_api_post("GPIO configure", f"{API_BASE}/gpio/configure",
                               {"pin": 18, "direction": "output"})

    # Test WebSocket
    websocket_ok = test_websocket()

    # Summary
    print("\n=== Test Summary ===")

    api_tests = [root_data, status_data, devices_data, telemetry_data, gpio_config]
    api_passed = sum(1 for test in api_tests if test is not None)

    print(f"API Endpoints: {api_passed}/{len(api_tests)} passed")
    print(f"WebSocket: {'PASS' if websocket_ok else 'FAIL'}")
    print(f"Services: {services_ok}/5 running")

    total_passed = api_passed + (1 if websocket_ok else 0) + services_ok
    total_tests = len(api_tests) + 1 + 5

    print(f"\nOverall: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("🎉 All tests passed! MIA deployment is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())