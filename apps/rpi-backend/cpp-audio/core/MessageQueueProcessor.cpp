#include "MessageQueueProcessor.h"
#include "FlatBuffersRequestReader.h"
#include "IResponseWriter.h"
#include "IJob.h"
#include "DownloadJob.h"
#include <filesystem>

MessageQueueProcessor::MessageQueueProcessor(const std::string& workingDir,
                                           const std::string& mqtt_host,
                                           int mqtt_port)
    : workingDir_(workingDir), next_session_id_(1), mqtt_enabled_(false) {}

MessageQueueProcessor::~MessageQueueProcessor() = default;

std::unique_ptr<IJob> MessageQueueProcessor::processMessage(std::unique_ptr<FlatBuffersRequestReader> reader, IResponseWriter* writer) {
    switch (reader->getType()) {
    case RequestType::Download: {
        std::string url = reader->getDownloadUrl();
        enqueueJob(url, writer);
        writer->write(DownloadResponse{next_session_id_ - 1});
        return nullptr; // Job already enqueued
    }
    case RequestType::Status: {
        uint32_t id = reader->getSessionId();
        std::lock_guard<std::mutex> lock(jobs_mutex_);
        auto it = jobs_.find(id);
        std::string status_str = it != jobs_.end() ? statusToString(it->second.status) : "Not found";
        writer->write(StatusResponse{id, status_str});
        return nullptr;
    }
    // Add others
    default:
        return nullptr;
    }
}

void MessageQueueProcessor::enqueueJob(const std::string& url, IResponseWriter* writer) {
    uint32_t sessionId = next_session_id_++;
    std::string filePath = workingDir_ + "/download_" + std::to_string(sessionId);

    std::lock_guard<std::mutex> lock(jobs_mutex_);
    jobs_[sessionId] = {sessionId, url, JobStatus::Queued, filePath};

    auto job = std::make_unique<DownloadJob>(std::shared_ptr<IResponseWriter>(writer, [](IResponseWriter*){}), url, sessionId, filePath);
    // In real impl, add to job_worker_
}

std::string MessageQueueProcessor::statusToString(JobStatus status) {
    switch (status) {
    case JobStatus::Queued: return "Queued";
    case JobStatus::Downloading: return "Downloading";
    case JobStatus::Completed: return "Completed";
    case JobStatus::Failed: return "Failed";
    case JobStatus::Aborted: return "Aborted";
    default: return "Unknown";
    }
}