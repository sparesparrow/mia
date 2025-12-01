#include "HardwareControlServer.h"

// Standard library includes (alphabetically)
#include <cstring>
#include <iostream>
#include <sstream>
#include <thread>
#include <chrono>
#include <unistd.h>
#include <mosquitto.h>
#include <json/json.h>

namespace WebGrab {

HardwareControlServer::HardwareControlServer(int port,
                                               const std::string& mqtt_host,
                                               int mqtt_port)
    : port(port), serverSocket(-1), running(false),
      mqtt_host(mqtt_host), mqtt_port(mqtt_port), mqtt_client(nullptr) {
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

    activeLines.clear();
    std::cout << "Hardware Control Server stopped" << std::endl;
}

bool HardwareControlServer::InitializeGPIO() {
    try {
        chip = std::make_unique<gpiod::chip>("gpiochip0");
        std::cout << "Hardware Control Server: GPIO chip initialized" << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Hardware Control Server: Failed to initialize GPIO chip: " << e.what() << std::endl;
        return false;
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

    try {
        // Release existing line if it exists
        if (activeLines.find(pin) != activeLines.end()) {
            activeLines.erase(pin);
        }

        // Get and configure the new line
        gpiod::line line = chip->get_line(pin);

        if (direction == "input") {
            gpiod::line_request request = {
                "hardware-control-server",
                gpiod::line_request::DIRECTION_INPUT,
                0
            };
            line.request(request);
        } else if (direction == "output") {
            gpiod::line_request request = {
                "hardware-control-server",
                gpiod::line_request::DIRECTION_OUTPUT,
                0
            };
            line.request(request);
        }

        // Store the configured line
        activeLines[pin] = std::move(line);
        return true;

    } catch (const std::exception& e) {
        std::cerr << "Failed to configure GPIO pin " << pin << ": " << e.what() << std::endl;
        return false;
    }
}

bool HardwareControlServer::SetGPIOPin(int pin, bool value) {
    auto it = activeLines.find(pin);
    if (it == activeLines.end()) return false;

    try {
        it->second.set_value(value ? 1 : 0);
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to set GPIO pin " << pin << ": " << e.what() << std::endl;
        return false;
    }
}

bool HardwareControlServer::GetGPIOPin(int pin, bool& value) {
    auto it = activeLines.find(pin);
    if (it == activeLines.end()) return false;

    try {
        int val = it->second.get_value();
        value = (val != 0);
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to get GPIO pin " << pin << ": " << e.what() << std::endl;
        return false;
    }
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
    auto* server = static_cast<HardwareControlServer*>(obj);
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
        for (const auto& [pin, line] : activeLines) {
            Json::Value pinInfo;
            pinInfo["pin"] = pin;
            try {
                bool value;
                if (GetGPIOPin(pin, value)) {
                    pinInfo["value"] = value ? 1 : 0;
                }
            } catch (...) {
                // Ignore errors
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