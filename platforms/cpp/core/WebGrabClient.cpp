#include "WebGrabClient.h"
#include "FlatBuffersRequestWriter.h"
#include "FlatBuffersResponseReader.h"
#include "TcpSocket.h"
#include <iostream>

WebGrabClient::WebGrabClient(const std::string& host, uint16_t port)
    : socket_(std::make_shared<TcpSocket>(host, port)) {}

WebGrabClient::~WebGrabClient() = default;

bool WebGrabClient::connect() {
    if (!socket_->connect()) return false;
    writer_ = std::make_unique<FlatBuffersRequestWriter>(socket_);
    reader_ = std::make_unique<FlatBuffersResponseReader>(socket_);
    return true;
}

bool WebGrabClient::executeDownload(const std::string& url, uint32_t& sessionId) {
    DownloadRequest req{url};
    if (!writer_->send(req)) return false;
    DownloadResponse resp;
    if (reader_->recv(resp)) {
        sessionId = resp.sessionId;
        std::cout << "Download started, session ID: " << resp.sessionId << std::endl;
        return true;
    }
    return false;
}

bool WebGrabClient::executeStatus(uint32_t sessionId, std::string& status) {
    DownloadStatusRequest req{sessionId};
    if (!writer_->send(req)) return false;
    StatusResponse resp;
    if (reader_->recv(resp)) {
        status = resp.status;
        std::cout << "Status for " << sessionId << ": " << resp.status << std::endl;
        return true;
    }
    return false;
}

bool WebGrabClient::executeAbort(uint32_t sessionId) {
    DownloadAbortRequest req{sessionId};
    if (!writer_->send(req)) return false;
    // Assume success, no specific response
    std::cout << "Abort request sent for session ID: " << sessionId << std::endl;
    return true;
}

bool WebGrabClient::executeQuit() {
    ShutdownRequest req;
    return writer_->send(req);
}