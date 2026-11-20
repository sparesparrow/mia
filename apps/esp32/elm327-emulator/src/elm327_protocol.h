#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace elm327 {

struct VehicleState {
    int speed_kph;
    int rpm;
    int coolant_temp_c;
};

inline bool parseIntegerField(
    const char*& cursor,
    char delimiter,
    int minimum,
    int maximum,
    int& value
) {
    bool negative = false;
    if (*cursor == '-' && minimum < 0) {
        negative = true;
        ++cursor;
    }

    if (*cursor < '0' || *cursor > '9') {
        return false;
    }

    const int magnitude_limit = negative ? -minimum : maximum;
    int magnitude = 0;
    while (*cursor >= '0' && *cursor <= '9') {
        const int digit = *cursor - '0';
        if (magnitude > (magnitude_limit - digit) / 10) {
            return false;
        }
        magnitude = magnitude * 10 + digit;
        ++cursor;
    }

    const int parsed = negative ? -magnitude : magnitude;
    if (parsed < minimum || parsed > maximum || *cursor != delimiter) {
        return false;
    }

    if (delimiter != '\0') {
        ++cursor;
    }
    value = parsed;
    return true;
}

// Serial2 contract: S:<speed_kph>:<rpm>:<coolant_temp_c>\n
// Invalid or out-of-range updates leave the current state unchanged.
inline bool parseStateUpdate(const char* line, VehicleState* state) {
    if (line == NULL || state == NULL || line[0] != 'S' || line[1] != ':') {
        return false;
    }

    const char* cursor = line + 2;
    VehicleState parsed = {0, 0, 0};
    if (!parseIntegerField(cursor, ':', 0, 255, parsed.speed_kph) ||
        !parseIntegerField(cursor, ':', 0, 16383, parsed.rpm) ||
        !parseIntegerField(cursor, '\0', -40, 215, parsed.coolant_temp_c)) {
        return false;
    }

    *state = parsed;
    return true;
}

// Binary producer contract from obd_physics.py: U, little-endian RPM,
// speed, zero-valued checksum/reserved byte.
inline bool parseBinaryStateUpdate(
    const uint8_t* packet,
    size_t packet_size,
    VehicleState* state
) {
    if (packet == NULL || state == NULL || packet_size != 5 ||
        packet[0] != 'U' || packet[4] != 0) {
        return false;
    }

    const int rpm = static_cast<int>(packet[1]) |
                    (static_cast<int>(packet[2]) << 8);
    if (rpm > 16383) {
        return false;
    }

    state->rpm = rpm;
    state->speed_kph = packet[3];
    return true;
}

class StateUpdateStream {
public:
    StateUpdateStream()
        : mode_(IDLE), text_length_(0), binary_length_(0), overflow_(false) {}

    // Feed one Serial2 byte. Returns true only when a valid update is applied.
    bool feed(uint8_t byte, VehicleState* state) {
        if (mode_ == IDLE) {
            if (byte == 'S') {
                mode_ = TEXT;
                text_[0] = 'S';
                text_length_ = 1;
            } else if (byte == 'U') {
                mode_ = BINARY;
                binary_[0] = 'U';
                binary_length_ = 1;
            }
            return false;
        }

        if (mode_ == BINARY) {
            binary_[binary_length_++] = byte;
            if (binary_length_ == sizeof(binary_)) {
                const bool updated = parseBinaryStateUpdate(
                    binary_, sizeof(binary_), state);
                reset();
                return updated;
            }
            return false;
        }

        if (byte == '\n') {
            if (overflow_) {
                reset();
                return false;
            }
            if (text_length_ > 0 && text_[text_length_ - 1] == '\r') {
                --text_length_;
            }
            text_[text_length_] = '\0';
            const bool updated = parseStateUpdate(text_, state);
            reset();
            return updated;
        }

        if (!overflow_) {
            if (text_length_ < sizeof(text_) - 1) {
                text_[text_length_++] = static_cast<char>(byte);
            } else {
                overflow_ = true;
            }
        }
        return false;
    }

private:
    enum Mode { IDLE, TEXT, BINARY };

    void reset() {
        mode_ = IDLE;
        text_length_ = 0;
        binary_length_ = 0;
        overflow_ = false;
    }

    Mode mode_;
    char text_[48];
    size_t text_length_;
    uint8_t binary_[5];
    size_t binary_length_;
    bool overflow_;
};

inline bool buildResponse(
    const char* command,
    const VehicleState& state,
    char* response,
    size_t response_size
) {
    if (command == NULL || response == NULL || response_size == 0) {
        return false;
    }

    int written = -1;
    if (strcmp(command, "ATZ") == 0) {
        written = snprintf(response, response_size, "ELM327 v1.5");
    } else if (strcmp(command, "010C") == 0) {
        const uint16_t encoded_rpm = static_cast<uint16_t>(state.rpm * 4);
        written = snprintf(
            response,
            response_size,
            "41 0C %02X %02X",
            static_cast<unsigned int>((encoded_rpm >> 8) & 0xFF),
            static_cast<unsigned int>(encoded_rpm & 0xFF)
        );
    } else if (strcmp(command, "010D") == 0) {
        written = snprintf(
            response,
            response_size,
            "41 0D %02X",
            static_cast<unsigned int>(state.speed_kph & 0xFF)
        );
    } else {
        written = snprintf(response, response_size, "?");
    }

    return written >= 0 && static_cast<size_t>(written) < response_size;
}

}  // namespace elm327
