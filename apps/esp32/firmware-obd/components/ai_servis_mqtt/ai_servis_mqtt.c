#include "ai_servis_mqtt.h"

#include <string.h>

#include "ai_servis_config.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "mqtt_client.h"

static const char *TAG = "AI_SERVIS_MQTT";

// Backing off rather than hammering the AP: the car's hotspot may not be up yet.
#define WIFI_RECONNECT_DELAY_MS 5000
#define QUEUE_WAIT_MS           1000

static esp_mqtt_client_handle_t s_client = NULL;
static volatile bool s_mqtt_connected = false;
static volatile bool s_wifi_got_ip = false;
static bool s_initialized = false;

static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data)
{
    (void)handler_args;
    (void)base;
    (void)event_data;

    switch ((esp_mqtt_event_id_t)event_id) {
        case MQTT_EVENT_CONNECTED:
            s_mqtt_connected = true;
            ESP_LOGI(TAG, "Connected to broker");
            break;

        case MQTT_EVENT_DISCONNECTED:
            s_mqtt_connected = false;
            ESP_LOGW(TAG, "Disconnected from broker");
            break;

        case MQTT_EVENT_ERROR:
            ESP_LOGE(TAG, "MQTT transport error");
            break;

        default:
            break;
    }
}

static void wifi_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data)
{
    (void)handler_args;
    (void)event_data;

    if (base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
        return;
    }

    if (base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        s_wifi_got_ip = false;
        ESP_LOGW(TAG, "WiFi disconnected, retrying in %d ms", WIFI_RECONNECT_DELAY_MS);
        vTaskDelay(pdMS_TO_TICKS(WIFI_RECONNECT_DELAY_MS));
        esp_wifi_connect();
        return;
    }

    if (base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        s_wifi_got_ip = true;
        ESP_LOGI(TAG, "WiFi connected, got IP");
    }
}

/**
 * Start WiFi in station mode from the stored configuration.
 * Returns ESP_ERR_INVALID_STATE when no SSID is configured, which the caller
 * treats as "run offline" rather than as a failure.
 */
static esp_err_t wifi_start(void)
{
    const ai_servis_config_t *config = ai_servis_config_get();

    if (!ai_servis_config_has_wifi()) {
        ESP_LOGW(TAG, "No WiFi SSID configured, staying offline");
        return ESP_ERR_INVALID_STATE;
    }

    esp_netif_t *netif = esp_netif_create_default_wifi_sta();
    if (!netif) {
        ESP_LOGE(TAG, "Failed to create default WiFi STA interface");
        return ESP_FAIL;
    }

    wifi_init_config_t init_config = WIFI_INIT_CONFIG_DEFAULT();
    esp_err_t ret = esp_wifi_init(&init_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "esp_wifi_init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                                        wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                                        wifi_event_handler, NULL, NULL));

    wifi_config_t wifi_config = {0};
    strlcpy((char *)wifi_config.sta.ssid, config->wifi_ssid, sizeof(wifi_config.sta.ssid));
    strlcpy((char *)wifi_config.sta.password, config->wifi_password, sizeof(wifi_config.sta.password));

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi station started, joining '%s'", config->wifi_ssid);
    return ESP_OK;
}

esp_err_t ai_servis_mqtt_init(void)
{
    if (s_initialized) {
        return ESP_OK;
    }

    ai_servis_config_init();
    const ai_servis_config_t *config = ai_servis_config_get();

    // Offline is a supported mode: OBD polling and BLE stay useful without a broker.
    if (wifi_start() != ESP_OK) {
        s_initialized = true;
        return ESP_OK;
    }

    esp_mqtt_client_config_t mqtt_config = {
        .broker.address.uri = config->mqtt_uri,
        .credentials.client_id = config->device_id,
    };

    s_client = esp_mqtt_client_init(&mqtt_config);
    if (!s_client) {
        ESP_LOGE(TAG, "Failed to create MQTT client");
        s_initialized = true;
        return ESP_OK;
    }

    ESP_ERROR_CHECK(esp_mqtt_client_register_event(s_client, ESP_EVENT_ANY_ID,
                                                   mqtt_event_handler, NULL));

    esp_err_t ret = esp_mqtt_client_start(s_client);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start MQTT client: %s", esp_err_to_name(ret));
        esp_mqtt_client_destroy(s_client);
        s_client = NULL;
        s_initialized = true;
        return ESP_OK;
    }

    ESP_LOGI(TAG, "MQTT client started, broker: %s", config->mqtt_uri);
    s_initialized = true;
    return ESP_OK;
}

bool ai_servis_mqtt_is_connected(void)
{
    return s_mqtt_connected;
}

esp_err_t ai_servis_mqtt_publish(const char *topic, const char *payload, uint8_t qos, bool retain)
{
    if (!topic || !payload) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!mqtt_queue) {
        return ESP_ERR_INVALID_STATE;
    }

    mqtt_message_t message = {0};
    strlcpy(message.topic, topic, sizeof(message.topic));
    strlcpy(message.payload, payload, sizeof(message.payload));
    message.payload_len = (uint16_t)strnlen(message.payload, sizeof(message.payload) - 1);
    message.qos = qos;
    message.retain = retain;

    if (xQueueSend(mqtt_queue, &message, 0) != pdTRUE) {
        ESP_LOGW(TAG, "Publish queue full, dropping message for %s", topic);
        return ESP_ERR_NO_MEM;
    }
    return ESP_OK;
}

void ai_servis_mqtt_task(void *pvParameters)
{
    (void)pvParameters;

    ESP_LOGI(TAG, "MQTT task started");

    mqtt_message_t message;

    while (1) {
        if (xQueueReceive(mqtt_queue, &message, pdMS_TO_TICKS(QUEUE_WAIT_MS)) != pdTRUE) {
            continue;
        }

        // Drop rather than block: telemetry is only useful while it is fresh,
        // and a stalled task would back up the queue behind it.
        if (!s_client || !s_mqtt_connected) {
            ESP_LOGD(TAG, "Broker unavailable, dropping message for %s", message.topic);
            continue;
        }

        int msg_id = esp_mqtt_client_publish(s_client, message.topic, message.payload,
                                             message.payload_len, message.qos,
                                             message.retain ? 1 : 0);
        if (msg_id < 0) {
            ESP_LOGW(TAG, "Publish to %s failed", message.topic);
        }
    }
}
