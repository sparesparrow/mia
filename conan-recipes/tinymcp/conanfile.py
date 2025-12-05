from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy, save, load, rmdir
from conan.tools.build import check_min_cppstd
import os


class TinyMCPConan(ConanFile):
    """TinyMCP - Lightweight C++ implementation of Model Context Protocol"""
    
    name = "tinymcp"
    version = "0.2.0"
    license = "MIT"
    author = "MIA Team"
    url = "https://github.com/sparesparrow/tinymcp"
    homepage = "https://github.com/sparesparrow/tinymcp"
    description = "A minimalistic, high-performance C++ SDK for implementing MCP servers and clients"
    topics = ("mcp", "model-context-protocol", "json-rpc", "sdk", "lightweight")
    
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_examples": [True, False],
        "with_tests": [True, False],
        "enable_logging": [True, False],
        "use_system_json": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_examples": False,
        "with_tests": False,
        "enable_logging": True,
        "use_system_json": False
    }
    
    # generators are created in generate() method
    
    # Git repository configuration
    _git_url = "https://github.com/sparesparrow/tinymcp.git"
    _git_branch = "master"  # Use master branch
    _git_commit = None  # Use specific commit for reproducibility
    
    @property
    def _min_cppstd(self):
        return "17"
    
    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
    
    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def layout(self):
        cmake_layout(self)
    
    def requirements(self):
        # TinyMCP dependencies
        if not self.options.use_system_json:
            self.requires("jsoncpp/1.9.5")
        
        if self.options.enable_logging:
            self.requires("spdlog/1.13.0")
    
    def build_requirements(self):
        self.tool_requires("cmake/3.28.1")
        if self.options.with_tests:
            self.requires("gtest/1.14.0")
    
    def source(self):
        # Copy local TinyMCP implementation
        src_path = "/workspace/external/tinymcp"
        copy(self, "*", src=src_path, dst=self.source_folder, keep_path=True)
    
    def _apply_patches(self):
        """Apply any necessary patches to TinyMCP source"""
        # Create a CMakeLists.txt if it doesn't exist
        cmakelists_content = """cmake_minimum_required(VERSION 3.15)
project(tinymcp VERSION ${CONAN_PACKAGE_VERSION} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(TINYMCP_BUILD_SHARED "Build shared library" ${TINYMCP_SHARED})
option(TINYMCP_BUILD_EXAMPLES "Build examples" ${TINYMCP_WITH_EXAMPLES})
option(TINYMCP_BUILD_TESTS "Build tests" ${TINYMCP_WITH_TESTS})
option(TINYMCP_ENABLE_LOGGING "Enable logging support" ${TINYMCP_ENABLE_LOGGING})

# Find dependencies
if(NOT TINYMCP_USE_SYSTEM_JSON)
    find_package(jsoncpp REQUIRED)
endif()

if(TINYMCP_ENABLE_LOGGING)
    find_package(spdlog REQUIRED)
endif()

# Source files
set(TINYMCP_HEADERS
    include/tinymcp/protocol.h
    include/tinymcp/server.h
    include/tinymcp/client.h
    include/tinymcp/transport.h
    include/tinymcp/tools.h
    include/tinymcp/resources.h
    include/tinymcp/utils.h
)

set(TINYMCP_SOURCES
    src/protocol.cpp
    src/server.cpp
    src/client.cpp
    src/transport.cpp
    src/tools.cpp
    src/resources.cpp
    src/utils.cpp
)

# Create library
if(TINYMCP_BUILD_SHARED)
    add_library(tinymcp SHARED ${TINYMCP_SOURCES})
    target_compile_definitions(tinymcp PUBLIC TINYMCP_SHARED)
else()
    add_library(tinymcp STATIC ${TINYMCP_SOURCES})
endif()

# Include directories
target_include_directories(tinymcp PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Link dependencies
target_link_libraries(tinymcp PUBLIC
    $<$<NOT:$<BOOL:${TINYMCP_USE_SYSTEM_JSON}>>:JsonCpp::JsonCpp>
    $<$<BOOL:${TINYMCP_ENABLE_LOGGING}>:spdlog::spdlog>
)

# Compile definitions
if(TINYMCP_ENABLE_LOGGING)
    target_compile_definitions(tinymcp PUBLIC TINYMCP_ENABLE_LOGGING)
endif()

# Examples
if(TINYMCP_BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

# Tests
if(TINYMCP_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Installation
include(GNUInstallDirs)

install(TARGETS tinymcp
    EXPORT tinymcp-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/tinymcp
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT tinymcp-targets
    FILE tinymcp-targets.cmake
    NAMESPACE tinymcp::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/tinymcp
)

# Package config
include(CMakePackageConfigHelpers)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/tinymcp-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/tinymcp-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/tinymcp
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/tinymcp-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/tinymcp-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/tinymcp-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/tinymcp
)
"""
        
        if not os.path.exists(os.path.join(self.source_folder, "CMakeLists.txt")):
            save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmakelists_content)
        
        # Create a basic config template if needed
        config_template = """@PACKAGE_INIT@

include("${CMAKE_CURRENT_LIST_DIR}/tinymcp-targets.cmake")

check_required_components(tinymcp)
"""
        cmake_dir = os.path.join(self.source_folder, "cmake")
        if not os.path.exists(cmake_dir):
            os.makedirs(cmake_dir)
        
        config_file = os.path.join(cmake_dir, "tinymcp-config.cmake.in")
        if not os.path.exists(config_file):
            save(self, config_file, config_template)
    
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TINYMCP_SHARED"] = self.options.shared
        tc.variables["TINYMCP_WITH_EXAMPLES"] = self.options.with_examples
        tc.variables["TINYMCP_WITH_TESTS"] = self.options.with_tests
        tc.variables["TINYMCP_ENABLE_LOGGING"] = self.options.enable_logging
        tc.variables["TINYMCP_USE_SYSTEM_JSON"] = self.options.use_system_json
        tc.variables["CONAN_PACKAGE_VERSION"] = self.version
        tc.generate()
        
        deps = CMakeDeps(self)
        deps.generate()
    
    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_folder)
        cmake.build()
        
        if self.options.with_tests:
            cmake.test()
    
    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        
        # Remove CMake files from lib folder
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
    
    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tinymcp")
        self.cpp_info.set_property("cmake_target_name", "tinymcp::tinymcp")
        
        # Library name
        self.cpp_info.libs = ["tinymcp"]
        
        # Defines
        if self.options.shared:
            self.cpp_info.defines.append("TINYMCP_SHARED")
        
        if self.options.enable_logging:
            self.cpp_info.defines.append("TINYMCP_ENABLE_LOGGING")
        
        # System libraries
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread", "m"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32"]
        
        # Backward compatibility
        self.cpp_info.names["cmake_find_package"] = "tinymcp"
        self.cpp_info.names["cmake_find_package_multi"] = "tinymcp"