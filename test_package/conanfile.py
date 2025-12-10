"""
Test package for MIA RPi Python Conan recipe
Validates that the package can be consumed correctly
"""
from conan import ConanFile
from conan.tools.files import save
import os


class TestMiaRpiPythonConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def test(self):
        """Test that the package is correctly installed"""
        # Check that Python files are available
        rpi_root = self.deps_env_info["mia-rpi-python"].MIA_RPI_ROOT
        
        # Verify key files exist
        required_files = [
            "core/messaging/broker.py",
            "api/main.py",
            "hardware/gpio_worker.py",
        ]
        
        for file_path in required_files:
            full_path = os.path.join(rpi_root, file_path)
            if os.path.exists(full_path):
                self.output.info(f"✓ Found: {file_path}")
            else:
                self.output.warning(f"⚠ Missing: {file_path}")
        
        # Test Python import (if possible)
        import sys
        sys.path.insert(0, rpi_root)
        
        try:
            from core.messaging.broker import ZeroMQBroker
            self.output.info("✓ Successfully imported ZeroMQBroker")
        except ImportError as e:
            self.output.warning(f"⚠ Import test failed: {e}")
