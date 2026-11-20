#include <Arduino.h>
#include <ctype.h>
#include <stddef.h>
#include <string.h>

#include "elm327_protocol.h"

namespace {

elm327::VehicleState g_vehicle_state = {0, 0, 0};
elm327::StateUpdateStream g_state_stream;

char g_obd_command[32];
size_t g_obd_command_length = 0;
bool g_obd_command_overflow = false;

void normalizeCommand(char* command) {
    size_t first = 0;
    while (command[first] == ' ' || command[first] == '\t') {
        ++first;
    }

    size_t length = strlen(command);
    while (length > first &&
           (command[length - 1] == ' ' || command[length - 1] == '\t')) {
        --length;
    }

    const size_t normalized_length = length - first;
    if (first > 0 && normalized_length > 0) {
        memmove(command, command + first, normalized_length);
    }
    command[normalized_length] = '\0';

    for (size_t i = 0; i < normalized_length; ++i) {
        command[i] = static_cast<char>(
            toupper(static_cast<unsigned char>(command[i]))
        );
    }
}

void handleObdCommand() {
    char response[16];
    if (g_obd_command_overflow) {
        strcpy(response, "?");
    } else {
        g_obd_command[g_obd_command_length] = '\0';
        normalizeCommand(g_obd_command);
        if (!elm327::buildResponse(
                g_obd_command,
                g_vehicle_state,
                response,
                sizeof(response))) {
            strcpy(response, "?");
        }
    }

    Serial.println(response);
    Serial.print('>');
    g_obd_command_length = 0;
    g_obd_command_overflow = false;
}

void readObdCommands() {
    while (Serial.available() > 0) {
        const int incoming = Serial.read();
        if (incoming == '\r') {
            handleObdCommand();
        } else if (incoming == '\n') {
            continue;
        } else if (!g_obd_command_overflow) {
            if (g_obd_command_length < sizeof(g_obd_command) - 1) {
                g_obd_command[g_obd_command_length++] =
                    static_cast<char>(incoming);
            } else {
                g_obd_command_overflow = true;
            }
        }
    }
}

void readStateUpdates() {
    while (Serial2.available() > 0) {
        const int incoming = Serial2.read();
        g_state_stream.feed(
            static_cast<uint8_t>(incoming),
            &g_vehicle_state
        );
    }
}

}  // namespace

void setup() {
    Serial.begin(38400);
    Serial2.begin(115200);
}

void loop() {
    readObdCommands();
    readStateUpdates();
}
