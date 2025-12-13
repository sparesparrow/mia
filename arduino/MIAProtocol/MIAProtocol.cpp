#include "MIAProtocol.h"

// Constructor
MIAProtocol::MIAProtocol(HardwareSerial* serial, uint32_t baudRate)
    : _serial(serial), _baudRate(baudRate), _deviceType(DEVICE_ARDUINO_UNO),
      _lastError(ERROR_NONE), _handshakeComplete(false), _lastActivity(0) {
    memset(_deviceName, 0, sizeof(_deviceName));
    memset(_deviceVersion, 0, sizeof(_deviceVersion));
    strcpy(_deviceVersion, "1.0.0");
}

// Initialize the protocol
bool MIAProtocol::begin() {
    _serial->begin(_baudRate);
    _serial->setTimeout(100); // 100ms timeout for reads

    // Wait for serial to be ready
    delay(100);

    _lastError = ERROR_NONE;
    _lastActivity = millis();

    return _serial->availableForWrite() > 0;
}

// End the protocol
void MIAProtocol::end() {
    _handshakeComplete = false;
    _serial->end();
}

// Send a message with type and data
bool MIAProtocol::sendMessage(MIAMessageType type, const uint8_t* data, size_t length) {
    if (length > MIA_MAX_MESSAGE_SIZE - 8) { // Account for protocol overhead
        _setLastError(ERROR_BUFFER_OVERFLOW);
        return false;
    }

    // Encode message into tx buffer
    size_t encodedLength = _encodeMessage(type, data, length, _txBuffer);

    if (encodedLength == 0) {
        return false;
    }

    // Send framed message
    if (_sendFramedMessage(_txBuffer, encodedLength)) {
        _lastActivity = millis();
        return true;
    }

    return false;
}

// Receive a message
bool MIAProtocol::receiveMessage(MIAMessageType& type, uint8_t* buffer, size_t& length, uint32_t timeout) {
    if (_receiveFramedMessage(_rxBuffer, length, timeout)) {
        if (_decodeMessage(_rxBuffer, length, type, buffer, length)) {
            _lastActivity = millis();
            return true;
        }
    }

    return false;
}

// Perform handshake with host
bool MIAProtocol::performHandshake(MIADeviceType deviceType, const char* deviceName) {
    // Create handshake message
    uint8_t handshakeData[64];
    size_t dataLength = 0;

    // Pack device info into handshake data
    handshakeData[dataLength++] = (uint8_t)deviceType;
    handshakeData[dataLength++] = MIA_PROTOCOL_VERSION;

    size_t nameLen = strlen(deviceName);
    if (nameLen > 30) nameLen = 30; // Limit name length

    memcpy(&handshakeData[dataLength], deviceName, nameLen);
    dataLength += nameLen;
    handshakeData[dataLength++] = 0; // Null terminator

    memcpy(&handshakeData[dataLength], _deviceVersion, strlen(_deviceVersion));
    dataLength += strlen(_deviceVersion) + 1; // Include null terminator

    // Send handshake request
    if (!sendMessage(MSG_HANDSHAKE_REQUEST, handshakeData, dataLength)) {
        return false;
    }

    // Wait for handshake response
    MIAMessageType responseType;
    uint8_t responseBuffer[32];
    size_t responseLength;

    if (receiveMessage(responseType, responseBuffer, responseLength, 2000)) {
        if (responseType == MSG_HANDSHAKE_RESPONSE && responseLength >= 1) {
            if (responseBuffer[0] == 1) { // Success byte
                _handshakeComplete = true;
                return true;
            }
        }
    }

    _setLastError(ERROR_TIMEOUT);
    return false;
}

// Wait for incoming handshake
bool MIAProtocol::waitForHandshake(uint32_t timeout) {
    uint32_t startTime = millis();

    while (millis() - startTime < timeout) {
        MIAMessageType msgType;
        uint8_t buffer[64];
        size_t length;

        if (receiveMessage(msgType, buffer, length, 100)) {
            if (msgType == MSG_HANDSHAKE_REQUEST && length >= 3) {
                // Parse handshake request
                MIADeviceType remoteDeviceType = (MIADeviceType)buffer[0];
                uint8_t protocolVersion = buffer[1];

                // Extract device name and version
                char remoteName[32] = {0};
                char remoteVersion[16] = {0};

                size_t offset = 2;
                size_t nameLen = 0;
                while (offset < length && buffer[offset] != 0 && nameLen < 31) {
                    remoteName[nameLen++] = buffer[offset++];
                }
                offset++; // Skip null terminator

                size_t versionLen = 0;
                while (offset < length && buffer[offset] != 0 && versionLen < 15) {
                    remoteVersion[versionLen++] = buffer[offset++];
                }

                // Send handshake response
                uint8_t responseData[2] = {1, 0}; // Success, reserved
                if (sendMessage(MSG_HANDSHAKE_RESPONSE, responseData, 2)) {
                    _handshakeComplete = true;
                    return true;
                }
            }
        }
    }

    _setLastError(ERROR_TIMEOUT);
    return false;
}

// Set device information
void MIAProtocol::setDeviceInfo(MIADeviceType type, const char* name, const char* version) {
    _deviceType = type;
    strncpy(_deviceName, name, sizeof(_deviceName) - 1);
    if (version) {
        strncpy(_deviceVersion, version, sizeof(_deviceVersion) - 1);
    }
}

// Calculate CRC16-CCITT
uint16_t MIAProtocol::calculateCRC16(const uint8_t* data, size_t length) {
    uint16_t crc = 0xFFFF;

    for (size_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;

        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }

    return crc;
}

// Validate CRC16
bool MIAProtocol::validateCRC16(const uint8_t* data, size_t length, uint16_t expectedCRC) {
    uint16_t calculatedCRC = calculateCRC16(data, length);
    return calculatedCRC == expectedCRC;
}

// Get error string
const char* MIAProtocol::getErrorString(MIAErrorCode error) const {
    switch (error) {
        case ERROR_NONE: return "No error";
        case ERROR_CRC_MISMATCH: return "CRC mismatch";
        case ERROR_INVALID_MESSAGE: return "Invalid message";
        case ERROR_TIMEOUT: return "Timeout";
        case ERROR_BUFFER_OVERFLOW: return "Buffer overflow";
        case ERROR_UNSUPPORTED_COMMAND: return "Unsupported command";
        default: return "Unknown error";
    }
}

// Convenience function to send GPIO command
bool MIAProtocol::sendGPIOCommand(uint8_t pin, uint8_t direction, bool value) {
    uint8_t gpioData[3] = {pin, direction, value ? 1 : 0};
    return sendMessage(MSG_GPIO_COMMAND, gpioData, 3);
}

// Convenience function to send sensor telemetry
bool MIAProtocol::sendSensorTelemetry(uint8_t sensorId, uint8_t sensorType, float value, const char* unit) {
    uint8_t sensorData[64];
    size_t offset = 0;

    sensorData[offset++] = sensorId;
    sensorData[offset++] = sensorType;

    // Pack float as bytes (little-endian)
    memcpy(&sensorData[offset], &value, sizeof(float));
    offset += sizeof(float);

    // Copy unit string
    size_t unitLen = strlen(unit);
    if (unitLen > 10) unitLen = 10; // Limit unit length
    memcpy(&sensorData[offset], unit, unitLen);
    offset += unitLen;
    sensorData[offset++] = 0; // Null terminator

    return sendMessage(MSG_SENSOR_TELEMETRY, sensorData, offset);
}

// Private: Set last error
void MIAProtocol::_setLastError(MIAErrorCode error) {
    _lastError = error;
}

// Private: Send framed message with start/end bytes and CRC
bool MIAProtocol::_sendFramedMessage(const uint8_t* data, size_t length) {
    // Send start byte
    _serial->write(MIA_START_BYTE);

    // Send length (2 bytes, big-endian)
    _serial->write((length >> 8) & 0xFF);
    _serial->write(length & 0xFF);

    // Send data
    _serial->write(data, length);

    // Calculate and send CRC
    uint16_t crc = calculateCRC16(data, length);
    _serial->write((crc >> 8) & 0xFF);
    _serial->write(crc & 0xFF);

    // Send end byte
    _serial->write(MIA_END_BYTE);

    // Wait for data to be sent
    _serial->flush();

    return true;
}

// Private: Receive framed message
bool MIAProtocol::_receiveFramedMessage(uint8_t* buffer, size_t& length, uint32_t timeout) {
    uint32_t startTime = millis();

    // Wait for start byte
    while (millis() - startTime < timeout) {
        if (_serial->available()) {
            uint8_t byte = _serial->read();
            if (byte == MIA_START_BYTE) {
                break;
            }
        }
        delay(1);
    }

    if (millis() - startTime >= timeout) {
        _setLastError(ERROR_TIMEOUT);
        return false;
    }

    // Read length (2 bytes, big-endian)
    uint16_t msgLength = 0;
    if (_serial->available() >= 2) {
        msgLength = (_serial->read() << 8) | _serial->read();
    } else {
        _setLastError(ERROR_INVALID_MESSAGE);
        return false;
    }

    if (msgLength > MIA_MAX_MESSAGE_SIZE) {
        _setLastError(ERROR_BUFFER_OVERFLOW);
        return false;
    }

    // Read data
    uint32_t dataStartTime = millis();
    size_t bytesRead = 0;

    while (bytesRead < msgLength && millis() - dataStartTime < timeout) {
        if (_serial->available()) {
            buffer[bytesRead++] = _serial->read();
        }
        delay(1);
    }

    if (bytesRead != msgLength) {
        _setLastError(ERROR_TIMEOUT);
        return false;
    }

    // Read CRC (2 bytes)
    uint16_t receivedCRC = 0;
    if (_serial->available() >= 2) {
        receivedCRC = (_serial->read() << 8) | _serial->read();
    } else {
        _setLastError(ERROR_INVALID_MESSAGE);
        return false;
    }

    // Validate CRC
    if (!validateCRC16(buffer, msgLength, receivedCRC)) {
        _setLastError(ERROR_CRC_MISMATCH);
        return false;
    }

    // Read end byte
    uint32_t endByteStartTime = millis();
    while (millis() - endByteStartTime < 100) { // 100ms timeout for end byte
        if (_serial->available()) {
            uint8_t endByte = _serial->read();
            if (endByte == MIA_END_BYTE) {
                length = msgLength;
                return true;
            }
        }
        delay(1);
    }

    _setLastError(ERROR_INVALID_MESSAGE);
    return false;
}

// Private: Encode message with type prefix
size_t MIAProtocol::_encodeMessage(MIAMessageType type, const uint8_t* data, size_t length, uint8_t* output) {
    if (length > MIA_MAX_MESSAGE_SIZE - 1) {
        _setLastError(ERROR_BUFFER_OVERFLOW);
        return 0;
    }

    output[0] = (uint8_t)type;
    memcpy(&output[1], data, length);

    return length + 1;
}

// Private: Decode message and extract type
bool MIAProtocol::_decodeMessage(const uint8_t* input, size_t inputLength, MIAMessageType& type, uint8_t* output, size_t& outputLength) {
    if (inputLength < 1) {
        _setLastError(ERROR_INVALID_MESSAGE);
        return false;
    }

    type = (MIAMessageType)input[0];
    outputLength = inputLength - 1;

    if (outputLength > 0) {
        memcpy(output, &input[1], outputLength);
    }

    return true;
}

// Global instance
MIAProtocol MIAProtocolInstance;