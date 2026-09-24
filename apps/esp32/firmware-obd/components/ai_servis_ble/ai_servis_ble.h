#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "ai_servis_obd.h"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

#define AI_SERVIS_BLE_PAYLOAD_MAX 32

// Wire size of one telemetry notification, see pack_telemetry().
#define AI_SERVIS_BLE_TELEMETRY_LEN 12

/** Commands a phone can write to the command characteristic. */
typedef enum {
    BLE_CMD_NONE = 0,
    BLE_CMD_REQUEST_STATUS = 1,      /**< no payload; replies with a telemetry notify */
    BLE_CMD_READ_PID = 2,            /**< payload[0] = PID, answered from the last poll */
    BLE_CMD_SET_POLL_INTERVAL = 3,   /**< payload[0..1] = interval in ms, little-endian */
} ble_command_id_t;

/**
 * One command received over GATT. Pointer-free so it can be copied by value
 * through a FreeRTOS queue.
 */
typedef struct {
    uint8_t id;
    uint8_t payload[AI_SERVIS_BLE_PAYLOAD_MAX];
    uint16_t length;
    uint32_t timestamp;
} ble_command_t;

/** Created in app_main() before the tasks start. */
extern QueueHandle_t ble_queue;

/**
 * Bring up the BLE controller, Bluedroid, the GATT server and advertising.
 * Failures are logged and reported, but leave the rest of the firmware running.
 */
esp_err_t ai_servis_ble_init(void);

void ai_servis_ble_task(void *pvParameters);

/**
 * Cache a telemetry sample and, if a client has subscribed, notify it.
 * Safe to call when no client is connected.
 */
esp_err_t ai_servis_ble_notify_telemetry(const obd_data_t *data);

bool ai_servis_ble_is_connected(void);
