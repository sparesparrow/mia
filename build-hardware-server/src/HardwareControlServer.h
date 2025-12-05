#pragma once

// Use libgpiod C API for compatibility with both 1.x and 2.x
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
#include <mutex>

namespace WebGrab {

/**
 * @brief GPIO Line Info for tracking configured pins
 */
struct GPIOLineInfo {
    struct gpiod_line_request* request;
    unsigned int offset;
    bool is_output;
    
    GPIOLineInfo() : request(nullptr), offset(0), is_output(false) {}
};

/**
 * @brief Hardware Control Server for GPIO operations
 *
 * This server provides GPIO control capabilities for Raspberry Pi
 * via hybrid TCP + MQTT communication. Uses libgpiod C API for
 * maximum compatibility across different libgpiod versions.
 */
class HardwareControlServer {
public:
    explicit HardwareControlServer(int port = 8081,
                                   const std::string& mqtt_host = "localhost",
                                   int mqtt_port = 1883);
    ~HardwareControlServer();

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
    std::thread mqttThread;
    std::mutex mqttMutex;

    // GPIO management using C API
    struct gpiod_chip* chip;
    std::unordered_map<int, GPIOLineInfo> activeLines;
    std::mutex gpioMutex;

    // Server methods
    bool InitializeGPIO();
    void CleanupGPIO();
    bool SetupServerSocket();
    bool InitializeMQTT();
    void AcceptConnections();
    void HandleClient(int clientSocket);
    void MQTTLoop();

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