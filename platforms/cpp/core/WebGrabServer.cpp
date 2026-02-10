#include "WebGrabServer.h"
#include "MessageQueueProcessor.h"
#include "JobWorker.h"
#include "TcpListener.h"
#include "TcpSocket.h"
#include "FlatBuffersRequestReader.h"
#include "FlatBuffersResponseWriter.h"
#include "IJob.h"
#include <iostream>

WebGrabServer::WebGrabServer(uint16_t port, const std::string& workingDir)
    : processor_(std::make_unique<MessageQueueProcessor>(workingDir)),
      job_worker_(std::make_unique<JobWorker>(4)), // 4 threads
      listener_(std::make_unique<TcpListener>(port)),
      running_(false) {}

WebGrabServer::~WebGrabServer() {
    stop();
}

bool WebGrabServer::start() {
    if (!listener_->start()) return false;
    running_ = true;
    worker_threads_.emplace_back(&WebGrabServer::acceptLoop, this);
    return true;
}

void WebGrabServer::stop() {
    running_ = false;
    cv_.notify_all();
    for (auto& t : worker_threads_) {
        if (t.joinable()) t.join();
    }
    worker_threads_.clear();
}

void WebGrabServer::acceptLoop() {
    while (running_) {
        auto client_socket = listener_->accept();
        if (client_socket) {
            worker_threads_.emplace_back(&WebGrabServer::handleClient, this, std::move(client_socket));
        }
    }
}

void WebGrabServer::handleClient(std::unique_ptr<TcpSocket> client_socket) {
    auto socket_shared = std::shared_ptr<TcpSocket>(std::move(client_socket));
    auto writer = std::make_unique<FlatBuffersResponseWriter>(socket_shared);

    while (writer->isConnected()) {
        std::vector<uint8_t> buffer;
        if (!client_socket->receive(buffer)) break;

        auto reader = std::make_unique<FlatBuffersRequestReader>(buffer.data(), buffer.size());

        if (reader->getType() == RequestType::Shutdown) {
            // Handle shutdown
            break;
        }

        auto job = processor_->processMessage(std::move(reader), writer.get());
        if (job) {
            job_worker_->addJob(std::move(job));
        }
    }
}