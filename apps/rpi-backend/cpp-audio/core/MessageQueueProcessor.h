#pragma once
#include <memory>
#include <string>
#include <unordered_map>
#include <mutex>
#include <atomic>
#include <thread>

#include "IRequestReader.h"
#include "IResponseWriter.h"
#include "FlatBuffersRequestReader.h"
#include "MQTTReader.h"
#include "MQTTWriter.h"

enum class JobStatus { Queued, Downloading, Completed, Failed, Aborted };

struct JobInfo {
    uint32_t sessionId;
    std::string url;
    JobStatus status;
    std::string filePath;
};

class MessageQueueProcessor : public IRequestReader, public IResponseWriter {
public:
    MessageQueueProcessor(const std::string& workingDir,
                         const std::string& mqtt_host = "localhost",
                         int mqtt_port = 1883);
    ~MessageQueueProcessor();

    // IRequestReader interface
    bool next(RequestEnvelope& out) override;
    bool good() const override;
    void close() override;

    // IResponseWriter interface
    bool write(const DownloadResponse& resp) override;
    bool write(const StatusResponse& resp) override;
    bool write(const ErrorResponse& resp) override;
    bool flush() override;

    // Legacy method for backward compatibility
    std::unique_ptr<class IJob> processMessage(std::unique_ptr<FlatBuffersRequestReader> reader, IResponseWriter* writer);

    // MQTT integration methods
    void enableMQTT(bool enable = true);
    bool isMQTTEnabled() const { return mqtt_enabled_; }

private:
    std::string workingDir_;
    std::unordered_map<uint32_t, JobInfo> jobs_;
    std::mutex jobs_mutex_;
    uint32_t next_session_id_;

    // MQTT integration
    bool mqtt_enabled_;
    std::unique_ptr<WebGrab::MQTTReader> mqtt_reader_;
    std::unique_ptr<WebGrab::MQTTWriter> mqtt_writer_;
    std::thread mqtt_processor_thread_;
    std::atomic<bool> running_;

    void enqueueJob(const std::string& url, IResponseWriter* writer);
    void processMQTTMessages();
    std::string statusToString(JobStatus status);

    // GPIO control methods (for hybrid functionality)
    bool handleGPIORequest(const std::string& request_json, std::string& response_json);
};