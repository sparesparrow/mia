#pragma once
#include <string>
#include <cstdint>

enum class RequestType {
    Download,
    Status,
    Abort,
    Shutdown,
    Unknown
};

struct RequestEnvelope {
    RequestType type;
    // Additional data can be added
};

class IRequestReader {
public:
    virtual ~IRequestReader() = default;
    virtual bool next(RequestEnvelope& out) = 0;
    virtual bool good() const = 0;
    virtual void close() = 0;
};