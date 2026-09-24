idf_component_register(
    SRCS "ai_servis_ble.c"
    INCLUDE_DIRS "."
    REQUIRES bt ai_servis_obd ai_servis_config
)
