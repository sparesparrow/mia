/* MIA Universal ESP32 Firmware
 * Publishes line-delimited JSON over UART0 for the Raspberry Pi serial bridge.
 */

#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/adc.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "nvs_flash.h"

#define TAG "MIA_ESP32"
#define TELEMETRY_INTERVAL_MS 1000

// GPIO Configuration
#define LED_PIN GPIO_NUM_2
#define BUTTON_PIN GPIO_NUM_0
#define ADC_CHANNEL ADC1_CHANNEL_0

typedef struct {
    int adc_value;
    int gpio_state;
    uint32_t uptime;
} sensor_data_t;

static char g_device_id[20] = "esp32-generic";

static void init_device_id(void) {
    uint8_t mac[6] = {0};

    if (esp_efuse_mac_get_default(mac) == ESP_OK) {
        snprintf(g_device_id, sizeof(g_device_id), "esp32-%02X%02X%02X", mac[3], mac[4], mac[5]);
    }
}

static void gpio_init(void) {
    // Configure LED pin as output
    gpio_config_t led_conf = {
        .pin_bit_mask = (1ULL << LED_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&led_conf);

    // Configure button pin as input
    gpio_config_t btn_conf = {
        .pin_bit_mask = (1ULL << BUTTON_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&btn_conf);

    ESP_LOGI(TAG, "GPIO initialized.");
}

static void adc_init(void) {
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC_CHANNEL, ADC_ATTEN_DB_11);
    ESP_LOGI(TAG, "ADC initialized.");
}

static void emit_sensor_data(const sensor_data_t *data) {
    // The Pi serial bridge expects newline-delimited JSON messages.
    printf(
        "{\"device_id\":\"%s\",\"device_type\":\"esp32\",\"adc_value\":%d,\"gpio_state\":%d,\"uptime\":%" PRIu32 ",\"free_heap\":%" PRIu32 "}\n",
        g_device_id,
        data->adc_value,
        data->gpio_state,
        data->uptime,
        (uint32_t)esp_get_free_heap_size()
    );
    fflush(stdout);
}

static void sensor_task(void *pvParameters) {
    sensor_data_t sensor_data;

    while (1) {
        // Read ADC value
        sensor_data.adc_value = adc1_get_raw(ADC_CHANNEL);

        // Read GPIO state (button)
        sensor_data.gpio_state = gpio_get_level(BUTTON_PIN);

        // Get uptime
        sensor_data.uptime = esp_timer_get_time() / 1000000; // Convert to seconds

        // Send data to Raspberry Pi over the shared serial JSON bridge.
        emit_sensor_data(&sensor_data);

        // Toggle LED to show activity
        static int led_state = 0;
        gpio_set_level(LED_PIN, led_state);
        led_state = !led_state;

        vTaskDelay(pdMS_TO_TICKS(TELEMETRY_INTERVAL_MS));
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "Starting MIA Universal ESP32 Firmware");
    setvbuf(stdout, NULL, _IONBF, 0);

    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    init_device_id();
    ESP_LOGI(TAG, "Using device ID: %s", g_device_id);

    // Initialize peripherals
    gpio_init();
    adc_init();

    // Create sensor monitoring task
    xTaskCreate(sensor_task, "sensor_task", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "MIA ESP32 firmware initialized and running");
}