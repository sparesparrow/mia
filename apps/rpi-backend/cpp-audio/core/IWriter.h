#pragma once

class IWriter {
public:
    virtual ~IWriter() = default;
    virtual bool write(const void* buffer, size_t size) = 0;
    virtual void close() = 0;
};