cmake_minimum_required(VERSION 3.15)
project(tinymcp VERSION 0.2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(TINYMCP_BUILD_SHARED "Build shared library" OFF)
option(TINYMCP_BUILD_EXAMPLES "Build examples" OFF)
option(TINYMCP_BUILD_TESTS "Build tests" OFF)
option(TINYMCP_ENABLE_LOGGING "Enable logging support" ON)

# Find dependencies
find_package(jsoncpp REQUIRED)
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
target_link_libraries(tinymcp PUBLIC JsonCpp::JsonCpp)
if(TINYMCP_ENABLE_LOGGING)
    target_link_libraries(tinymcp PUBLIC spdlog::spdlog)
    target_compile_definitions(tinymcp PUBLIC TINYMCP_ENABLE_LOGGING)
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