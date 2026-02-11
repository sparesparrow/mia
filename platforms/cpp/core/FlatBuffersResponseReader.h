#pragma once
#include "IResponseReader.h"
#include "IReader.h"
#include <memory>
#include <vector>
#include <span>

class TcpSocket; // Forward declaration

class FlatBuffersResponseReader : public IResponseReader, public IReader {
private:
    std::shared_ptr<TcpSocket> socket_;
    std::vector<uint8_t> buffer_;

public:
    explicit FlatBuffersResponseReader(std::shared_ptr<TcpSocket> socket);
    ~FlatBuffersResponseReader() override;

    // IResponseReader
    bool recv(DownloadResponse& out) override;
    bool recv(StatusResponse& out) override;
    bool recv(ErrorResponse& out) override;
    bool tryRecv(DownloadResponse& out, std::chrono::milliseconds timeout) override;
    bool tryRecv(StatusResponse& out, std::chrono::milliseconds timeout) override;
    bool tryRecv(ErrorResponse& out, std::chrono::milliseconds timeout) override;
    void close() override;

    // IReader
    bool read(void* buffer, size_t size) override;

private:
    bool receiveMessage();
};