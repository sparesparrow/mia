#include "TcpListener.h"
#include "TcpSocket.h"
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <iostream>

TcpListener::TcpListener(uint16_t port) : listenfd_(-1), port_(port) {}

TcpListener::~TcpListener() {
    if (listenfd_ >= 0) {
        close(listenfd_);
    }
}

bool TcpListener::start() {
    listenfd_ = socket(AF_INET, SOCK_STREAM, 0);
    if (listenfd_ < 0) return false;

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port_);

    if (bind(listenfd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
        close(listenfd_);
        return false;
    }

    if (listen(listenfd_, 10) < 0) {
        close(listenfd_);
        return false;
    }

    return true;
}

std::unique_ptr<TcpSocket> TcpListener::accept() {
    sockaddr_in client_addr{};
    socklen_t addr_len = sizeof(client_addr);
    int clientfd = ::accept(listenfd_, reinterpret_cast<sockaddr*>(&client_addr), &addr_len);
    if (clientfd < 0) return nullptr;

    // Create TcpSocket from accepted file descriptor
    return std::make_unique<TcpSocket>(clientfd);
}