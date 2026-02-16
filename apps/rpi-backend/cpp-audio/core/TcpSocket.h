#pragma once
#include <string>
#include <vector>
#include <memory>

class TcpSocket {
public:
    TcpSocket(const std::string& host, uint16_t port);
    explicit TcpSocket(int sockfd);  // Constructor from existing file descriptor
    ~TcpSocket();

    bool connect();
    bool isConnected() const;
    void disconnect();

    bool send(const void* data, size_t size);
    bool receive(std::vector<uint8_t>& buffer);
    bool receiveExact(std::vector<uint8_t>& buffer, size_t expectedSize);
    
    int getFd() const { return sockfd_; }  // For timeout operations

private:
    int sockfd_;
    std::string host_;
    uint16_t port_;
    bool connected_;
};