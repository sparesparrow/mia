# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(sparetools-embedded_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(sparetools-embedded_FRAMEWORKS_FOUND_RELEASE "${sparetools-embedded_FRAMEWORKS_RELEASE}" "${sparetools-embedded_FRAMEWORK_DIRS_RELEASE}")

set(sparetools-embedded_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET sparetools-embedded_DEPS_TARGET)
    add_library(sparetools-embedded_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET sparetools-embedded_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${sparetools-embedded_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${sparetools-embedded_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:sparetools-test-framework::sparetools-test-framework>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### sparetools-embedded_DEPS_TARGET to all of them
conan_package_library_targets("${sparetools-embedded_LIBS_RELEASE}"    # libraries
                              "${sparetools-embedded_LIB_DIRS_RELEASE}" # package_libdir
                              "${sparetools-embedded_BIN_DIRS_RELEASE}" # package_bindir
                              "${sparetools-embedded_LIBRARY_TYPE_RELEASE}"
                              "${sparetools-embedded_IS_HOST_WINDOWS_RELEASE}"
                              sparetools-embedded_DEPS_TARGET
                              sparetools-embedded_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "sparetools-embedded"    # package_name
                              "${sparetools-embedded_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${sparetools-embedded_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## GLOBAL TARGET PROPERTIES Release ########################################
    set_property(TARGET sparetools-embedded::sparetools-embedded
                 APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                 $<$<CONFIG:Release>:${sparetools-embedded_OBJECTS_RELEASE}>
                 $<$<CONFIG:Release>:${sparetools-embedded_LIBRARIES_TARGETS}>
                 )

    if("${sparetools-embedded_LIBS_RELEASE}" STREQUAL "")
        # If the package is not declaring any "cpp_info.libs" the package deps, system libs,
        # frameworks etc are not linked to the imported targets and we need to do it to the
        # global target
        set_property(TARGET sparetools-embedded::sparetools-embedded
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     sparetools-embedded_DEPS_TARGET)
    endif()

    set_property(TARGET sparetools-embedded::sparetools-embedded
                 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                 $<$<CONFIG:Release>:${sparetools-embedded_LINKER_FLAGS_RELEASE}>)
    set_property(TARGET sparetools-embedded::sparetools-embedded
                 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                 $<$<CONFIG:Release>:${sparetools-embedded_INCLUDE_DIRS_RELEASE}>)
    # Necessary to find LINK shared libraries in Linux
    set_property(TARGET sparetools-embedded::sparetools-embedded
                 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                 $<$<CONFIG:Release>:${sparetools-embedded_LIB_DIRS_RELEASE}>)
    set_property(TARGET sparetools-embedded::sparetools-embedded
                 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                 $<$<CONFIG:Release>:${sparetools-embedded_COMPILE_DEFINITIONS_RELEASE}>)
    set_property(TARGET sparetools-embedded::sparetools-embedded
                 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                 $<$<CONFIG:Release>:${sparetools-embedded_COMPILE_OPTIONS_RELEASE}>)

########## For the modules (FindXXX)
set(sparetools-embedded_LIBRARIES_RELEASE sparetools-embedded::sparetools-embedded)
