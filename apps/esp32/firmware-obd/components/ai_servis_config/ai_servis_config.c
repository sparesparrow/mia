#include "ai_servis_config.h"

#include <string.h>

#include "esp_log.h"
#include "esp_mac.h"
#include "nvs.h"
#include "nvs_flash.h"

static const char *TAG = "AI_SERVIS_CONFIG";

#define CONFIG_NAMESPACE "ai-servis"
#define KEY_SSID     "wifi_ssid"
#define KEY_PASSWORD "wifi_pass"
#define KEY_MQTT_URI "mqtt_uri"
#define KEY_POLL_MS  "poll_ms"

static ai_servis_config_t s_config;
static bool s_initialized = false;

/**
 * Derive a stable device id from the factory MAC, so two boards on the same
 * broker never collide. Falls back to a fixed string if the efuse read fails.
 */
static void derive_device_id(char *out, size_t out_len)
{
    uint8_t mac[6] = {0};

    if (esp_efuse_mac_get_default(mac) == ESP_OK) {
        snprintf(out, out_len, "obd-%02X%02X%02X", mac[3], mac[4], mac[5]);
    } else {
        snprintf(out, out_len, "obd-unknown");
    }
}

/**
 * Read one string key into a fixed buffer, leaving the buffer untouched when
 * the key is absent so the caller's default survives.
 */
static void load_str(nvs_handle_t handle, const char *key, char *out, size_t out_len)
{
    size_t length = out_len;
    esp_err_t ret = nvs_get_str(handle, key, out, &length);

    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        return;
    }
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Failed to read '%s' from NVS: %s", key, esp_err_to_name(ret));
    }
}

esp_err_t ai_servis_config_init(void)
{
    if (s_initialized) {
        return ESP_OK;
    }

    // Defaults first, so a missing or unreadable NVS still yields a usable config.
    memset(&s_config, 0, sizeof(s_config));
    derive_device_id(s_config.device_id, sizeof(s_config.device_id));
    strlcpy(s_config.wifi_ssid, AI_SERVIS_DEFAULT_WIFI_SSID, sizeof(s_config.wifi_ssid));
    strlcpy(s_config.wifi_password, AI_SERVIS_DEFAULT_WIFI_PASSWORD, sizeof(s_config.wifi_password));
    strlcpy(s_config.mqtt_uri, AI_SERVIS_DEFAULT_MQTT_URI, sizeof(s_config.mqtt_uri));
    s_config.obd_poll_interval_ms = AI_SERVIS_DEFAULT_POLL_INTERVAL_MS;

    nvs_handle_t handle;
    esp_err_t ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &handle);
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGI(TAG, "No stored configuration, using defaults");
        s_initialized = true;
        return ESP_OK;
    }
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Failed to open NVS namespace: %s - using defaults", esp_err_to_name(ret));
        s_initialized = true;
        return ESP_OK;
    }

    load_str(handle, KEY_SSID, s_config.wifi_ssid, sizeof(s_config.wifi_ssid));
    load_str(handle, KEY_PASSWORD, s_config.wifi_password, sizeof(s_config.wifi_password));
    load_str(handle, KEY_MQTT_URI, s_config.mqtt_uri, sizeof(s_config.mqtt_uri));

    uint16_t poll_ms = 0;
    if (nvs_get_u16(handle, KEY_POLL_MS, &poll_ms) == ESP_OK && poll_ms > 0) {
        s_config.obd_poll_interval_ms = poll_ms;
    }

    nvs_close(handle);

    s_initialized = true;
    ESP_LOGI(TAG, "Configuration loaded: device_id=%s ssid=%s mqtt=%s poll=%ums",
             s_config.device_id,
             s_config.wifi_ssid[0] ? s_config.wifi_ssid : "(unset)",
             s_config.mqtt_uri,
             (unsigned)s_config.obd_poll_interval_ms);
    return ESP_OK;
}

const ai_servis_config_t *ai_servis_config_get(void)
{
    if (!s_initialized) {
        ai_servis_config_init();
    }
    return &s_config;
}

bool ai_servis_config_has_wifi(void)
{
    return ai_servis_config_get()->wifi_ssid[0] != '\0';
}

esp_err_t ai_servis_config_set_wifi(const char *ssid, const char *password)
{
    if (!ssid) {
        return ESP_ERR_INVALID_ARG;
    }

    ai_servis_config_init();
    strlcpy(s_config.wifi_ssid, ssid, sizeof(s_config.wifi_ssid));
    strlcpy(s_config.wifi_password, password ? password : "", sizeof(s_config.wifi_password));
    return ai_servis_config_save();
}

esp_err_t ai_servis_config_set_mqtt_uri(const char *uri)
{
    if (!uri) {
        return ESP_ERR_INVALID_ARG;
    }

    ai_servis_config_init();
    strlcpy(s_config.mqtt_uri, uri, sizeof(s_config.mqtt_uri));
    return ai_servis_config_save();
}

esp_err_t ai_servis_config_save(void)
{
    nvs_handle_t handle;
    esp_err_t ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS for writing: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = nvs_set_str(handle, KEY_SSID, s_config.wifi_ssid);
    if (ret == ESP_OK) {
        ret = nvs_set_str(handle, KEY_PASSWORD, s_config.wifi_password);
    }
    if (ret == ESP_OK) {
        ret = nvs_set_str(handle, KEY_MQTT_URI, s_config.mqtt_uri);
    }
    if (ret == ESP_OK) {
        ret = nvs_set_u16(handle, KEY_POLL_MS, s_config.obd_poll_interval_ms);
    }
    if (ret == ESP_OK) {
        ret = nvs_commit(handle);
    }

    nvs_close(handle);

    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to persist configuration: %s", esp_err_to_name(ret));
    } else {
        ESP_LOGI(TAG, "Configuration persisted");
    }
    return ret;
}
