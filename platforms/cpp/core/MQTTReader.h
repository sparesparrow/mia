#pragma once

#include "IReader.h"
#include "IRequestReader.h"
#include "IResponseReader.h"
#include <mosquitto.h>
#include <string>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <atomic>

namespace WebGrab {

class MQTTReader : public IReader, public IRequestReader, public IResponseReader {
public:
    MQTTReader(const std::string& host = "localhost", int port = 1883,
                const std::string& topic_prefix = "webgrab/");
    virtual ~MQTTReader();

    // IReader interface
    bool read(void* buffer, size_t size) override;
    void close() override;

    // IRequestReader interface
    bool next(RequestEnvelope& out) override;
    bool good() const override;

    // IResponseReader interface
    bool recv(DownloadResponse& out) override;
    bool recv(StatusResponse& out) override;
    bool recv(ErrorResponse& out) override;
    bool tryRecv(DownloadResponse& out, std::chrono::milliseconds timeout) override;
    bool tryRecv(StatusResponse& out, std::chrono::milliseconds timeout) override;
    bool tryRecv(ErrorResponse& out, std::chrono::milliseconds timeout) override;

private:
    // MQTT connection
    struct mosquitto* mqtt_client_;
    std::string host_;
    int port_;
    std::string topic_prefix_;
    std::atomic<bool> connected_;
    std::thread mqtt_thread_;

    // Message queues
    std::queue<std::string> message_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;

    // MQTT callbacks
    static void on_connect(struct mosquitto* mosq, void* obj, int rc);
    static void on_message(struct mosquitto* mosq, void* obj,
                          const struct mosquitto_message* msg);
    void handle_message(const std::string& topic, const std::string& payload);

    // Helper methods
    bool initialize_mqtt();
    void mqtt_loop();
    bool wait_for_message(std::string& message, std::chrono::milliseconds timeout);
    RequestType parse_request_type(const std::string& json_payload);
};

} // namespace WebGrab