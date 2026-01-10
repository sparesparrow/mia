from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout
from conan.tools.files import copy
import os


class MIAConan(ConanFile):
    name = "sparetools-mia"
    version = "2.0.1"
    description = "AI Service with MCP and Hardware Control"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_hardware": [True, False],
        "with_mcp": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_hardware": True,   # Testing libgpiod compatibility
        "with_mcp": True
    }

    # SpareTools ecosystem integration
    python_requires = "sparetools-base/2.0.3"

    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        # Core dependencies - always required
        self.requires("jsoncpp/1.9.5")           # JSON handling for all components
        self.requires("libcurl/8.5.0")           # HTTP client for downloads and APIs
        self.requires("zlib/1.2.13")             # Compression support

        # SpareTools runtime dependencies
        self.requires("sparetools-flatbuffers/24.3.25")  # FlatBuffers for serialization
        self.requires("sparetools-mcp-core/1.0.1")       # MCP framework integration

        # Hardware-specific dependencies
        if self.options.with_hardware:
            self.requires("libgpiod/2.0.1")      # GPIO control for Raspberry Pi
            self.requires("mosquitto/2.0.18")    # MQTT communication

        # MCP-specific dependencies
        if self.options.with_mcp:
            self.requires("sparetools-mcp-orchestrator/2.0.3")  # MCP orchestration
            self.requires("sparetools-tinymcp/2.0.0")           # Lightweight MCP server

    def build_requirements(self):
        # SpareTools build-time dependencies
        self.tool_requires("sparetools-cpython/3.12.7")          # Python runtime for build scripts
        self.tool_requires("sparetools-flatbuffers/24.3.25")     # FlatBuffers compiler

        # Keep system flatbuffers for now (compatibility)
        self.tool_requires("flatbuffers/23.5.26")

    def export_sources(self):
        # Export source files needed for building
        copy(self, "platforms/**", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "protos/**", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Generate CMake toolchain and dependencies
        tc = CMakeToolchain(self)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        # Generate runtime environment for running applications
        ve = VirtualRunEnv(self)
        ve.generate()

    def build(self):
        # Generate FlatBuffers headers before building
        self._generate_flatbuffers()

        cmake = CMake(self)
        # Change to platforms/cpp directory where CMakeLists.txt is located
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "platforms", "cpp"))
        cmake.build()

    def _generate_flatbuffers(self):
        """Generate C++ headers from FlatBuffers schema"""
        import os
        from pathlib import Path

        # Find bundled Python executable from sparetools-cpython
        python_bin = None
        if hasattr(self, 'deps_cpp_info') and self.deps_cpp_info.has_components:
            try:
                cpython_info = self.deps_cpp_info["sparetools-cpython"]
                python_bin = os.path.join(cpython_info.bin_paths[0], "python3")
                if not os.path.exists(python_bin):
                    python_bin = os.path.join(cpython_info.bin_paths[0], "python3.12")
                if not os.path.exists(python_bin):
                    python_bin = os.path.join(cpython_info.bin_paths[0], "python")
            except:
                pass

        if not python_bin or not os.path.exists(python_bin):
            self.output.warning("Bundled Python executable not found. FlatBuffers Python generation may fail.")
            python_bin = "python3"  # Fallback to system Python

        # Find flatc executable
        flatc_path = None
        if hasattr(self, 'deps_cpp_info') and self.deps_cpp_info.has_components:
            # Try to get flatc from Conan dependencies
            try:
                flatbuffers_info = self.deps_cpp_info["flatbuffers"]
                flatc_path = os.path.join(flatbuffers_info.bin_paths[0], "flatc")
            except:
                pass

        if not flatc_path or not os.path.exists(flatc_path):
            # Try system flatc
            import shutil
            flatc_path = shutil.which("flatc")

        if not flatc_path:
            self.output.warning("FlatBuffers compiler (flatc) not found. C++ headers will not be generated.")
            return

        # Schema and output paths
        schema_dir = os.path.join(self.source_folder, "platforms", "cpp", "core")
        schema_file = os.path.join(schema_dir, "webgrab.fbs")
        output_file = os.path.join(schema_dir, "webgrab_generated.h")

        if not os.path.exists(schema_file):
            self.output.warning(f"FlatBuffers schema not found: {schema_file}")
            return

        # Generate headers
        import subprocess
        cmd = [
            flatc_path,
            "--cpp",
            "--gen-mutable",
            "-o", schema_dir,
            schema_file
        ]

        try:
            self.output.info(f"Generating FlatBuffers headers: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.output.info(f"FlatBuffers headers generated successfully: {output_file}")
        except subprocess.CalledProcessError as e:
            self.output.error(f"Failed to generate FlatBuffers headers: {e}")
            self.output.error(f"stdout: {e.stdout}")
            self.output.error(f"stderr: {e.stderr}")
            raise

        # Generate Python bindings for Vehicle schema
        vehicle_schema = os.path.join(self.source_folder, "protos", "vehicle.fbs")
        if os.path.exists(vehicle_schema):
            cmd_py = [
                flatc_path,
                "--python",
                "-o", self.source_folder,
                vehicle_schema
            ]
            try:
                self.output.info(f"Generating Python FlatBuffers: {' '.join(cmd_py)}")
                subprocess.run(cmd_py, check=True, capture_output=True, text=True)
                self.output.info("Python FlatBuffers generated successfully.")
            except subprocess.CalledProcessError as e:
                self.output.error(f"Failed to generate Python FlatBuffers: {e}")

    def package(self):
        # Package the executables and libraries
        cmake = CMake(self)
        cmake.install()

        # Package bundled CPython executable and libraries if available
        self._package_cpython()

    def _package_cpython(self):
        """Package bundled CPython if available"""
        try:
            if hasattr(self, 'deps_cpp_info') and "sparetools-cpython" in self.deps_cpp_info:
                cpython_info = self.deps_cpp_info["sparetools-cpython"]
                # Copy CPython bin directory (includes python3 executable)
                copy(self, "*", cpython_info.bin_paths[0], os.path.join(self.package_folder, "bin"))
                # Copy CPython lib directory (includes standard library)
                copy(self, "*", cpython_info.lib_paths[0], os.path.join(self.package_folder, "lib"))
                # Copy include files if they exist
                if cpython_info.include_paths:
                    copy(self, "*", cpython_info.include_paths[0], os.path.join(self.package_folder, "include"))
                self.output.info("Bundled CPython packaged successfully")
            else:
                self.output.info("No bundled CPython found - using system Python")
        except Exception as e:
            self.output.warning(f"Could not package bundled CPython: {e}")
            self.output.info("Falling back to system Python")

    def package_info(self):
        # Define library information
        self.cpp_info.libs = []

        # Core library (always present if build succeeds)
        if self._library_exists("webgrab_core"):
            self.cpp_info.libs.append("webgrab_core")

        if self.options.with_hardware and self._library_exists("hardware-server"):
            self.cpp_info.libs.append("hardware-server")

        if self.options.with_mcp and self._library_exists("mcp-server"):
            self.cpp_info.libs.append("mcp-server")

        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "crypt32", "advapi32"]

        # Configure Python environment if bundled CPython is available
        self._configure_python_environment()

    def _library_exists(self, lib_name):
        """Check if a library file exists in the package"""
        import os
        lib_extensions = [".so", ".a", ".lib", ".dll"]
        for ext in lib_extensions:
            lib_file = f"lib{lib_name}{ext}"
            lib_path = os.path.join(self.package_folder, "lib", lib_file)
            if os.path.exists(lib_path):
                return True
        return False

    def _configure_python_environment(self):
        """Configure Python environment for bundled CPython if available"""
        try:
            if hasattr(self, 'deps_cpp_info') and "sparetools-cpython" in self.deps_cpp_info:
                cpython_info = self.deps_cpp_info["sparetools-cpython"]
                # Prepend CPython bin directory to PATH to ensure bundled Python is found first
                self.runenv_info.prepend_path("PATH", cpython_info.bin_paths[0])
                # Set PYTHONHOME to ensure Python uses the bundled installation
                if hasattr(cpython_info, 'lib_paths') and cpython_info.lib_paths:
                    python_home = cpython_info.lib_paths[0]
                    if python_home.endswith("/lib"):
                        python_home = python_home[:-4]  # Remove /lib to get root
                    self.runenv_info.define_path("PYTHONHOME", python_home)
        except Exception as e:
            self.output.warning(f"Could not configure Python environment: {e}")
