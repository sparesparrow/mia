"""
Conan recipe for MIA Raspberry Pi Python Services
Manages Python dependencies for OBD simulator and other RPi services
"""
from conan import ConanFile
from conan.tools.python import Python
from conan.tools.files import copy, save
import os


class MiaRpiPythonConan(ConanFile):
    name = "mia-rpi-python"
    version = "1.0"
    description = "MIA Raspberry Pi Python Services - OBD Simulator, Serial Bridge, GPIO Worker"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_obd": [True, False],
        "with_gpio": [True, False],
        "with_serial": [True, False],
    }
    default_options = {
        "with_obd": True,
        "with_gpio": True,
        "with_serial": True,
    }
    exports_sources = "requirements.txt", "*.py", "services/*", "hardware/*", "core/*", "api/*"
    no_copy_source = False

    def requirements(self):
        """Python dependencies are managed via requirements.txt"""
        # Conan doesn't directly manage Python packages,
        # but we can validate that system dependencies are available
        pass

    def build_requirements(self):
        """System dependencies needed for Python packages"""
        # These are typically installed via apt-get, not Conan
        # But we document them here for reference
        pass

    def build(self):
        """Build/validate Python services"""
        # Validate Python files are present
        required_files = [
            "core/messaging/broker.py",
            "api/main.py",
            "hardware/gpio_worker.py",
        ]
        
        if self.options.with_obd:
            required_files.append("services/obd_worker.py")
        
        if self.options.with_serial:
            required_files.append("hardware/serial_bridge.py")
        
        for file_path in required_files:
            full_path = os.path.join(self.source_folder, file_path)
            if not os.path.exists(full_path):
                self.output.warning(f"Required file not found: {file_path}")
            else:
                self.output.info(f"Found: {file_path}")

    def package(self):
        """Package Python services"""
        # Copy all Python files
        copy(self, "*.py", self.source_folder, os.path.join(self.package_folder, "rpi"))
        copy(self, "requirements.txt", self.source_folder, self.package_folder)
        
        # Copy subdirectories
        for subdir in ["services", "hardware", "core", "api"]:
            src = os.path.join(self.source_folder, subdir)
            dst = os.path.join(self.package_folder, "rpi", subdir)
            if os.path.exists(src):
                copy(self, "*.py", src, dst)
                copy(self, "*.service", src, os.path.join(self.package_folder, "rpi", "services"))
        
        # Copy Arduino firmware example
        copy(self, "*.ino", os.path.join(self.source_folder, "hardware"), 
             os.path.join(self.package_folder, "rpi", "hardware"))

    def package_info(self):
        """Define package information"""
        self.cpp_info.libs = []  # No C++ libraries
        
        # Python package info
        self.env_info.PYTHONPATH.append(os.path.join(self.package_folder, "rpi"))
        self.env_info.MIA_RPI_ROOT = os.path.join(self.package_folder, "rpi")
        
        # Service files location
        self.env_info.MIA_RPI_SERVICES = os.path.join(self.package_folder, "rpi", "services")
