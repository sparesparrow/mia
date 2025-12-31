########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

list(APPEND sparesparrow-protocols_COMPONENT_NAMES sparesparrow-protocols::bpm sparesparrow-protocols::mia sparesparrow-protocols::mcp sparesparrow-protocols::vehicle sparesparrow-protocols::common)
list(REMOVE_DUPLICATES sparesparrow-protocols_COMPONENT_NAMES)
if(DEFINED sparesparrow-protocols_FIND_DEPENDENCY_NAMES)
  list(APPEND sparesparrow-protocols_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES sparesparrow-protocols_FIND_DEPENDENCY_NAMES)
else()
  set(sparesparrow-protocols_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(sparesparrow-protocols_PACKAGE_FOLDER_RELEASE "/home/sparrow/.conan2/p/b/spare5b7a57b2bdef5/p")
set(sparesparrow-protocols_BUILD_MODULES_PATHS_RELEASE )


set(sparesparrow-protocols_INCLUDE_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/include")
set(sparesparrow-protocols_RES_DIRS_RELEASE )
set(sparesparrow-protocols_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_SHARED_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_EXE_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_OBJECTS_RELEASE )
set(sparesparrow-protocols_COMPILE_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_COMPILE_OPTIONS_C_RELEASE )
set(sparesparrow-protocols_COMPILE_OPTIONS_CXX_RELEASE )
set(sparesparrow-protocols_LIB_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/lib")
set(sparesparrow-protocols_BIN_DIRS_RELEASE )
set(sparesparrow-protocols_LIBRARY_TYPE_RELEASE UNKNOWN)
set(sparesparrow-protocols_IS_HOST_WINDOWS_RELEASE 0)
set(sparesparrow-protocols_LIBS_RELEASE )
set(sparesparrow-protocols_SYSTEM_LIBS_RELEASE )
set(sparesparrow-protocols_FRAMEWORK_DIRS_RELEASE )
set(sparesparrow-protocols_FRAMEWORKS_RELEASE )
set(sparesparrow-protocols_BUILD_DIRS_RELEASE )
set(sparesparrow-protocols_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(sparesparrow-protocols_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${sparesparrow-protocols_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${sparesparrow-protocols_COMPILE_OPTIONS_C_RELEASE}>")
set(sparesparrow-protocols_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${sparesparrow-protocols_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${sparesparrow-protocols_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${sparesparrow-protocols_EXE_LINK_FLAGS_RELEASE}>")


set(sparesparrow-protocols_COMPONENTS_RELEASE sparesparrow-protocols::bpm sparesparrow-protocols::mia sparesparrow-protocols::mcp sparesparrow-protocols::vehicle sparesparrow-protocols::common)
########### COMPONENT sparesparrow-protocols::common VARIABLES ############################################

set(sparesparrow-protocols_sparesparrow-protocols_common_INCLUDE_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/include")
set(sparesparrow-protocols_sparesparrow-protocols_common_LIB_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/lib")
set(sparesparrow-protocols_sparesparrow-protocols_common_BIN_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_LIBRARY_TYPE_RELEASE UNKNOWN)
set(sparesparrow-protocols_sparesparrow-protocols_common_IS_HOST_WINDOWS_RELEASE 0)
set(sparesparrow-protocols_sparesparrow-protocols_common_RES_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_OBJECTS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_COMPILE_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_COMPILE_OPTIONS_C_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_common_COMPILE_OPTIONS_CXX_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_common_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_SYSTEM_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_FRAMEWORK_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_FRAMEWORKS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_DEPENDENCIES_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_SHARED_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_EXE_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_common_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(sparesparrow-protocols_sparesparrow-protocols_common_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_common_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_common_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${sparesparrow-protocols_sparesparrow-protocols_common_EXE_LINK_FLAGS_RELEASE}>
)
set(sparesparrow-protocols_sparesparrow-protocols_common_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${sparesparrow-protocols_sparesparrow-protocols_common_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${sparesparrow-protocols_sparesparrow-protocols_common_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT sparesparrow-protocols::vehicle VARIABLES ############################################

set(sparesparrow-protocols_sparesparrow-protocols_vehicle_INCLUDE_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/include")
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_LIB_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/lib")
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_BIN_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_LIBRARY_TYPE_RELEASE UNKNOWN)
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_IS_HOST_WINDOWS_RELEASE 0)
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_RES_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_OBJECTS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_COMPILE_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_COMPILE_OPTIONS_C_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_COMPILE_OPTIONS_CXX_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_SYSTEM_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_FRAMEWORK_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_FRAMEWORKS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_DEPENDENCIES_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_SHARED_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_EXE_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_EXE_LINK_FLAGS_RELEASE}>
)
set(sparesparrow-protocols_sparesparrow-protocols_vehicle_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${sparesparrow-protocols_sparesparrow-protocols_vehicle_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT sparesparrow-protocols::mcp VARIABLES ############################################

set(sparesparrow-protocols_sparesparrow-protocols_mcp_INCLUDE_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/include")
set(sparesparrow-protocols_sparesparrow-protocols_mcp_LIB_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/lib")
set(sparesparrow-protocols_sparesparrow-protocols_mcp_BIN_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_LIBRARY_TYPE_RELEASE UNKNOWN)
set(sparesparrow-protocols_sparesparrow-protocols_mcp_IS_HOST_WINDOWS_RELEASE 0)
set(sparesparrow-protocols_sparesparrow-protocols_mcp_RES_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_OBJECTS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_COMPILE_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_COMPILE_OPTIONS_C_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_mcp_COMPILE_OPTIONS_CXX_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_mcp_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_SYSTEM_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_FRAMEWORK_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_FRAMEWORKS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_DEPENDENCIES_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_SHARED_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_EXE_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mcp_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(sparesparrow-protocols_sparesparrow-protocols_mcp_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_mcp_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_mcp_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${sparesparrow-protocols_sparesparrow-protocols_mcp_EXE_LINK_FLAGS_RELEASE}>
)
set(sparesparrow-protocols_sparesparrow-protocols_mcp_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${sparesparrow-protocols_sparesparrow-protocols_mcp_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${sparesparrow-protocols_sparesparrow-protocols_mcp_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT sparesparrow-protocols::mia VARIABLES ############################################

set(sparesparrow-protocols_sparesparrow-protocols_mia_INCLUDE_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/include")
set(sparesparrow-protocols_sparesparrow-protocols_mia_LIB_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/lib")
set(sparesparrow-protocols_sparesparrow-protocols_mia_BIN_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_LIBRARY_TYPE_RELEASE UNKNOWN)
set(sparesparrow-protocols_sparesparrow-protocols_mia_IS_HOST_WINDOWS_RELEASE 0)
set(sparesparrow-protocols_sparesparrow-protocols_mia_RES_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_OBJECTS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_COMPILE_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_COMPILE_OPTIONS_C_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_mia_COMPILE_OPTIONS_CXX_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_mia_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_SYSTEM_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_FRAMEWORK_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_FRAMEWORKS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_DEPENDENCIES_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_SHARED_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_EXE_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_mia_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(sparesparrow-protocols_sparesparrow-protocols_mia_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_mia_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_mia_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${sparesparrow-protocols_sparesparrow-protocols_mia_EXE_LINK_FLAGS_RELEASE}>
)
set(sparesparrow-protocols_sparesparrow-protocols_mia_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${sparesparrow-protocols_sparesparrow-protocols_mia_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${sparesparrow-protocols_sparesparrow-protocols_mia_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT sparesparrow-protocols::bpm VARIABLES ############################################

set(sparesparrow-protocols_sparesparrow-protocols_bpm_INCLUDE_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/include")
set(sparesparrow-protocols_sparesparrow-protocols_bpm_LIB_DIRS_RELEASE "${sparesparrow-protocols_PACKAGE_FOLDER_RELEASE}/lib")
set(sparesparrow-protocols_sparesparrow-protocols_bpm_BIN_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_LIBRARY_TYPE_RELEASE UNKNOWN)
set(sparesparrow-protocols_sparesparrow-protocols_bpm_IS_HOST_WINDOWS_RELEASE 0)
set(sparesparrow-protocols_sparesparrow-protocols_bpm_RES_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_OBJECTS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_COMPILE_DEFINITIONS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_COMPILE_OPTIONS_C_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_bpm_COMPILE_OPTIONS_CXX_RELEASE "")
set(sparesparrow-protocols_sparesparrow-protocols_bpm_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_SYSTEM_LIBS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_FRAMEWORK_DIRS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_FRAMEWORKS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_DEPENDENCIES_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_SHARED_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_EXE_LINK_FLAGS_RELEASE )
set(sparesparrow-protocols_sparesparrow-protocols_bpm_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(sparesparrow-protocols_sparesparrow-protocols_bpm_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_bpm_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${sparesparrow-protocols_sparesparrow-protocols_bpm_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${sparesparrow-protocols_sparesparrow-protocols_bpm_EXE_LINK_FLAGS_RELEASE}>
)
set(sparesparrow-protocols_sparesparrow-protocols_bpm_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${sparesparrow-protocols_sparesparrow-protocols_bpm_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${sparesparrow-protocols_sparesparrow-protocols_bpm_COMPILE_OPTIONS_C_RELEASE}>")