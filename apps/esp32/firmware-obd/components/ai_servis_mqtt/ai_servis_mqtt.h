#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

#define AI_SERVIS_MQTT_TOPIC_MAX   64
#define AI_SERVIS_MQTT_PAYLOAD_MAX 256

/**
 * One queued publish. Kept free of pointers so the struct can be copied by
 * value through a FreeRTOS queue without owning any heap.
 */
typedef struct {
    char topic[AI_SERVIS_MQTT_TOPIC_MAX];
    char payload[AI_SERVIS_MQTT_PAYLOAD_MAX];
    uint16_t payload_len;
    uint8_t qos;
    bool retain;
} mqtt_message_t;

/** Created in app_main() before the tasks start. */
extern QueueHandle_t mqtt_queue;

/**
 * Bring up WiFi in station mode and start the MQTT client.
 *
 * The client owns network bring-up because it is the only network consumer in
 * this firmware. Both are non-fatal: with no SSID configured, or with the
 * broker unreachable, init still succeeds and the task keeps draining the
 * queue, dropping messages rather than blocking the rest of the firmware.
 */
esp_err_t ai_servis_mqtt_init(void);

void ai_servis_mqtt_task(void *pvParameters);

/** Queue a publish. Returns ESP_ERR_NO_MEM if the queue is full. */
esp_err_t ai_servis_mqtt_publish(const char *topic, const char *payload, uint8_t qos, bool retain);

bool ai_servis_mqtt_is_connected(void);
