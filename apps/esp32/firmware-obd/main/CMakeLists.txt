idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES ai_servis_obd ai_servis_ble ai_servis_mqtt ai_servis_config
             driver esp_wifi esp_netif esp_event nvs_flash bt
)
