#include "ai_servis_obd.h"
#include "esp_log.h"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/twai.h"
#include "driver/gpio.h"

static const char *TAG = "AI_SERVIS_OBD";

// TWAI configuration
#define TWAI_RX_PIN GPIO_NUM_16
#define TWAI_TX_PIN GPIO_NUM_17
#define TWAI_BITRATE TWAI_TIMING_CONFIG_500KBITS()

// OBD-II request template
static const uint8_t obd_request_template[] = {
    0x7DF,  // CAN ID (broadcast)
    0x02,   // Data length
    0x01,   // Service mode 01
    0x00,   // PID (to be filled)
    0x00,   // Padding
    0x00,   // Padding
    0x00,   // Padding
    0x00    // Padding
};

static QueueHandle_t obd_queue = NULL;
static bool obd_initialized = false;

esp_err_t ai_servis_obd_init(void)
{
    ESP_LOGI(TAG, "Initializing OBD component");

    // Configure TWAI pins
    gpio_config_t io_conf = {
        .intr_type = GPIO_INTR_DISABLE,
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = (1ULL << TWAI_TX_PIN),
        .pull_down_en = 0,
        .pull_up_en = 0,
    };
    gpio_config(&io_conf);

    // Install TWAI driver
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(TWAI_TX_PIN, TWAI_RX_PIN, TWAI_MODE_NORMAL);
    twai_timing_config_t t_config = TWAI_BITRATE;
    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();

    esp_err_t ret = twai_driver_install(&g_config, &t_config, &f_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to install TWAI driver: %s", esp_err_to_name(ret));
        return ret;
    }

    // Start TWAI driver
    ret = twai_start();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start TWAI driver: %s", esp_err_to_name(ret));
        return ret;
    }

    // Create OBD queue
    obd_queue = xQueueCreate(10, sizeof(obd_data_t));
    if (!obd_queue) {
        ESP_LOGE(TAG, "Failed to create OBD queue");
        return ESP_ERR_NO_MEM;
    }

    obd_initialized = true;
    ESP_LOGI(TAG, "OBD component initialized successfully");
    return ESP_OK;
}

void ai_servis_obd_task(void *pvParameters)
{
    obd_data_t obd_data = {0};
    uint8_t request_pids[] = {PID_ENGINE_RPM, PID_VEHICLE_SPEED, PID_COOLANT_TEMP, PID_FUEL_LEVEL};
    uint8_t pid_index = 0;
    TickType_t last_read_time = 0;

    ESP_LOGI(TAG, "OBD task started");

    while (obd_initialized) {
        TickType_t current_time = xTaskGetTickCount();

        // Read OBD data every 100ms
        if (current_time - last_read_time >= pdMS_TO_TICKS(100)) {
            uint8_t pid = request_pids[pid_index];
            uint8_t response[8];
            size_t response_length = 0;

            // Read current PID
            if (ai_servis_obd_read_pid(pid, response, &response_length) == ESP_OK) {
                if (ai_servis_obd_parse_data(&obd_data, response, response_length) == ESP_OK) {
                    obd_data.timestamp = xTaskGetTickCount();
                    
                    // Check for alerts
                    ai_servis_obd_check_alerts(&obd_data);

                    // Send to queue
                    if (obd_queue) {
                        xQueueSend(obd_queue, &obd_data, 0);
                    }
                }
            }

            // Move to next PID
            pid_index = (pid_index + 1) % (sizeof(request_pids) / sizeof(request_pids[0]));
            last_read_time = current_time;
        }

        vTaskDelay(pdMS_TO_TICKS(10));
    }

    ESP_LOGI(TAG, "OBD task stopped");
    vTaskDelete(NULL);
}

esp_err_t ai_servis_obd_read_pid(uint8_t pid, uint8_t *data, size_t *length)
{
    twai_message_t message;
    memcpy(&message.data, obd_request_template, sizeof(obd_request_template));
    message.data[3] = pid;  // Set PID
    message.identifier = 0x7DF;
    message.data_length_code = 8;

    // Send request
    esp_err_t ret = twai_transmit(&message);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to transmit OBD request: %s", esp_err_to_name(ret));
        return ret;
    }

    // Wait for response
    TickType_t timeout = pdMS_TO_TICKS(100);
    TickType_t start_time = xTaskGetTickCount();

    while (xTaskGetTickCount() - start_time < timeout) {
        if (twai_receive(&message, pdMS_TO_TICKS(10)) == ESP_OK) {
            // Check if response is for our PID
            if (message.identifier == 0x7E8 && message.data[2] == pid) {
                memcpy(data, message.data, message.data_length_code);
                *length = message.data_length_code;
                return ESP_OK;
            }
        }
    }

    ESP_LOGW(TAG, "Timeout waiting for OBD response");
    return ESP_ERR_TIMEOUT;
}

esp_err_t ai_servis_obd_parse_data(obd_data_t *data, uint8_t *response, size_t length)
{
    if (!data || !response || length < 4) {
        return ESP_ERR_INVALID_ARG;
    }

    uint8_t pid = response[2];
    uint8_t data_length = response[0] - 1;
    uint8_t *pid_data = &response[3];

    switch (pid) {
        case PID_ENGINE_RPM:
            if (data_length >= 2) {
                data->engine_rpm = (pid_data[0] * 256 + pid_data[1]) / 4;
            }
            break;

        case PID_VEHICLE_SPEED:
            if (data_length >= 1) {
                data->vehicle_speed = pid_data[0];
            }
            break;

        case PID_COOLANT_TEMP:
            if (data_length >= 1) {
                data->coolant_temp = pid_data[0] - 40;
            }
            break;

        case PID_FUEL_LEVEL:
            if (data_length >= 1) {
                data->fuel_level = (pid_data[0] * 100) / 255;
            }
            break;

        case PID_ENGINE_LOAD:
            if (data_length >= 1) {
                data->engine_load = (pid_data[0] * 100) / 255;
            }
            break;

        default:
            ESP_LOGW(TAG, "Unknown PID: 0x%02X", pid);
            break;
    }

    return ESP_OK;
}

void ai_servis_obd_check_alerts(obd_data_t *data)
{
    if (!data) return;

    // Check fuel level
    if (data->fuel_level < 20) {
        ESP_LOGW(TAG, "Low fuel alert: %d%%", data->fuel_level);
        // TODO: Send alert to MQTT/BLE
    }

    // Check coolant temperature
    if (data->coolant_temp > 105) {
        ESP_LOGE(TAG, "High coolant temperature alert: %d°C", data->coolant_temp);
        // TODO: Send critical alert
    }

    // Check engine RPM
    if (data->engine_rpm > 6000) {
        ESP_LOGW(TAG, "High RPM alert: %d", data->engine_rpm);
        // TODO: Send warning
    }
}
