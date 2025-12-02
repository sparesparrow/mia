#include "FlatBuffersResponseReader.h"
#include "TcpSocket.h"
#include "webgrab_generated.h"
#include <cstring>
#include <arpa/inet.h>
#include <fcntl.h>
#include <unistd.h>
#include <thread>
#include <chrono>

FlatBuffersResponseReader::FlatBuffersResponseReader(std::shared_ptr<TcpSocket> socket)
    : socket_(socket) {}

FlatBuffersResponseReader::~FlatBuffersResponseReader() {
    close();
}

bool FlatBuffersResponseReader::recv(DownloadResponse& out) {
    if (!receiveMessage()) return false;
    // Try Message union first
    auto msg = flatbuffers::GetRoot<webgrab::Message>(buffer_.data());
    if (msg && msg->response_type() == webgrab::Response_DownloadResponse) {
        auto resp = msg->response_as_DownloadResponse();
        if (resp) {
            out.sessionId = resp->sessionId();
            return true;
        }
    }
    // Fallback to direct parsing
    auto resp = flatbuffers::GetRoot<webgrab::DownloadResponse>(buffer_.data());
    if (!resp) return false;
    out.sessionId = resp->sessionId();
    return true;
}

bool FlatBuffersResponseReader::recv(StatusResponse& out) {
    if (!receiveMessage()) return false;
    // Try Message union first
    auto msg = flatbuffers::GetRoot<webgrab::Message>(buffer_.data());
    if (msg && msg->response_type() == webgrab::Response_DownloadStatusResponse) {
        auto resp = msg->response_as_DownloadStatusResponse();
        if (resp) {
            out.sessionId = 0;
            out.status = resp->status() ? resp->status()->str() : "";
            return true;
        }
    }
    // Fallback to direct parsing
    auto resp = flatbuffers::GetRoot<webgrab::DownloadStatusResponse>(buffer_.data());
    if (!resp) return false;
    out.sessionId = 0;
    out.status = resp->status() ? resp->status()->str() : "";
    return true;
}

bool FlatBuffersResponseReader::recv(ErrorResponse& out) {
    if (!receiveMessage()) return false;
    // Try Message union first
    auto msg = flatbuffers::GetRoot<webgrab::Message>(buffer_.data());
    if (msg && msg->response_type() == webgrab::Response_ErrorResponse) {
        auto resp = msg->response_as_ErrorResponse();
        if (resp) {
            out.error = resp->error() ? resp->error()->str() : "";
            return true;
        }
    }
    // Fallback to direct parsing
    auto resp = flatbuffers::GetRoot<webgrab::ErrorResponse>(buffer_.data());
    if (!resp) return false;
    out.error = resp->error() ? resp->error()->str() : "";
    return true;
}

bool FlatBuffersResponseReader::tryRecv(DownloadResponse& out, std::chrono::milliseconds timeout) {
    if (!socket_ || !socket_->isConnected()) return false;
    
    // Set socket to non-blocking mode temporarily
    int flags = fcntl(socket_->getFd(), F_GETFL, 0);
    if (flags < 0) return false;
    fcntl(socket_->getFd(), F_SETFL, flags | O_NONBLOCK);
    
    auto start = std::chrono::steady_clock::now();
    bool result = false;
    
    while (std::chrono::steady_clock::now() - start < timeout) {
        if (receiveMessage()) {
            auto resp = flatbuffers::GetRoot<webgrab::DownloadResponse>(buffer_.data());
            if (resp) {
                out.sessionId = resp->sessionId();
                result = true;
                break;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    
    // Restore blocking mode
    fcntl(socket_->getFd(), F_SETFL, flags);
    return result;
}

bool FlatBuffersResponseReader::tryRecv(StatusResponse& out, std::chrono::milliseconds timeout) {
    if (!socket_ || !socket_->isConnected()) return false;
    
    // Set socket to non-blocking mode temporarily
    int flags = fcntl(socket_->getFd(), F_GETFL, 0);
    if (flags < 0) return false;
    fcntl(socket_->getFd(), F_SETFL, flags | O_NONBLOCK);
    
    auto start = std::chrono::steady_clock::now();
    bool result = false;
    
    while (std::chrono::steady_clock::now() - start < timeout) {
        if (receiveMessage()) {
            auto resp = flatbuffers::GetRoot<webgrab::DownloadStatusResponse>(buffer_.data());
            if (resp) {
                out.sessionId = 0; // StatusResponse doesn't have sessionId in the struct
                out.status = resp->status() ? resp->status()->str() : "";
                result = true;
                break;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    
    // Restore blocking mode
    fcntl(socket_->getFd(), F_SETFL, flags);
    return result;
}

bool FlatBuffersResponseReader::tryRecv(ErrorResponse& out, std::chrono::milliseconds timeout) {
    if (!socket_ || !socket_->isConnected()) return false;
    
    // Set socket to non-blocking mode temporarily
    int flags = fcntl(socket_->getFd(), F_GETFL, 0);
    if (flags < 0) return false;
    fcntl(socket_->getFd(), F_SETFL, flags | O_NONBLOCK);
    
    auto start = std::chrono::steady_clock::now();
    bool result = false;
    
    while (std::chrono::steady_clock::now() - start < timeout) {
        if (receiveMessage()) {
            auto resp = flatbuffers::GetRoot<webgrab::ErrorResponse>(buffer_.data());
            if (resp) {
                out.error = resp->error() ? resp->error()->str() : "";
                result = true;
                break;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    
    // Restore blocking mode
    fcntl(socket_->getFd(), F_SETFL, flags);
    return result;
}

void FlatBuffersResponseReader::close() {
    if (socket_) {
        socket_->disconnect();
    }
}

bool FlatBuffersResponseReader::read(void* buffer, size_t size) {
    if (!socket_) return false;
    std::vector<uint8_t> temp;
    if (!socket_->receive(temp)) return false;
    if (temp.size() < size) return false;
    std::memcpy(buffer, temp.data(), size);
    return true;
}

bool FlatBuffersResponseReader::receiveMessage() {
    if (!socket_ || !socket_->isConnected()) return false;

    // Read length prefix
    std::vector<uint8_t> length_buf(sizeof(uint32_t));
    if (!read(length_buf.data(), sizeof(uint32_t))) return false;
    uint32_t length = ntohl(*reinterpret_cast<uint32_t*>(length_buf.data()));

    // Read data
    buffer_.resize(length);
    return read(buffer_.data(), length);
}