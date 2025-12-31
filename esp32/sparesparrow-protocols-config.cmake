########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(sparesparrow-protocols_FIND_QUIETLY)
    set(sparesparrow-protocols_MESSAGE_MODE VERBOSE)
else()
    set(sparesparrow-protocols_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/sparesparrow-protocolsTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${sparesparrow-protocols_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(sparesparrow-protocols_VERSION_STRING "1.0.0")
set(sparesparrow-protocols_INCLUDE_DIRS ${sparesparrow-protocols_INCLUDE_DIRS_RELEASE} )
set(sparesparrow-protocols_INCLUDE_DIR ${sparesparrow-protocols_INCLUDE_DIRS_RELEASE} )
set(sparesparrow-protocols_LIBRARIES ${sparesparrow-protocols_LIBRARIES_RELEASE} )
set(sparesparrow-protocols_DEFINITIONS ${sparesparrow-protocols_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${sparesparrow-protocols_BUILD_MODULES_PATHS_RELEASE} )
    message(${sparesparrow-protocols_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


