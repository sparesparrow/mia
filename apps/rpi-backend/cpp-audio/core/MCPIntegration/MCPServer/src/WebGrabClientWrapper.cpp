#include "WebGrabClientWrapper.h"

// Local includes
#include "../../WebGrabClient.h"

// Standard library includes
#include <iostream>

namespace MCPIntegration {

WebGrabClientWrapper::WebGrabClientWrapper() = default;

WebGrabClientWrapper::~WebGrabClientWrapper() = default;

bool WebGrabClientWrapper::connect(const std::string& host, uint16_t port) {
    std::lock_guard<std::mutex> lock(mutex_);
    client = std::make_unique<WebGrabClient>(host, port);
    return client->connect();
}

bool WebGrabClientWrapper::download(const std::string& url, uint32_t& sessionId) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!client) {
        return false;
    }

    // WebGrabClient::executeDownload returns a session ID
    // We need to capture it somehow - let's assume it modifies a reference parameter
    // This is a simplification; in reality we'd need to modify WebGrabClient to return session ID
    sessionId = 0;  // Placeholder - need to implement proper session ID handling
    return client->executeDownload(url);
}

bool WebGrabClientWrapper::status(uint32_t sessionId, std::string& status) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!client) {
        return false;
    }

    // For now, we can't get status string from WebGrabClient
    // This is a limitation of the current WebGrabClient API
    return client->executeStatus(sessionId);
}

bool WebGrabClientWrapper::abort(uint32_t sessionId) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!client) {
        return false;
    }

    return client->executeAbort(sessionId);
}

} // namespace MCPIntegration