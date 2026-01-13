/**
 * @file thread_pool.cpp
 * @brief Implementation of ThreadPool
 */

#include "agenkit/infrastructure/thread_pool.hpp"

namespace agenkit {
namespace infrastructure {

ThreadPool::ThreadPool(size_t num_threads)
    : stop_(false)
{
    if (num_threads == 0) {
        throw std::invalid_argument("ThreadPool must have at least 1 thread");
    }

    workers_.reserve(num_threads);

    // Create worker threads
    for (size_t i = 0; i < num_threads; ++i) {
        workers_.emplace_back([this] { worker_thread(); });
    }
}

ThreadPool::~ThreadPool() {
    {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        stop_ = true;
    }

    // Wake up all threads
    condition_.notify_all();

    // Wait for all threads to finish
    for (std::thread& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
}

void ThreadPool::worker_thread() {
    while (true) {
        std::function<void()> task;

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);

            // Wait for task or stop signal
            condition_.wait(lock, [this] {
                return stop_.load() || !tasks_.empty();
            });

            // Exit if stopped and no more tasks
            if (stop_ && tasks_.empty()) {
                return;
            }

            // Get task from queue
            if (!tasks_.empty()) {
                task = std::move(tasks_.front());
                tasks_.pop();
            }
        }

        // Execute task outside the lock
        if (task) {
            task();
        }
    }
}

ThreadPool& global_thread_pool() {
    static ThreadPool pool(std::thread::hardware_concurrency());
    return pool;
}

} // namespace infrastructure
} // namespace agenkit
