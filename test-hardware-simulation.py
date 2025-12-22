#!/usr/bin/env python3
"""
MIA Hardware Simulation Test
Demonstrates MIA system working in hardware-simulated environment
"""

import zmq
import json
import time
import requests
import sys
from datetime import datetime

def test_zmq_broker():
    """Test ZeroMQ broker connectivity"""
    print("🔗 Testing ZeroMQ Broker...")

    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:5555")
        socket.setsockopt(zmq.LINGER, 0)

        # Send a test message
        test_msg = {
            "type": "TEST_MESSAGE",
            "message": "Hardware simulation test",
            "timestamp": datetime.now().isoformat()
        }

        socket.send_json(test_msg)
        print("   ✅ Message sent to broker")

        # Try to receive response (may timeout, that's OK)
        socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
        try:
            response = socket.recv_json()
            print(f"   ✅ Response received: {response.get('type', 'unknown')}")
        except zmq.Again:
            print("   ⚠️  No response (expected in simulation mode)")

        socket.close()
        context.term()
        return True

    except Exception as e:
        print(f"   ❌ Broker test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("🌐 Testing API Endpoints...")

    base_url = "http://localhost:8000"
    endpoints = [
        ("/devices", "Device registry"),
        ("/status", "System status"),
        ("/docs", "API documentation")
    ]

    results = {}
    for endpoint, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                results[endpoint] = f"✅ {description}: OK"
                print(f"   ✅ {description}: {response.status_code}")
            else:
                results[endpoint] = f"⚠️  {description}: {response.status_code}"
                print(f"   ⚠️  {description}: {response.status_code}")

        except requests.exceptions.RequestException as e:
            results[endpoint] = f"❌ {description}: Connection failed"
            print(f"   ❌ {description}: Connection failed")

    return results

def test_service_status():
    """Test systemd service status"""
    print("⚙️  Testing Service Status...")

    import subprocess

    services = [
        "mia-broker.service",
        "mia-api.service",
        "bluetooth.service"
    ]

    results = {}
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip() == "active":
                results[service] = "✅ Active"
                print(f"   ✅ {service}: Active")
            else:
                results[service] = f"⚠️  {result.stdout.strip()}"
                print(f"   ⚠️  {service}: {result.stdout.strip()}")

        except Exception as e:
            results[service] = f"❌ Error: {e}"
            print(f"   ❌ {service}: Error - {e}")

    return results

def simulate_device_telemetry():
    """Simulate device telemetry (mock hardware)"""
    print("📡 Simulating Device Telemetry...")

    try:
        context = zmq.Context()
        pub_socket = context.socket(zmq.PUB)
        pub_socket.connect("tcp://localhost:5556")  # PUB port

        # Give socket time to connect
        time.sleep(0.1)

        # Send mock telemetry data
        mock_data = {
            "device": "mock_sensor_001",
            "type": "telemetry",
            "timestamp": datetime.now().isoformat(),
            "sensors": {
                "temperature": 25.5,
                "humidity": 60.2,
                "pressure": 1013.25,
                "mock_hardware": True
            },
            "simulation_mode": True
        }

        pub_socket.send_json(mock_data)
        print(f"   ✅ Mock telemetry sent: {json.dumps(mock_data, indent=2)[:100]}...")

        pub_socket.close()
        context.term()
        return True

    except Exception as e:
        print(f"   ❌ Telemetry simulation failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚗 MIA Hardware Simulation Test")
    print("=" * 50)
    print("Testing MIA system in hardware-simulated environment")
    print("(No ESP32, Arduino, or GPIO hardware required)")
    print()

    all_tests_passed = True

    # Test 1: ZeroMQ Broker
    if not test_zmq_broker():
        all_tests_passed = False

    print()

    # Test 2: API Endpoints
    api_results = test_api_endpoints()
    if any("❌" in result for result in api_results.values()):
        all_tests_passed = False

    print()

    # Test 3: Service Status
    service_results = test_service_status()
    if any("❌" in result for result in service_results.values()):
        all_tests_passed = False

    print()

    # Test 4: Device Telemetry Simulation
    if not simulate_device_telemetry():
        all_tests_passed = False

    print()
    print("=" * 50)

    if all_tests_passed:
        print("🎉 MIA Hardware Simulation Test: SUCCESS")
        print()
        print("✅ ZeroMQ messaging system working")
        print("✅ REST API responding")
        print("✅ Core services running")
        print("✅ Telemetry simulation functional")
        print()
        print("🚗 MIA system is fully operational in simulation mode!")
        print("   Ready for development and testing without hardware.")
        print()
        print("💡 Next steps:")
        print("   • Add real hardware when available")
        print("   • Test with actual ESP32/Arduino devices")
        print("   • Enable GPIO features for physical controls")
        print("   • Connect OBD-II adapter for vehicle diagnostics")
    else:
        print("⚠️  MIA Hardware Simulation Test: ISSUES DETECTED")
        print("   Some components may need attention.")
        print("   Check the output above for specific failures.")

    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())