#include "HardwareControlServer.h"

#include <gpiod.h>
#include <cstring>
#include <iostream>
#include <sstream>
#include <thread>
#include <chrono>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>

namespace WebGrab {

HardwareControlServer::HardwareControlServer(int port,
                                             const std::string& mqtt_host,
                                             int mqtt_port)
    : port(port), serverSocket(-1), running(false),
    mqtt_host(mqtt_host), mqtt_port(mqtt_port), mqtt_client(nullptr),
    mqttLibraryInitialized(false),
      chip(nullptr) {
}

HardwareControlServer::~HardwareControlServer() {
    Stop();
}

bool HardwareControlServer::Start() {
    if (running.load()) {
        std::cerr << "Hardware Control Server is already running" << std::endl;
        return false;
    }

    if (!InitializeGPIO()) {
        std::cerr << "Failed to initialize GPIO" << std::endl;
        return false;
    }

    if (!SetupServerSocket()) {
        std::cerr << "Failed to setup server socket" << std::endl;
        CleanupGPIO();
        return false;
    }

    running = true;

    if (!InitializeMQTT()) {
        std::cerr << "Failed to initialize MQTT (continuing without MQTT)" << std::endl;
        // Continue without MQTT - it's optional
    }

    try {
        acceptThread = std::thread(&HardwareControlServer::AcceptConnections, this);
    } catch (const std::exception& e) {
        std::cerr << "Failed to start accept thread: " << e.what() << std::endl;
        Stop();
        return false;
    }

    std::cout << "Hardware Control Server started on port " << port << std::endl;
    return true;
}

void HardwareControlServer::Stop() {
    const bool wasRunning = running.exchange(false);

    CloseServerSocket();

    if (acceptThread.joinable()) {
        acceptThread.join();
    }

    ShutdownClientConnections();

    for (auto& clientThread : clientThreads) {
        if (clientThread.joinable()) {
            clientThread.join();
        }
    }
    clientThreads.clear();

    CleanupMQTT();
    CleanupGPIO();

    if (wasRunning) {
        std::cout << "Hardware Control Server stopped" << std::endl;
    }
}

bool HardwareControlServer::InitializeGPIO() {
    // Try common chip paths
    const char* chip_paths[] = {
        "/dev/gpiochip0",
        "/dev/gpiochip4",  // Raspberry Pi 5 uses gpiochip4
        nullptr
    };

    for (int i = 0; chip_paths[i] != nullptr; i++) {
        chip = gpiod_chip_open(chip_paths[i]);
        if (chip) {
            std::cout << "GPIO chip opened: " << chip_paths[i] << std::endl;
            return true;
        }
    }

    std::cerr << "Failed to open any GPIO chip" << std::endl;
    return false;
}

void HardwareControlServer::CleanupGPIO() {
    std::lock_guard<std::mutex> lock(gpioMutex);
    
    // Release all requested lines.
    for (auto& [pin, info] : activeLines) {
        if (info.line) {
            gpiod_line_release(info.line);
            info.line = nullptr;
        }
    }
    activeLines.clear();

    // Close the chip
    if (chip) {
        gpiod_chip_close(chip);
        chip = nullptr;
    }
}

void HardwareControlServer::CleanupMQTT() {
    if (mqtt_client) {
        mosquitto_disconnect(mqtt_client);
    }

    if (mqttThread.joinable()) {
        mqttThread.join();
    }

    if (mqtt_client) {
        mosquitto_destroy(mqtt_client);
        mqtt_client = nullptr;
    }

    if (mqttLibraryInitialized) {
        mosquitto_lib_cleanup();
        mqttLibraryInitialized = false;
    }
}

void HardwareControlServer::CloseServerSocket() {
    if (serverSocket == -1) {
        return;
    }

    shutdown(serverSocket, SHUT_RDWR);
    close(serverSocket);
    serverSocket = -1;
}

void HardwareControlServer::ShutdownClientConnections() {
    std::lock_guard<std::mutex> lock(clientMutex);

    for (int clientSocket : clientSockets) {
        shutdown(clientSocket, SHUT_RDWR);
    }
}

bool HardwareControlServer::SetupServerSocket() {
    serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (serverSocket == -1) {
        std::cerr << "Failed to create socket" << std::endl;
        return false;
    }

    int opt = 1;
    if (setsockopt(serverSocket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) == -1) {
        std::cerr << "Failed to set socket options" << std::endl;
        CloseServerSocket();
        return false;
    }

    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(port);

    if (bind(serverSocket, reinterpret_cast<sockaddr*>(&serverAddr), sizeof(serverAddr)) == -1) {
        std::cerr << "Failed to bind socket" << std::endl;
        CloseServerSocket();
        return false;
    }

    if (listen(serverSocket, 5) == -1) {
        std::cerr << "Failed to listen on socket" << std::endl;
        CloseServerSocket();
        return false;
    }

    return true;
}

void HardwareControlServer::AcceptConnections() {
    while (running) {
        sockaddr_in clientAddr{};
        socklen_t clientAddrLen = sizeof(clientAddr);

        int clientSocket = accept(serverSocket, reinterpret_cast<sockaddr*>(&clientAddr), &clientAddrLen);
        if (clientSocket == -1) {
            if (running) {
                std::cerr << "Failed to accept connection" << std::endl;
            }
            continue;
        }

        std::cout << "Client connected" << std::endl;

        {
            std::lock_guard<std::mutex> lock(clientMutex);
            clientSockets.insert(clientSocket);
        }

        try {
            clientThreads.emplace_back(&HardwareControlServer::HandleClient, this, clientSocket);
        } catch (const std::exception& e) {
            {
                std::lock_guard<std::mutex> lock(clientMutex);
                clientSockets.erase(clientSocket);
            }
            close(clientSocket);
            std::cerr << "Failed to start client thread: " << e.what() << std::endl;
        }
    }
}

void HardwareControlServer::HandleClient(int clientSocket) {
    char buffer[4096];

    while (running) {
        ssize_t bytesRead = recv(clientSocket, buffer, sizeof(buffer) - 1, 0);
        if (bytesRead <= 0) {
            break;
        }

        buffer[bytesRead] = '\0';
        std::string request(buffer);
        std::string response = HandleGPIOControl(request);

        if (send(clientSocket, response.c_str(), response.length(), MSG_NOSIGNAL) < 0) {
            break;
        }
    }

    shutdown(clientSocket, SHUT_RDWR);
    close(clientSocket);

    {
        std::lock_guard<std::mutex> lock(clientMutex);
        clientSockets.erase(clientSocket);
    }

    std::cout << "Client disconnected" << std::endl;
}

std::string HardwareControlServer::HandleGPIOControl(const std::string& jsonRequest) {
    Json::Value params;
    Json::Value response;
    Json::Reader reader;

    try {
        if (!reader.parse(jsonRequest, params)) {
            response["success"] = false;
            response["error"] = "Invalid JSON request";
            return Json::FastWriter().write(response);
        }

        // Extract parameters
        int pin = params.get("pin", -1).asInt();
        std::string direction = params.get("direction", "").asString();
        int value = params.get("value", -1).asInt();

        // Validate pin
        if (pin < 0 || pin > 40) {
            response["success"] = false;
            response["error"] = "Invalid pin number. Must be between 0 and 40.";
            return Json::FastWriter().write(response);
        }

        // Handle direction configuration
        if (!direction.empty()) {
            if (direction == "input" || direction == "output") {
                if (ConfigureGPIOPin(pin, direction)) {
                    response["success"] = true;
                    response["message"] = "GPIO pin " + std::to_string(pin) + " configured as " + direction;

                    // If output and value provided, set the value
                    if (direction == "output" && value >= 0) {
                        if (SetGPIOPin(pin, value != 0)) {
                            std::string currentMessage = response.get("message", "").asString();
                            response["message"] = currentMessage + " and set to " + std::to_string(value);
                        } else {
                            response["success"] = false;
                            response["error"] = "Failed to set GPIO pin value";
                        }
                    }
                    // If input, read the current value
                    else if (direction == "input") {
                        bool currentValue;
                        if (GetGPIOPin(pin, currentValue)) {
                            response["value"] = currentValue ? 1 : 0;
                        } else {
                            response["success"] = false;
                            response["error"] = "Failed to read GPIO pin value";
                        }
                    }
                } else {
                    response["success"] = false;
                    response["error"] = "Failed to configure GPIO pin";
                }
            } else {
                response["success"] = false;
                response["error"] = "Invalid direction. Must be 'input' or 'output'.";
            }
        }
        // Handle value setting without direction change
        else if (value >= 0) {
            if (SetGPIOPin(pin, value != 0)) {
                response["success"] = true;
                response["message"] = "GPIO pin " + std::to_string(pin) + " set to " + std::to_string(value);
            } else {
                response["success"] = false;
                response["error"] = "Failed to set GPIO pin value. Pin may not be configured as output.";
            }
        }
        // Handle value reading
        else {
            bool currentValue;
            if (GetGPIOPin(pin, currentValue)) {
                response["success"] = true;
                response["value"] = currentValue ? 1 : 0;
                response["message"] = "GPIO pin " + std::to_string(pin) + " value read successfully";
            } else {
                response["success"] = false;
                response["error"] = "Failed to read GPIO pin value. Pin may not be configured as input.";
            }
        }

        return Json::FastWriter().write(response);

    } catch (const std::exception& e) {
        response["success"] = false;
        response["error"] = "GPIO control failed";
        response["details"] = e.what();
        return Json::FastWriter().write(response);
    }
}

bool HardwareControlServer::ConfigureGPIOPin(int pin, const std::string& direction) {
    if (!chip) return false;

    std::lock_guard<std::mutex> lock(gpioMutex);

    try {
        // Release existing line request if it exists
        auto it = activeLines.find(pin);
        if (it != activeLines.end()) {
            if (it->second.line) {
                gpiod_line_release(it->second.line);
            }
            activeLines.erase(it);
        }

        struct gpiod_line* line = gpiod_chip_get_line(chip, static_cast<unsigned int>(pin));
        if (!line) {
            std::cerr << "Failed to get GPIO line " << pin << std::endl;
            return false;
        }

        bool is_output = (direction == "output");
        int ret = is_output
            ? gpiod_line_request_output(line, "hardware-control-server", 0)
            : gpiod_line_request_input(line, "hardware-control-server");

        if (ret < 0) {
            std::cerr << "Failed to request GPIO line " << pin << std::endl;
            return false;
        }

        GPIOLineInfo info;
        info.line = line;
        info.offset = static_cast<unsigned int>(pin);
        info.is_output = is_output;
        activeLines[pin] = info;

        std::cout << "GPIO pin " << pin << " configured as " << direction << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cerr << "Failed to configure GPIO pin " << pin << ": " << e.what() << std::endl;
        return false;
    }
}

bool HardwareControlServer::SetGPIOPin(int pin, bool value) {
    std::lock_guard<std::mutex> lock(gpioMutex);

    auto it = activeLines.find(pin);
    if (it == activeLines.end() || !it->second.line) {
        std::cerr << "GPIO pin " << pin << " not configured" << std::endl;
        return false;
    }

    if (!it->second.is_output) {
        std::cerr << "GPIO pin " << pin << " is not configured as output" << std::endl;
        return false;
    }

    int ret = gpiod_line_set_value(it->second.line, value ? 1 : 0);
    
    if (ret < 0) {
        std::cerr << "Failed to set GPIO pin " << pin << std::endl;
        return false;
    }

    return true;
}

bool HardwareControlServer::GetGPIOPin(int pin, bool& value) {
    std::lock_guard<std::mutex> lock(gpioMutex);

    auto it = activeLines.find(pin);
    if (it == activeLines.end() || !it->second.line) {
        std::cerr << "GPIO pin " << pin << " not configured" << std::endl;
        return false;
    }

    int ret = gpiod_line_get_value(it->second.line);
    
    if (ret < 0) {
        std::cerr << "Failed to get GPIO pin " << pin << std::endl;
        return false;
    }

    value = (ret != 0);
    return true;
}

bool HardwareControlServer::InitializeMQTT() {
    if (!mqttLibraryInitialized) {
        const int initResult = mosquitto_lib_init();
        if (initResult != MOSQ_ERR_SUCCESS) {
            std::cerr << "Failed to initialize MQTT library: "
                      << mosquitto_strerror(initResult) << std::endl;
            return false;
        }

        mqttLibraryInitialized = true;
    }
    
    mqtt_client = mosquitto_new("hardware-control-server", true, this);
    if (!mqtt_client) {
        std::cerr << "Failed to create MQTT client" << std::endl;
        return false;
    }

    mosquitto_connect_callback_set(mqtt_client, on_mqtt_connect);
    mosquitto_message_callback_set(mqtt_client, on_mqtt_message);

    int rc = mosquitto_connect(mqtt_client, mqtt_host.c_str(), mqtt_port, 60);
    if (rc != MOSQ_ERR_SUCCESS) {
        std::cerr << "Failed to connect to MQTT broker: " << mosquitto_strerror(rc) << std::endl;
        mosquitto_destroy(mqtt_client);
        mqtt_client = nullptr;
        return false;
    }

    // Subscribe to GPIO control topics
    int subscribeRc = mosquitto_subscribe(mqtt_client, nullptr, "hardware/gpio/control", 0);
    if (subscribeRc != MOSQ_ERR_SUCCESS) {
        std::cerr << "Failed to subscribe to hardware/gpio/control: "
                  << mosquitto_strerror(subscribeRc) << std::endl;
    }

    subscribeRc = mosquitto_subscribe(mqtt_client, nullptr, "hardware/gpio/status", 0);
    if (subscribeRc != MOSQ_ERR_SUCCESS) {
        std::cerr << "Failed to subscribe to hardware/gpio/status: "
                  << mosquitto_strerror(subscribeRc) << std::endl;
    }

    // Start MQTT loop thread
    try {
        mqttThread = std::thread(&HardwareControlServer::MQTTLoop, this);
    } catch (const std::exception& e) {
        std::cerr << "Failed to start MQTT thread: " << e.what() << std::endl;
        mosquitto_destroy(mqtt_client);
        mqtt_client = nullptr;
        return false;
    }

    std::cout << "MQTT initialized and connected to " << mqtt_host << ":" << mqtt_port << std::endl;
    return true;
}

void HardwareControlServer::MQTTLoop() {
    while (running && mqtt_client) {
        int rc = mosquitto_loop(mqtt_client, 100, 1);
        if (rc != MOSQ_ERR_SUCCESS) {
            if (running) {
                std::cerr << "MQTT loop error: " << mosquitto_strerror(rc) << std::endl;
                // Try to reconnect
                mosquitto_reconnect(mqtt_client);
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

void HardwareControlServer::on_mqtt_connect(struct mosquitto* mosq, void* obj, int rc) {
    if (rc == 0) {
        std::cout << "MQTT connected successfully" << std::endl;
    } else {
        std::cerr << "MQTT connection failed: " << mosquitto_connack_string(rc) << std::endl;
    }
}

void HardwareControlServer::on_mqtt_message(struct mosquitto* mosq, void* obj,
                                           const struct mosquitto_message* msg) {
    auto* server = static_cast<HardwareControlServer*>(obj);
    if (!server || !msg || !msg->payload) {
        return;
    }

    std::string topic(msg->topic);
    std::string payload(static_cast<const char*>(msg->payload), msg->payloadlen);

    server->HandleMQTTMessage(topic, payload);
}

void HardwareControlServer::HandleMQTTMessage(const std::string& topic, const std::string& payload) {
    std::lock_guard<std::mutex> lock(mqttMutex);

    if (topic == "hardware/gpio/control") {
        // Handle GPIO control via MQTT
        std::string response = HandleGPIOControl(payload);
        
        // Publish response
        if (mqtt_client) {
            mosquitto_publish(mqtt_client, nullptr, "hardware/gpio/response", 
                           response.length(), response.c_str(), 0, false);
        }
    } else if (topic == "hardware/gpio/status") {
        // Handle status request
        Json::Value status;
        Json::Value pins(Json::arrayValue);

        {
            std::lock_guard<std::mutex> gpioLock(gpioMutex);
            status["active_pins"] = static_cast<int>(activeLines.size());

            for (const auto& [pin, info] : activeLines) {
                Json::Value pinInfo;
                pinInfo["pin"] = pin;
                pinInfo["is_output"] = info.is_output;

                if (info.line) {
                    int value = gpiod_line_get_value(info.line);
                    if (value >= 0) {
                        pinInfo["value"] = value;
                    }
                }

                pins.append(pinInfo);
            }
        }

        status["pins"] = pins;
        
        Json::StreamWriterBuilder builder;
        std::string statusJson = Json::writeString(builder, status);
        
        if (mqtt_client) {
            mosquitto_publish(mqtt_client, nullptr, "hardware/gpio/status_response",
                           statusJson.length(), statusJson.c_str(), 0, false);
        }
    }
}

} // namespace WebGrab
