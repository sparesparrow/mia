from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import copy, save
from conan.tools.build import check_min_cppstd
from conan.tools.scm import Git
import os


class MCPCppBridgeConan(ConanFile):
    """MCP C++ Bridge - Advanced integration between MCP Python and C++ components"""
    
    name = "mcp-cpp-bridge"
    version = "1.0.0"
    description = "Model Context Protocol C++ Bridge with Python integration"
    license = "MIT"
    url = "https://github.com/ai-servis/mcp-cpp-bridge"
    homepage = "https://ai-servis.io"
    topics = ("mcp", "rpc", "json-rpc", "microservices", "orchestration")
    
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_python": [True, False],
        "with_grpc": [True, False],
        "with_mqtt": [True, False],
        "with_websocket": [True, False],
        "enable_testing": [True, False],
        "enable_benchmarks": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_python": True,
        "with_grpc": True,
        "with_mqtt": True,
        "with_websocket": True,
        "enable_testing": True,
        "enable_benchmarks": False
    }
    
    generators = "CMakeToolchain", "CMakeDeps"
    
    def validate(self):
        check_min_cppstd(self, "20")
    
    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            
    def layout(self):
        cmake_layout(self, src_folder="src")
        
    def requirements(self):
        # TinyMCP as base MCP implementation
        self.requires("tinymcp/0.2.0@ai-servis/stable")
        
        # Core dependencies
        self.requires("jsoncpp/1.9.5")
        self.requires("spdlog/1.13.0")
        self.requires("fmt/10.2.1")
        
        # Async and networking
        self.requires("asio/1.28.2")
        self.requires("libcurl/8.5.0")
        
        # Serialization
        self.requires("protobuf/3.21.12")
        self.requires("flatbuffers/23.5.26")
        
        # Testing
        if self.options.enable_testing:
            self.requires("gtest/1.14.0")
            self.requires("benchmark/1.8.3")
        
        # Optional features
        if self.options.with_grpc:
            self.requires("grpc/1.54.3")
            
        if self.options.with_mqtt:
            self.requires("mosquitto/2.0.18")
            
        if self.options.with_websocket:
            self.requires("websocketpp/0.8.2")
            
        if self.options.with_python:
            self.requires("pybind11/2.11.1")
            
    def build_requirements(self):
        self.tool_requires("cmake/3.28.1")
        self.tool_requires("protobuf/3.21.12")  # For protoc
        if self.options.with_grpc:
            self.tool_requires("grpc/1.54.3")  # For grpc plugins
    
    def source(self):
        # In real scenario, would clone from git
        # Git(self).clone(url=self.url, target=".")
        pass
        
    def generate(self):
        # Generate CMake toolchain
        tc = CMakeToolchain(self)
        tc.variables["MCP_BUILD_SHARED"] = self.options.shared
        tc.variables["MCP_WITH_PYTHON"] = self.options.with_python
        tc.variables["MCP_WITH_GRPC"] = self.options.with_grpc
        tc.variables["MCP_WITH_MQTT"] = self.options.with_mqtt
        tc.variables["MCP_WITH_WEBSOCKET"] = self.options.with_websocket
        tc.variables["MCP_ENABLE_TESTING"] = self.options.enable_testing
        tc.variables["MCP_ENABLE_BENCHMARKS"] = self.options.enable_benchmarks
        tc.generate()
        
        # Generate CMake dependencies
        deps = CMakeDeps(self)
        deps.generate()
        
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        
    def package(self):
        cmake = CMake(self)
        cmake.install()
        
        # Package license
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        
        # Package Python bindings if enabled
        if self.options.with_python:
            copy(self, "*.py", 
                 src=os.path.join(self.build_folder, "python"),
                 dst=os.path.join(self.package_folder, "python"))
                 
    def package_info(self):
        self.cpp_info.libs = ["mcp-cpp-bridge"]
        
        if self.options.shared:
            self.cpp_info.defines.append("MCP_SHARED")
            
        # Add Python path if Python bindings are enabled
        if self.options.with_python:
            self.python_info.append_path = os.path.join(self.package_folder, "python")
            
        # System libraries
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "crypt32", "advapi32"]
            
        # Export build modules for downstream packages
        self.cpp_info.set_property("cmake_build_modules", [
            os.path.join("lib", "cmake", "mcp-cpp-bridge", "MCPHelpers.cmake")
        ])