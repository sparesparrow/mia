########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

list(APPEND libgpiod_COMPONENT_NAMES libgpiod::gpiod)
list(REMOVE_DUPLICATES libgpiod_COMPONENT_NAMES)
if(DEFINED libgpiod_FIND_DEPENDENCY_NAMES)
  list(APPEND libgpiod_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES libgpiod_FIND_DEPENDENCY_NAMES)
else()
  set(libgpiod_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(libgpiod_PACKAGE_FOLDER_RELEASE "/home/mia/.conan2/p/b/libgp893f4e4a0ed1c/p")
set(libgpiod_BUILD_MODULES_PATHS_RELEASE )


set(libgpiod_INCLUDE_DIRS_RELEASE "${libgpiod_PACKAGE_FOLDER_RELEASE}/include")
set(libgpiod_RES_DIRS_RELEASE )
set(libgpiod_DEFINITIONS_RELEASE )
set(libgpiod_SHARED_LINK_FLAGS_RELEASE )
set(libgpiod_EXE_LINK_FLAGS_RELEASE )
set(libgpiod_OBJECTS_RELEASE )
set(libgpiod_COMPILE_DEFINITIONS_RELEASE )
set(libgpiod_COMPILE_OPTIONS_C_RELEASE )
set(libgpiod_COMPILE_OPTIONS_CXX_RELEASE )
set(libgpiod_LIB_DIRS_RELEASE "${libgpiod_PACKAGE_FOLDER_RELEASE}/lib")
set(libgpiod_BIN_DIRS_RELEASE )
set(libgpiod_LIBRARY_TYPE_RELEASE STATIC)
set(libgpiod_IS_HOST_WINDOWS_RELEASE 0)
set(libgpiod_LIBS_RELEASE gpiod)
set(libgpiod_SYSTEM_LIBS_RELEASE )
set(libgpiod_FRAMEWORK_DIRS_RELEASE )
set(libgpiod_FRAMEWORKS_RELEASE )
set(libgpiod_BUILD_DIRS_RELEASE )
set(libgpiod_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(libgpiod_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${libgpiod_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${libgpiod_COMPILE_OPTIONS_C_RELEASE}>")
set(libgpiod_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${libgpiod_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${libgpiod_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${libgpiod_EXE_LINK_FLAGS_RELEASE}>")


set(libgpiod_COMPONENTS_RELEASE libgpiod::gpiod)
########### COMPONENT libgpiod::gpiod VARIABLES ############################################

set(libgpiod_libgpiod_gpiod_INCLUDE_DIRS_RELEASE "${libgpiod_PACKAGE_FOLDER_RELEASE}/include")
set(libgpiod_libgpiod_gpiod_LIB_DIRS_RELEASE "${libgpiod_PACKAGE_FOLDER_RELEASE}/lib")
set(libgpiod_libgpiod_gpiod_BIN_DIRS_RELEASE )
set(libgpiod_libgpiod_gpiod_LIBRARY_TYPE_RELEASE STATIC)
set(libgpiod_libgpiod_gpiod_IS_HOST_WINDOWS_RELEASE 0)
set(libgpiod_libgpiod_gpiod_RES_DIRS_RELEASE )
set(libgpiod_libgpiod_gpiod_DEFINITIONS_RELEASE )
set(libgpiod_libgpiod_gpiod_OBJECTS_RELEASE )
set(libgpiod_libgpiod_gpiod_COMPILE_DEFINITIONS_RELEASE )
set(libgpiod_libgpiod_gpiod_COMPILE_OPTIONS_C_RELEASE "")
set(libgpiod_libgpiod_gpiod_COMPILE_OPTIONS_CXX_RELEASE "")
set(libgpiod_libgpiod_gpiod_LIBS_RELEASE gpiod)
set(libgpiod_libgpiod_gpiod_SYSTEM_LIBS_RELEASE )
set(libgpiod_libgpiod_gpiod_FRAMEWORK_DIRS_RELEASE )
set(libgpiod_libgpiod_gpiod_FRAMEWORKS_RELEASE )
set(libgpiod_libgpiod_gpiod_DEPENDENCIES_RELEASE )
set(libgpiod_libgpiod_gpiod_SHARED_LINK_FLAGS_RELEASE )
set(libgpiod_libgpiod_gpiod_EXE_LINK_FLAGS_RELEASE )
set(libgpiod_libgpiod_gpiod_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(libgpiod_libgpiod_gpiod_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${libgpiod_libgpiod_gpiod_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${libgpiod_libgpiod_gpiod_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${libgpiod_libgpiod_gpiod_EXE_LINK_FLAGS_RELEASE}>
)
set(libgpiod_libgpiod_gpiod_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${libgpiod_libgpiod_gpiod_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${libgpiod_libgpiod_gpiod_COMPILE_OPTIONS_C_RELEASE}>")