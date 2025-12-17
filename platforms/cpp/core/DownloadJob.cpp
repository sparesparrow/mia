#include "DownloadJob.h"
#include "IResponseWriter.h"
#include "CurlClientWrapper.h"
#include <iostream>

DownloadJob::DownloadJob(std::shared_ptr<IResponseWriter> writer, const std::string& url, uint32_t sessionId, const std::string& outputPath)
    : response_writer_(writer), url_(url), session_id_(sessionId), output_path_(outputPath),
      curl_client_(std::make_unique<CurlClient>()) {
    curl_client_->init(nullptr, nullptr, false);
}

DownloadJob::~DownloadJob() = default;

void DownloadJob::execute() {
    std::vector<std::string> headers;
    CURLcode res = curl_client_->getFile(url_.c_str(), output_path_.c_str(), headers, true);
    if (res == CURLE_OK) {
        response_writer_->write(StatusResponse{session_id_, "Completed"});
    } else {
        response_writer_->write(StatusResponse{session_id_, "Failed"});
    }
}