#ifndef MIA_PROTOCOL_H
#define MIA_PROTOCOL_H

#include <Arduino.h>
#include <HardwareSerial.h>

// Protocol constants
#define MIA_PROTOCOL_VERSION 1
#define MIA_START_BYTE 0xAA
#define MIA_END_BYTE 0x55
#define MIA_MAX_MESSAGE_SIZE 256
#define MIA_DEFAULT_TIMEOUT 1000  // ms

// Message types (must match FlatBuffers schema)
enum MIAMessageType {
    MSG_GPIO_COMMAND = 0,
    MSG_SENSOR_TELEMETRY = 1,
    MSG_SYSTEM_STATUS = 2,
    MSG_COMMAND_ACK = 3,
    MSG_DEVICE_INFO = 4,
    MSG_LED_STATE = 5,
    MSG_VEHICLE_TELEMETRY = 6,
    MSG_HANDSHAKE_REQUEST = 7,
    MSG_HANDSHAKE_RESPONSE = 8,
    MSG_ERROR = 9
};

// Device types
enum MIADeviceType {
    DEVICE_ARDUINO_UNO = 0,
    DEVICE_ARDUINO_MEGA = 1,
    DEVICE_ESP32 = 2,
    DEVICE_ESP8266 = 3,
    DEVICE_RASPBERRY_PI_PICO = 4
};

// Error codes
enum MIAErrorCode {
    ERROR_NONE = 0,
    ERROR_CRC_MISMATCH = 1,
    ERROR_INVALID_MESSAGE = 2,
    ERROR_TIMEOUT = 3,
    ERROR_BUFFER_OVERFLOW = 4,
    ERROR_UNSUPPORTED_COMMAND = 5
};

class MIAProtocol {
public:
    MIAProtocol(HardwareSerial* serial = &Serial, uint32_t baudRate = 115200);

    // Initialization
    bool begin();
    void end();

    // Message handling
    bool sendMessage(MIAMessageType type, const uint8_t* data, size_t length);
    bool receiveMessage(MIAMessageType& type, uint8_t* buffer, size_t& length, uint32_t timeout = MIA_DEFAULT_TIMEOUT);

    // Handshake protocol
    bool performHandshake(MIADeviceType deviceType, const char* deviceName);
    bool waitForHandshake(uint32_t timeout = 5000);

    // Utility functions
    uint16_t calculateCRC16(const uint8_t* data, size_t length);
    bool validateCRC16(const uint8_t* data, size_t length, uint16_t expectedCRC);

    // Device information
    void setDeviceInfo(MIADeviceType type, const char* name, const char* version = "1.0.0");
    MIADeviceType getDeviceType() const { return _deviceType; }
    const char* getDeviceName() const { return _deviceName; }

    // Error handling
    MIAErrorCode getLastError() const { return _lastError; }
    const char* getErrorString(MIAErrorCode error) const;

    // GPIO command handling (convenience functions)
    bool sendGPIOCommand(uint8_t pin, uint8_t direction, bool value);
    bool sendSensorTelemetry(uint8_t sensorId, uint8_t sensorType, float value, const char* unit);

private:
    HardwareSerial* _serial;
    uint32_t _baudRate;
    MIADeviceType _deviceType;
    char _deviceName[32];
    char _deviceVersion[16];
    MIAErrorCode _lastError;

    // Internal buffers
    uint8_t _txBuffer[MIA_MAX_MESSAGE_SIZE];
    uint8_t _rxBuffer[MIA_MAX_MESSAGE_SIZE];

    // Protocol state
    bool _handshakeComplete;
    uint32_t _lastActivity;

    // Private methods
    void _setLastError(MIAErrorCode error);
    bool _sendFramedMessage(const uint8_t* data, size_t length);
    bool _receiveFramedMessage(uint8_t* buffer, size_t& length, uint32_t timeout);
    size_t _encodeMessage(MIAMessageType type, const uint8_t* data, size_t length, uint8_t* output);
    bool _decodeMessage(const uint8_t* input, size_t inputLength, MIAMessageType& type, uint8_t* output, size_t& outputLength);
};

// Global protocol instance (optional convenience)
extern MIAProtocol MIAProtocolInstance;

#endif // MIA_PROTOCOL_H