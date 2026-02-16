#include "JobWorker.h"
#include "IJob.h"
#include <iostream>

JobWorker::JobWorker(size_t numThreads) : stop_requested_(false) {
    for (size_t i = 0; i < numThreads; ++i) {
        workers_.emplace_back(&JobWorker::workerLoop, this);
    }
}

JobWorker::~JobWorker() {
    stop();
}

void JobWorker::addJob(std::unique_ptr<IJob> job) {
    std::lock_guard<std::mutex> lock(queue_mutex_);
    job_queue_.push(std::move(job));
    cv_.notify_one();
}

void JobWorker::stop() {
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        stop_requested_ = true;
    }
    cv_.notify_all();
    for (auto& w : workers_) {
        if (w.joinable()) w.join();
    }
}

void JobWorker::workerLoop() {
    while (true) {
        std::unique_ptr<IJob> job;
        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            cv_.wait(lock, [this]() { return stop_requested_ || !job_queue_.empty(); });
            if (stop_requested_ && job_queue_.empty()) break;
            job = std::move(job_queue_.front());
            job_queue_.pop();
        }
        job->execute();
    }
}