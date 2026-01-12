/**
 * @file batching.cpp
 * @brief Batching middleware implementation
 */

#include "agenkit/middleware/batching.hpp"
#include <algorithm>
#include <stdexcept>

namespace agenkit {
namespace middleware {

BatchingMiddleware::BatchingMiddleware(
    std::shared_ptr<core::Agent> agent,
    BatchingConfig config)
    : inner_(std::move(agent)), config_(std::move(config)) {
    config_.validate();

    // Start background processor thread
    processor_thread_ = std::thread(&BatchingMiddleware::process_loop, this);
}

BatchingMiddleware::~BatchingMiddleware() {
    shutdown_.store(true);
    queue_cv_.notify_all();

    if (processor_thread_.joinable()) {
        processor_thread_.join();
    }
}

std::string BatchingMiddleware::name() const {
    return inner_->name();
}

std::future<core::Result<core::Message, core::AgentError>> BatchingMiddleware::process(core::Message message) {
    auto promise = std::make_shared<std::promise<core::Result<core::Message, core::AgentError>>>();
    auto future = promise->get_future();

    {
        std::unique_lock<std::mutex> lock(queue_mutex_);

        // Check if queue is full (backpressure)
        if (queue_.size() >= config_.max_queue_size) {
            core::AgentError error(core::AgentErrorType::Internal,
                "batch queue full: " + std::to_string(queue_.size()) +
                " requests pending (max: " + std::to_string(config_.max_queue_size) + ")");
            promise->set_value(core::Result<core::Message, core::AgentError>::err(std::move(error)));
            return future;
        }

        // Add to queue
        PendingRequest req{
            std::move(message),
            std::move(*promise),
            std::chrono::steady_clock::now()
        };
        queue_.push(std::move(req));
        metrics_.total_requests.fetch_add(1);
    }

    // Notify processor thread
    queue_cv_.notify_one();

    return future;
}

void BatchingMiddleware::flush() {
    // Wait for queue to drain
    while (true) {
        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            if (queue_.empty()) {
                break;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void BatchingMiddleware::process_loop() {
    auto batch_start_time = std::chrono::steady_clock::time_point{};
    std::vector<PendingRequest> batch;

    while (!shutdown_.load()) {
        std::unique_lock<std::mutex> lock(queue_mutex_);

        // Wait for items or timeout
        if (queue_.empty()) {
            queue_cv_.wait_for(lock, std::chrono::milliseconds(10));
        }

        // Check if we should process batch
        bool should_process = false;
        if (!queue_.empty()) {
            if (batch.empty()) {
                batch_start_time = std::chrono::steady_clock::now();
            }

            // Move items from queue to batch
            while (!queue_.empty() && batch.size() < config_.max_batch_size) {
                batch.push_back(std::move(queue_.front()));
                queue_.pop();
            }

            // Check flush conditions
            if (batch.size() >= config_.max_batch_size) {
                should_process = true;
            } else {
                auto elapsed = std::chrono::steady_clock::now() - batch_start_time;
                if (elapsed >= config_.max_wait_time) {
                    should_process = true;
                }
            }
        }

        // Process batch if conditions met
        if (should_process && !batch.empty()) {
            lock.unlock();  // Release lock before processing
            process_batch(std::move(batch));
            batch.clear();
            batch_start_time = std::chrono::steady_clock::time_point{};
        }
    }

    // Process remaining items on shutdown
    if (!batch.empty()) {
        process_batch(std::move(batch));
    }
}

void BatchingMiddleware::process_batch(std::vector<PendingRequest>&& batch) {
    size_t batch_size = batch.size();
    if (batch_size == 0) return;

    metrics_.total_batches.fetch_add(1);
    metrics_.total_batch_size.fetch_add(batch_size);

    // Update min/max batch size
    size_t current_min = metrics_.min_batch_size.load();
    while (batch_size < current_min) {
        if (metrics_.min_batch_size.compare_exchange_weak(current_min, batch_size)) {
            break;
        }
    }

    size_t current_max = metrics_.max_batch_size.load();
    while (batch_size > current_max) {
        if (metrics_.max_batch_size.compare_exchange_weak(current_max, batch_size)) {
            break;
        }
    }

    // Process requests in parallel using std::async
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    futures.reserve(batch_size);

    for (auto& req : batch) {
        // Calculate wait time
        auto wait_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - req.enqueued_at
        ).count();
        metrics_.total_wait_time_ms.fetch_add(wait_time_ms);

        // Launch async task - copy message for async call
        auto msg = req.message;
        futures.push_back(std::async(std::launch::async, [this, msg]() mutable {
            return inner_->process(std::move(msg)).get();
        }));
    }

    // Collect results
    size_t successes = 0;
    size_t failures = 0;

    for (size_t i = 0; i < batch_size; ++i) {
        try {
            auto result = futures[i].get();
            if (result.is_ok()) {
                successes++;
            } else {
                failures++;
            }
            batch[i].promise.set_value(std::move(result));
        } catch (...) {
            // Unexpected exception - wrap as error
            core::AgentError error(core::AgentErrorType::ProcessingError, "unexpected exception during batch processing");
            batch[i].promise.set_value(core::Result<core::Message, core::AgentError>::err(std::move(error)));
            failures++;
        }
    }

    // Update batch outcome metrics
    if (failures == 0) {
        metrics_.successful_batches.fetch_add(1);
    } else if (successes == 0) {
        metrics_.failed_batches.fetch_add(1);
    } else {
        metrics_.partial_batches.fetch_add(1);
    }
}

}  // namespace middleware
}  // namespace agenkit
