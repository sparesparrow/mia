cmake_minimum_required(VERSION 3.10)
project(WebGrabMCPServer)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(CURL REQUIRED)
find_package(Threads REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GPIOD REQUIRED libgpiod)

# Include directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../../../TinyMCP/Source)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../../../TinyMCP/Source/External/jsoncpp/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../)

# Add FlatBuffers generation
find_program(FLATBUFFERS_FLATC_EXECUTABLE flatc)
if(NOT FLATBUFFERS_FLATC_EXECUTABLE)
    message(FATAL_ERROR "FlatBuffers compiler (flatc) not found")
endif()

# Generate FlatBuffers headers
set(FLATBUFFERS_SCHEMA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../)
set(FLATBUFFERS_OUTPUT_DIR ${CMAKE_CURRENT_BINARY_DIR})

add_custom_command(
    OUTPUT ${FLATBUFFERS_OUTPUT_DIR}/webgrab_generated.h
    COMMAND ${FLATBUFFERS_FLATC_EXECUTABLE} --cpp --gen-mutable -o ${FLATBUFFERS_OUTPUT_DIR} ${FLATBUFFERS_SCHEMA_DIR}/webgrab.fbs
    DEPENDS ${FLATBUFFERS_SCHEMA_DIR}/webgrab.fbs
    COMMENT "Generating FlatBuffers C++ headers"
)

# Add executable
add_executable(webgrab-mcp-server
    src/WebGrabMCPServer.cpp
    src/WebGrabMCPServerImpl.cpp
    src/DownloadTask.cpp
    src/StatusTask.cpp
    src/AbortTask.cpp
    src/GPIOTask.cpp
    src/WebGrabClientWrapper.cpp
    ${FLATBUFFERS_OUTPUT_DIR}/webgrab_generated.h
)

# Include generated headers
target_include_directories(webgrab-mcp-server PRIVATE ${FLATBUFFERS_OUTPUT_DIR} ${GPIOD_INCLUDE_DIRS})

# Link libraries
target_link_libraries(webgrab-mcp-server
    ${CURL_LIBRARIES}
    Threads::Threads
    jsoncpp
    ${GPIOD_LIBRARIES}
)

# Copy config file
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.ini ${CMAKE_CURRENT_BINARY_DIR}/config.ini COPYONLY)