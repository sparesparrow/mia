#pragma once
#include <string>
#include <cstdint>

// Local response structs (matching IResponseReader.h pattern)
struct DownloadResponse {
    uint32_t sessionId;
};

struct StatusResponse {
    uint32_t sessionId;
    std::string status;
};

struct ErrorResponse {
    std::string error;
};

class IResponseWriter {
public:
    virtual ~IResponseWriter() = default;
    virtual bool write(const DownloadResponse& resp) = 0;
    virtual bool write(const StatusResponse& resp) = 0;
    virtual bool write(const ErrorResponse& resp) = 0;
    virtual bool flush() = 0;
    virtual void close() = 0;
};