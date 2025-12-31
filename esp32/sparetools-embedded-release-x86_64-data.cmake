########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(sparetools-embedded_COMPONENT_NAMES "")
if(DEFINED sparetools-embedded_FIND_DEPENDENCY_NAMES)
  list(APPEND sparetools-embedded_FIND_DEPENDENCY_NAMES sparetools-test-framework)
  list(REMOVE_DUPLICATES sparetools-embedded_FIND_DEPENDENCY_NAMES)
else()
  set(sparetools-embedded_FIND_DEPENDENCY_NAMES sparetools-test-framework)
endif()
set(sparetools-test-framework_FIND_MODE "NO_MODULE")

########### VARIABLES #######################################################################
#############################################################################################
set(sparetools-embedded_PACKAGE_FOLDER_RELEASE "/home/sparrow/.conan2/p/b/spare9cdf7834e7d34/p")
set(sparetools-embedded_BUILD_MODULES_PATHS_RELEASE )


set(sparetools-embedded_INCLUDE_DIRS_RELEASE "${sparetools-embedded_PACKAGE_FOLDER_RELEASE}/include")
set(sparetools-embedded_RES_DIRS_RELEASE )
set(sparetools-embedded_DEFINITIONS_RELEASE )
set(sparetools-embedded_SHARED_LINK_FLAGS_RELEASE )
set(sparetools-embedded_EXE_LINK_FLAGS_RELEASE )
set(sparetools-embedded_OBJECTS_RELEASE )
set(sparetools-embedded_COMPILE_DEFINITIONS_RELEASE )
set(sparetools-embedded_COMPILE_OPTIONS_C_RELEASE )
set(sparetools-embedded_COMPILE_OPTIONS_CXX_RELEASE )
set(sparetools-embedded_LIB_DIRS_RELEASE "${sparetools-embedded_PACKAGE_FOLDER_RELEASE}/lib")
set(sparetools-embedded_BIN_DIRS_RELEASE )
set(sparetools-embedded_LIBRARY_TYPE_RELEASE UNKNOWN)
set(sparetools-embedded_IS_HOST_WINDOWS_RELEASE 0)
set(sparetools-embedded_LIBS_RELEASE )
set(sparetools-embedded_SYSTEM_LIBS_RELEASE )
set(sparetools-embedded_FRAMEWORK_DIRS_RELEASE )
set(sparetools-embedded_FRAMEWORKS_RELEASE )
set(sparetools-embedded_BUILD_DIRS_RELEASE )
set(sparetools-embedded_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(sparetools-embedded_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${sparetools-embedded_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${sparetools-embedded_COMPILE_OPTIONS_C_RELEASE}>")
set(sparetools-embedded_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${sparetools-embedded_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${sparetools-embedded_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${sparetools-embedded_EXE_LINK_FLAGS_RELEASE}>")


set(sparetools-embedded_COMPONENTS_RELEASE )