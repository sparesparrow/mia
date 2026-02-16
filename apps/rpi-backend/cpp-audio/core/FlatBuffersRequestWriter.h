#pragma once
#include "IRequestWriter.h"
#include "IWriter.h"
#include <memory>
#include <flatbuffers/flatbuffers.h>

class TcpSocket; // Forward declaration

class FlatBuffersRequestWriter : public IRequestWriter, public IWriter {
private:
    std::shared_ptr<TcpSocket> socket_;
    flatbuffers::FlatBufferBuilder builder_;

public:
    explicit FlatBuffersRequestWriter(std::shared_ptr<TcpSocket> socket);
    ~FlatBuffersRequestWriter() override;

    // IRequestWriter
    bool send(const DownloadRequest& req) override;
    bool send(const DownloadStatusRequest& req) override;
    bool send(const DownloadAbortRequest& req) override;
    bool send(const ShutdownRequest& req) override;
    bool sendRaw(std::span<const uint8_t> data) override;
    void close() override;

    // IWriter
    bool write(const void* buffer, size_t size) override;

private:
    bool sendMessage(const void* data, size_t size);
};