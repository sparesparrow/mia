from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake
from conan.tools.layout import basic_layout


class AiServisConan(ConanFile):
    name = "ai-servis"
    version = "1.0"
    description = "AI Service with MCP and Hardware Control"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_hardware": [True, False],
        "with_mcp": [True, False],
        "with_proxy_mcp": [True, False],  # Kernun proxy MCP integration
        "with_rpi_python": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_hardware": True,
        "with_mcp": True,
        "with_proxy_mcp": False,  # Optional, disabled by default
        "with_rpi_python": False
    }

    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        # Core dependencies - always required
        # NOTE: Using newer versions for CMake 4.x compatibility (cmake_minimum_required >= 3.5)
        self.requires("jsoncpp/1.9.6")       # JSON handling for all components
        self.requires("flatbuffers/24.3.25") # Serialization for all components
        self.requires("libcurl/8.11.1")      # HTTP client for downloads and APIs
        self.requires("openssl/3.4.0")       # SSL/TLS support
        self.requires("zlib/1.3.1")          # Compression support

        # Hardware-specific dependencies
        if self.options.with_hardware:
            self.requires("libgpiod/2.1.3")      # GPIO control for Raspberry Pi
            self.requires("mosquitto/2.0.18")    # MQTT communication

        # MCP-specific dependencies
        if self.options.with_mcp:
            # MCP integration may need additional deps
            pass

        # Kernun proxy MCP integration (optional)
        if self.options.with_proxy_mcp:
            # Kernun MCP tools for network security analysis
            # Provides: analyze_traffic, inspect_session, modify_tls_policy,
            #           update_proxy_rules, update_clearweb_database
            self.requires("kernun-mcp-tools/0.1.0")

        # RPi Python services dependencies
        if self.options.with_rpi_python:
            # Python dependencies are managed via requirements.txt
            # This option allows Conan to track the dependency
            pass
    def build_requirements(self):
        # Tools needed for building
        self.tool_requires("flatbuffers/24.3.25")  # For flatc compiler
        
        # Note: sparetools-cpython available from sparesparrow-conan Cloudsmith remote
        # The bootstrap scripts handle Python environment setup automatically

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Generate CMake toolchain and dependencies
        tc = CMakeToolchain(self)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        # Generate FlatBuffers headers before building
        self._generate_flatbuffers()

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _generate_flatbuffers(self):
        """Generate C++ headers from FlatBuffers schema"""
        import os
        from pathlib import Path

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

    def package(self):
        # Package the executables and libraries
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Define library information
        self.cpp_info.libs = ["webgrab_core"]

        if self.options.with_hardware:
            self.cpp_info.libs.append("hardware-server")

        if self.options.with_mcp:
            self.cpp_info.libs.append("mcp-server")

        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "crypt32", "advapi32"]