#include "tinymcp/client.h"
#include "tinymcp/utils.h"
#include <map>
#include <mutex>
#include <condition_variable>
#include <thread>

#ifdef TINYMCP_ENABLE_LOGGING
#include <spdlog/spdlog.h>
#endif

namespace tinymcp {

class Client::Impl {
public:
    ClientConfig config;
    bool connected = false;
    std::mutex mutex;
    std::map<std::string, std::promise<Response>> pendingRequests;
    
    NotificationHandler onNotification;
    ErrorHandler onError;
    
    Impl(const ClientConfig& cfg) : config(cfg) {
#ifdef TINYMCP_ENABLE_LOGGING
        if (config.enableLogging) {
            spdlog::info("TinyMCP Client initialized: {}", config.name);
        }
#endif
    }
    
    Response waitForResponse(const std::string& id) {
        std::promise<Response> promise;
        auto future = promise.get_future();
        
        {
            std::lock_guard<std::mutex> lock(mutex);
            pendingRequests[id] = std::move(promise);
        }
        
        // Wait with timeout
        if (future.wait_for(std::chrono::milliseconds(config.timeout)) == std::future_status::ready) {
            return future.get();
        } else {
            throw utils::MCPException("Request timeout");
        }
    }
};

Client::Client() : pImpl(std::make_unique<Impl>(ClientConfig{})) {}

Client::Client(const ClientConfig& config) : pImpl(std::make_unique<Impl>(config)) {}

Client::~Client() {
    if (isConnected()) {
        disconnect();
    }
}

void Client::connect(const std::string& endpoint) {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    pImpl->connected = true;
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::info("Client connected to: {}", endpoint);
#endif
}

void Client::disconnect() {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    pImpl->connected = false;
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::info("Client disconnected");
#endif
}

bool Client::isConnected() const {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    return pImpl->connected;
}

Response Client::sendRequest(const Request& request) {
    if (!isConnected()) {
        throw utils::MCPException("Client not connected");
    }
    
    // In a real implementation, this would send over transport
    // For now, return a mock response
    return pImpl->waitForResponse(request.id);
}

Response Client::initialize() {
    Request request("initialize");
    request.params["clientInfo"]["name"] = pImpl->config.name;
    request.params["clientInfo"]["version"] = pImpl->config.version;
    request.params["protocolVersion"] = PROTOCOL_VERSION;
    
    return sendRequest(request);
}

Response Client::listTools() {
    Request request("tools/list");
    return sendRequest(request);
}

Response Client::callTool(const std::string& name, const Json::Value& arguments) {
    Request request("tools/call");
    request.params["name"] = name;
    request.params["arguments"] = arguments;
    return sendRequest(request);
}

Response Client::listResources() {
    Request request("resources/list");
    return sendRequest(request);
}

Response Client::readResource(const std::string& uri) {
    Request request("resources/read");
    request.params["uri"] = uri;
    return sendRequest(request);
}

std::future<Response> Client::sendRequestAsync(const Request& request) {
    return std::async(std::launch::async, [this, request]() {
        return sendRequest(request);
    });
}

std::future<Response> Client::initializeAsync() {
    return std::async(std::launch::async, [this]() {
        return initialize();
    });
}

std::future<Response> Client::listToolsAsync() {
    return std::async(std::launch::async, [this]() {
        return listTools();
    });
}

std::future<Response> Client::callToolAsync(const std::string& name, const Json::Value& arguments) {
    return std::async(std::launch::async, [this, name, arguments]() {
        return callTool(name, arguments);
    });
}

void Client::sendNotification(const Notification& notification) {
    if (!isConnected()) {
        throw utils::MCPException("Client not connected");
    }
    
    // In a real implementation, this would send over transport
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::debug("Sent notification: {}", notification.method);
#endif
}

void Client::onRequest(const Request& request, Response& response) {
    // Clients typically don't handle requests
    response.error = Json::Value();
    response.error["code"] = -32601;
    response.error["message"] = "Client does not handle requests";
}

void Client::onNotification(const Notification& notification) {
    if (pImpl->onNotification) {
        pImpl->onNotification(notification);
    }
}

void Client::onResponse(const Response& response) {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    
    auto it = pImpl->pendingRequests.find(response.id);
    if (it != pImpl->pendingRequests.end()) {
        it->second.set_value(response);
        pImpl->pendingRequests.erase(it);
    }
}

void Client::setOnNotification(NotificationHandler handler) {
    pImpl->onNotification = handler;
}

void Client::setOnError(ErrorHandler handler) {
    pImpl->onError = handler;
}

// ClientBuilder implementation
ClientBuilder& ClientBuilder::withName(const std::string& name) {
    config.name = name;
    return *this;
}

ClientBuilder& ClientBuilder::withVersion(const std::string& version) {
    config.version = version;
    return *this;
}

ClientBuilder& ClientBuilder::withTimeout(int milliseconds) {
    config.timeout = milliseconds;
    return *this;
}

ClientBuilder& ClientBuilder::withMaxRetries(int retries) {
    config.maxRetries = retries;
    return *this;
}

ClientBuilder& ClientBuilder::withLogging(bool enable) {
    config.enableLogging = enable;
    return *this;
}

std::unique_ptr<Client> ClientBuilder::build() {
    return std::make_unique<Client>(config);
}

} // namespace tinymcp