#include "tinymcp/transport.h"
#include <iostream>
#include <sstream>

namespace tinymcp {

// StdioTransport implementation
class StdioTransport::Impl {
public:
    bool connected = false;
    MessageHandler onMessage;
    ErrorHandler onError;
};

StdioTransport::StdioTransport() : pImpl(std::make_unique<Impl>()) {}
StdioTransport::~StdioTransport() = default;

void StdioTransport::connect(const std::string& endpoint) {
    pImpl->connected = true;
}

void StdioTransport::disconnect() {
    pImpl->connected = false;
}

bool StdioTransport::isConnected() const {
    return pImpl->connected;
}

void StdioTransport::send(const std::string& data) {
    if (!pImpl->connected) return;
    
    std::cout << "Content-Length: " << data.length() << "\r\n\r\n";
    std::cout << data << std::flush;
}

std::string StdioTransport::receive() {
    if (!pImpl->connected) return "";
    
    std::string line;
    int contentLength = 0;
    
    // Read headers
    while (std::getline(std::cin, line)) {
        if (line == "\r" || line.empty()) break;
        
        if (line.find("Content-Length:") == 0) {
            contentLength = std::stoi(line.substr(15));
        }
    }
    
    // Read content
    if (contentLength > 0) {
        std::string content(contentLength, '\0');
        std::cin.read(&content[0], contentLength);
        return content;
    }
    
    return "";
}

void StdioTransport::setOnMessage(MessageHandler handler) {
    pImpl->onMessage = handler;
}

void StdioTransport::setOnError(ErrorHandler handler) {
    pImpl->onError = handler;
}

// TcpTransport implementation
class TcpTransport::Impl {
public:
    bool connected = false;
    MessageHandler onMessage;
    ErrorHandler onError;
    // In a real implementation, would include socket handling
};

TcpTransport::TcpTransport() : pImpl(std::make_unique<Impl>()) {}
TcpTransport::~TcpTransport() = default;

void TcpTransport::connect(const std::string& endpoint) {
    // Parse endpoint and establish TCP connection
    pImpl->connected = true;
}

void TcpTransport::disconnect() {
    // Close TCP connection
    pImpl->connected = false;
}

bool TcpTransport::isConnected() const {
    return pImpl->connected;
}

void TcpTransport::send(const std::string& data) {
    if (!pImpl->connected) return;
    // Send over TCP socket
}

std::string TcpTransport::receive() {
    if (!pImpl->connected) return "";
    // Receive from TCP socket
    return "";
}

void TcpTransport::setOnMessage(MessageHandler handler) {
    pImpl->onMessage = handler;
}

void TcpTransport::setOnError(ErrorHandler handler) {
    pImpl->onError = handler;
}

// TransportFactory implementation
std::unique_ptr<ITransport> TransportFactory::create(Type type) {
    switch (type) {
        case Type::Stdio:
            return std::make_unique<StdioTransport>();
        case Type::Tcp:
            return std::make_unique<TcpTransport>();
        default:
            return nullptr;
    }
}

std::unique_ptr<ITransport> TransportFactory::createFromUri(const std::string& uri) {
    if (uri == "stdio" || uri.empty()) {
        return create(Type::Stdio);
    } else if (uri.find("tcp://") == 0) {
        return create(Type::Tcp);
    }
    return nullptr;
}

} // namespace tinymcp