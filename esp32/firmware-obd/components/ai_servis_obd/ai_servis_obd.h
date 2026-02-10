#pragma once

#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "driver/twai.h"

#define FIRMWARE_VERSION "1.0.0"

// OBD-II PID definitions
#define PID_ENGINE_RPM          0x0C
#define PID_VEHICLE_SPEED       0x0D
#define PID_COOLANT_TEMP        0x05
#define PID_FUEL_LEVEL          0x2F
#define PID_ENGINE_LOAD         0x04
#define PID_FUEL_PRESSURE       0x0A
#define PID_INTAKE_TEMP         0x0F
#define PID_THROTTLE_POS        0x11
#define PID_GET_DTC             0x03

// OBD data structure
typedef struct {
    uint16_t engine_rpm;
    uint8_t vehicle_speed;
    uint8_t coolant_temp;
    uint8_t fuel_level;
    uint8_t engine_load;
    uint8_t fuel_pressure;
    uint8_t intake_temp;
    uint8_t throttle_pos;
    uint32_t timestamp;
} obd_data_t;

// OBD alert structure
typedef struct {
    uint8_t alert_type;
    uint8_t severity;
    char message[128];
    uint32_t timestamp;
} obd_alert_t;

// Function declarations
esp_err_t ai_servis_obd_init(void);
void ai_servis_obd_task(void *pvParameters);
esp_err_t ai_servis_obd_read_pid(uint8_t pid, uint8_t *data, size_t *length);
esp_err_t ai_servis_obd_parse_data(obd_data_t *data, uint8_t *response, size_t length);
void ai_servis_obd_check_alerts(obd_data_t *data);
