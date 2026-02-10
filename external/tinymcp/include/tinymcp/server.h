#pragma once

#include "tinymcp/protocol.h"
#include "tinymcp/tools.h"
#include "tinymcp/resources.h"
#include <memory>
#include <string>
#include <map>
#include <functional>

namespace tinymcp {

/**
 * Server configuration
 */
struct ServerConfig {
    std::string name = "TinyMCP Server";
    std::string version = "0.1.0";
    std::string description = "Lightweight MCP server";
    int maxConnections = 100;
    int workerThreads = 4;
    bool enableLogging = true;
};

/**
 * MCP Server implementation
 */
class Server : public IProtocolHandler {
public:
    Server();
    explicit Server(const ServerConfig& config);
    virtual ~Server();
    
    // Tool management
    void registerTool(const Tool& tool);
    void removeTool(const std::string& name);
    std::vector<Tool> getTools() const;
    
    // Resource management
    void registerResource(const Resource& resource);
    void removeResource(const std::string& uri);
    std::vector<Resource> getResources() const;
    
    // Server control
    void start();
    void stop();
    bool isRunning() const;
    
    // Protocol handler implementation
    void onRequest(const Request& request, Response& response) override;
    void onNotification(const Notification& notification) override;
    void onResponse(const Response& response) override;
    
    // Event handlers
    using ConnectionHandler = std::function<void(const std::string& clientId)>;
    using ErrorHandler = std::function<void(const std::string& error)>;
    
    void setOnConnect(ConnectionHandler handler);
    void setOnDisconnect(ConnectionHandler handler);
    void setOnError(ErrorHandler handler);
    
protected:
    // Request handlers
    virtual void handleInitialize(const Request& request, Response& response);
    virtual void handleListTools(const Request& request, Response& response);
    virtual void handleCallTool(const Request& request, Response& response);
    virtual void handleListResources(const Request& request, Response& response);
    virtual void handleReadResource(const Request& request, Response& response);
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

/**
 * Server builder for fluent API
 */
class ServerBuilder {
public:
    ServerBuilder& withName(const std::string& name);
    ServerBuilder& withVersion(const std::string& version);
    ServerBuilder& withDescription(const std::string& description);
    ServerBuilder& withMaxConnections(int max);
    ServerBuilder& withWorkerThreads(int threads);
    ServerBuilder& withLogging(bool enable);
    ServerBuilder& addTool(const Tool& tool);
    ServerBuilder& addResource(const Resource& resource);
    
    std::unique_ptr<Server> build();
    
private:
    ServerConfig config;
    std::vector<Tool> tools;
    std::vector<Resource> resources;
};

} // namespace tinymcp