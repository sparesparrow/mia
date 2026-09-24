#include "ai_servis_ble.h"

#include <string.h>

#include "ai_servis_config.h"
#include "esp_bt.h"
#include "esp_bt_defs.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatt_common_api.h"
#include "esp_gatts_api.h"
#include "esp_log.h"
#include "freertos/task.h"

static const char *TAG = "AI_SERVIS_BLE";

#define BLE_APP_ID      0
#define BLE_SVC_INST_ID 0
#define BLE_LOCAL_MTU   256
#define QUEUE_WAIT_MS   1000

// 16-bit UUIDs from the range reserved for vendor use.
#define UUID_SERVICE   0xFF01
#define UUID_CHAR_CMD  0xFF02
#define UUID_CHAR_TELE 0xFF03

enum {
    IDX_SVC,
    IDX_CHAR_CMD,
    IDX_CHAR_VAL_CMD,
    IDX_CHAR_TELE,
    IDX_CHAR_VAL_TELE,
    IDX_CHAR_CFG_TELE,
    IDX_NB,
};

static uint16_t s_handle_table[IDX_NB];
static esp_gatt_if_t s_gatts_if = ESP_GATT_IF_NONE;
static uint16_t s_conn_id;
static volatile bool s_connected = false;
static volatile bool s_notify_enabled = false;
static obd_data_t s_last_telemetry;

static const uint16_t primary_service_uuid = ESP_GATT_UUID_PRI_SERVICE;
static const uint16_t character_declaration_uuid = ESP_GATT_UUID_CHAR_DECLARE;
static const uint16_t character_client_config_uuid = ESP_GATT_UUID_CHAR_CLIENT_CONFIG;
static const uint8_t char_prop_write = ESP_GATT_CHAR_PROP_BIT_WRITE | ESP_GATT_CHAR_PROP_BIT_WRITE_NR;
static const uint8_t char_prop_read_notify = ESP_GATT_CHAR_PROP_BIT_READ | ESP_GATT_CHAR_PROP_BIT_NOTIFY;

static const uint16_t service_uuid = UUID_SERVICE;
static const uint16_t char_cmd_uuid = UUID_CHAR_CMD;
static const uint16_t char_tele_uuid = UUID_CHAR_TELE;

static uint8_t char_cmd_value[AI_SERVIS_BLE_PAYLOAD_MAX + 1];
static uint8_t char_tele_value[AI_SERVIS_BLE_TELEMETRY_LEN];
static uint8_t char_tele_ccc[2] = {0x00, 0x00};

static const esp_gatts_attr_db_t gatt_db[IDX_NB] = {
    [IDX_SVC] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&primary_service_uuid, ESP_GATT_PERM_READ,
         sizeof(uint16_t), sizeof(service_uuid), (uint8_t *)&service_uuid},
    },

    [IDX_CHAR_CMD] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&character_declaration_uuid, ESP_GATT_PERM_READ,
         sizeof(uint8_t), sizeof(uint8_t), (uint8_t *)&char_prop_write},
    },

    [IDX_CHAR_VAL_CMD] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&char_cmd_uuid, ESP_GATT_PERM_WRITE,
         sizeof(char_cmd_value), 0, char_cmd_value},
    },

    [IDX_CHAR_TELE] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&character_declaration_uuid, ESP_GATT_PERM_READ,
         sizeof(uint8_t), sizeof(uint8_t), (uint8_t *)&char_prop_read_notify},
    },

    [IDX_CHAR_VAL_TELE] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&char_tele_uuid, ESP_GATT_PERM_READ,
         sizeof(char_tele_value), sizeof(char_tele_value), char_tele_value},
    },

    [IDX_CHAR_CFG_TELE] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&character_client_config_uuid,
         ESP_GATT_PERM_READ | ESP_GATT_PERM_WRITE,
         sizeof(char_tele_ccc), sizeof(char_tele_ccc), char_tele_ccc},
    },
};

static uint8_t adv_service_uuid[2] = {
    (uint8_t)(UUID_SERVICE & 0xFF),
    (uint8_t)((UUID_SERVICE >> 8) & 0xFF),
};

static esp_ble_adv_data_t adv_data = {
    .set_scan_rsp = false,
    .include_name = true,
    .include_txpower = true,
    .min_interval = 0x0006,
    .max_interval = 0x0010,
    .appearance = 0x00,
    .manufacturer_len = 0,
    .p_manufacturer_data = NULL,
    .service_data_len = 0,
    .p_service_data = NULL,
    .service_uuid_len = sizeof(adv_service_uuid),
    .p_service_uuid = adv_service_uuid,
    .flag = (ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT),
};

static esp_ble_adv_params_t adv_params = {
    .adv_int_min = 0x20,
    .adv_int_max = 0x40,
    .adv_type = ADV_TYPE_IND,
    .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
    .channel_map = ADV_CHNL_ALL,
    .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
};

/**
 * Serialise a sample into the 12-byte notification format. Explicit
 * little-endian rather than memcpy of the struct, so the layout does not
 * depend on the compiler's padding.
 */
static void pack_telemetry(const obd_data_t *data, uint8_t *out)
{
    out[0] = (uint8_t)(data->engine_rpm & 0xFF);
    out[1] = (uint8_t)((data->engine_rpm >> 8) & 0xFF);
    out[2] = data->vehicle_speed;
    out[3] = data->coolant_temp;
    out[4] = data->fuel_level;
    out[5] = data->engine_load;
    out[6] = data->throttle_pos;
    out[7] = data->intake_temp;
    out[8] = (uint8_t)(data->timestamp & 0xFF);
    out[9] = (uint8_t)((data->timestamp >> 8) & 0xFF);
    out[10] = (uint8_t)((data->timestamp >> 16) & 0xFF);
    out[11] = (uint8_t)((data->timestamp >> 24) & 0xFF);
}

static void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param)
{
    switch (event) {
        case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
            esp_ble_gap_start_advertising(&adv_params);
            break;

        case ESP_GAP_BLE_ADV_START_COMPLETE_EVT:
            if (param->adv_start_cmpl.status != ESP_BT_STATUS_SUCCESS) {
                ESP_LOGE(TAG, "Advertising failed to start");
            } else {
                ESP_LOGI(TAG, "Advertising started");
            }
            break;

        case ESP_GAP_BLE_ADV_STOP_COMPLETE_EVT:
            if (param->adv_stop_cmpl.status != ESP_BT_STATUS_SUCCESS) {
                ESP_LOGE(TAG, "Advertising failed to stop");
            }
            break;

        default:
            break;
    }
}

/** Turn a GATT write on the command characteristic into a queued command. */
static void handle_command_write(const uint8_t *value, uint16_t length)
{
    if (length == 0 || !ble_queue) {
        return;
    }

    ble_command_t command = {0};
    command.id = value[0];
    command.length = (uint16_t)(length - 1);
    if (command.length > AI_SERVIS_BLE_PAYLOAD_MAX) {
        command.length = AI_SERVIS_BLE_PAYLOAD_MAX;
    }
    if (command.length > 0) {
        memcpy(command.payload, &value[1], command.length);
    }
    command.timestamp = (uint32_t)xTaskGetTickCount();

    if (xQueueSend(ble_queue, &command, 0) != pdTRUE) {
        ESP_LOGW(TAG, "Command queue full, dropping command %u", (unsigned)command.id);
    }
}

static void gatts_event_handler(esp_gatts_cb_event_t event, esp_gatt_if_t gatts_if,
                                esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
        case ESP_GATTS_REG_EVT: {
            s_gatts_if = gatts_if;
            const ai_servis_config_t *config = ai_servis_config_get();

            esp_err_t ret = esp_ble_gap_set_device_name(config->device_id);
            if (ret != ESP_OK) {
                ESP_LOGE(TAG, "Failed to set device name: %s", esp_err_to_name(ret));
            }

            ret = esp_ble_gap_config_adv_data(&adv_data);
            if (ret != ESP_OK) {
                ESP_LOGE(TAG, "Failed to configure advertising data: %s", esp_err_to_name(ret));
            }

            ret = esp_ble_gatts_create_attr_tab(gatt_db, gatts_if, IDX_NB, BLE_SVC_INST_ID);
            if (ret != ESP_OK) {
                ESP_LOGE(TAG, "Failed to create attribute table: %s", esp_err_to_name(ret));
            }
            break;
        }

        case ESP_GATTS_CREAT_ATTR_TAB_EVT:
            if (param->add_attr_tab.status != ESP_GATT_OK) {
                ESP_LOGE(TAG, "Attribute table creation failed, status %d",
                         param->add_attr_tab.status);
            } else if (param->add_attr_tab.num_handle != IDX_NB) {
                ESP_LOGE(TAG, "Attribute table has %d handles, expected %d",
                         param->add_attr_tab.num_handle, IDX_NB);
            } else {
                memcpy(s_handle_table, param->add_attr_tab.handles, sizeof(s_handle_table));
                esp_ble_gatts_start_service(s_handle_table[IDX_SVC]);
                ESP_LOGI(TAG, "GATT service started");
            }
            break;

        case ESP_GATTS_WRITE_EVT:
            if (param->write.handle == s_handle_table[IDX_CHAR_VAL_CMD]) {
                handle_command_write(param->write.value, param->write.len);
            } else if (param->write.handle == s_handle_table[IDX_CHAR_CFG_TELE] &&
                       param->write.len == 2) {
                uint16_t descriptor = (uint16_t)(param->write.value[0] |
                                                 (param->write.value[1] << 8));
                s_notify_enabled = (descriptor == 0x0001);
                ESP_LOGI(TAG, "Telemetry notifications %s",
                         s_notify_enabled ? "enabled" : "disabled");
            }
            break;

        case ESP_GATTS_CONNECT_EVT:
            s_conn_id = param->connect.conn_id;
            s_connected = true;
            ESP_LOGI(TAG, "Client connected, conn_id=%u", (unsigned)s_conn_id);
            break;

        case ESP_GATTS_DISCONNECT_EVT:
            s_connected = false;
            s_notify_enabled = false;
            ESP_LOGI(TAG, "Client disconnected, reason 0x%x, restarting advertising",
                     param->disconnect.reason);
            esp_ble_gap_start_advertising(&adv_params);
            break;

        default:
            break;
    }
}

esp_err_t ai_servis_ble_init(void)
{
    ai_servis_config_init();
    memset(&s_last_telemetry, 0, sizeof(s_last_telemetry));

    // BLE-only firmware: hand the Classic BT memory back before the controller starts.
    esp_err_t ret = esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Failed to release Classic BT memory: %s", esp_err_to_name(ret));
    }

    esp_bt_controller_config_t bt_config = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    ret = esp_bt_controller_init(&bt_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BT controller init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_bt_controller_enable(ESP_BT_MODE_BLE);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BT controller enable failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_bluedroid_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Bluedroid init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_bluedroid_enable();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Bluedroid enable failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_ble_gatts_register_callback(gatts_event_handler);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register GATTS callback: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_ble_gap_register_callback(gap_event_handler);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register GAP callback: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_ble_gatts_app_register(BLE_APP_ID);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register GATTS app: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_ble_gatt_set_local_mtu(BLE_LOCAL_MTU);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Failed to set local MTU: %s", esp_err_to_name(ret));
    }

    ESP_LOGI(TAG, "BLE GATT server initialized");
    return ESP_OK;
}

bool ai_servis_ble_is_connected(void)
{
    return s_connected;
}

esp_err_t ai_servis_ble_notify_telemetry(const obd_data_t *data)
{
    if (!data) {
        return ESP_ERR_INVALID_ARG;
    }

    s_last_telemetry = *data;
    pack_telemetry(data, char_tele_value);

    // Keep the readable value current even with nobody subscribed, so a plain
    // GATT read returns the last sample rather than zeroes.
    if (s_handle_table[IDX_CHAR_VAL_TELE] != 0) {
        esp_ble_gatts_set_attr_value(s_handle_table[IDX_CHAR_VAL_TELE],
                                     sizeof(char_tele_value), char_tele_value);
    }

    if (!s_connected || !s_notify_enabled || s_gatts_if == ESP_GATT_IF_NONE) {
        return ESP_OK;
    }

    return esp_ble_gatts_send_indicate(s_gatts_if, s_conn_id,
                                       s_handle_table[IDX_CHAR_VAL_TELE],
                                       sizeof(char_tele_value), char_tele_value,
                                       false);
}

/** Answer a single-PID query from the last sample rather than hitting the bus. */
static void report_pid(uint8_t pid)
{
    switch (pid) {
        case PID_ENGINE_RPM:
            ESP_LOGI(TAG, "PID 0x%02X (RPM) = %u", pid, (unsigned)s_last_telemetry.engine_rpm);
            break;
        case PID_VEHICLE_SPEED:
            ESP_LOGI(TAG, "PID 0x%02X (speed) = %u", pid, (unsigned)s_last_telemetry.vehicle_speed);
            break;
        case PID_COOLANT_TEMP:
            ESP_LOGI(TAG, "PID 0x%02X (coolant) = %u", pid, (unsigned)s_last_telemetry.coolant_temp);
            break;
        case PID_FUEL_LEVEL:
            ESP_LOGI(TAG, "PID 0x%02X (fuel) = %u", pid, (unsigned)s_last_telemetry.fuel_level);
            break;
        default:
            ESP_LOGW(TAG, "PID 0x%02X is not polled, no cached value", pid);
            break;
    }
}

void ai_servis_ble_task(void *pvParameters)
{
    (void)pvParameters;

    ESP_LOGI(TAG, "BLE task started");

    ble_command_t command;

    while (1) {
        if (xQueueReceive(ble_queue, &command, pdMS_TO_TICKS(QUEUE_WAIT_MS)) != pdTRUE) {
            continue;
        }

        switch (command.id) {
            case BLE_CMD_REQUEST_STATUS:
                ai_servis_ble_notify_telemetry(&s_last_telemetry);
                break;

            case BLE_CMD_READ_PID:
                // Answered from cache on purpose: transmitting here would race
                // the OBD polling task for the TWAI bus.
                if (command.length >= 1) {
                    report_pid(command.payload[0]);
                }
                break;

            case BLE_CMD_SET_POLL_INTERVAL:
                if (command.length >= 2) {
                    uint16_t interval = (uint16_t)(command.payload[0] |
                                                   (command.payload[1] << 8));
                    ESP_LOGI(TAG, "Poll interval change requested: %u ms", (unsigned)interval);
                }
                break;

            default:
                ESP_LOGW(TAG, "Unknown command id %u", (unsigned)command.id);
                break;
        }
    }
}
