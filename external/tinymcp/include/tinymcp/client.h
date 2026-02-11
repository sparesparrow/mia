#pragma once

#include "tinymcp/protocol.h"
#include <memory>
#include <string>
#include <future>
#include <functional>

namespace tinymcp {

/**
 * Client configuration
 */
struct ClientConfig {
    std::string name = "TinyMCP Client";
    std::string version = "0.1.0";
    int timeout = 30000; // milliseconds
    int maxRetries = 3;
    bool enableLogging = true;
};

/**
 * MCP Client implementation
 */
class Client : public IProtocolHandler {
public:
    Client();
    explicit Client(const ClientConfig& config);
    virtual ~Client();
    
    // Connection management
    void connect(const std::string& endpoint);
    void disconnect();
    bool isConnected() const;
    
    // Synchronous requests
    Response sendRequest(const Request& request);
    Response initialize();
    Response listTools();
    Response callTool(const std::string& name, const Json::Value& arguments);
    Response listResources();
    Response readResource(const std::string& uri);
    
    // Asynchronous requests
    std::future<Response> sendRequestAsync(const Request& request);
    std::future<Response> initializeAsync();
    std::future<Response> listToolsAsync();
    std::future<Response> callToolAsync(const std::string& name, const Json::Value& arguments);
    
    // Notifications
    void sendNotification(const Notification& notification);
    
    // Protocol handler implementation
    void onRequest(const Request& request, Response& response) override;
    void onNotification(const Notification& notification) override;
    void onResponse(const Response& response) override;
    
    // Event handlers
    using NotificationHandler = std::function<void(const Notification&)>;
    using ErrorHandler = std::function<void(const std::string&)>;
    
    void setOnNotification(NotificationHandler handler);
    void setOnError(ErrorHandler handler);
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

/**
 * Client builder for fluent API
 */
class ClientBuilder {
public:
    ClientBuilder& withName(const std::string& name);
    ClientBuilder& withVersion(const std::string& version);
    ClientBuilder& withTimeout(int milliseconds);
    ClientBuilder& withMaxRetries(int retries);
    ClientBuilder& withLogging(bool enable);
    
    std::unique_ptr<Client> build();
    
private:
    ClientConfig config;
};

} // namespace tinymcp