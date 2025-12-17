########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(libgpiod_FIND_QUIETLY)
    set(libgpiod_MESSAGE_MODE VERBOSE)
else()
    set(libgpiod_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/libgpiodTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${libgpiod_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(libgpiod_VERSION_STRING "1.6.3")
set(libgpiod_INCLUDE_DIRS ${libgpiod_INCLUDE_DIRS_RELEASE} )
set(libgpiod_INCLUDE_DIR ${libgpiod_INCLUDE_DIRS_RELEASE} )
set(libgpiod_LIBRARIES ${libgpiod_LIBRARIES_RELEASE} )
set(libgpiod_DEFINITIONS ${libgpiod_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${libgpiod_BUILD_MODULES_PATHS_RELEASE} )
    message(${libgpiod_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


