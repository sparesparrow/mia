#pragma once
#include <string>
#include <cstdint>

namespace webgrab {
    struct DownloadResponse;
    struct DownloadStatusResponse;
    struct ErrorResponse;
}

class IResponseWriter {
public:
    virtual ~IResponseWriter() = default;
    virtual bool write(const webgrab::DownloadResponse& resp) = 0;
    virtual bool write(const webgrab::DownloadStatusResponse& resp) = 0;
    virtual bool write(const webgrab::ErrorResponse& resp) = 0;
    virtual bool flush() = 0;
    virtual void close() = 0;
};