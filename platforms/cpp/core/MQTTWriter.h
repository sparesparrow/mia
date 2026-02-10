#pragma once

#include "IWriter.h"
#include "IResponseWriter.h"
#include <mosquitto.h>
#include <string>
#include <atomic>

namespace WebGrab {

class MQTTWriter : public IWriter, public IResponseWriter {
public:
    MQTTWriter(const std::string& host = "localhost", int port = 1883,
                const std::string& topic_prefix = "webgrab/");
    virtual ~MQTTWriter();

    // IWriter interface
    bool write(const void* buffer, size_t size) override;
    void close() override;

    // IResponseWriter interface
    bool write(const DownloadResponse& resp) override;
    bool write(const StatusResponse& resp) override;
    bool write(const ErrorResponse& resp) override;
    bool flush() override;

private:
    // MQTT connection
    struct mosquitto* mqtt_client_;
    std::string host_;
    int port_;
    std::string topic_prefix_;
    std::atomic<bool> connected_;

    // Helper methods
    bool initialize_mqtt();
    bool publish_message(const std::string& topic, const std::string& payload, int qos = 0, bool retain = false);

    // Response topic generation
    std::string get_response_topic(const std::string& response_type) const;
};

} // namespace WebGrab