#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_bt.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_gatt_common_api.h"
#include "driver/twai.h"
#include "driver/gpio.h"

#include "ai_servis_ble.h"
#include "ai_servis_mqtt.h"
#include "ai_servis_obd.h"
#include "ai_servis_config.h"

static const char *TAG = "AI_SERVIS_MAIN";

// Global queues for inter-task communication
QueueHandle_t obd_queue;
QueueHandle_t ble_queue;
QueueHandle_t mqtt_queue;

void app_main(void)
{
    ESP_LOGI(TAG, "Starting AI-SERVIS OBD firmware v%s", FIRMWARE_VERSION);

    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Initialize TCP/IP adapter
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // Create queues
    obd_queue = xQueueCreate(10, sizeof(obd_data_t));
    ble_queue = xQueueCreate(10, sizeof(ble_command_t));
    mqtt_queue = xQueueCreate(10, sizeof(mqtt_message_t));

    if (!obd_queue || !ble_queue || !mqtt_queue) {
        ESP_LOGE(TAG, "Failed to create queues");
        return;
    }

    // Initialize components
    ai_servis_config_init();
    ai_servis_ble_init();
    ai_servis_mqtt_init();
    ai_servis_obd_init();

    // Create tasks
    xTaskCreate(ai_servis_obd_task, "obd_task", 4096, NULL, 5, NULL);
    xTaskCreate(ai_servis_ble_task, "ble_task", 4096, NULL, 5, NULL);
    xTaskCreate(ai_servis_mqtt_task, "mqtt_task", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "AI-SERVIS OBD firmware started successfully");
}
