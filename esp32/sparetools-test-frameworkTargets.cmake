# Load the debug and release variables
file(GLOB DATA_FILES "${CMAKE_CURRENT_LIST_DIR}/sparetools-test-framework-*-data.cmake")

foreach(f ${DATA_FILES})
    include(${f})
endforeach()

# Create the targets for all the components
foreach(_COMPONENT ${sparetools-test-framework_COMPONENT_NAMES} )
    if(NOT TARGET ${_COMPONENT})
        add_library(${_COMPONENT} INTERFACE IMPORTED)
        message(${sparetools-test-framework_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
    endif()
endforeach()

if(NOT TARGET sparetools-test-framework::sparetools-test-framework)
    add_library(sparetools-test-framework::sparetools-test-framework INTERFACE IMPORTED)
    message(${sparetools-test-framework_MESSAGE_MODE} "Conan: Target declared 'sparetools-test-framework::sparetools-test-framework'")
endif()
# Load the debug and release library finders
file(GLOB CONFIG_FILES "${CMAKE_CURRENT_LIST_DIR}/sparetools-test-framework-Target-*.cmake")

foreach(f ${CONFIG_FILES})
    include(${f})
endforeach()