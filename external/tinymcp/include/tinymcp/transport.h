#pragma once

#include <string>
#include <functional>
#include <memory>

namespace tinymcp {

// Forward declarations
class Message;

/**
 * Transport interface for MCP communication
 */
class ITransport {
public:
    virtual ~ITransport() = default;
    
    // Connection management
    virtual void connect(const std::string& endpoint) = 0;
    virtual void disconnect() = 0;
    virtual bool isConnected() const = 0;
    
    // Message handling
    virtual void send(const std::string& data) = 0;
    virtual std::string receive() = 0;
    
    // Event handlers
    using MessageHandler = std::function<void(const std::string&)>;
    using ErrorHandler = std::function<void(const std::string&)>;
    
    virtual void setOnMessage(MessageHandler handler) = 0;
    virtual void setOnError(ErrorHandler handler) = 0;
};

/**
 * Standard I/O transport
 */
class StdioTransport : public ITransport {
public:
    StdioTransport();
    ~StdioTransport() override;
    
    void connect(const std::string& endpoint) override;
    void disconnect() override;
    bool isConnected() const override;
    
    void send(const std::string& data) override;
    std::string receive() override;
    
    void setOnMessage(MessageHandler handler) override;
    void setOnError(ErrorHandler handler) override;
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

/**
 * TCP transport
 */
class TcpTransport : public ITransport {
public:
    TcpTransport();
    ~TcpTransport() override;
    
    void connect(const std::string& endpoint) override;
    void disconnect() override;
    bool isConnected() const override;
    
    void send(const std::string& data) override;
    std::string receive() override;
    
    void setOnMessage(MessageHandler handler) override;
    void setOnError(ErrorHandler handler) override;
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

/**
 * Transport factory
 */
class TransportFactory {
public:
    enum class Type {
        Stdio,
        Tcp,
        WebSocket
    };
    
    static std::unique_ptr<ITransport> create(Type type);
    static std::unique_ptr<ITransport> createFromUri(const std::string& uri);
};

} // namespace tinymcp