/* MIA Universal ESP32 Firmware
 * Connects to Raspberry Pi and provides sensor data and hardware control
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_http_client.h"

#define TAG "MIA_ESP32"

// WiFi Configuration
#define WIFI_SSID "MIA_NETWORK"
#define WIFI_PASS "mia_password"
#define RPI_HOST "192.168.200.134"
#define RPI_PORT 8080

// GPIO Configuration
#define LED_PIN GPIO_NUM_2
#define BUTTON_PIN GPIO_NUM_0
#define ADC_CHANNEL ADC1_CHANNEL_0

// Sensor data structure
typedef struct {
    int adc_value;
    int gpio_state;
    uint32_t uptime;
} sensor_data_t;

// HTTP client configuration
esp_http_client_config_t http_config = {
    .host = RPI_HOST,
    .port = RPI_PORT,
    .path = "/api/v1/sensors",
    .method = HTTP_METHOD_POST,
};

static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                              int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
        ESP_LOGI(TAG, "Retrying WiFi connection...");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
    }
}

static void wifi_init(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi initialized.");
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

static esp_err_t send_sensor_data(sensor_data_t *data) {
    char post_data[256];
    snprintf(post_data, sizeof(post_data),
             "{\"adc_value\":%d,\"gpio_state\":%d,\"uptime\":%lu,\"device\":\"esp32\"}",
             data->adc_value, data->gpio_state, data->uptime);

    esp_http_client_handle_t client = esp_http_client_init(&http_config);

    esp_http_client_set_header(client, "Content-Type", "application/json");
    esp_http_client_set_post_field(client, post_data, strlen(post_data));

    esp_err_t err = esp_http_client_perform(client);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Sensor data sent successfully");
        int status_code = esp_http_client_get_status_code(client);
        ESP_LOGI(TAG, "HTTP Status = %d", status_code);
    } else {
        ESP_LOGE(TAG, "HTTP POST request failed: %s", esp_err_to_name(err));
    }

    esp_http_client_cleanup(client);
    return err;
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

        // Send data to Raspberry Pi
        send_sensor_data(&sensor_data);

        // Toggle LED to show activity
        static int led_state = 0;
        gpio_set_level(LED_PIN, led_state);
        led_state = !led_state;

        // Wait 5 seconds
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "Starting MIA Universal ESP32 Firmware");

    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Initialize peripherals
    gpio_init();
    adc_init();

    // Initialize WiFi
    wifi_init();

    // Wait for WiFi connection
    vTaskDelay(pdMS_TO_TICKS(5000));

    // Create sensor monitoring task
    xTaskCreate(sensor_task, "sensor_task", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "MIA ESP32 firmware initialized and running");
}