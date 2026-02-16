#pragma once
#include <optional>
#include <string>
#include <cstdint>
#include <chrono>
#include "IResponseWriter.h"  // For DownloadResponse, StatusResponse, ErrorResponse

class IResponseReader {
public:
    virtual ~IResponseReader() = default;
    virtual bool recv(DownloadResponse& out) = 0;
    virtual bool recv(StatusResponse& out) = 0;
    virtual bool recv(ErrorResponse& out) = 0;
    virtual bool tryRecv(DownloadResponse& out, std::chrono::milliseconds timeout) = 0;
    virtual bool tryRecv(StatusResponse& out, std::chrono::milliseconds timeout) = 0;
    virtual bool tryRecv(ErrorResponse& out, std::chrono::milliseconds timeout) = 0;
    virtual void close() = 0;
};