# Load the debug and release variables
file(GLOB DATA_FILES "${CMAKE_CURRENT_LIST_DIR}/sparesparrow-protocols-*-data.cmake")

foreach(f ${DATA_FILES})
    include(${f})
endforeach()

# Create the targets for all the components
foreach(_COMPONENT ${sparesparrow-protocols_COMPONENT_NAMES} )
    if(NOT TARGET ${_COMPONENT})
        add_library(${_COMPONENT} INTERFACE IMPORTED)
        message(${sparesparrow-protocols_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
    endif()
endforeach()

if(NOT TARGET sparesparrow-protocols::sparesparrow-protocols)
    add_library(sparesparrow-protocols::sparesparrow-protocols INTERFACE IMPORTED)
    message(${sparesparrow-protocols_MESSAGE_MODE} "Conan: Target declared 'sparesparrow-protocols::sparesparrow-protocols'")
endif()
# Load the debug and release library finders
file(GLOB CONFIG_FILES "${CMAKE_CURRENT_LIST_DIR}/sparesparrow-protocols-Target-*.cmake")

foreach(f ${CONFIG_FILES})
    include(${f})
endforeach()