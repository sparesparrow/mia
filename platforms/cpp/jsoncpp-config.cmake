########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(jsoncpp_FIND_QUIETLY)
    set(jsoncpp_MESSAGE_MODE VERBOSE)
else()
    set(jsoncpp_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/jsoncppTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${jsoncpp_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(jsoncpp_VERSION_STRING "1.9.5")
set(jsoncpp_INCLUDE_DIRS ${jsoncpp_INCLUDE_DIRS_RELEASE} )
set(jsoncpp_INCLUDE_DIR ${jsoncpp_INCLUDE_DIRS_RELEASE} )
set(jsoncpp_LIBRARIES ${jsoncpp_LIBRARIES_RELEASE} )
set(jsoncpp_DEFINITIONS ${jsoncpp_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${jsoncpp_BUILD_MODULES_PATHS_RELEASE} )
    message(${jsoncpp_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


