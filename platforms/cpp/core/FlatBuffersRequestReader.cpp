#include "FlatBuffersRequestReader.h"
#include "webgrab_generated.h"

// Use the Mia::Protocol namespace for convenience
namespace fb = Mia::Protocol;
#include <flatbuffers/verifier.h>

FlatBuffersRequestReader::FlatBuffersRequestReader()
    : current_type_(RequestType::Unknown) {}

FlatBuffersRequestReader::FlatBuffersRequestReader(const uint8_t* buffer, size_t size)
    : buffer_(buffer, buffer + size), current_type_(RequestType::Unknown) {
    // Parse the buffer immediately to set current_type_
    receiveMessage();
}

bool FlatBuffersRequestReader::next(RequestEnvelope& out) {
    if (!receiveMessage()) return false;

    // Try to parse as Message union first
    auto msg = flatbuffers::GetRoot<fb::Message>(buffer_.data());
    if (msg && msg->request_type() != fb::Request_NONE) {
        switch (msg->request_type()) {
            case fb::Request_DownloadRequest:
                current_type_ = RequestType::Download;
                break;
            case fb::Request_DownloadStatusRequest:
                current_type_ = RequestType::Status;
                break;
            case fb::Request_DownloadAbortRequest:
                current_type_ = RequestType::Abort;
                break;
            case fb::Request_ShutdownRequest:
                current_type_ = RequestType::Shutdown;
                break;
            default:
                current_type_ = RequestType::Unknown;
                break;
        }
    } else {
        // Fallback: try to parse as individual message types
        flatbuffers::Verifier verifier(buffer_.data(), buffer_.size());
        if (verifier.VerifyBuffer<fb::DownloadRequest>(nullptr)) {
            current_type_ = RequestType::Download;
        } else if (verifier.VerifyBuffer<fb::DownloadStatusRequest>(nullptr)) {
            current_type_ = RequestType::Status;
        } else if (verifier.VerifyBuffer<fb::DownloadAbortRequest>(nullptr)) {
            current_type_ = RequestType::Abort;
        } else if (verifier.VerifyBuffer<fb::ShutdownRequest>(nullptr)) {
            current_type_ = RequestType::Shutdown;
        } else {
            current_type_ = RequestType::Unknown;
        }
    }

    out.type = current_type_;
    return true;
}

bool FlatBuffersRequestReader::good() const {
    return !buffer_.empty();
}

void FlatBuffersRequestReader::close() {
    buffer_.clear();
}

bool FlatBuffersRequestReader::read(void* buffer, size_t size) {
    // This method is called by receiveMessage to read from socket
    // The actual socket reading should be done by the caller
    // For now, return false as this is meant to be overridden or used differently
    return false;
}

bool FlatBuffersRequestReader::receiveMessage() {
    // This is a placeholder - in a real implementation, this would read from a socket
    // The actual implementation depends on how FlatBuffersRequestReader is used
    // If it's used with a socket, the socket should be passed in constructor
    // For now, return false to indicate no message available
    return false;
}

std::string FlatBuffersRequestReader::getDownloadUrl() const {
    if (current_type_ == RequestType::Download) {
        // Try Message union first
        auto msg = flatbuffers::GetRoot<fb::Message>(buffer_.data());
        if (msg && msg->request_type() == fb::Request_DownloadRequest) {
            auto req = msg->request_as_DownloadRequest();
            return req && req->url() ? req->url()->str() : "";
        }
        // Fallback to direct parsing
        auto req = flatbuffers::GetRoot<fb::DownloadRequest>(buffer_.data());
        return req && req->url() ? req->url()->str() : "";
    }
    return "";
}

uint32_t FlatBuffersRequestReader::getSessionId() const {
    auto msg = flatbuffers::GetRoot<fb::Message>(buffer_.data());
    
    if (current_type_ == RequestType::Status) {
        if (msg && msg->request_type() == fb::Request_DownloadStatusRequest) {
            auto req = msg->request_as_DownloadStatusRequest();
            return req ? req->sessionId() : 0;
        }
        auto req = flatbuffers::GetRoot<fb::DownloadStatusRequest>(buffer_.data());
        return req ? req->sessionId() : 0;
    } else if (current_type_ == RequestType::Abort) {
        if (msg && msg->request_type() == fb::Request_DownloadAbortRequest) {
            auto req = msg->request_as_DownloadAbortRequest();
            return req ? req->sessionId() : 0;
        }
        auto req = flatbuffers::GetRoot<fb::DownloadAbortRequest>(buffer_.data());
        return req ? req->sessionId() : 0;
    }
    return 0;
}

bool FlatBuffersRequestReader::isValid() const {
    flatbuffers::Verifier verifier(buffer_.data(), buffer_.size());
    switch (current_type_) {
    case RequestType::Download:
        return verifier.VerifyBuffer<fb::DownloadRequest>(nullptr);
    case RequestType::Status:
        return verifier.VerifyBuffer<fb::DownloadStatusRequest>(nullptr);
    case RequestType::Abort:
        return verifier.VerifyBuffer<fb::DownloadAbortRequest>(nullptr);
    case RequestType::Shutdown:
        return verifier.VerifyBuffer<fb::ShutdownRequest>(nullptr);
    default:
        return false;
    }
}

std::string FlatBuffersRequestReader::getValidationError() const {
    return "Validation failed";
}