idf_component_register(
    SRCS "ai_servis_obd.c"
    INCLUDE_DIRS "."
    REQUIRES driver mqtt
)

# Passive sniffing build: idf.py build -DMIA_TWAI_LISTEN_ONLY=1
# Without this the option would be accepted on the command line and silently
# ignored, leaving the controller in normal mode.
if(MIA_TWAI_LISTEN_ONLY)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE MIA_TWAI_LISTEN_ONLY=1)
endif()
