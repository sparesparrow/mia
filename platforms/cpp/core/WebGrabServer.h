#pragma once
#include <memory>
#include <string>
#include <thread>
#include <vector>
#include <mutex>
#include <condition_variable>

class MessageQueueProcessor;
class JobWorker;

class WebGrabServer {
private:
    std::unique_ptr<MessageQueueProcessor> processor_;
    std::unique_ptr<JobWorker> job_worker_;
    std::unique_ptr<class TcpListener> listener_;
    std::vector<std::thread> worker_threads_;
    bool running_;
    std::mutex mtx_;
    std::condition_variable cv_;

public:
    WebGrabServer(uint16_t port, const std::string& workingDir);
    ~WebGrabServer();

    bool start();
    void stop();

private:
    void acceptLoop();
    void handleClient(std::unique_ptr<class TcpSocket> client_socket);
};