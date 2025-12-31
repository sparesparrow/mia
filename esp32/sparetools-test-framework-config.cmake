########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(sparetools-test-framework_FIND_QUIETLY)
    set(sparetools-test-framework_MESSAGE_MODE VERBOSE)
else()
    set(sparetools-test-framework_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/sparetools-test-frameworkTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${sparetools-test-framework_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(sparetools-test-framework_VERSION_STRING "1.0.0")
set(sparetools-test-framework_INCLUDE_DIRS ${sparetools-test-framework_INCLUDE_DIRS_RELEASE} )
set(sparetools-test-framework_INCLUDE_DIR ${sparetools-test-framework_INCLUDE_DIRS_RELEASE} )
set(sparetools-test-framework_LIBRARIES ${sparetools-test-framework_LIBRARIES_RELEASE} )
set(sparetools-test-framework_DEFINITIONS ${sparetools-test-framework_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${sparetools-test-framework_BUILD_MODULES_PATHS_RELEASE} )
    message(${sparetools-test-framework_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


