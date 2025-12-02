########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

list(APPEND mosquitto_COMPONENT_NAMES mosquitto::libmosquitto mosquitto::libmosquittopp)
list(REMOVE_DUPLICATES mosquitto_COMPONENT_NAMES)
if(DEFINED mosquitto_FIND_DEPENDENCY_NAMES)
  list(APPEND mosquitto_FIND_DEPENDENCY_NAMES OpenSSL)
  list(REMOVE_DUPLICATES mosquitto_FIND_DEPENDENCY_NAMES)
else()
  set(mosquitto_FIND_DEPENDENCY_NAMES OpenSSL)
endif()
set(OpenSSL_FIND_MODE "NO_MODULE")

########### VARIABLES #######################################################################
#############################################################################################
set(mosquitto_PACKAGE_FOLDER_RELEASE "/home/sparrow/.conan2/p/b/mosqu00aa8e8e20dd5/p")
set(mosquitto_BUILD_MODULES_PATHS_RELEASE )


set(mosquitto_INCLUDE_DIRS_RELEASE "${mosquitto_PACKAGE_FOLDER_RELEASE}/include")
set(mosquitto_RES_DIRS_RELEASE "${mosquitto_PACKAGE_FOLDER_RELEASE}/res")
set(mosquitto_DEFINITIONS_RELEASE "-DLIBMOSQUITTO_STATIC")
set(mosquitto_SHARED_LINK_FLAGS_RELEASE )
set(mosquitto_EXE_LINK_FLAGS_RELEASE )
set(mosquitto_OBJECTS_RELEASE )
set(mosquitto_COMPILE_DEFINITIONS_RELEASE "LIBMOSQUITTO_STATIC")
set(mosquitto_COMPILE_OPTIONS_C_RELEASE )
set(mosquitto_COMPILE_OPTIONS_CXX_RELEASE )
set(mosquitto_LIB_DIRS_RELEASE "${mosquitto_PACKAGE_FOLDER_RELEASE}/lib")
set(mosquitto_BIN_DIRS_RELEASE )
set(mosquitto_LIBRARY_TYPE_RELEASE STATIC)
set(mosquitto_IS_HOST_WINDOWS_RELEASE 0)
set(mosquitto_LIBS_RELEASE mosquittopp_static mosquitto_static)
set(mosquitto_SYSTEM_LIBS_RELEASE pthread m)
set(mosquitto_FRAMEWORK_DIRS_RELEASE )
set(mosquitto_FRAMEWORKS_RELEASE )
set(mosquitto_BUILD_DIRS_RELEASE )
set(mosquitto_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(mosquitto_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${mosquitto_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${mosquitto_COMPILE_OPTIONS_C_RELEASE}>")
set(mosquitto_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${mosquitto_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${mosquitto_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${mosquitto_EXE_LINK_FLAGS_RELEASE}>")


set(mosquitto_COMPONENTS_RELEASE mosquitto::libmosquitto mosquitto::libmosquittopp)
########### COMPONENT mosquitto::libmosquittopp VARIABLES ############################################

set(mosquitto_mosquitto_libmosquittopp_INCLUDE_DIRS_RELEASE "${mosquitto_PACKAGE_FOLDER_RELEASE}/include")
set(mosquitto_mosquitto_libmosquittopp_LIB_DIRS_RELEASE "${mosquitto_PACKAGE_FOLDER_RELEASE}/lib")
set(mosquitto_mosquitto_libmosquittopp_BIN_DIRS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_LIBRARY_TYPE_RELEASE STATIC)
set(mosquitto_mosquitto_libmosquittopp_IS_HOST_WINDOWS_RELEASE 0)
set(mosquitto_mosquitto_libmosquittopp_RES_DIRS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_DEFINITIONS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_OBJECTS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_COMPILE_DEFINITIONS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_COMPILE_OPTIONS_C_RELEASE "")
set(mosquitto_mosquitto_libmosquittopp_COMPILE_OPTIONS_CXX_RELEASE "")
set(mosquitto_mosquitto_libmosquittopp_LIBS_RELEASE mosquittopp_static)
set(mosquitto_mosquitto_libmosquittopp_SYSTEM_LIBS_RELEASE pthread m)
set(mosquitto_mosquitto_libmosquittopp_FRAMEWORK_DIRS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_FRAMEWORKS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_DEPENDENCIES_RELEASE mosquitto::libmosquitto)
set(mosquitto_mosquitto_libmosquittopp_SHARED_LINK_FLAGS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_EXE_LINK_FLAGS_RELEASE )
set(mosquitto_mosquitto_libmosquittopp_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(mosquitto_mosquitto_libmosquittopp_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${mosquitto_mosquitto_libmosquittopp_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${mosquitto_mosquitto_libmosquittopp_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${mosquitto_mosquitto_libmosquittopp_EXE_LINK_FLAGS_RELEASE}>
)
set(mosquitto_mosquitto_libmosquittopp_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${mosquitto_mosquitto_libmosquittopp_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${mosquitto_mosquitto_libmosquittopp_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT mosquitto::libmosquitto VARIABLES ############################################

set(mosquitto_mosquitto_libmosquitto_INCLUDE_DIRS_RELEASE "${mosquitto_PACKAGE_FOLDER_RELEASE}/include")
set(mosquitto_mosquitto_libmosquitto_LIB_DIRS_RELEASE "${mosquitto_PACKAGE_FOLDER_RELEASE}/lib")
set(mosquitto_mosquitto_libmosquitto_BIN_DIRS_RELEASE )
set(mosquitto_mosquitto_libmosquitto_LIBRARY_TYPE_RELEASE STATIC)
set(mosquitto_mosquitto_libmosquitto_IS_HOST_WINDOWS_RELEASE 0)
set(mosquitto_mosquitto_libmosquitto_RES_DIRS_RELEASE "${mosquitto_PACKAGE_FOLDER_RELEASE}/res")
set(mosquitto_mosquitto_libmosquitto_DEFINITIONS_RELEASE "-DLIBMOSQUITTO_STATIC")
set(mosquitto_mosquitto_libmosquitto_OBJECTS_RELEASE )
set(mosquitto_mosquitto_libmosquitto_COMPILE_DEFINITIONS_RELEASE "LIBMOSQUITTO_STATIC")
set(mosquitto_mosquitto_libmosquitto_COMPILE_OPTIONS_C_RELEASE "")
set(mosquitto_mosquitto_libmosquitto_COMPILE_OPTIONS_CXX_RELEASE "")
set(mosquitto_mosquitto_libmosquitto_LIBS_RELEASE mosquitto_static)
set(mosquitto_mosquitto_libmosquitto_SYSTEM_LIBS_RELEASE pthread m)
set(mosquitto_mosquitto_libmosquitto_FRAMEWORK_DIRS_RELEASE )
set(mosquitto_mosquitto_libmosquitto_FRAMEWORKS_RELEASE )
set(mosquitto_mosquitto_libmosquitto_DEPENDENCIES_RELEASE openssl::openssl)
set(mosquitto_mosquitto_libmosquitto_SHARED_LINK_FLAGS_RELEASE )
set(mosquitto_mosquitto_libmosquitto_EXE_LINK_FLAGS_RELEASE )
set(mosquitto_mosquitto_libmosquitto_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(mosquitto_mosquitto_libmosquitto_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${mosquitto_mosquitto_libmosquitto_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${mosquitto_mosquitto_libmosquitto_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${mosquitto_mosquitto_libmosquitto_EXE_LINK_FLAGS_RELEASE}>
)
set(mosquitto_mosquitto_libmosquitto_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${mosquitto_mosquitto_libmosquitto_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${mosquitto_mosquitto_libmosquitto_COMPILE_OPTIONS_C_RELEASE}>")