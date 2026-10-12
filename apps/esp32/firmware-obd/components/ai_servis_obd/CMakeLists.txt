idf_component_register(
    SRCS "ai_servis_obd.c"
    INCLUDE_DIRS "."
    REQUIRES driver mqtt
)

# The default build is passive / listen-only (ADR-0006).
# Active OBD polling needs an explicit opt-in: idf.py -B build-tx -DMIA_ALLOW_TX=1 build
# Without this the option would be accepted on the command line and silently
# ignored.
# -D values persist in CMakeCache.txt, so an active configuration may only live
# in a build directory whose name ends in "-tx": a later plain `idf.py build` in
# build/ can then never reuse transmitting objects.
if(MIA_ALLOW_TX AND NOT MIA_TWAI_LISTEN_ONLY)
    get_filename_component(_mia_build_dir "${CMAKE_BINARY_DIR}" NAME)
    if(NOT _mia_build_dir MATCHES "-tx$")
        message(FATAL_ERROR
            "MIA_ALLOW_TX builds a CAN-transmitting image (ADR-0006). Use a separate "
            "build directory: idf.py -B build-tx -DMIA_ALLOW_TX=1 build")
    endif()
    message(WARNING "MIA_ALLOW_TX=1: this image TRANSMITS on the CAN bus")
    target_compile_definitions(${COMPONENT_LIB} PRIVATE MIA_ALLOW_TX=1)
else()
    target_compile_definitions(${COMPONENT_LIB} PRIVATE MIA_TWAI_LISTEN_ONLY=1)
endif()
