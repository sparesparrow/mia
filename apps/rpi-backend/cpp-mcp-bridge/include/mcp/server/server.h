#pragma once

#include "mcp/core/protocol.h"
#include "mcp/transport/transport.h"
#include <memory>
#include <unordered_map>
#include <mutex>
#include <future>
#include <chrono>
#include <cstdint>

// Forward declaration for logging
namespace spdlog {
    namespace level {
        enum level_enum : int;
    }
}

namespace mcp {
namespace server {

/**
 * Advanced MCP Server implementation with full protocol support
 */
class Server {
public:
    struct Config {
        std::string name = "mcp-cpp-server";
        std::string version = "1.0.0";
        ServerCapabilities capabilities;
        
        // Performance tuning
        size_t workerThreads = 4;
        size_t maxConcurrentRequests = 100;
        std::chrono::milliseconds requestTimeout{30000};
        
        // Logging
        int logLevel = 2; // Info level
    };
    
    explicit Server(Config config = {});
    ~Server();
    
    // Tool management
    void registerTool(Tool tool);
    void unregisterTool(const std::string& name);
    
    // Resource management
    void registerResource(Resource resource);
    void unregisterResource(const std::string& uri);
    
    // Prompt management
    void registerPrompt(Prompt prompt);
    void unregisterPrompt(const std::string& name);
    
    // Transport management
    void addTransport(std::unique_ptr<transport::Transport> transport);
    
    // Server lifecycle
    void start();
    void stop();
    bool isRunning() const;
    
    // Statistics and monitoring
    struct Stats {
        uint64_t requestsReceived = 0;
        uint64_t requestsProcessed = 0;
        uint64_t requestsFailed = 0;
        uint64_t notificationsReceived = 0;
        std::chrono::milliseconds avgResponseTime{0};
    };
    
    Stats getStats() const;
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
    
    // Request handlers
    void handleInitialize(const Protocol::Request& req);
    void handleInitialized(const Protocol::Notification& notif);
    void handleShutdown(const Protocol::Request& req);
    
    void handleToolsList(const Protocol::Request& req);
    void handleToolsCall(const Protocol::Request& req);
    
    void handleResourcesList(const Protocol::Request& req);
    void handleResourcesRead(const Protocol::Request& req);
    void handleResourcesSubscribe(const Protocol::Request& req);
    
    void handlePromptsList(const Protocol::Request& req);
    void handlePromptsGet(const Protocol::Request& req);
    
    void handleLoggingSetLevel(const Protocol::Request& req);
    
    // Internal message processing
    void processMessage(const Protocol::Message& msg, 
                       std::shared_ptr<transport::Transport> transport);
    void sendResponse(const Protocol::Response& resp,
                     std::shared_ptr<transport::Transport> transport);
    void sendNotification(const Protocol::Notification& notif,
                         std::shared_ptr<transport::Transport> transport);
};

/**
 * Builder pattern for Server configuration
 */
class ServerBuilder {
public:
    ServerBuilder& withName(std::string name);
    ServerBuilder& withVersion(std::string version);
    ServerBuilder& withCapabilities(ServerCapabilities caps);
    ServerBuilder& withWorkerThreads(size_t count);
    ServerBuilder& withMaxConcurrentRequests(size_t max);
    ServerBuilder& withRequestTimeout(std::chrono::milliseconds timeout);
    ServerBuilder& withLogLevel(int level);
    
    ServerBuilder& addTool(Tool tool);
    ServerBuilder& addResource(Resource resource);
    ServerBuilder& addPrompt(Prompt prompt);
    ServerBuilder& addTransport(std::unique_ptr<transport::Transport> transport);
    
    std::unique_ptr<Server> build();
    
private:
    Server::Config config_;
    std::vector<Tool> tools_;
    std::vector<Resource> resources_;
    std::vector<Prompt> prompts_;
    std::vector<std::unique_ptr<transport::Transport>> transports_;
};

} // namespace server
} // namespace mcp