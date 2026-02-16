#pragma once

#include <mosquitto.h>
#include <string>
#include <functional>
#include <memory>
#include <unordered_map>
#include <mutex>
#include <atomic>

namespace WebGrab {

/**
 * @brief MQTT Bridge for encapsulating MQTT communication
 *
 * Provides a high-level interface for MQTT pub/sub operations
 * while maintaining compatibility with existing interfaces.
 */
class MQTTBridge {
public:
    using MessageCallback = std::function<void(const std::string& topic, const std::string& payload)>;

    MQTTBridge(const std::string& host = "localhost", int port = 1883,
                const std::string& client_id = "");
    ~MQTTBridge();

    // Connection management
    bool connect();
    void disconnect();
    bool isConnected() const { return connected_; }

    // Publishing
    bool publish(const std::string& topic, const std::string& payload,
                 int qos = 0, bool retain = false);

    // Subscribing
    bool subscribe(const std::string& topic, int qos = 0);
    bool unsubscribe(const std::string& topic);

    // Message handling
    void setMessageCallback(MessageCallback callback) { message_callback_ = callback; }

    // Utility methods
    std::string getClientId() const { return client_id_; }
    void setLastWill(const std::string& topic, const std::string& payload, int qos = 0, bool retain = false);

private:
    struct mosquitto* mosq_;
    std::string host_;
    int port_;
    std::string client_id_;
    std::atomic<bool> connected_;

    MessageCallback message_callback_;
    std::mutex callback_mutex_;

    // MQTT callbacks
    static void on_connect(struct mosquitto* mosq, void* obj, int rc);
    static void on_disconnect(struct mosquitto* mosq, void* obj, int rc);
    static void on_message(struct mosquitto* mosq, void* obj, const struct mosquitto_message* msg);
    static void on_publish(struct mosquitto* mosq, void* obj, int mid);

    void handle_connect(int rc);
    void handle_disconnect(int rc);
    void handle_message(const struct mosquitto_message* msg);
};

} // namespace WebGrab