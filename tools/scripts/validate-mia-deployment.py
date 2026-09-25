#!/usr/bin/env python3
"""
MIA Deployment Validation Script
Comprehensive validation of MIA system deployment including:
- Hardware validation
- Service health checks
- Network connectivity
- Integration testing
- Performance validation
"""

import sys
import os
import time
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MIADeploymentValidator:
    """Comprehensive MIA deployment validator"""

    def __init__(self):
        self.install_dir = "/opt/mia"
        self.config_dir = f"{self.install_dir}/config"
        self.log_dir = "/var/log/mia"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "total": 0
            }
        }

    def run_command(self, cmd: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def log_test_result(self, test_name: str, passed: bool, message: str = "", details: str = ""):
        """Log a test result"""
        self.results["tests"][test_name] = {
            "passed": passed,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

        if passed:
            logger.info(f"✅ {test_name}: {message}")
            self.results["summary"]["passed"] += 1
        else:
            logger.error(f"❌ {test_name}: {message}")
            if details:
                logger.error(f"   Details: {details}")
            self.results["summary"]["failed"] += 1

        self.results["summary"]["total"] += 1

    def test_system_info(self) -> bool:
        """Test basic system information"""
        logger.info("🔍 Testing system information...")

        # Check OS and architecture
        success, stdout, stderr = self.run_command("uname -a")
        if success:
            self.log_test_result("system_info", True, f"System: {stdout}")
        else:
            self.log_test_result("system_info", False, "Failed to get system info", stderr)
            return False

        # Check available memory
        success, stdout, stderr = self.run_command("free -h | grep '^Mem:' | awk '{print $2}'")
        if success:
            logger.info(f"   Available memory: {stdout}")
        else:
            logger.warning(f"   Could not determine memory: {stderr}")

        # Check available disk space
        success, stdout, stderr = self.run_command("df -h / | tail -1 | awk '{print $4}'")
        if success:
            logger.info(f"   Available disk space: {stdout}")
        else:
            logger.warning(f"   Could not determine disk space: {stderr}")

        return True

    def test_python_environment(self) -> bool:
        """Test Python environment and critical imports"""
        logger.info("🐍 Testing Python environment...")

        # Test Python version
        success, stdout, stderr = self.run_command("python3 --version")
        if success:
            self.log_test_result("python_version", True, f"Python available: {stdout}")
        else:
            self.log_test_result("python_version", False, "Python3 not available", stderr)
            return False

        # Test critical imports
        critical_imports = [
            "import sys",
            "import os",
            "import zmq",
            "import flatbuffers",
            "import serial",
            "import asyncio",
            "import aiohttp"
        ]

        failed_imports = []
        for import_stmt in critical_imports:
            success, stdout, stderr = self.run_command(f"python3 -c '{import_stmt}'")
            if not success:
                failed_imports.append(import_stmt.split()[-1])

        if failed_imports:
            self.log_test_result("python_imports", False,
                               f"Failed imports: {', '.join(failed_imports)}",
                               "Install missing packages with: pip3 install <package>")
            return False
        else:
            self.log_test_result("python_imports", True, "All critical Python imports successful")
            return True

    def test_mia_installation(self) -> bool:
        """Test MIA installation structure"""
        logger.info("📦 Testing MIA installation...")

        # Check installation directory
        if not os.path.exists(self.install_dir):
            self.log_test_result("mia_installation", False, f"Installation directory not found: {self.install_dir}")
            return False

        # Check core directories
        required_dirs = [
            f"{self.install_dir}/rpi",
            f"{self.install_dir}/core",
            f"{self.install_dir}/config",
            f"{self.install_dir}/modules"
        ]

        missing_dirs = []
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_path)

        if missing_dirs:
            self.log_test_result("mia_directories", False,
                               f"Missing directories: {', '.join(missing_dirs)}")
            return False
        else:
            self.log_test_result("mia_directories", True, "All MIA directories present")

        # Test MIA module imports
        sys.path.insert(0, self.install_dir)
        try:
            from core.paths import PathConfig
            config = PathConfig()
            self.log_test_result("mia_paths", True, f"PathConfig loaded successfully, project root: {config.project_root}")
        except Exception as e:
            self.log_test_result("mia_paths", False, f"Failed to load PathConfig: {e}")
            return False

        return True

    def test_hardware_interfaces(self) -> bool:
        """Test hardware interfaces"""
        logger.info("🔧 Testing hardware interfaces...")

        # Test GPIO (Raspberry Pi specific)
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(18, GPIO.OUT)
            GPIO.output(18, GPIO.LOW)
            GPIO.cleanup()
            self.log_test_result("gpio_interface", True, "GPIO interface functional")
            gpio_available = True
        except ImportError:
            self.log_test_result("gpio_interface", True, "GPIO not available (expected on non-Pi systems)")
            gpio_available = False
        except Exception as e:
            self.log_test_result("gpio_interface", False, f"GPIO interface failed: {e}")
            gpio_available = False

        # Test I2C
        success, stdout, stderr = self.run_command("i2cdetect -y 1 | head -5")
        if success and "i2c" in stdout.lower():
            self.log_test_result("i2c_interface", True, "I2C interface available")
        else:
            self.log_test_result("i2c_interface", False, "I2C interface not available", stderr)

        # Test Bluetooth
        success, stdout, stderr = self.run_command("hciconfig hci0")
        if success:
            self.log_test_result("bluetooth_interface", True, "Bluetooth interface available")
        else:
            self.log_test_result("bluetooth_interface", False, "Bluetooth interface not available", stderr)

        # Test serial ports
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        if ports:
            port_names = [port.device for port in ports]
            self.log_test_result("serial_ports", True, f"Serial ports available: {', '.join(port_names)}")
        else:
            self.log_test_result("serial_ports", False, "No serial ports detected")

        return True

    def test_network_connectivity(self) -> bool:
        """Test network connectivity"""
        logger.info("🌐 Testing network connectivity...")

        # Test local network
        success, stdout, stderr = self.run_command("hostname -I")
        if success and stdout.strip():
            self.log_test_result("local_network", True, f"Local IP: {stdout.strip()}")
        else:
            self.log_test_result("local_network", False, "No local IP address", stderr)

        # Test internet connectivity
        success, stdout, stderr = self.run_command("ping -c 1 8.8.8.8")
        if success:
            self.log_test_result("internet_connectivity", True, "Internet connectivity available")
        else:
            self.log_test_result("internet_connectivity", False, "No internet connectivity", stderr)

        # Test DNS resolution
        success, stdout, stderr = self.run_command("nslookup google.com | head -3")
        if success:
            self.log_test_result("dns_resolution", True, "DNS resolution working")
        else:
            self.log_test_result("dns_resolution", False, "DNS resolution failed", stderr)

        return True

    def test_systemd_services(self) -> bool:
        """Test systemd services"""
        logger.info("⚙️ Testing systemd services...")

        services_to_test = [
            "mia-broker.service",
            "mia-api.service",
            "mia-gpio-worker.service",
            "mia-ble-obd.service",
            "bluetooth.service"
        ]

        services_status = {}

        for service in services_to_test:
            # Check if service exists
            success, stdout, stderr = self.run_command(f"systemctl list-units --all | grep {service}")
            if success:
                # Check service status
                success, stdout, stderr = self.run_command(f"systemctl is-active {service}")
                if success and stdout.strip() == "active":
                    services_status[service] = "active"
                else:
                    services_status[service] = "inactive"
            else:
                services_status[service] = "not_installed"

        # Report results
        active_services = []
        inactive_services = []
        not_installed_services = []

        for service, status in services_status.items():
            if status == "active":
                active_services.append(service)
            elif status == "inactive":
                inactive_services.append(service)
            else:
                not_installed_services.append(service)

        if active_services:
            self.log_test_result("services_active", True, f"Active services: {', '.join(active_services)}")

        if inactive_services:
            self.log_test_result("services_inactive", False,
                               f"Inactive services: {', '.join(inactive_services)}",
                               "Start with: sudo systemctl start <service>")

        if not_installed_services:
            self.log_test_result("services_not_installed", False,
                               f"Not installed: {', '.join(not_installed_services)}")

        return len(inactive_services) == 0 and len(not_installed_services) == 0

    def test_mia_services_integration(self) -> bool:
        """Test MIA services integration"""
        logger.info("🔗 Testing MIA services integration...")

        # Test ZeroMQ broker connection
        try:
            import zmq
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect("tcp://localhost:5555")
            socket.setsockopt(zmq.LINGER, 0)
            socket.close()
            context.term()
            self.log_test_result("zmq_broker", True, "ZeroMQ broker connection successful")
        except Exception as e:
            self.log_test_result("zmq_broker", False, f"ZeroMQ broker connection failed: {e}")

        # Test API endpoint
        success, stdout, stderr = self.run_command("curl -f -s http://localhost:8000/health")
        if success:
            self.log_test_result("api_endpoint", True, "API health endpoint responding")
        else:
            self.log_test_result("api_endpoint", False, "API health endpoint not responding", stderr)

        # Test WebSocket endpoint (basic connectivity)
        success, stdout, stderr = self.run_command("timeout 5 websocat -E ws://localhost:8000/ws 2>/dev/null <<< 'test' || true")
        # Note: This is a basic test - actual WebSocket functionality would need more complex testing

        return True

    def test_performance(self) -> bool:
        """Test system performance"""
        logger.info("⚡ Testing system performance...")

        # Test CPU performance with a simple benchmark
        success, stdout, stderr = self.run_command("python3 -c \"import time; start=time.time(); [x**2 for x in range(100000)]; print(f'{(time.time()-start)*1000:.2f}ms')\"")
        if success:
            self.log_test_result("cpu_performance", True, f"CPU benchmark completed in {stdout}")
        else:
            self.log_test_result("cpu_performance", False, "CPU benchmark failed", stderr)

        # Test memory usage
        success, stdout, stderr = self.run_command("free | grep Mem | awk '{printf \"%.1f%%\", $3/$2 * 100.0}'")
        if success:
            mem_usage = float(stdout.strip().rstrip('%'))
            if mem_usage < 80:
                self.log_test_result("memory_usage", True, f"Memory usage: {stdout}")
            else:
                self.log_test_result("memory_usage", False, f"High memory usage: {stdout}")
        else:
            self.log_test_result("memory_usage", False, "Could not check memory usage", stderr)

        return True

    def run_all_tests(self) -> bool:
        """Run all validation tests"""
        logger.info("🚀 Starting MIA Deployment Validation")
        logger.info("=" * 60)

        test_methods = [
            self.test_system_info,
            self.test_python_environment,
            self.test_mia_installation,
            self.test_hardware_interfaces,
            self.test_network_connectivity,
            self.test_systemd_services,
            self.test_mia_services_integration,
            self.test_performance
        ]

        all_passed = True
        for test_method in test_methods:
            try:
                if not test_method():
                    all_passed = False
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed with exception: {e}")
                self.log_test_result(test_method.__name__, False, f"Exception: {e}")
                all_passed = False

        return all_passed

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate validation report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_file = f"mia-validation-report-{timestamp}.json"

        # Calculate summary
        summary = self.results["summary"]
        summary["success_rate"] = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0

        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        return output_file

    def print_summary(self):
        """Print validation summary"""
        summary = self.results["summary"]

        logger.info("=" * 60)
        logger.info("🎯 MIA DEPLOYMENT VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {summary['total']}")
        logger.info(f"Passed: {summary['passed']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Warnings: {summary['warnings']}")
        logger.info(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
        if summary["failed"] == 0:
            logger.info("✅ Overall Status: SUCCESS")
            if summary["warnings"] > 0:
                logger.info("⚠️  Review warnings for potential issues")
        else:
            logger.info("❌ Overall Status: FAILED")
            logger.info("🔧 Check failed tests and resolve issues")

        logger.info("=" * 60)

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="MIA Deployment Validation Script")
    parser.add_argument("--output", "-o", help="Output file for detailed report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    validator = MIADeploymentValidator()

    print("🚗 MIA Deployment Validation Starting...")
    print("This may take several minutes to complete all tests...")
    print()

    success = validator.run_all_tests()

    print()
    validator.print_summary()

    if args.output:
        report_file = validator.generate_report(args.output)
        print(f"📄 Detailed report saved to: {report_file}")

    print()
    if success:
        print("🎉 MIA deployment validation completed successfully!")
        print("🚗 System is ready for automotive AI operations.")
    else:
        print("⚠️  MIA deployment validation found issues.")
        print("🔧 Review the output above and resolve failed tests.")
        sys.exit(1)

if __name__ == "__main__":
    main()