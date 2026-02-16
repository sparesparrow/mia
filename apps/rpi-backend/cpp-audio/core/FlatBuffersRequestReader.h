#pragma once
#include "IRequestReader.h"
#include "IReader.h"
#include <cstdint>
#include <vector>

class FlatBuffersRequestReader : public IRequestReader, public IReader {
private:
    std::vector<uint8_t> buffer_;
    RequestType current_type_;

public:
    explicit FlatBuffersRequestReader();
    explicit FlatBuffersRequestReader(const uint8_t* buffer, size_t size);
    ~FlatBuffersRequestReader() override = default;

    // IRequestReader
    bool next(RequestEnvelope& out) override;
    bool good() const override;
    void close() override;

    // IReader
    bool read(void* buffer, size_t size) override;

    RequestType getType() const { return current_type_; }
    std::string getDownloadUrl() const;
    uint32_t getSessionId() const;
    bool isValid() const;
    std::string getValidationError() const;

private:
    bool receiveMessage();
};