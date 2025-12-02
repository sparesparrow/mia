#include "HardwareControlServer.h"

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
      chip(nullptr) {
}

HardwareControlServer::~HardwareControlServer() {
    Stop();
}

bool HardwareControlServer::Start() {
    if (!InitializeGPIO()) {
        std::cerr << "Failed to initialize GPIO" << std::endl;
        return false;
    }

    if (!SetupServerSocket()) {
        std::cerr << "Failed to setup server socket" << std::endl;
        return false;
    }

    if (!InitializeMQTT()) {
        std::cerr << "Failed to initialize MQTT (continuing without MQTT)" << std::endl;
        // Continue without MQTT - it's optional
    }

    running = true;
    acceptThread = std::thread(&HardwareControlServer::AcceptConnections, this);

    std::cout << "Hardware Control Server started on port " << port << std::endl;
    return true;
}

void HardwareControlServer::Stop() {
    running = false;

    if (acceptThread.joinable()) {
        acceptThread.join();
    }

    if (serverSocket != -1) {
        close(serverSocket);
        serverSocket = -1;
    }

    // Clean up MQTT
    if (mqtt_client) {
        mosquitto_disconnect(mqtt_client);
        mosquitto_destroy(mqtt_client);
        mqtt_client = nullptr;
    }

    if (mqttThread.joinable()) {
        mqttThread.join();
    }

    CleanupGPIO();
    std::cout << "Hardware Control Server stopped" << std::endl;
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
    
    // Release all line requests
    for (auto& [pin, info] : activeLines) {
        if (info.request) {
            gpiod_line_request_release(info.request);
            info.request = nullptr;
        }
    }
    activeLines.clear();

    // Close the chip
    if (chip) {
        gpiod_chip_close(chip);
        chip = nullptr;
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
        return false;
    }

    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(port);

    if (bind(serverSocket, reinterpret_cast<sockaddr*>(&serverAddr), sizeof(serverAddr)) == -1) {
        std::cerr << "Failed to bind socket" << std::endl;
        return false;
    }

    if (listen(serverSocket, 5) == -1) {
        std::cerr << "Failed to listen on socket" << std::endl;
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
        std::thread(&HardwareControlServer::HandleClient, this, clientSocket).detach();
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

        send(clientSocket, response.c_str(), response.length(), 0);
    }

    close(clientSocket);
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
            if (it->second.request) {
                gpiod_line_request_release(it->second.request);
            }
            activeLines.erase(it);
        }

        // Create line settings
        struct gpiod_line_settings* settings = gpiod_line_settings_new();
        if (!settings) {
            std::cerr << "Failed to create line settings" << std::endl;
            return false;
        }

        // Set direction
        bool is_output = (direction == "output");
        if (is_output) {
            gpiod_line_settings_set_direction(settings, GPIOD_LINE_DIRECTION_OUTPUT);
            gpiod_line_settings_set_output_value(settings, GPIOD_LINE_VALUE_INACTIVE);
        } else {
            gpiod_line_settings_set_direction(settings, GPIOD_LINE_DIRECTION_INPUT);
        }

        // Create line config
        struct gpiod_line_config* line_config = gpiod_line_config_new();
        if (!line_config) {
            gpiod_line_settings_free(settings);
            std::cerr << "Failed to create line config" << std::endl;
            return false;
        }

        // Add the line offset to config
        unsigned int offset = static_cast<unsigned int>(pin);
        int ret = gpiod_line_config_add_line_settings(line_config, &offset, 1, settings);
        gpiod_line_settings_free(settings);

        if (ret < 0) {
            gpiod_line_config_free(line_config);
            std::cerr << "Failed to add line settings to config" << std::endl;
            return false;
        }

        // Create request config with consumer name
        struct gpiod_request_config* req_config = gpiod_request_config_new();
        if (!req_config) {
            gpiod_line_config_free(line_config);
            std::cerr << "Failed to create request config" << std::endl;
            return false;
        }
        gpiod_request_config_set_consumer(req_config, "hardware-control-server");

        // Request the line
        struct gpiod_line_request* request = gpiod_chip_request_lines(chip, req_config, line_config);
        
        gpiod_request_config_free(req_config);
        gpiod_line_config_free(line_config);

        if (!request) {
            std::cerr << "Failed to request GPIO line " << pin << std::endl;
            return false;
        }

        // Store the configured line
        GPIOLineInfo info;
        info.request = request;
        info.offset = offset;
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
    if (it == activeLines.end() || !it->second.request) {
        std::cerr << "GPIO pin " << pin << " not configured" << std::endl;
        return false;
    }

    if (!it->second.is_output) {
        std::cerr << "GPIO pin " << pin << " is not configured as output" << std::endl;
        return false;
    }

    enum gpiod_line_value val = value ? GPIOD_LINE_VALUE_ACTIVE : GPIOD_LINE_VALUE_INACTIVE;
    int ret = gpiod_line_request_set_value(it->second.request, it->second.offset, val);
    
    if (ret < 0) {
        std::cerr << "Failed to set GPIO pin " << pin << std::endl;
        return false;
    }

    return true;
}

bool HardwareControlServer::GetGPIOPin(int pin, bool& value) {
    std::lock_guard<std::mutex> lock(gpioMutex);

    auto it = activeLines.find(pin);
    if (it == activeLines.end() || !it->second.request) {
        std::cerr << "GPIO pin " << pin << " not configured" << std::endl;
        return false;
    }

    enum gpiod_line_value val = gpiod_line_request_get_value(it->second.request, it->second.offset);
    
    if (val == GPIOD_LINE_VALUE_ERROR) {
        std::cerr << "Failed to get GPIO pin " << pin << std::endl;
        return false;
    }

    value = (val == GPIOD_LINE_VALUE_ACTIVE);
    return true;
}

bool HardwareControlServer::InitializeMQTT() {
    mosquitto_lib_init();
    
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
    mosquitto_subscribe(mqtt_client, nullptr, "hardware/gpio/control", 0);
    mosquitto_subscribe(mqtt_client, nullptr, "hardware/gpio/status", 0);

    // Start MQTT loop thread
    mqttThread = std::thread(&HardwareControlServer::MQTTLoop, this);

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
        status["active_pins"] = static_cast<int>(activeLines.size());
        
        Json::Value pins(Json::arrayValue);
        for (const auto& [pin, info] : activeLines) {
            Json::Value pinInfo;
            pinInfo["pin"] = pin;
            pinInfo["is_output"] = info.is_output;
            
            bool value;
            // Temporarily unlock for GetGPIOPin (it will lock again)
            // Actually, since we're in HandleMQTTMessage which already holds mqttMutex,
            // and GetGPIOPin holds gpioMutex, this is safe
            if (info.request) {
                enum gpiod_line_value val = gpiod_line_request_get_value(info.request, info.offset);
                if (val != GPIOD_LINE_VALUE_ERROR) {
                    pinInfo["value"] = (val == GPIOD_LINE_VALUE_ACTIVE) ? 1 : 0;
                }
            }
            pins.append(pinInfo);
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
