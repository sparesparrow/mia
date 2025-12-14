########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(jsoncpp_COMPONENT_NAMES "")
if(DEFINED jsoncpp_FIND_DEPENDENCY_NAMES)
  list(APPEND jsoncpp_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES jsoncpp_FIND_DEPENDENCY_NAMES)
else()
  set(jsoncpp_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(jsoncpp_PACKAGE_FOLDER_RELEASE "/home/mia/.conan2/p/b/jsonc4673fc0877213/p")
set(jsoncpp_BUILD_MODULES_PATHS_RELEASE )


set(jsoncpp_INCLUDE_DIRS_RELEASE "${jsoncpp_PACKAGE_FOLDER_RELEASE}/include")
set(jsoncpp_RES_DIRS_RELEASE )
set(jsoncpp_DEFINITIONS_RELEASE )
set(jsoncpp_SHARED_LINK_FLAGS_RELEASE )
set(jsoncpp_EXE_LINK_FLAGS_RELEASE )
set(jsoncpp_OBJECTS_RELEASE )
set(jsoncpp_COMPILE_DEFINITIONS_RELEASE )
set(jsoncpp_COMPILE_OPTIONS_C_RELEASE )
set(jsoncpp_COMPILE_OPTIONS_CXX_RELEASE )
set(jsoncpp_LIB_DIRS_RELEASE "${jsoncpp_PACKAGE_FOLDER_RELEASE}/lib")
set(jsoncpp_BIN_DIRS_RELEASE )
set(jsoncpp_LIBRARY_TYPE_RELEASE STATIC)
set(jsoncpp_IS_HOST_WINDOWS_RELEASE 0)
set(jsoncpp_LIBS_RELEASE jsoncpp)
set(jsoncpp_SYSTEM_LIBS_RELEASE m)
set(jsoncpp_FRAMEWORK_DIRS_RELEASE )
set(jsoncpp_FRAMEWORKS_RELEASE )
set(jsoncpp_BUILD_DIRS_RELEASE )
set(jsoncpp_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(jsoncpp_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${jsoncpp_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${jsoncpp_COMPILE_OPTIONS_C_RELEASE}>")
set(jsoncpp_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${jsoncpp_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${jsoncpp_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${jsoncpp_EXE_LINK_FLAGS_RELEASE}>")


set(jsoncpp_COMPONENTS_RELEASE )