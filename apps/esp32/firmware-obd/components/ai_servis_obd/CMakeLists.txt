idf_component_register(
    SRCS "ai_servis_obd.c"
    INCLUDE_DIRS "."
    REQUIRES driver mqtt
)

# The default build is passive / listen-only (ADR-0006).
# Active OBD polling needs an explicit opt-in: idf.py build -DMIA_ALLOW_TX=1
# Without this the option would be accepted on the command line and silently
# ignored.
if(MIA_ALLOW_TX AND NOT MIA_TWAI_LISTEN_ONLY)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE MIA_ALLOW_TX=1)
else()
    target_compile_definitions(${COMPONENT_LIB} PRIVATE MIA_TWAI_LISTEN_ONLY=1)
endif()
