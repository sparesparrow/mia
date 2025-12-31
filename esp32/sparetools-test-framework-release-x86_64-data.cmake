########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(sparetools-test-framework_COMPONENT_NAMES "")
if(DEFINED sparetools-test-framework_FIND_DEPENDENCY_NAMES)
  list(APPEND sparetools-test-framework_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES sparetools-test-framework_FIND_DEPENDENCY_NAMES)
else()
  set(sparetools-test-framework_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(sparetools-test-framework_PACKAGE_FOLDER_RELEASE "/home/sparrow/.conan2/p/b/sparecab2724936d27/p")
set(sparetools-test-framework_BUILD_MODULES_PATHS_RELEASE )


set(sparetools-test-framework_INCLUDE_DIRS_RELEASE "${sparetools-test-framework_PACKAGE_FOLDER_RELEASE}/include")
set(sparetools-test-framework_RES_DIRS_RELEASE )
set(sparetools-test-framework_DEFINITIONS_RELEASE )
set(sparetools-test-framework_SHARED_LINK_FLAGS_RELEASE )
set(sparetools-test-framework_EXE_LINK_FLAGS_RELEASE )
set(sparetools-test-framework_OBJECTS_RELEASE )
set(sparetools-test-framework_COMPILE_DEFINITIONS_RELEASE )
set(sparetools-test-framework_COMPILE_OPTIONS_C_RELEASE )
set(sparetools-test-framework_COMPILE_OPTIONS_CXX_RELEASE )
set(sparetools-test-framework_LIB_DIRS_RELEASE "${sparetools-test-framework_PACKAGE_FOLDER_RELEASE}/lib")
set(sparetools-test-framework_BIN_DIRS_RELEASE )
set(sparetools-test-framework_LIBRARY_TYPE_RELEASE UNKNOWN)
set(sparetools-test-framework_IS_HOST_WINDOWS_RELEASE 0)
set(sparetools-test-framework_LIBS_RELEASE )
set(sparetools-test-framework_SYSTEM_LIBS_RELEASE )
set(sparetools-test-framework_FRAMEWORK_DIRS_RELEASE )
set(sparetools-test-framework_FRAMEWORKS_RELEASE )
set(sparetools-test-framework_BUILD_DIRS_RELEASE )
set(sparetools-test-framework_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(sparetools-test-framework_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${sparetools-test-framework_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${sparetools-test-framework_COMPILE_OPTIONS_C_RELEASE}>")
set(sparetools-test-framework_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${sparetools-test-framework_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${sparetools-test-framework_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${sparetools-test-framework_EXE_LINK_FLAGS_RELEASE}>")


set(sparetools-test-framework_COMPONENTS_RELEASE )