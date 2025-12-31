# Load the debug and release variables
file(GLOB DATA_FILES "${CMAKE_CURRENT_LIST_DIR}/sparetools-embedded-*-data.cmake")

foreach(f ${DATA_FILES})
    include(${f})
endforeach()

# Create the targets for all the components
foreach(_COMPONENT ${sparetools-embedded_COMPONENT_NAMES} )
    if(NOT TARGET ${_COMPONENT})
        add_library(${_COMPONENT} INTERFACE IMPORTED)
        message(${sparetools-embedded_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
    endif()
endforeach()

if(NOT TARGET sparetools-embedded::sparetools-embedded)
    add_library(sparetools-embedded::sparetools-embedded INTERFACE IMPORTED)
    message(${sparetools-embedded_MESSAGE_MODE} "Conan: Target declared 'sparetools-embedded::sparetools-embedded'")
endif()
# Load the debug and release library finders
file(GLOB CONFIG_FILES "${CMAKE_CURRENT_LIST_DIR}/sparetools-embedded-Target-*.cmake")

foreach(f ${CONFIG_FILES})
    include(${f})
endforeach()