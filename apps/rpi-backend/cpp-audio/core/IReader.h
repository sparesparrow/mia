#pragma once

class IReader {
public:
    virtual ~IReader() = default;
    virtual bool read(void* buffer, size_t size) = 0;
    virtual void close() = 0;
};