#pragma once
#include "IJob.h"
#include <memory>
#include <string>

class IResponseWriter;
class CurlClient;

class DownloadJob : public IJob {
private:
    std::shared_ptr<IResponseWriter> response_writer_;
    std::string url_;
    uint32_t session_id_;
    std::string output_path_;
    std::unique_ptr<CurlClient> curl_client_;

public:
    DownloadJob(std::shared_ptr<IResponseWriter> writer, const std::string& url, uint32_t sessionId, const std::string& outputPath);
    ~DownloadJob() override;

    void execute() override;
};