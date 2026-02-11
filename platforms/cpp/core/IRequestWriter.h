#pragma once
#include <string>
#include <cstdint>
#include <span>

// Forward declarations or simple structs
struct DownloadRequest { std::string url; };
struct DownloadStatusRequest { uint32_t session_id; };
struct DownloadAbortRequest { uint32_t session_id; };
struct ShutdownRequest {};

class IRequestWriter {
public:
    virtual ~IRequestWriter() = default;
    virtual bool send(const DownloadRequest& req) = 0;
    virtual bool send(const DownloadStatusRequest& req) = 0;
    virtual bool send(const DownloadAbortRequest& req) = 0;
    virtual bool send(const ShutdownRequest& req) = 0;
    virtual bool sendRaw(std::span<const uint8_t> data) = 0;
    virtual void close() = 0;
};