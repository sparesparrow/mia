#include <stdio.h>
#include <string.h>

#include "elm327_protocol.h"

namespace {

bool expect(bool condition, const char* message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return false;
    }
    return true;
}

}  // namespace

int main() {
    bool ok = true;
    elm327::VehicleState state = {0, 0, 0};

    ok &= expect(
        elm327::parseStateUpdate("S:25:800:90", &state),
        "parses speed, RPM, and coolant temperature"
    );
    ok &= expect(
        state.speed_kph == 25 && state.rpm == 800 && state.coolant_temp_c == 90,
        "stores parsed vehicle values"
    );

    const elm327::VehicleState previous = state;
    ok &= expect(
        !elm327::parseStateUpdate("S:256:800:90", &state),
        "rejects speed above the OBD PID range"
    );
    ok &= expect(
        !elm327::parseStateUpdate("S:25:16384:90", &state),
        "rejects RPM above the OBD PID range"
    );
    ok &= expect(
        !elm327::parseStateUpdate("S:25:800:-41", &state),
        "rejects coolant temperature below the OBD PID range"
    );
    ok &= expect(
        !elm327::parseStateUpdate("S:25:800:216", &state),
        "rejects coolant temperature above the OBD PID range"
    );
    ok &= expect(
        !elm327::parseStateUpdate("S:25:800:90:extra", &state),
        "rejects extra fields"
    );
    ok &= expect(
        state.speed_kph == previous.speed_kph &&
            state.rpm == previous.rpm &&
            state.coolant_temp_c == previous.coolant_temp_c,
        "leaves the previous state unchanged after an invalid update"
    );

    const uint8_t binary_update[] = {'U', 0x20, 0x03, 40, 0};
    ok &= expect(
        elm327::parseBinaryStateUpdate(
            binary_update, sizeof(binary_update), &state),
        "parses the binary Serial2 packet emitted by obd_physics.py"
    );
    ok &= expect(
        state.speed_kph == 40 && state.rpm == 800 && state.coolant_temp_c == 90,
        "updates binary RPM and speed while preserving coolant temperature"
    );

    const elm327::VehicleState binary_previous = state;
    const uint8_t bad_checksum[] = {'U', 0x20, 0x03, 41, 1};
    const uint8_t bad_rpm[] = {'U', 0xFF, 0xFF, 41, 0};
    ok &= expect(
        !elm327::parseBinaryStateUpdate(
            bad_checksum, sizeof(bad_checksum), &state),
        "rejects a binary packet with a nonzero checksum marker"
    );
    ok &= expect(
        !elm327::parseBinaryStateUpdate(bad_rpm, sizeof(bad_rpm), &state),
        "rejects binary RPM outside the OBD PID range"
    );
    ok &= expect(
        state.speed_kph == binary_previous.speed_kph &&
            state.rpm == binary_previous.rpm &&
            state.coolant_temp_c == binary_previous.coolant_temp_c,
        "leaves state unchanged after an invalid binary packet"
    );

    elm327::StateUpdateStream stream;
    elm327::VehicleState streamed_state = {0, 0, 85};
    bool stream_updated = false;
    for (size_t i = 0; i < sizeof(binary_update); ++i) {
        stream_updated = stream.feed(binary_update[i], &streamed_state) ||
                         stream_updated;
    }
    ok &= expect(
        stream_updated && streamed_state.speed_kph == 40 && streamed_state.rpm == 800,
        "assembles a binary update across incoming Serial2 bytes"
    );
    const char text_update[] = "S:25:900:91\r\n";
    stream_updated = false;
    for (size_t i = 0; i < sizeof(text_update) - 1; ++i) {
        stream_updated = stream.feed(
            static_cast<uint8_t>(text_update[i]), &streamed_state) ||
            stream_updated;
    }
    ok &= expect(
        stream_updated && streamed_state.speed_kph == 25 &&
            streamed_state.rpm == 900 && streamed_state.coolant_temp_c == 91,
        "assembles newline-delimited text updates across incoming Serial2 bytes"
    );
    const elm327::VehicleState streamed_previous = streamed_state;
    const char malformed_update[] = "S:256:900:91\n";
    stream_updated = false;
    for (size_t i = 0; i < sizeof(malformed_update) - 1; ++i) {
        stream_updated = stream.feed(
            static_cast<uint8_t>(malformed_update[i]), &streamed_state) ||
            stream_updated;
    }
    ok &= expect(
        !stream_updated && streamed_state.speed_kph == streamed_previous.speed_kph &&
            streamed_state.rpm == streamed_previous.rpm &&
            streamed_state.coolant_temp_c == streamed_previous.coolant_temp_c,
        "does not change streamed state after an invalid text update"
    );

    char response[16];
    ok &= expect(
        elm327::buildResponse("ATZ", state, response, sizeof(response)) &&
            strcmp(response, "ELM327 v1.5") == 0,
        "answers ATZ with the adapter identity"
    );
    ok &= expect(
        elm327::buildResponse("010C", state, response, sizeof(response)) &&
            strcmp(response, "41 0C 0C 80") == 0,
        "encodes RPM in quarter-RPM units for PID 010C"
    );
    ok &= expect(
        elm327::buildResponse("010D", state, response, sizeof(response)) &&
            strcmp(response, "41 0D 28") == 0,
        "encodes speed in km/h for PID 010D"
    );
    ok &= expect(
        elm327::buildResponse("0105", state, response, sizeof(response)) &&
            strcmp(response, "?") == 0,
        "returns the ELM error marker for unsupported commands"
    );
    ok &= expect(
        !elm327::buildResponse("010C", state, response, 4),
        "rejects a response buffer that is too small"
    );

    return ok ? 0 : 1;
}
