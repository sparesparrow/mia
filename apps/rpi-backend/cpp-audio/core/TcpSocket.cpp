#include "TcpSocket.h"
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <iostream>

TcpSocket::TcpSocket(const std::string& host, uint16_t port)
    : sockfd_(-1), host_(host), port_(port), connected_(false) {}

TcpSocket::TcpSocket(int sockfd)
    : sockfd_(sockfd), host_(""), port_(0), connected_(sockfd >= 0) {}

TcpSocket::~TcpSocket() {
    disconnect();
}

bool TcpSocket::connect() {
    sockfd_ = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd_ < 0) return false;

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port_);
    inet_pton(AF_INET, host_.c_str(), &server_addr.sin_addr);

    socklen_t addr_len = sizeof(server_addr);
    if (::connect(sockfd_, reinterpret_cast<sockaddr*>(&server_addr), addr_len) < 0) {
        close(sockfd_);
        sockfd_ = -1;
        return false;
    }

    connected_ = true;
    return true;
}

bool TcpSocket::isConnected() const {
    return connected_;
}

void TcpSocket::disconnect() {
    if (sockfd_ >= 0) {
        close(sockfd_);
        sockfd_ = -1;
    }
    connected_ = false;
}

bool TcpSocket::send(const void* data, size_t size) {
    if (!connected_) return false;
    return ::send(sockfd_, data, size, 0) == static_cast<ssize_t>(size);
}

bool TcpSocket::receive(std::vector<uint8_t>& buffer) {
    if (!connected_) return false;
    uint8_t temp[1024];
    ssize_t bytes = recv(sockfd_, temp, sizeof(temp), 0);
    if (bytes <= 0) {
        connected_ = false;
        return false;
    }
    buffer.insert(buffer.end(), temp, temp + bytes);
    return true;
}

bool TcpSocket::receiveExact(std::vector<uint8_t>& buffer, size_t expectedSize) {
    if (buffer.size() < expectedSize) return false;
    size_t received = 0;
    while (received < expectedSize) {
        ssize_t bytes = recv(sockfd_, buffer.data() + received, expectedSize - received, 0);
        if (bytes <= 0) {
            connected_ = false;
            return false;
        }
        received += bytes;
    }
    return true;
}