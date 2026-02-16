cmake_minimum_required(VERSION 3.5)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(mia_esp32)

# Add FlatBuffers component if needed
# idf_component_register(SRCS "main/main.c" "flatbuffers_generated.c"
#                       INCLUDE_DIRS "main" "include")
#
# Or just the main component
idf_component_register(SRCS "main/main.c"
                      INCLUDE_DIRS "main")