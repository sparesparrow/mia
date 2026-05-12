cmake_minimum_required(VERSION 3.10)
project(WebGrab)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(CURL REQUIRED)
find_package(Threads REQUIRED)

# FSM implemented without external dependencies

# Find JSON library — prefer Conan-generated CMake config, fall back to pkg-config
find_package(jsoncpp QUIET)
if(NOT jsoncpp_FOUND)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(JSONCPP REQUIRED jsoncpp)
    set(JSONCPP_TARGET_NAME "")
else()
    if(TARGET jsoncpp_lib)
        set(JSONCPP_TARGET_NAME jsoncpp_lib)
    elseif(TARGET JsonCpp::JsonCpp)
        set(JSONCPP_TARGET_NAME JsonCpp::JsonCpp)
    else()
        set(JSONCPP_TARGET_NAME "")
    endif()
endif()

# Find ALSA for audio I/O
pkg_check_modules(ALSA alsa)

# Find Mosquitto MQTT library (pkg-config name is libmosquitto on Debian)
pkg_check_modules(MOSQUITTO libmosquitto)

include_directories(${CMAKE_CURRENT_SOURCE_DIR})
include_directories(/usr/include) # For FlatBuffers

# Linux-specific: Use pkg-config for flatbuffers if available, else assume installed
find_library(FLATBUFFERS_LIBRARY flatbuffers)
if(NOT FLATBUFFERS_LIBRARY)
    message(FATAL_ERROR "FlatBuffers library not found")
endif()

add_library(webgrab_lib
    FlatBuffersRequestWriter.cpp
    FlatBuffersResponseReader.cpp
    FlatBuffersRequestReader.cpp
    FlatBuffersResponseWriter.cpp
    TcpSocket.cpp
    WebGrabClient.cpp
    WebGrabServer.cpp
    MessageQueueProcessor.cpp
    DownloadJob.cpp
    JobWorker.cpp
    TcpListener.cpp
    CurlClientWrapper.cpp
    CoreOrchestrator.cpp
    UIAdapter.cpp
    ContextManager.cpp
    # Voice Control Components
    voice_control_fsm.cpp
    audio_device.cpp
    stt_worker.cpp
    tts_worker.cpp
)

target_link_libraries(webgrab_lib
    ${FLATBUFFERS_LIBRARY}
    CURL::libcurl
    Threads::Threads
    ${ALSA_LIBRARIES}
)

# Link jsoncpp via Conan target or pkg-config
if(JSONCPP_TARGET_NAME)
    target_link_libraries(webgrab_lib ${JSONCPP_TARGET_NAME})
else()
    target_link_libraries(webgrab_lib ${JSONCPP_LIBRARIES})
    target_include_directories(webgrab_lib PRIVATE ${JSONCPP_INCLUDE_DIRS})
endif()

add_executable(webgrab-client main_client.cpp)
target_link_libraries(webgrab-client webgrab_lib)

add_executable(webgrab-server main_server.cpp)
target_link_libraries(webgrab-server webgrab_lib)

# Linux host application with hot reload
if(UNIX AND NOT APPLE)
    add_executable(webgrab-linux-host main_linux.cpp HotReloadManager.cpp)
    target_link_libraries(webgrab-linux-host dl)
endif()

# Linux Shared Library (equivalent to Windows DLL)
if(UNIX AND NOT APPLE)
    add_library(webgrab SHARED WebGrabDll.cpp)
    target_link_libraries(webgrab webgrab_lib)
    set_target_properties(webgrab PROPERTIES
        VERSION 1.0.0
        SOVERSION 1
        OUTPUT_NAME webgrab
    )
endif()

# Hardware Control Server
# pkg-config name is libgpiod on most systems
pkg_check_modules(GPIOD REQUIRED libgpiod)
add_executable(hardware-server
    main_hardware_server.cpp
    HardwareControlServer.cpp
)
target_link_libraries(hardware-server
    webgrab_lib
    ${GPIOD_LIBRARIES}
    ${MOSQUITTO_LIBRARIES}
)
if(JSONCPP_TARGET_NAME)
    target_link_libraries(hardware-server ${JSONCPP_TARGET_NAME})
else()
    target_link_libraries(hardware-server ${JSONCPP_LIBRARIES})
endif()
target_include_directories(hardware-server PRIVATE 
    ${GPIOD_INCLUDE_DIRS}
    ${MOSQUITTO_INCLUDE_DIRS}
)

# Optional: Windows DLL (placeholder for MinGW)
if(WIN32)
    add_library(webgrab_dll SHARED WebGrabDll.cpp)
    target_link_libraries(webgrab_dll webgrab_lib)
endif()

# Raspberry Pi Main Application
add_executable(mia-rpi main_raspberry_pi.cpp HardwareControlServer.cpp)
target_link_libraries(mia-rpi
    webgrab_lib
    ${GPIOD_LIBRARIES}
    ${MOSQUITTO_LIBRARIES}
)
if(JSONCPP_TARGET_NAME)
    target_link_libraries(mia-rpi ${JSONCPP_TARGET_NAME})
else()
    target_link_libraries(mia-rpi ${JSONCPP_LIBRARIES})
endif()
target_include_directories(mia-rpi PRIVATE
    ${GPIOD_INCLUDE_DIRS}
    ${MOSQUITTO_INCLUDE_DIRS}
)

# Unit tests
enable_testing()
add_executable(tests 
    tests/test_main.cpp
    tests/test_tcp_socket.cpp
    tests/test_gpio_control.cpp
    tests/test_orchestrator.cpp
    tests/test_gpio_tcp.cpp
)
target_link_libraries(tests
    webgrab_lib
    ${GPIOD_LIBRARIES}
    ${JSONCPP_LIBRARIES}
    Threads::Threads
)
target_include_directories(tests PRIVATE 
    ${GPIOD_INCLUDE_DIRS}
    ${JSONCPP_INCLUDE_DIRS}
)
add_test(NAME BasicTests COMMAND tests)