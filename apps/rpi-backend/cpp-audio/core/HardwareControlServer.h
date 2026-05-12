#pragma once

// Use the libgpiod C line API shipped on Raspberry Pi OS Bookworm.
#include <gpiod.h>
#include <json/json.h>
#include <mosquitto.h>

// Standard library includes
#include <atomic>
#include <memory>
#include <netinet/in.h>
#include <string>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <mutex>

namespace WebGrab {

/**
 * @brief GPIO Line Info for tracking configured pins
 */
struct GPIOLineInfo {
    struct gpiod_line* line;
    unsigned int offset;
    bool is_output;

    GPIOLineInfo() : line(nullptr), offset(0), is_output(false) {}
};

/**
 * @brief Hardware Control Server for GPIO operations
 *
 * This server provides GPIO control capabilities for Raspberry Pi
 * via hybrid TCP + MQTT communication using the libgpiod 2.x line API.
 */
class HardwareControlServer {
public:
    explicit HardwareControlServer(int port = 8081,
                                   const std::string& mqtt_host = "localhost",
                                   int mqtt_port = 1883);
    ~HardwareControlServer();

    HardwareControlServer(const HardwareControlServer&) = delete;
    HardwareControlServer& operator=(const HardwareControlServer&) = delete;
    HardwareControlServer(HardwareControlServer&&) = delete;
    HardwareControlServer& operator=(HardwareControlServer&&) = delete;

    bool Start();
    void Stop();

private:
    // Server configuration
    int port;
    int serverSocket;
    std::atomic<bool> running;
    std::thread acceptThread;

    // MQTT configuration
    std::string mqtt_host;
    int mqtt_port;
    struct mosquitto* mqtt_client;
    bool mqttLibraryInitialized;
    std::thread mqttThread;
    std::mutex mqttMutex;

    // GPIO management using C API
    struct gpiod_chip* chip;
    std::unordered_map<int, GPIOLineInfo> activeLines;
    std::mutex gpioMutex;

    // Server methods
    bool InitializeGPIO();
    void CleanupGPIO();
    void CleanupMQTT();
    bool SetupServerSocket();
    void CloseServerSocket();
    void ShutdownClientConnections();
    bool InitializeMQTT();
    void AcceptConnections();
    void HandleClient(int clientSocket);
    void MQTTLoop();

    std::vector<std::thread> clientThreads;
    std::unordered_set<int> clientSockets;
    std::mutex clientMutex;

    // MQTT callbacks
    static void on_mqtt_connect(struct mosquitto* mosq, void* obj, int rc);
    static void on_mqtt_message(struct mosquitto* mosq, void* obj,
                               const struct mosquitto_message* msg);
    void HandleMQTTMessage(const std::string& topic, const std::string& payload);

    // Hardware control methods
    std::string HandleGPIOControl(const std::string& jsonRequest);
    bool SetGPIOPin(int pin, bool value);
    bool GetGPIOPin(int pin, bool& value);
    bool ConfigureGPIOPin(int pin, const std::string& direction);
};

} // namespace WebGrab