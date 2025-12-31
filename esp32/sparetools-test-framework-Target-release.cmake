# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(sparetools-test-framework_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(sparetools-test-framework_FRAMEWORKS_FOUND_RELEASE "${sparetools-test-framework_FRAMEWORKS_RELEASE}" "${sparetools-test-framework_FRAMEWORK_DIRS_RELEASE}")

set(sparetools-test-framework_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET sparetools-test-framework_DEPS_TARGET)
    add_library(sparetools-test-framework_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET sparetools-test-framework_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${sparetools-test-framework_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${sparetools-test-framework_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### sparetools-test-framework_DEPS_TARGET to all of them
conan_package_library_targets("${sparetools-test-framework_LIBS_RELEASE}"    # libraries
                              "${sparetools-test-framework_LIB_DIRS_RELEASE}" # package_libdir
                              "${sparetools-test-framework_BIN_DIRS_RELEASE}" # package_bindir
                              "${sparetools-test-framework_LIBRARY_TYPE_RELEASE}"
                              "${sparetools-test-framework_IS_HOST_WINDOWS_RELEASE}"
                              sparetools-test-framework_DEPS_TARGET
                              sparetools-test-framework_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "sparetools-test-framework"    # package_name
                              "${sparetools-test-framework_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${sparetools-test-framework_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## GLOBAL TARGET PROPERTIES Release ########################################
    set_property(TARGET sparetools-test-framework::sparetools-test-framework
                 APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                 $<$<CONFIG:Release>:${sparetools-test-framework_OBJECTS_RELEASE}>
                 $<$<CONFIG:Release>:${sparetools-test-framework_LIBRARIES_TARGETS}>
                 )

    if("${sparetools-test-framework_LIBS_RELEASE}" STREQUAL "")
        # If the package is not declaring any "cpp_info.libs" the package deps, system libs,
        # frameworks etc are not linked to the imported targets and we need to do it to the
        # global target
        set_property(TARGET sparetools-test-framework::sparetools-test-framework
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     sparetools-test-framework_DEPS_TARGET)
    endif()

    set_property(TARGET sparetools-test-framework::sparetools-test-framework
                 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                 $<$<CONFIG:Release>:${sparetools-test-framework_LINKER_FLAGS_RELEASE}>)
    set_property(TARGET sparetools-test-framework::sparetools-test-framework
                 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                 $<$<CONFIG:Release>:${sparetools-test-framework_INCLUDE_DIRS_RELEASE}>)
    # Necessary to find LINK shared libraries in Linux
    set_property(TARGET sparetools-test-framework::sparetools-test-framework
                 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                 $<$<CONFIG:Release>:${sparetools-test-framework_LIB_DIRS_RELEASE}>)
    set_property(TARGET sparetools-test-framework::sparetools-test-framework
                 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                 $<$<CONFIG:Release>:${sparetools-test-framework_COMPILE_DEFINITIONS_RELEASE}>)
    set_property(TARGET sparetools-test-framework::sparetools-test-framework
                 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                 $<$<CONFIG:Release>:${sparetools-test-framework_COMPILE_OPTIONS_RELEASE}>)

########## For the modules (FindXXX)
set(sparetools-test-framework_LIBRARIES_RELEASE sparetools-test-framework::sparetools-test-framework)
