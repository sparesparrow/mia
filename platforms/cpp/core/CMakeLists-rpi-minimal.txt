# Minimal CMakeLists.txt for Raspberry Pi Hardware Server
# This builds just the hardware-server without the complex FlatBuffers infrastructure

cmake_minimum_required(VERSION 3.10)
project(HardwareServer VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(PkgConfig REQUIRED)
find_package(Threads REQUIRED)

# Required: jsoncpp
pkg_check_modules(JSONCPP REQUIRED jsoncpp)

# Required: libgpiod
pkg_check_modules(GPIOD REQUIRED libgpiod)

# Optional: mosquitto (for MQTT support)
pkg_check_modules(MOSQUITTO libmosquitto)

# Define options
option(WITH_MQTT "Enable MQTT support" ${MOSQUITTO_FOUND})

# Compile definitions
if(WITH_MQTT AND MOSQUITTO_FOUND)
    add_compile_definitions(WITH_MQTT=1)
    message(STATUS "MQTT support: enabled")
else()
    add_compile_definitions(WITH_MQTT=0)
    message(STATUS "MQTT support: disabled")
endif()

# Hardware Control Server executable
add_executable(hardware-server
    main_hardware_server.cpp
    HardwareControlServer.cpp
)

target_include_directories(hardware-server PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${JSONCPP_INCLUDE_DIRS}
    ${GPIOD_INCLUDE_DIRS}
)

target_link_libraries(hardware-server PRIVATE
    ${JSONCPP_LIBRARIES}
    ${GPIOD_LIBRARIES}
    Threads::Threads
)

if(WITH_MQTT AND MOSQUITTO_FOUND)
    target_include_directories(hardware-server PRIVATE ${MOSQUITTO_INCLUDE_DIRS})
    target_link_libraries(hardware-server PRIVATE ${MOSQUITTO_LIBRARIES})
endif()

# Installation
install(TARGETS hardware-server
    RUNTIME DESTINATION bin
)

message(STATUS "")
message(STATUS "=== Raspberry Pi Hardware Server Build Configuration ===")
message(STATUS "  Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  MQTT Support: ${WITH_MQTT}")
message(STATUS "")
