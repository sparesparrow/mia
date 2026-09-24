idf_component_register(
    SRCS "ai_servis_mqtt.c"
    INCLUDE_DIRS "."
    REQUIRES mqtt esp_wifi esp_netif esp_event ai_servis_config
)
