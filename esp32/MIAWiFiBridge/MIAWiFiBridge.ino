/*
 * MIA WiFi Bridge for ESP32
 *
 * This ESP32 application creates a WiFi bridge for MIA devices,
 * allowing them to communicate with the MIA system over WiFi.
 *
 * Features:
 * - WiFi Access Point mode for direct connection
 * - WiFi Station mode for network integration
 * - TCP server for device connections
 * - Bridge to ZeroMQ via serial or network
 * - Device discovery and management
 * - OTA updates support
 */

#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiServer.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include <Preferences.h>

// Bridge configuration
#define WIFI_AP_MODE true          // Start in AP mode by default
#define WIFI_STATION_MODE false    // Station mode backup
#define TCP_SERVER_PORT 8888       // TCP server port for device connections
#define MAX_DEVICES 8              // Maximum connected devices
#define HEARTBEAT_INTERVAL 30000   // 30 seconds
#define DEVICE_TIMEOUT 60000       // 60 seconds device timeout

// WiFi configuration
const char* AP_SSID = "MIA-Bridge";
const char* AP_PASSWORD = "mia123456";
const char* STA_SSID = "YourWiFiSSID";     // Configure for your network
const char* STA_PASSWORD = "YourWiFiPass";

// Bridge state
enum BridgeMode { MODE_AP, MODE_STATION, MODE_AUTO };
enum BridgeState { STATE_INIT, STATE_CONNECTING, STATE_CONNECTED, STATE_ERROR };

BridgeMode currentMode = WIFI_AP_MODE ? MODE_AP : MODE_STATION;
BridgeState currentState = STATE_INIT;

// TCP server
WiFiServer tcpServer(TCP_SERVER_PORT);
WiFiClient clients[MAX_DEVICES];

// Device management
struct DeviceInfo {
    uint8_t id;
    IPAddress ip;
    uint32_t lastSeen;
    bool connected;
    char name[32];
};

DeviceInfo devices[MAX_DEVICES];
uint8_t nextDeviceId = 1;

// Timing
unsigned long lastHeartbeat = 0;
unsigned long lastStatusPrint = 0;

// Preferences for persistent config
Preferences preferences;

// Forward declarations
void setupWiFi();
void handleClients();
void broadcastMessage(const uint8_t* data, size_t length, uint8_t excludeId = 0);
void sendDeviceList(WiFiClient& client);
void handleDeviceMessage(WiFiClient& client, uint8_t deviceId, const uint8_t* data, size_t length);
void cleanupDisconnectedDevices();
void printStatus();

void setup() {
    Serial.begin(115200);
    Serial.println("\n=== MIA WiFi Bridge Starting ===");

    // Initialize preferences
    preferences.begin("mia-bridge", false);

    // Load configuration
    currentMode = (BridgeMode)preferences.getInt("bridge_mode", currentMode);

    // Setup WiFi
    setupWiFi();

    // Start TCP server
    tcpServer.begin();
    Serial.print("TCP server started on port ");
    Serial.println(TCP_SERVER_PORT);

    // Setup OTA
    setupOTA();

    // Initialize device array
    memset(devices, 0, sizeof(devices));

    Serial.println("MIA WiFi Bridge initialized");
    printStatus();
}

void loop() {
    // Handle WiFi reconnection if needed
    if (WiFi.status() != WL_CONNECTED && currentMode == MODE_STATION) {
        Serial.println("WiFi disconnected, attempting reconnection...");
        setupWiFi();
    }

    // Handle incoming client connections
    handleClients();

    // Cleanup disconnected devices
    cleanupDisconnectedDevices();

    // Send periodic heartbeat
    if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
        uint8_t heartbeatMsg[4] = {'H', 'B', 0, 0}; // Heartbeat message
        broadcastMessage(heartbeatMsg, 4);
        lastHeartbeat = millis();
    }

    // Print status periodically
    if (millis() - lastStatusPrint > 10000) { // Every 10 seconds
        printStatus();
        lastStatusPrint = millis();
    }

    // Handle OTA
    ArduinoOTA.handle();

    delay(10); // Small delay to prevent overwhelming the processor
}

void setupWiFi() {
    currentState = STATE_CONNECTING;

    if (currentMode == MODE_AP) {
        // Access Point mode
        Serial.println("Starting WiFi Access Point...");
        WiFi.mode(WIFI_AP);
        WiFi.softAP(AP_SSID, AP_PASSWORD);

        IPAddress apIP = WiFi.softAPIP();
        Serial.print("AP IP address: ");
        Serial.println(apIP);

        // Setup mDNS
        if (MDNS.begin("mia-bridge")) {
            Serial.println("mDNS responder started");
            MDNS.addService("mia-bridge", "tcp", TCP_SERVER_PORT);
        }

        currentState = STATE_CONNECTED;

    } else if (currentMode == MODE_STATION) {
        // Station mode
        Serial.println("Connecting to WiFi network...");
        WiFi.mode(WIFI_STA);
        WiFi.begin(STA_SSID, STA_PASSWORD);

        // Wait for connection
        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 20) {
            delay(500);
            Serial.print(".");
            attempts++;
        }

        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("\nWiFi connected!");
            Serial.print("IP address: ");
            Serial.println(WiFi.localIP());
            currentState = STATE_CONNECTED;
        } else {
            Serial.println("\nWiFi connection failed!");
            currentState = STATE_ERROR;

            // Fallback to AP mode
            if (currentMode == MODE_AUTO) {
                Serial.println("Falling back to AP mode...");
                currentMode = MODE_AP;
                setupWiFi();
            }
        }
    }
}

void setupOTA() {
    ArduinoOTA.setHostname("mia-bridge");
    ArduinoOTA.setPassword("miaota"); // Change this for security

    ArduinoOTA.onStart([]() {
        Serial.println("OTA update starting...");
    });

    ArduinoOTA.onEnd([]() {
        Serial.println("OTA update finished!");
    });

    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        Serial.printf("OTA progress: %u%%\r", (progress / (total / 100)));
    });

    ArduinoOTA.onError([](ota_error_t error) {
        Serial.printf("OTA error[%u]: ", error);
        if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
        else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
        else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
        else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
        else if (error == OTA_END_ERROR) Serial.println("End Failed");
    });

    ArduinoOTA.begin();
    Serial.println("OTA ready");
}

void handleClients() {
    // Accept new connections
    WiFiClient newClient = tcpServer.accept();
    if (newClient) {
        Serial.println("New client connected");

        // Find free slot
        for (int i = 0; i < MAX_DEVICES; i++) {
            if (!clients[i] || !clients[i].connected()) {
                clients[i] = newClient;
                devices[i].id = nextDeviceId++;
                devices[i].ip = newClient.remoteIP();
                devices[i].connected = true;
                devices[i].lastSeen = millis();
                memset(devices[i].name, 0, sizeof(devices[i].name));
                strcpy(devices[i].name, "Unknown");

                Serial.printf("Assigned device ID: %d, IP: %s\n",
                            devices[i].id,
                            devices[i].ip.toString().c_str());

                // Send welcome message
                uint8_t welcomeMsg[8] = {'W', 'E', 'L', 'C', 'O', 'M', 'E', 0};
                clients[i].write(welcomeMsg, 8);

                break;
            }
        }
    }

    // Handle existing clients
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (clients[i] && clients[i].connected()) {
            // Check for incoming data
            if (clients[i].available()) {
                // Read message (simple protocol: length + data)
                if (clients[i].available() >= 2) {
                    uint8_t length = clients[i].read();
                    uint8_t msgType = clients[i].read();

                    if (clients[i].available() >= length) {
                        uint8_t* buffer = new uint8_t[length];
                        clients[i].readBytes(buffer, length);

                        handleDeviceMessage(clients[i], devices[i].id, buffer, length);
                        delete[] buffer;
                    }
                }

                devices[i].lastSeen = millis();
            }
        }
    }
}

void handleDeviceMessage(WiFiClient& client, uint8_t deviceId, const uint8_t* data, size_t length) {
    if (length < 1) return;

    uint8_t msgType = data[0];

    switch (msgType) {
        case 'R': // Register device
            if (length >= 2) {
                uint8_t nameLen = data[1];
                if (length >= 2 + nameLen) {
                    // Find device and update name
                    for (int i = 0; i < MAX_DEVICES; i++) {
                        if (devices[i].id == deviceId) {
                            memcpy(devices[i].name, &data[2], nameLen);
                            devices[i].name[nameLen] = 0;
                            Serial.printf("Device %d registered as: %s\n", deviceId, devices[i].name);

                            // Send acknowledgment
                            uint8_t ackMsg[4] = {'A', 'C', 'K', deviceId};
                            client.write(ackMsg, 4);
                            break;
                        }
                    }
                }
            }
            break;

        case 'D': // Data message
            if (length >= 2) {
                // Broadcast to other devices (excluding sender)
                broadcastMessage(data, length, deviceId);

                // Forward to serial (for ZeroMQ bridge)
                Serial.write(data, length);
            }
            break;

        case 'P': // Ping/heartbeat
            // Send pong
            uint8_t pongMsg[4] = {'P', 'O', 'N', 'G'};
            client.write(pongMsg, 4);
            break;

        default:
            Serial.printf("Unknown message type: %c from device %d\n", msgType, deviceId);
            break;
    }
}

void broadcastMessage(const uint8_t* data, size_t length, uint8_t excludeId) {
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (clients[i] && clients[i].connected() && devices[i].id != excludeId) {
            clients[i].write(data, length);
        }
    }
}

void sendDeviceList(WiFiClient& client) {
    uint8_t buffer[256];
    size_t offset = 0;

    buffer[offset++] = 'L'; // List command
    buffer[offset++] = 0;   // Placeholder for count

    uint8_t count = 0;
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (devices[i].connected) {
            buffer[offset++] = devices[i].id;
            uint8_t nameLen = strlen(devices[i].name);
            buffer[offset++] = nameLen;
            memcpy(&buffer[offset], devices[i].name, nameLen);
            offset += nameLen;
            count++;
        }
    }

    buffer[1] = count; // Update count
    client.write(buffer, offset);
}

void cleanupDisconnectedDevices() {
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (clients[i] && !clients[i].connected()) {
            if (devices[i].connected) {
                Serial.printf("Device %d disconnected (%s)\n",
                            devices[i].id, devices[i].name);
                devices[i].connected = false;
            }
            clients[i].stop();
        } else if (devices[i].connected &&
                   millis() - devices[i].lastSeen > DEVICE_TIMEOUT) {
            Serial.printf("Device %d timed out (%s)\n",
                        devices[i].id, devices[i].name);
            devices[i].connected = false;
            clients[i].stop();
        }
    }
}

void printStatus() {
    Serial.println("\n=== Bridge Status ===");
    Serial.printf("Mode: %s\n", currentMode == MODE_AP ? "AP" : "Station");
    Serial.printf("State: %s\n", currentState == STATE_CONNECTED ? "Connected" : "Disconnected");

    if (currentMode == MODE_AP) {
        Serial.printf("AP IP: %s\n", WiFi.softAPIP().toString().c_str());
    } else {
        Serial.printf("STA IP: %s\n", WiFi.localIP().toString().c_str());
    }

    int connectedCount = 0;
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (devices[i].connected) connectedCount++;
    }
    Serial.printf("Connected devices: %d/%d\n", connectedCount, MAX_DEVICES);

    Serial.println("==================");
}