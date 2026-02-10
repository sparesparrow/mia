#pragma once
#include <string>
#include <memory>
#include <cstdint>

class TcpSocket;

class TcpListener {
public:
    TcpListener(uint16_t port);
    ~TcpListener();

    bool start();
    std::unique_ptr<TcpSocket> accept();

private:
    int listenfd_;
    uint16_t port_;
};