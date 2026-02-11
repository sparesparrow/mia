#include "tinymcp/server.h"
#include "tinymcp/utils.h"
#include <map>
#include <mutex>

#ifdef TINYMCP_ENABLE_LOGGING
#include <spdlog/spdlog.h>
#endif

namespace tinymcp {

class Server::Impl {
public:
    ServerConfig config;
    ToolRegistry toolRegistry;
    ResourceRegistry resourceRegistry;
    bool running = false;
    std::mutex mutex;
    
    ConnectionHandler onConnect;
    ConnectionHandler onDisconnect;
    ErrorHandler onError;
    
    Impl(const ServerConfig& cfg) : config(cfg) {
#ifdef TINYMCP_ENABLE_LOGGING
        if (config.enableLogging) {
            spdlog::info("TinyMCP Server initialized: {}", config.name);
        }
#endif
    }
};

Server::Server() : pImpl(std::make_unique<Impl>(ServerConfig{})) {}

Server::Server(const ServerConfig& config) : pImpl(std::make_unique<Impl>(config)) {}

Server::~Server() {
    if (isRunning()) {
        stop();
    }
}

void Server::registerTool(const Tool& tool) {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    pImpl->toolRegistry.registerTool(tool);
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::debug("Registered tool: {}", tool.name);
#endif
}

void Server::removeTool(const std::string& name) {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    pImpl->toolRegistry.unregisterTool(name);
}

std::vector<Tool> Server::getTools() const {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    return pImpl->toolRegistry.getAllTools();
}

void Server::registerResource(const Resource& resource) {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    pImpl->resourceRegistry.registerResource(resource);
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::debug("Registered resource: {}", resource.uri);
#endif
}

void Server::removeResource(const std::string& uri) {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    pImpl->resourceRegistry.unregisterResource(uri);
}

std::vector<Resource> Server::getResources() const {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    return pImpl->resourceRegistry.getAllResources();
}

void Server::start() {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    pImpl->running = true;
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::info("Server started: {}", pImpl->config.name);
#endif
}

void Server::stop() {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    pImpl->running = false;
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::info("Server stopped: {}", pImpl->config.name);
#endif
}

bool Server::isRunning() const {
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    return pImpl->running;
}

void Server::onRequest(const Request& request, Response& response) {
    response.id = request.id;
    
    if (request.method == "initialize") {
        handleInitialize(request, response);
    } else if (request.method == "tools/list") {
        handleListTools(request, response);
    } else if (request.method == "tools/call") {
        handleCallTool(request, response);
    } else if (request.method == "resources/list") {
        handleListResources(request, response);
    } else if (request.method == "resources/read") {
        handleReadResource(request, response);
    } else {
        response.error = Json::Value();
        response.error["code"] = -32601;
        response.error["message"] = "Method not found";
    }
}

void Server::onNotification(const Notification& notification) {
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::debug("Received notification: {}", notification.method);
#endif
}

void Server::onResponse(const Response& response) {
#ifdef TINYMCP_ENABLE_LOGGING
    spdlog::debug("Received response: {}", response.id);
#endif
}

void Server::handleInitialize(const Request& request, Response& response) {
    Json::Value result;
    result["protocolVersion"] = PROTOCOL_VERSION;
    result["capabilities"]["tools"] = Json::Value();
    result["capabilities"]["resources"] = Json::Value();
    result["serverInfo"]["name"] = pImpl->config.name;
    result["serverInfo"]["version"] = pImpl->config.version;
    response.result = result;
}

void Server::handleListTools(const Request& request, Response& response) {
    Json::Value result;
    Json::Value tools(Json::arrayValue);
    
    for (const auto& tool : getTools()) {
        tools.append(tool.toJson());
    }
    
    result["tools"] = tools;
    response.result = result;
}

void Server::handleCallTool(const Request& request, Response& response) {
    std::string toolName = request.params.get("name", "").asString();
    Json::Value arguments = request.params.get("arguments", Json::Value());
    
    auto* tool = pImpl->toolRegistry.getTool(toolName);
    if (!tool) {
        response.error = Json::Value();
        response.error["code"] = -32602;
        response.error["message"] = "Tool not found: " + toolName;
        return;
    }
    
    if (tool->handler) {
        try {
            response.result = tool->handler(arguments);
        } catch (const std::exception& e) {
            response.error = Json::Value();
            response.error["code"] = -32603;
            response.error["message"] = e.what();
        }
    } else {
        response.error = Json::Value();
        response.error["code"] = -32603;
        response.error["message"] = "Tool handler not implemented";
    }
}

void Server::handleListResources(const Request& request, Response& response) {
    Json::Value result;
    Json::Value resources(Json::arrayValue);
    
    for (const auto& resource : getResources()) {
        resources.append(resource.toJson());
    }
    
    result["resources"] = resources;
    response.result = result;
}

void Server::handleReadResource(const Request& request, Response& response) {
    std::string uri = request.params.get("uri", "").asString();
    
    auto* resource = pImpl->resourceRegistry.getResource(uri);
    if (!resource) {
        response.error = Json::Value();
        response.error["code"] = -32602;
        response.error["message"] = "Resource not found: " + uri;
        return;
    }
    
    Json::Value result;
    result["contents"] = Json::Value();
    result["contents"][0]["uri"] = uri;
    result["contents"][0]["text"] = resource->getContent();
    
    if (!resource->mimeType.empty()) {
        result["contents"][0]["mimeType"] = resource->mimeType;
    }
    
    response.result = result;
}

void Server::setOnConnect(ConnectionHandler handler) {
    pImpl->onConnect = handler;
}

void Server::setOnDisconnect(ConnectionHandler handler) {
    pImpl->onDisconnect = handler;
}

void Server::setOnError(ErrorHandler handler) {
    pImpl->onError = handler;
}

// ServerBuilder implementation
ServerBuilder& ServerBuilder::withName(const std::string& name) {
    config.name = name;
    return *this;
}

ServerBuilder& ServerBuilder::withVersion(const std::string& version) {
    config.version = version;
    return *this;
}

ServerBuilder& ServerBuilder::withDescription(const std::string& description) {
    config.description = description;
    return *this;
}

ServerBuilder& ServerBuilder::withMaxConnections(int max) {
    config.maxConnections = max;
    return *this;
}

ServerBuilder& ServerBuilder::withWorkerThreads(int threads) {
    config.workerThreads = threads;
    return *this;
}

ServerBuilder& ServerBuilder::withLogging(bool enable) {
    config.enableLogging = enable;
    return *this;
}

ServerBuilder& ServerBuilder::addTool(const Tool& tool) {
    tools.push_back(tool);
    return *this;
}

ServerBuilder& ServerBuilder::addResource(const Resource& resource) {
    resources.push_back(resource);
    return *this;
}

std::unique_ptr<Server> ServerBuilder::build() {
    auto server = std::make_unique<Server>(config);
    
    for (const auto& tool : tools) {
        server->registerTool(tool);
    }
    
    for (const auto& resource : resources) {
        server->registerResource(resource);
    }
    
    return server;
}

} // namespace tinymcp