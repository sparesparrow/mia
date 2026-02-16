cmake_minimum_required(VERSION 3.20)
project(MIA VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Find Conan-generated packages
find_package(flatbuffers REQUIRED)
find_package(CURL REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(ZLIB REQUIRED)
find_package(Threads REQUIRED)
# FSM implemented without Boost dependency

# Find jsoncpp via pkg-config (needed for some executables)
find_package(PkgConfig REQUIRED)
pkg_check_modules(JSONCPP REQUIRED jsoncpp)

# Find system libraries
if(UNIX AND NOT APPLE)
    find_package(ALSA REQUIRED)
endif()

# Hardware-specific packages (only if hardware support is enabled)
option(WITH_HARDWARE "Enable hardware support" ON)
if(WITH_HARDWARE)
    find_package(libgpiod REQUIRED)
    find_package(mosquitto REQUIRED)
endif()

# FlatBuffers code generation (ensure header matches installed flatbuffers)
find_program(FLATBUFFERS_FLATC_EXECUTABLE flatc)
if(FLATBUFFERS_FLATC_EXECUTABLE)
    set(FLATBUFFERS_SCHEMA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/core)
    set(FLATBUFFERS_OUTPUT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/core)

    add_custom_target(gen_flatbuffers_headers
        COMMAND ${FLATBUFFERS_FLATC_EXECUTABLE} --cpp --gen-mutable -o ${FLATBUFFERS_OUTPUT_DIR} ${FLATBUFFERS_SCHEMA_DIR}/webgrab.fbs
        BYPRODUCTS ${FLATBUFFERS_OUTPUT_DIR}/webgrab_generated.h
        DEPENDS ${FLATBUFFERS_SCHEMA_DIR}/webgrab.fbs
        COMMENT "Generating FlatBuffers C++ headers"
        VERBATIM
    )
else()
    message(WARNING "FlatBuffers compiler (flatc) not found. Generated headers may be outdated.")
endif()

# Core library
add_library(webgrab_core STATIC
    core/FlatBuffersRequestWriter.cpp
    core/FlatBuffersResponseReader.cpp
    core/FlatBuffersRequestReader.cpp
    core/FlatBuffersResponseWriter.cpp
    core/TcpSocket.cpp
    core/WebGrabClient.cpp
    core/WebGrabServer.cpp
    core/MessageQueueProcessor.cpp
    core/DownloadJob.cpp
    core/JobWorker.cpp
    core/TcpListener.cpp
    core/CurlClientWrapper.cpp
    core/audio_device.cpp
    core/stt_worker.cpp
    core/tts_worker.cpp
    core/voice_control_fsm.cpp
)

# Enable position-independent code for shared library compatibility
set_target_properties(webgrab_core PROPERTIES POSITION_INDEPENDENT_CODE TRUE)

if(TARGET gen_flatbuffers_headers)
    add_dependencies(webgrab_core gen_flatbuffers_headers)
endif()

# Include directories for core library
target_include_directories(webgrab_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/core
)

# Link core library (jsoncpp handled in core library via pkg-config)
target_link_libraries(webgrab_core
    flatbuffers::flatbuffers
    CURL::libcurl
    Threads::Threads
)

# Link ALSA on Linux systems
if(UNIX AND NOT APPLE)
    target_link_libraries(webgrab_core ALSA::ALSA)
endif()

if(WITH_HARDWARE)
    target_link_libraries(webgrab_core mosquitto::mosquitto)
endif()

# Hardware Control Server
if(WITH_HARDWARE)
    add_executable(hardware-server
        core/main_hardware_server.cpp
        core/HardwareControlServer.cpp
    )

    target_link_libraries(hardware-server
        webgrab_core
        libgpiod::libgpiod
        mosquitto::mosquitto
    )
    # Add jsoncpp includes for hardware-server
    target_include_directories(hardware-server PRIVATE ${JSONCPP_INCLUDE_DIRS})
endif()

# Voice Control Server
add_executable(voice-server
    core/main_voice_server.cpp
    core/stt_worker.cpp
    core/tts_worker.cpp
)

target_link_libraries(voice-server
    webgrab_core
)

# MCP Server with FlatBuffers generation - Temporarily disabled due to missing Entity/Server.h
# TODO: Fix missing Entity/Server.h dependency
# Find flatc (should be available via Conan)
# find_program(FLATBUFFERS_FLATC_EXECUTABLE flatc)
# if(FLATBUFFERS_FLATC_EXECUTABLE)
#     # Generate FlatBuffers headers
#     set(FLATBUFFERS_SCHEMA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/core)
#     set(FLATBUFFERS_OUTPUT_DIR ${CMAKE_CURRENT_BINARY_DIR})

#     add_custom_command(
#         OUTPUT ${FLATBUFFERS_OUTPUT_DIR}/webgrab_generated.h
#         COMMAND ${FLATBUFFERS_FLATC_EXECUTABLE} --cpp --gen-mutable -o ${FLATBUFFERS_OUTPUT_DIR} ${FLATBUFFERS_SCHEMA_DIR}/webgrab.fbs
#         DEPENDS ${FLATBUFFERS_SCHEMA_DIR}/webgrab.fbs
#         COMMENT "Generating FlatBuffers C++ headers with Conan flatc"
#     )

#     add_executable(mcp-server
#         core/MCPIntegration/MCPServer/src/WebGrabMCPServer.cpp
#         core/MCPIntegration/MCPServer/src/WebGrabMCPServerImpl.cpp
#         core/MCPIntegration/MCPServer/src/DownloadTask.cpp
#         core/MCPIntegration/MCPServer/src/StatusTask.cpp
#         core/MCPIntegration/MCPServer/src/AbortTask.cpp
#         core/MCPIntegration/MCPServer/src/GPIOTask.cpp
#         core/MCPIntegration/MCPServer/src/WebGrabClientWrapper.cpp
#         ${FLATBUFFERS_OUTPUT_DIR}/webgrab_generated.h
#     )

#     target_include_directories(mcp-server PRIVATE
#         ${FLATBUFFERS_OUTPUT_DIR}
#         ${CMAKE_CURRENT_SOURCE_DIR}/core/MCPIntegration/MCPServer/src
#     )

#     target_link_libraries(mcp-server
#         webgrab_core
#         mosquitto::mosquitto
#         libgpiod::libgpiod
#     )

#     # Copy MCP config
#     configure_file(${CMAKE_CURRENT_SOURCE_DIR}/core/MCPIntegration/MCPServer/config.ini
#                    ${CMAKE_CURRENT_BINARY_DIR}/config.ini COPYONLY)
# else()
#     message(WARNING "FlatBuffers compiler (flatc) not found. MCP server will not be built. Install with: conan install ... --build flatbuffers")
# endif()

# Messages MCP Server (does not depend on FlatBuffers) - Temporarily disabled due to missing Entity/Server.h
# TODO: Fix missing Entity/Server.h dependency
# add_executable(messages-mcp-server
#     core/MCPIntegration/MessagesServer/src/MessagesMCPServer.cpp
#     core/MCPIntegration/MessagesServer/src/MessagesMCPServerImpl.cpp
# )

# Link against core to reuse jsoncpp/libcurl/threads linkage
# target_link_libraries(messages-mcp-server webgrab_core)

# Copy Messages MCP config
# configure_file(${CMAKE_CURRENT_SOURCE_DIR}/core/MCPIntegration/MessagesServer/config.ini
#                ${CMAKE_CURRENT_BINARY_DIR}/messages.config.ini COPYONLY)

# Legacy executables (for compatibility)
add_executable(webgrab-client core/main_client.cpp)
target_link_libraries(webgrab-client webgrab_core)

add_executable(webgrab-server core/main_server.cpp)
target_link_libraries(webgrab-server webgrab_core)

# Linux-specific builds
if(UNIX AND NOT APPLE)
    add_executable(webgrab-linux-host core/main_linux.cpp core/HotReloadManager.cpp)
    target_link_libraries(webgrab-linux-host webgrab_core dl)

    add_library(webgrab SHARED core/WebGrabDll.cpp)
    target_link_libraries(webgrab webgrab_core)
    set_target_properties(webgrab PROPERTIES
        VERSION 1.0.0
        SOVERSION 1
        OUTPUT_NAME webgrab
    )
endif()

# Windows builds
if(WIN32)
    add_library(webgrab_dll SHARED core/WebGrabDll.cpp)
    target_link_libraries(webgrab_dll webgrab_core)
endif()

# Installation rules
install(TARGETS webgrab_core
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

# if(FLATBUFFERS_FLATC_EXECUTABLE)
#     install(FILES ${CMAKE_CURRENT_BINARY_DIR}/config.ini
#         DESTINATION etc/aiservis
#     )
# endif()

# install(FILES ${CMAKE_CURRENT_BINARY_DIR}/messages.config.ini
#     DESTINATION etc/aiservis
# )