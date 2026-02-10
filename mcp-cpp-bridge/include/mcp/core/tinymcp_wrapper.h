#pragma once

// TinyMCP base implementation
#include <tinymcp/protocol.h>
#include <tinymcp/server.h>
#include <tinymcp/client.h>
#include <tinymcp/transport.h>

// Our extensions
#include "mcp/core/protocol.h"
#include <json/json.h>
#include <memory>
#include <string>

namespace mcp {

/**
 * Wrapper class that bridges TinyMCP with our extended functionality
 * Provides compatibility layer between TinyMCP and our jsoncpp-based implementation
 */
class TinyMCPWrapper {
public:
    TinyMCPWrapper();
    ~TinyMCPWrapper();
    
    /**
     * Convert between TinyMCP and our JSON representations
     */
    static Json::Value tinyMcpToJson(const tinymcp::Message& msg);
    static tinymcp::Message jsonToTinyMcp(const Json::Value& json);
    
    /**
     * Create a TinyMCP server with our configuration
     */
    static std::unique_ptr<tinymcp::Server> createServer(const Server::Config& config);
    
    /**
     * Create a TinyMCP client with our configuration  
     */
    static std::unique_ptr<tinymcp::Client> createClient(const std::string& name);
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

/**
 * Extended MCP server that uses TinyMCP as base implementation
 * Adds our custom features on top of TinyMCP
 */
class ExtendedMCPServer : public tinymcp::Server {
public:
    ExtendedMCPServer(const Server::Config& config);
    ~ExtendedMCPServer() override;
    
    // Additional functionality beyond TinyMCP
    void registerAdvancedTool(const Tool& tool);
    void enableMetrics();
    void enableTracing();
    
    // Performance optimizations
    void setThreadPool(size_t numThreads);
    void enableCaching(size_t maxCacheSize);
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

/**
 * Extended MCP client with additional features
 */
class ExtendedMCPClient : public tinymcp::Client {
public:
    explicit ExtendedMCPClient(const std::string& name);
    ~ExtendedMCPClient() override;
    
    // Connection pooling
    void enableConnectionPool(size_t maxConnections);
    
    // Request batching
    void enableBatching(size_t batchSize, std::chrono::milliseconds timeout);
    
    // Retry logic
    void setRetryPolicy(size_t maxRetries, std::chrono::milliseconds baseDelay);
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

} // namespace mcp