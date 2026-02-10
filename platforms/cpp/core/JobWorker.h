#pragma once
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <vector>
#include <memory>

class IJob;

class JobWorker {
public:
    JobWorker(size_t numThreads);
    ~JobWorker();

    void addJob(std::unique_ptr<IJob> job);
    void stop();

private:
    std::vector<std::thread> workers_;
    std::queue<std::unique_ptr<IJob>> job_queue_;
    std::mutex queue_mutex_;
    std::condition_variable cv_;
    bool stop_requested_;

    void workerLoop();
};