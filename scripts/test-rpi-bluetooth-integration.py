#!/usr/bin/env python3
"""
Raspberry Pi Bluetooth Integration Test Script
Tests Bluetooth device scanning and pairing between Android app and RPi services
"""

import sys
import time
import json
import requests
import subprocess
from typing import Dict, List, Optional
import zmq
import socket

class RPITestSuite:
    def __init__(self, rpi_host: str = "mia.local", rpi_ip: str = "192.168.200.137"):
        self.rpi_host = rpi_host
        self.rpi_ip = rpi_ip
        self.api_base = f"http://{rpi_host}:8000"
        self.test_results = []
        self.context = zmq.Context()

    def log_test(self, test_name: str, status: str, message: str, details: Dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": details or {}
        }
        self.test_results.append(result)
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {message}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")

    def test_network_connectivity(self) -> bool:
        """Test basic network connectivity to Raspberry Pi"""
        try:
            # Test ping
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", self.rpi_ip],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.log_test("Network Connectivity", "PASS", "Raspberry Pi is reachable")
                return True
            else:
                self.log_test("Network Connectivity", "FAIL", "Cannot ping Raspberry Pi")
                return False
        except Exception as e:
            self.log_test("Network Connectivity", "FAIL", f"Network test failed: {e}")
            return False

    def test_api_connectivity(self) -> bool:
        """Test API connectivity"""
        try:
            response = requests.get(f"{self.api_base}/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("API Connectivity", "PASS", "API is responding",
                            {"status": data.get("status"), "services": data.get("services", [])})
                return True
            else:
                self.log_test("API Connectivity", "FAIL", f"API returned status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Connectivity", "FAIL", f"API connection failed: {e}")
            return False

    def test_zeromq_connectivity(self) -> bool:
        """Test ZeroMQ broker connectivity"""
        try:
            # Test broker port 5555
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.rpi_ip, 5555))
            sock.close()

            if result == 0:
                self.log_test("ZeroMQ Broker", "PASS", "ZeroMQ broker is accessible on port 5555")
                broker_ok = True
            else:
                self.log_test("ZeroMQ Broker", "FAIL", "ZeroMQ broker not accessible on port 5555")
                broker_ok = False

            # Test PUB port 5556
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.rpi_ip, 5556))
            sock.close()

            if result == 0:
                self.log_test("ZeroMQ PUB Socket", "PASS", "ZeroMQ PUB socket is accessible on port 5556")
                pub_ok = True
            else:
                self.log_test("ZeroMQ PUB Socket", "FAIL", "ZeroMQ PUB socket not accessible on port 5556")
                pub_ok = False

            return broker_ok and pub_ok

        except Exception as e:
            self.log_test("ZeroMQ Connectivity", "FAIL", f"ZeroMQ test failed: {e}")
            return False

    def test_bluetooth_services(self) -> bool:
        """Test for Bluetooth services on Raspberry Pi"""
        try:
            # Check if Raspberry Pi has Bluetooth hardware
            response = requests.get(f"{self.api_base}/devices", timeout=10)
            if response.status_code == 200:
                devices = response.json().get("devices", [])
                bluetooth_devices = [d for d in devices if "bluetooth" in d.get("type", "").lower()]

                if bluetooth_devices:
                    self.log_test("Bluetooth Services", "PASS",
                                f"Found {len(bluetooth_devices)} Bluetooth devices",
                                {"devices": bluetooth_devices})
                    return True
                else:
                    self.log_test("Bluetooth Services", "WARN",
                                "No Bluetooth devices found in registry")
                    return False
            else:
                self.log_test("Bluetooth Services", "FAIL", "Could not query device registry")
                return False

        except Exception as e:
            self.log_test("Bluetooth Services", "FAIL", f"Bluetooth test failed: {e}")
            return False

    def test_obd_services(self) -> bool:
        """Test OBD-II services"""
        try:
            # Check telemetry endpoint for OBD data
            response = requests.get(f"{self.api_base}/telemetry", timeout=10)
            if response.status_code == 200:
                telemetry = response.json().get("telemetry", {})
                obd_data = {k: v for k, v in telemetry.items() if "obd" in k.lower() or "rpm" in k.lower()}

                if obd_data:
                    self.log_test("OBD Services", "PASS",
                                f"OBD telemetry data available: {list(obd_data.keys())}",
                                {"obd_data": obd_data})
                    return True
                else:
                    self.log_test("OBD Services", "INFO", "No OBD telemetry data currently available")
                    return True  # This is OK, might not be actively running
            else:
                self.log_test("OBD Services", "FAIL", "Could not query telemetry")
                return False

        except Exception as e:
            self.log_test("OBD Services", "FAIL", f"OBD test failed: {e}")
            return False

    def test_ble_discovery(self) -> bool:
        """Test BLE device discovery capability"""
        try:
            # Try to send a BLE scan command
            command_data = {
                "device": "ble_scanner",
                "action": "scan",
                "timeout": 10
            }

            response = requests.post(f"{self.api_base}/command",
                                   json=command_data, timeout=15)

            if response.status_code == 200:
                result = response.json()
                if "devices" in result:
                    devices = result["devices"]
                    self.log_test("BLE Discovery", "PASS",
                                f"BLE scan successful, found {len(devices)} devices",
                                {"devices": devices})
                    return True
                else:
                    self.log_test("BLE Discovery", "INFO", "BLE scan completed but no devices found",
                                {"response": result})
                    return True
            else:
                self.log_test("BLE Discovery", "FAIL",
                            f"BLE scan command failed: {response.status_code}",
                            {"response": response.text})
                return False

        except Exception as e:
            self.log_test("BLE Discovery", "FAIL", f"BLE discovery test failed: {e}")
            return False

    def test_zeromq_subscriber(self) -> bool:
        """Test ZeroMQ subscriber for telemetry data"""
        try:
            socket = self.context.socket(zmq.SUB)
            socket.connect(f"tcp://{self.rpi_ip}:5556")
            socket.subscribe(b"mcu/telemetry")

            # Set a short timeout
            socket.setsockopt(zmq.RCVTIMEO, 5000)

            start_time = time.time()
            messages_received = 0

            while time.time() - start_time < 10:  # Test for 10 seconds
                try:
                    topic, message = socket.recv_multipart()
                    messages_received += 1
                    try:
                        data = json.loads(message.decode('utf-8'))
                        self.log_test("ZeroMQ Subscriber", "PASS",
                                    f"Received telemetry message {messages_received}",
                                    {"topic": topic.decode(), "data": data})
                    except json.JSONDecodeError:
                        self.log_test("ZeroMQ Subscriber", "INFO",
                                    f"Received non-JSON message on topic {topic.decode()}")

                except zmq.Again:
                    break  # Timeout

            socket.close()

            if messages_received > 0:
                self.log_test("ZeroMQ Subscriber", "PASS",
                            f"Successfully received {messages_received} messages")
                return True
            else:
                self.log_test("ZeroMQ Subscriber", "INFO",
                            "No telemetry messages received (this is normal if no devices connected)")
                return True  # Not a failure

        except Exception as e:
            self.log_test("ZeroMQ Subscriber", "FAIL", f"ZeroMQ subscriber test failed: {e}")
            return False

    def test_android_app_integration(self) -> bool:
        """Test Android app integration scenarios"""
        try:
            # This would simulate what the Android app does
            # 1. Check if BLE services are available
            # 2. Test device discovery
            # 3. Test connection establishment

            integration_tests = [
                ("BLE Manager Available", self.test_bluetooth_services()),
                ("OBD Data Available", self.test_obd_services()),
                ("Device Discovery", self.test_ble_discovery()),
            ]

            passed = sum(1 for _, result in integration_tests if result)
            total = len(integration_tests)

            if passed == total:
                self.log_test("Android App Integration", "PASS",
                            f"All integration tests passed ({passed}/{total})")
                return True
            elif passed > 0:
                self.log_test("Android App Integration", "WARN",
                            f"Partial integration success ({passed}/{total})",
                            {"results": integration_tests})
                return True
            else:
                self.log_test("Android App Integration", "FAIL",
                            "No integration tests passed")
                return False

        except Exception as e:
            self.log_test("Android App Integration", "FAIL", f"Integration test failed: {e}")
            return False

    def run_all_tests(self) -> Dict:
        """Run all tests and return results"""
        print("🚗 Raspberry Pi Bluetooth Integration Test Suite")
        print("=" * 60)
        print(f"Target: {self.rpi_host} ({self.rpi_ip})")
        print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Run all tests
        tests = [
            ("Network Connectivity", self.test_network_connectivity),
            ("API Connectivity", self.test_api_connectivity),
            ("ZeroMQ Connectivity", self.test_zeromq_connectivity),
            ("Bluetooth Services", self.test_bluetooth_services),
            ("OBD Services", self.test_obd_services),
            ("BLE Discovery", self.test_ble_discovery),
            ("ZeroMQ Subscriber", self.test_zeromq_subscriber),
            ("Android App Integration", self.test_android_app_integration),
        ]

        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                test_func()
            except Exception as e:
                self.log_test(test_name, "ERROR", f"Test execution failed: {e}")

        # Generate summary
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        warnings = sum(1 for r in self.test_results if r["status"] == "WARN")
        errors = sum(1 for r in self.test_results if r["status"] == "ERROR")
        total = len(self.test_results)

        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"💥 Errors: {errors}")

        if failed == 0 and errors == 0:
            print("\n🎉 All critical tests passed!")
        elif failed > 0:
            print(f"\n⚠️  {failed} tests failed - check Bluetooth/OBD services on Raspberry Pi")
        else:
            print(f"\n⚠️  {errors} tests had errors - check network connectivity")

        return {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "errors": errors
            },
            "results": self.test_results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test Raspberry Pi Bluetooth integration")
    parser.add_argument("--host", default="mia.local", help="Raspberry Pi hostname")
    parser.add_argument("--ip", default="192.168.200.137", help="Raspberry Pi IP address")
    parser.add_argument("--output", help="Output JSON file for results")

    args = parser.parse_args()

    tester = RPITestSuite(args.host, args.ip)
    results = tester.run_all_tests()

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Results saved to {args.output}")

if __name__ == "__main__":
    main()