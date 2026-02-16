cmake_minimum_required(VERSION 3.10)
project(WebGrabMCPClient)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../TinyMCP/Source)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../TinyMCP/Source/External/jsoncpp/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../)

# Add executable
add_executable(webgrab-mcp-client
    src/MCPClientSimulator.cpp
)

# Link libraries
target_link_libraries(webgrab-mcp-client
    jsoncpp
)