cmake_minimum_required(VERSION 3.20)
project(mcp-cpp-bridge VERSION 1.0.0 LANGUAGES CXX)

# C++ Standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(MCP_BUILD_SHARED "Build shared library" OFF)
option(MCP_WITH_PYTHON "Build Python bindings" ON)
option(MCP_WITH_GRPC "Enable gRPC transport" ON)
option(MCP_WITH_MQTT "Enable MQTT transport" ON)
option(MCP_WITH_WEBSOCKET "Enable WebSocket transport" ON)
option(MCP_ENABLE_TESTING "Enable testing" ON)
option(MCP_ENABLE_BENCHMARKS "Enable benchmarks" OFF)

# Find packages
find_package(tinymcp REQUIRED)
find_package(jsoncpp REQUIRED)
find_package(spdlog REQUIRED)
find_package(fmt REQUIRED)
find_package(asio REQUIRED)
find_package(CURL REQUIRED)
find_package(protobuf REQUIRED)
find_package(flatbuffers REQUIRED)
find_package(Threads REQUIRED)

if(MCP_WITH_GRPC)
    find_package(gRPC REQUIRED)
endif()

if(MCP_WITH_MQTT)
    find_package(mosquitto REQUIRED)
endif()

if(MCP_WITH_WEBSOCKET)
    find_package(websocketpp REQUIRED)
endif()

if(MCP_WITH_PYTHON)
    find_package(pybind11 REQUIRED)
    find_package(Python COMPONENTS Interpreter Development REQUIRED)
endif()

if(MCP_ENABLE_TESTING)
    find_package(GTest REQUIRED)
    enable_testing()
endif()

if(MCP_ENABLE_BENCHMARKS)
    find_package(benchmark REQUIRED)
endif()

# Source files
set(MCP_CORE_SOURCES
    src/core/protocol.cpp
    src/core/message.cpp
    src/core/error.cpp
    src/core/tool.cpp
    src/core/resource.cpp
    src/core/prompt.cpp
    src/core/tinymcp_wrapper.cpp
)

set(MCP_SERVER_SOURCES
    src/server/server.cpp
    src/server/server_impl.cpp
    src/server/request_handler.cpp
    src/server/session_manager.cpp
)

set(MCP_CLIENT_SOURCES
    src/client/client.cpp
    src/client/client_impl.cpp
    src/client/connection_pool.cpp
)

set(MCP_TRANSPORT_SOURCES
    src/transport/transport.cpp
    src/transport/stdio_transport.cpp
    src/transport/tcp_transport.cpp
    src/transport/unix_socket_transport.cpp
)

if(MCP_WITH_GRPC)
    list(APPEND MCP_TRANSPORT_SOURCES src/transport/grpc_transport.cpp)
endif()

if(MCP_WITH_MQTT)
    list(APPEND MCP_TRANSPORT_SOURCES src/transport/mqtt_transport.cpp)
endif()

if(MCP_WITH_WEBSOCKET)
    list(APPEND MCP_TRANSPORT_SOURCES src/transport/websocket_transport.cpp)
endif()

# Main library
if(MCP_BUILD_SHARED)
    add_library(mcp-cpp-bridge SHARED
        ${MCP_CORE_SOURCES}
        ${MCP_SERVER_SOURCES}
        ${MCP_CLIENT_SOURCES}
        ${MCP_TRANSPORT_SOURCES}
    )
    target_compile_definitions(mcp-cpp-bridge PUBLIC MCP_SHARED)
else()
    add_library(mcp-cpp-bridge STATIC
        ${MCP_CORE_SOURCES}
        ${MCP_SERVER_SOURCES}
        ${MCP_CLIENT_SOURCES}
        ${MCP_TRANSPORT_SOURCES}
    )
endif()

# Include directories
target_include_directories(mcp-cpp-bridge PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Link libraries
target_link_libraries(mcp-cpp-bridge PUBLIC
    tinymcp::tinymcp
    JsonCpp::JsonCpp
    spdlog::spdlog
    fmt::fmt
    asio::asio
    CURL::libcurl
    protobuf::protobuf
    flatbuffers::flatbuffers
    Threads::Threads
)

if(MCP_WITH_GRPC)
    target_link_libraries(mcp-cpp-bridge PUBLIC gRPC::grpc++)
    target_compile_definitions(mcp-cpp-bridge PUBLIC MCP_WITH_GRPC)
endif()

if(MCP_WITH_MQTT)
    target_link_libraries(mcp-cpp-bridge PUBLIC mosquitto::mosquitto)
    target_compile_definitions(mcp-cpp-bridge PUBLIC MCP_WITH_MQTT)
endif()

if(MCP_WITH_WEBSOCKET)
    target_link_libraries(mcp-cpp-bridge PUBLIC websocketpp::websocketpp)
    target_compile_definitions(mcp-cpp-bridge PUBLIC MCP_WITH_WEBSOCKET)
endif()

# Python bindings
if(MCP_WITH_PYTHON)
    pybind11_add_module(mcp_cpp_bridge_py 
        python/mcp_cpp_bridge.cpp
    )
    
    target_link_libraries(mcp_cpp_bridge_py PRIVATE
        mcp-cpp-bridge
        pybind11::module
    )
    
    set_target_properties(mcp_cpp_bridge_py PROPERTIES
        OUTPUT_NAME mcp_cpp_bridge
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/python
    )
    
    # Install Python module
    install(TARGETS mcp_cpp_bridge_py
        LIBRARY DESTINATION python
    )
endif()

# Example applications
add_subdirectory(examples)

# Testing
if(MCP_ENABLE_TESTING)
    add_subdirectory(tests)
endif()

# Benchmarks
if(MCP_ENABLE_BENCHMARKS)
    add_subdirectory(benchmarks)
endif()

# Installation
include(GNUInstallDirs)

install(TARGETS mcp-cpp-bridge
    EXPORT mcp-cpp-bridge-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# Export targets
install(EXPORT mcp-cpp-bridge-targets
    FILE mcp-cpp-bridge-targets.cmake
    NAMESPACE mcp::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/mcp-cpp-bridge
)

# Create config file
include(CMakePackageConfigHelpers)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/mcp-cpp-bridge-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/mcp-cpp-bridge-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/mcp-cpp-bridge
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/mcp-cpp-bridge-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/mcp-cpp-bridge-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/mcp-cpp-bridge-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/mcp-cpp-bridge
)

# Helper module for downstream packages
install(FILES
    cmake/MCPHelpers.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/mcp-cpp-bridge
)

# Package configuration
set(CPACK_PACKAGE_NAME ${PROJECT_NAME})
set(CPACK_PACKAGE_VERSION ${PROJECT_VERSION})
set(CPACK_PACKAGE_DESCRIPTION "MCP C++ Bridge - High-performance Model Context Protocol implementation")
set(CPACK_PACKAGE_HOMEPAGE_URL "https://github.com/ai-servis/mcp-cpp-bridge")
set(CPACK_PACKAGE_CONTACT "AI-SERVIS Team")
set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
set(CPACK_RESOURCE_FILE_README "${CMAKE_CURRENT_SOURCE_DIR}/README.md")

include(CPack)