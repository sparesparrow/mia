# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(sparesparrow-protocols_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(sparesparrow-protocols_FRAMEWORKS_FOUND_RELEASE "${sparesparrow-protocols_FRAMEWORKS_RELEASE}" "${sparesparrow-protocols_FRAMEWORK_DIRS_RELEASE}")

set(sparesparrow-protocols_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET sparesparrow-protocols_DEPS_TARGET)
    add_library(sparesparrow-protocols_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET sparesparrow-protocols_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${sparesparrow-protocols_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${sparesparrow-protocols_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### sparesparrow-protocols_DEPS_TARGET to all of them
conan_package_library_targets("${sparesparrow-protocols_LIBS_RELEASE}"    # libraries
                              "${sparesparrow-protocols_LIB_DIRS_RELEASE}" # package_libdir
                              "${sparesparrow-protocols_BIN_DIRS_RELEASE}" # package_bindir
                              "${sparesparrow-protocols_LIBRARY_TYPE_RELEASE}"
                              "${sparesparrow-protocols_IS_HOST_WINDOWS_RELEASE}"
                              sparesparrow-protocols_DEPS_TARGET
                              sparesparrow-protocols_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "sparesparrow-protocols"    # package_name
                              "${sparesparrow-protocols_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${sparesparrow-protocols_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## COMPONENTS TARGET PROPERTIES Release ########################################

    ########## COMPONENT sparesparrow-protocols::common #############

        set(sparesparrow-protocols_sparesparrow-protocols_common_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(sparesparrow-protocols_sparesparrow-protocols_common_FRAMEWORKS_FOUND_RELEASE "${sparesparrow-protocols_sparesparrow-protocols_common_FRAMEWORKS_RELEASE}" "${sparesparrow-protocols_sparesparrow-protocols_common_FRAMEWORK_DIRS_RELEASE}")

        set(sparesparrow-protocols_sparesparrow-protocols_common_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET sparesparrow-protocols_sparesparrow-protocols_common_DEPS_TARGET)
            add_library(sparesparrow-protocols_sparesparrow-protocols_common_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET sparesparrow-protocols_sparesparrow-protocols_common_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'sparesparrow-protocols_sparesparrow-protocols_common_DEPS_TARGET' to all of them
        conan_package_library_targets("${sparesparrow-protocols_sparesparrow-protocols_common_LIBS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_common_LIB_DIRS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_common_BIN_DIRS_RELEASE}" # package_bindir
                              "${sparesparrow-protocols_sparesparrow-protocols_common_LIBRARY_TYPE_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_common_IS_HOST_WINDOWS_RELEASE}"
                              sparesparrow-protocols_sparesparrow-protocols_common_DEPS_TARGET
                              sparesparrow-protocols_sparesparrow-protocols_common_LIBRARIES_TARGETS
                              "_RELEASE"
                              "sparesparrow-protocols_sparesparrow-protocols_common"
                              "${sparesparrow-protocols_sparesparrow-protocols_common_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET sparesparrow-protocols::common
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_LIBRARIES_TARGETS}>
                     )

        if("${sparesparrow-protocols_sparesparrow-protocols_common_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET sparesparrow-protocols::common
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         sparesparrow-protocols_sparesparrow-protocols_common_DEPS_TARGET)
        endif()

        set_property(TARGET sparesparrow-protocols::common APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::common APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::common APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_LIB_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::common APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::common APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_common_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT sparesparrow-protocols::vehicle #############

        set(sparesparrow-protocols_sparesparrow-protocols_vehicle_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(sparesparrow-protocols_sparesparrow-protocols_vehicle_FRAMEWORKS_FOUND_RELEASE "${sparesparrow-protocols_sparesparrow-protocols_vehicle_FRAMEWORKS_RELEASE}" "${sparesparrow-protocols_sparesparrow-protocols_vehicle_FRAMEWORK_DIRS_RELEASE}")

        set(sparesparrow-protocols_sparesparrow-protocols_vehicle_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET sparesparrow-protocols_sparesparrow-protocols_vehicle_DEPS_TARGET)
            add_library(sparesparrow-protocols_sparesparrow-protocols_vehicle_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET sparesparrow-protocols_sparesparrow-protocols_vehicle_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'sparesparrow-protocols_sparesparrow-protocols_vehicle_DEPS_TARGET' to all of them
        conan_package_library_targets("${sparesparrow-protocols_sparesparrow-protocols_vehicle_LIBS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_vehicle_LIB_DIRS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_vehicle_BIN_DIRS_RELEASE}" # package_bindir
                              "${sparesparrow-protocols_sparesparrow-protocols_vehicle_LIBRARY_TYPE_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_vehicle_IS_HOST_WINDOWS_RELEASE}"
                              sparesparrow-protocols_sparesparrow-protocols_vehicle_DEPS_TARGET
                              sparesparrow-protocols_sparesparrow-protocols_vehicle_LIBRARIES_TARGETS
                              "_RELEASE"
                              "sparesparrow-protocols_sparesparrow-protocols_vehicle"
                              "${sparesparrow-protocols_sparesparrow-protocols_vehicle_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET sparesparrow-protocols::vehicle
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_LIBRARIES_TARGETS}>
                     )

        if("${sparesparrow-protocols_sparesparrow-protocols_vehicle_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET sparesparrow-protocols::vehicle
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         sparesparrow-protocols_sparesparrow-protocols_vehicle_DEPS_TARGET)
        endif()

        set_property(TARGET sparesparrow-protocols::vehicle APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::vehicle APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::vehicle APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_LIB_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::vehicle APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::vehicle APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT sparesparrow-protocols::mcp #############

        set(sparesparrow-protocols_sparesparrow-protocols_mcp_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(sparesparrow-protocols_sparesparrow-protocols_mcp_FRAMEWORKS_FOUND_RELEASE "${sparesparrow-protocols_sparesparrow-protocols_mcp_FRAMEWORKS_RELEASE}" "${sparesparrow-protocols_sparesparrow-protocols_mcp_FRAMEWORK_DIRS_RELEASE}")

        set(sparesparrow-protocols_sparesparrow-protocols_mcp_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET sparesparrow-protocols_sparesparrow-protocols_mcp_DEPS_TARGET)
            add_library(sparesparrow-protocols_sparesparrow-protocols_mcp_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET sparesparrow-protocols_sparesparrow-protocols_mcp_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'sparesparrow-protocols_sparesparrow-protocols_mcp_DEPS_TARGET' to all of them
        conan_package_library_targets("${sparesparrow-protocols_sparesparrow-protocols_mcp_LIBS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_mcp_LIB_DIRS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_mcp_BIN_DIRS_RELEASE}" # package_bindir
                              "${sparesparrow-protocols_sparesparrow-protocols_mcp_LIBRARY_TYPE_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_mcp_IS_HOST_WINDOWS_RELEASE}"
                              sparesparrow-protocols_sparesparrow-protocols_mcp_DEPS_TARGET
                              sparesparrow-protocols_sparesparrow-protocols_mcp_LIBRARIES_TARGETS
                              "_RELEASE"
                              "sparesparrow-protocols_sparesparrow-protocols_mcp"
                              "${sparesparrow-protocols_sparesparrow-protocols_mcp_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET sparesparrow-protocols::mcp
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_LIBRARIES_TARGETS}>
                     )

        if("${sparesparrow-protocols_sparesparrow-protocols_mcp_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET sparesparrow-protocols::mcp
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         sparesparrow-protocols_sparesparrow-protocols_mcp_DEPS_TARGET)
        endif()

        set_property(TARGET sparesparrow-protocols::mcp APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::mcp APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::mcp APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_LIB_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::mcp APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::mcp APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mcp_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT sparesparrow-protocols::mia #############

        set(sparesparrow-protocols_sparesparrow-protocols_mia_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(sparesparrow-protocols_sparesparrow-protocols_mia_FRAMEWORKS_FOUND_RELEASE "${sparesparrow-protocols_sparesparrow-protocols_mia_FRAMEWORKS_RELEASE}" "${sparesparrow-protocols_sparesparrow-protocols_mia_FRAMEWORK_DIRS_RELEASE}")

        set(sparesparrow-protocols_sparesparrow-protocols_mia_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET sparesparrow-protocols_sparesparrow-protocols_mia_DEPS_TARGET)
            add_library(sparesparrow-protocols_sparesparrow-protocols_mia_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET sparesparrow-protocols_sparesparrow-protocols_mia_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'sparesparrow-protocols_sparesparrow-protocols_mia_DEPS_TARGET' to all of them
        conan_package_library_targets("${sparesparrow-protocols_sparesparrow-protocols_mia_LIBS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_mia_LIB_DIRS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_mia_BIN_DIRS_RELEASE}" # package_bindir
                              "${sparesparrow-protocols_sparesparrow-protocols_mia_LIBRARY_TYPE_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_mia_IS_HOST_WINDOWS_RELEASE}"
                              sparesparrow-protocols_sparesparrow-protocols_mia_DEPS_TARGET
                              sparesparrow-protocols_sparesparrow-protocols_mia_LIBRARIES_TARGETS
                              "_RELEASE"
                              "sparesparrow-protocols_sparesparrow-protocols_mia"
                              "${sparesparrow-protocols_sparesparrow-protocols_mia_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET sparesparrow-protocols::mia
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_LIBRARIES_TARGETS}>
                     )

        if("${sparesparrow-protocols_sparesparrow-protocols_mia_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET sparesparrow-protocols::mia
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         sparesparrow-protocols_sparesparrow-protocols_mia_DEPS_TARGET)
        endif()

        set_property(TARGET sparesparrow-protocols::mia APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::mia APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::mia APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_LIB_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::mia APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::mia APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_mia_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT sparesparrow-protocols::bpm #############

        set(sparesparrow-protocols_sparesparrow-protocols_bpm_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(sparesparrow-protocols_sparesparrow-protocols_bpm_FRAMEWORKS_FOUND_RELEASE "${sparesparrow-protocols_sparesparrow-protocols_bpm_FRAMEWORKS_RELEASE}" "${sparesparrow-protocols_sparesparrow-protocols_bpm_FRAMEWORK_DIRS_RELEASE}")

        set(sparesparrow-protocols_sparesparrow-protocols_bpm_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET sparesparrow-protocols_sparesparrow-protocols_bpm_DEPS_TARGET)
            add_library(sparesparrow-protocols_sparesparrow-protocols_bpm_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET sparesparrow-protocols_sparesparrow-protocols_bpm_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'sparesparrow-protocols_sparesparrow-protocols_bpm_DEPS_TARGET' to all of them
        conan_package_library_targets("${sparesparrow-protocols_sparesparrow-protocols_bpm_LIBS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_bpm_LIB_DIRS_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_bpm_BIN_DIRS_RELEASE}" # package_bindir
                              "${sparesparrow-protocols_sparesparrow-protocols_bpm_LIBRARY_TYPE_RELEASE}"
                              "${sparesparrow-protocols_sparesparrow-protocols_bpm_IS_HOST_WINDOWS_RELEASE}"
                              sparesparrow-protocols_sparesparrow-protocols_bpm_DEPS_TARGET
                              sparesparrow-protocols_sparesparrow-protocols_bpm_LIBRARIES_TARGETS
                              "_RELEASE"
                              "sparesparrow-protocols_sparesparrow-protocols_bpm"
                              "${sparesparrow-protocols_sparesparrow-protocols_bpm_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET sparesparrow-protocols::bpm
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_LIBRARIES_TARGETS}>
                     )

        if("${sparesparrow-protocols_sparesparrow-protocols_bpm_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET sparesparrow-protocols::bpm
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         sparesparrow-protocols_sparesparrow-protocols_bpm_DEPS_TARGET)
        endif()

        set_property(TARGET sparesparrow-protocols::bpm APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::bpm APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::bpm APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_LIB_DIRS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::bpm APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET sparesparrow-protocols::bpm APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${sparesparrow-protocols_sparesparrow-protocols_bpm_COMPILE_OPTIONS_RELEASE}>)


    ########## AGGREGATED GLOBAL TARGET WITH THE COMPONENTS #####################
    set_property(TARGET sparesparrow-protocols::sparesparrow-protocols APPEND PROPERTY INTERFACE_LINK_LIBRARIES sparesparrow-protocols::common)
    set_property(TARGET sparesparrow-protocols::sparesparrow-protocols APPEND PROPERTY INTERFACE_LINK_LIBRARIES sparesparrow-protocols::vehicle)
    set_property(TARGET sparesparrow-protocols::sparesparrow-protocols APPEND PROPERTY INTERFACE_LINK_LIBRARIES sparesparrow-protocols::mcp)
    set_property(TARGET sparesparrow-protocols::sparesparrow-protocols APPEND PROPERTY INTERFACE_LINK_LIBRARIES sparesparrow-protocols::mia)
    set_property(TARGET sparesparrow-protocols::sparesparrow-protocols APPEND PROPERTY INTERFACE_LINK_LIBRARIES sparesparrow-protocols::bpm)

########## For the modules (FindXXX)
set(sparesparrow-protocols_LIBRARIES_RELEASE sparesparrow-protocols::sparesparrow-protocols)
