#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

// Buffer sizes include room for the terminating NUL.
#define AI_SERVIS_DEVICE_ID_MAX 24
#define AI_SERVIS_SSID_MAX      33
#define AI_SERVIS_PASSWORD_MAX  65
#define AI_SERVIS_URI_MAX       128

// Compile-time defaults, used when nothing is stored in NVS yet.
// Override with -D at build time rather than editing this header.
#ifndef AI_SERVIS_DEFAULT_WIFI_SSID
#define AI_SERVIS_DEFAULT_WIFI_SSID ""
#endif

#ifndef AI_SERVIS_DEFAULT_WIFI_PASSWORD
#define AI_SERVIS_DEFAULT_WIFI_PASSWORD ""
#endif

#ifndef AI_SERVIS_DEFAULT_MQTT_URI
#define AI_SERVIS_DEFAULT_MQTT_URI "mqtt://192.168.1.100:1883"
#endif

#ifndef AI_SERVIS_DEFAULT_POLL_INTERVAL_MS
#define AI_SERVIS_DEFAULT_POLL_INTERVAL_MS 100
#endif

typedef struct {
    char device_id[AI_SERVIS_DEVICE_ID_MAX];
    char wifi_ssid[AI_SERVIS_SSID_MAX];
    char wifi_password[AI_SERVIS_PASSWORD_MAX];
    char mqtt_uri[AI_SERVIS_URI_MAX];
    uint16_t obd_poll_interval_ms;
} ai_servis_config_t;

/**
 * Load configuration from NVS, falling back to the compile-time defaults.
 * Safe to call more than once; later calls are no-ops.
 * Requires nvs_flash_init() to have run first.
 */
esp_err_t ai_servis_config_init(void);

/** Current configuration. Never NULL once ai_servis_config_init() has run. */
const ai_servis_config_t *ai_servis_config_get(void);

/** True when a WiFi SSID is configured; without one there is nothing to join. */
bool ai_servis_config_has_wifi(void);

esp_err_t ai_servis_config_set_wifi(const char *ssid, const char *password);
esp_err_t ai_servis_config_set_mqtt_uri(const char *uri);

/** Persist the current configuration to NVS. */
esp_err_t ai_servis_config_save(void);
