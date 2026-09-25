/*
 * MIA Protocol Basic Example
 *
 * This example demonstrates basic usage of the MIA Protocol library
 * for Arduino devices. It shows how to:
 * - Initialize the protocol
 * - Perform handshake
 * - Send sensor telemetry
 * - Receive and respond to GPIO commands
 */

#include <MIAProtocol.h>

// Create protocol instance
MIAProtocol miaProtocol(&Serial, 115200);

// Example sensor pins
const int TEMP_SENSOR_PIN = A0;
const int LIGHT_SENSOR_PIN = A1;

// LED for GPIO control demo
const int LED_PIN = 13;

// Timing
unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL = 2000; // 2 seconds

void setup() {
    // Initialize serial for debugging
    Serial.begin(9600);
    Serial.println("MIA Protocol Basic Example");

    // Set device information
    miaProtocol.setDeviceInfo(DEVICE_ARDUINO_UNO, "ArduinoUNO-01", "1.0.0");

    // Initialize protocol
    if (!miaProtocol.begin()) {
        Serial.println("Failed to initialize MIA Protocol!");
        while (1); // Halt
    }

    // Setup pins
    pinMode(LED_PIN, OUTPUT);
    pinMode(TEMP_SENSOR_PIN, INPUT);
    pinMode(LIGHT_SENSOR_PIN, INPUT);

    // Perform handshake with host
    Serial.println("Performing handshake...");
    if (miaProtocol.performHandshake(DEVICE_ARDUINO_UNO, "ArduinoUNO-01")) {
        Serial.println("Handshake successful!");
    } else {
        Serial.print("Handshake failed: ");
        Serial.println(miaProtocol.getErrorString(miaProtocol.getLastError()));
        // Continue anyway for demo purposes
    }
}

void loop() {
    // Check for incoming messages
    MIAMessageType msgType;
    uint8_t msgBuffer[128];
    size_t msgLength;

    if (miaProtocol.receiveMessage(msgType, msgBuffer, msgLength, 10)) { // 10ms timeout
        handleIncomingMessage(msgType, msgBuffer, msgLength);
    }

    // Send telemetry periodically
    if (millis() - lastTelemetryTime >= TELEMETRY_INTERVAL) {
        sendTelemetry();
        lastTelemetryTime = millis();
    }
}

void handleIncomingMessage(MIAMessageType msgType, uint8_t* buffer, size_t length) {
    switch (msgType) {
        case MSG_GPIO_COMMAND:
            handleGPIOCommand(buffer, length);
            break;

        case MSG_HANDSHAKE_REQUEST:
            // Handshake is handled automatically by the library
            break;

        default:
            Serial.print("Received unknown message type: ");
            Serial.println((int)msgType);
            break;
    }
}

void handleGPIOCommand(uint8_t* buffer, size_t length) {
    if (length >= 3) {
        uint8_t pin = buffer[0];
        uint8_t direction = buffer[1];
        bool value = buffer[2] > 0;

        Serial.print("GPIO Command - Pin: ");
        Serial.print(pin);
        Serial.print(", Direction: ");
        Serial.print(direction);
        Serial.print(", Value: ");
        Serial.println(value);

        // For demo, only handle LED pin
        if (pin == LED_PIN) {
            if (direction == 1) { // Output
                pinMode(pin, OUTPUT);
                digitalWrite(pin, value ? HIGH : LOW);
            }
        }

        // Send acknowledgment
        uint8_t ackData[4] = {0, 0, 0, 0}; // command_id, success, error_code, reserved
        ackData[1] = 1; // Success
        miaProtocol.sendMessage(MSG_COMMAND_ACK, ackData, 4);
    }
}

void sendTelemetry() {
    // Read temperature sensor (simulate with analog read)
    int tempRaw = analogRead(TEMP_SENSOR_PIN);
    float temperature = map(tempRaw, 0, 1023, -40, 125); // Convert to Celsius

    // Read light sensor
    int lightRaw = analogRead(LIGHT_SENSOR_PIN);
    float lightLevel = map(lightRaw, 0, 1023, 0, 100); // Convert to percentage

    // Send temperature telemetry
    if (!miaProtocol.sendSensorTelemetry(1, 0, temperature, "C")) {
        Serial.println("Failed to send temperature telemetry");
    }

    // Send light level telemetry
    if (!miaProtocol.sendSensorTelemetry(2, 4, lightLevel, "%")) {
        Serial.println("Failed to send light telemetry");
    }

    Serial.print("Sent telemetry - Temp: ");
    Serial.print(temperature);
    Serial.print("C, Light: ");
    Serial.print(lightLevel);
    Serial.println("%");
}