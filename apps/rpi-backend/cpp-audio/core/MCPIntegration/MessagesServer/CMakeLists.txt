cmake_minimum_required(VERSION 3.10)
project(MessagesMCPServer)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(Threads REQUIRED)
find_package(PkgConfig REQUIRED)

# jsoncpp via pkg-config if available
pkg_check_modules(JSONCPP jsoncpp)

# Include directories (TinyMCP headers expected to be available similarly to WebGrab server)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../../../TinyMCP/Source)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../../../TinyMCP/Source/External/jsoncpp/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../)

# Add executable
add_executable(messages-mcp-server
    src/MessagesMCPServer.cpp
    src/MessagesMCPServerImpl.cpp
)

# Link libraries
if (JSONCPP_FOUND)
    target_link_libraries(messages-mcp-server ${JSONCPP_LIBRARIES})
else()
    # Fallback to system jsoncpp name
    target_link_libraries(messages-mcp-server jsoncpp)
endif()

target_link_libraries(messages-mcp-server
    Threads::Threads
)

# Copy config file
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.ini ${CMAKE_CURRENT_BINARY_DIR}/config.ini COPYONLY)

