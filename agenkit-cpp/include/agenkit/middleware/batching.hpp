/**
 * @file batching.hpp
 * @brief Batching middleware for aggregating multiple requests
 *
 * Collects multiple requests and processes them together in a single batch,
 * reducing overhead for operations that benefit from batch processing.
 *
 * Features:
 * - Configurable batch size and wait time
 * - Queue size limiting with backpressure
 * - Parallel batch processing
 * - Comprehensive metrics tracking
 * - Graceful shutdown with pending batch flush
 * - Thread-safe operations
 *
 * Use Cases:
 * - LLM APIs with batch endpoints (OpenAI, Anthropic)
 * - Database batch operations (inserts, updates)
 * - Vector database operations (batch embeddings)
 * - Analytics event aggregation
 *
 * @example
 * @code
 * auto config = BatchingConfig::builder()
 *     .max_batch_size(10)
 *     .max_wait_time(std::chrono::milliseconds(100))
 *     .max_queue_size(1000)
 *     .build();
 *
 * auto batching_agent = std::make_shared<BatchingMiddleware>(agent, config);
 * auto result = batching_agent->process(message).get();
 * @endcode
 */

#pragma once

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <chrono>
#include <memory>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <queue>
#include <vector>
#include <future>
#include <optional>

namespace agenkit {
namespace middleware {

/// Batching metrics
struct BatchingMetrics {
    /// Total number of requests processed
    std::atomic<uint64_t> total_requests{0};

    /// Total number of batches processed
    std::atomic<uint64_t> total_batches{0};

    /// Number of successful batches (all requests succeeded)
    std::atomic<uint64_t> successful_batches{0};

    /// Number of failed batches (all requests failed)
    std::atomic<uint64_t> failed_batches{0};

    /// Number of partial batches (mixed success/failure)
    std::atomic<uint64_t> partial_batches{0};

    /// Total wait time in milliseconds
    std::atomic<uint64_t> total_wait_time_ms{0};

    /// Minimum batch size observed
    std::atomic<size_t> min_batch_size{SIZE_MAX};

    /// Maximum batch size observed
    std::atomic<size_t> max_batch_size{0};

    /// Total batch size (for calculating average)
    std::atomic<uint64_t> total_batch_size{0};

    /// Calculate average batch size
    double avg_batch_size() const {
        uint64_t batches = total_batches.load();
        if (batches == 0) return 0.0;
        return static_cast<double>(total_batch_size.load()) / batches;
    }

    /// Calculate average wait time per request (milliseconds)
    double avg_wait_time_ms() const {
        uint64_t requests = total_requests.load();
        if (requests == 0) return 0.0;
        return static_cast<double>(total_wait_time_ms.load()) / requests;
    }

    /// Calculate throughput improvement (requests / batches)
    double throughput_improvement() const {
        uint64_t batches = total_batches.load();
        if (batches == 0) return 1.0;
        return static_cast<double>(total_requests.load()) / batches;
    }
};

/// Batching configuration
struct BatchingConfig {
    /// Maximum number of requests in a batch
    size_t max_batch_size = 10;

    /// Maximum time to wait for batch to fill
    std::chrono::milliseconds max_wait_time{100};

    /// Maximum queue size (total pending requests)
    size_t max_queue_size = 1000;

    /// Validate configuration
    void validate() const {
        if (max_batch_size < 1) {
            throw std::invalid_argument("max_batch_size must be >= 1");
        }
        if (max_wait_time.count() <= 0) {
            throw std::invalid_argument("max_wait_time must be positive");
        }
        if (max_queue_size < max_batch_size) {
            throw std::invalid_argument("max_queue_size must be >= max_batch_size");
        }
    }

    /// Builder for fluent configuration
    class Builder;

    static Builder builder();
};

/// Builder implementation for BatchingConfig
class BatchingConfig::Builder {
public:
    Builder() = default;

    Builder& max_batch_size(size_t n) {
        config_.max_batch_size = n;
        return *this;
    }

    Builder& max_wait_time(std::chrono::milliseconds duration) {
        config_.max_wait_time = duration;
        return *this;
    }

    Builder& max_queue_size(size_t n) {
        config_.max_queue_size = n;
        return *this;
    }

    BatchingConfig build() {
        config_.validate();
        return config_;
    }

private:
    BatchingConfig config_;
};

inline BatchingConfig::Builder BatchingConfig::builder() {
    return Builder();
}

/// Batching middleware that aggregates multiple requests
class BatchingMiddleware : public core::Agent {
public:
    /**
     * @brief Construct batching middleware
     * @param agent The wrapped agent
     * @param config Batching configuration
     */
    BatchingMiddleware(std::shared_ptr<core::Agent> agent, BatchingConfig config);

    /**
     * @brief Destructor - ensures graceful shutdown
     */
    ~BatchingMiddleware() override;

    // Agent interface
    std::string name() const override;
    std::future<core::Result<core::Message, core::AgentError>> process(core::Message message) override;

    /**
     * @brief Flush all pending batches and wait for completion
     */
    void flush();

    /**
     * @brief Get current metrics
     */
    const BatchingMetrics& metrics() const { return metrics_; }

    /**
     * @brief Get configuration
     */
    const BatchingConfig& config() const { return config_; }

private:
    struct PendingRequest {
        core::Message message;
        std::promise<core::Result<core::Message, core::AgentError>> promise;
        std::chrono::steady_clock::time_point enqueued_at;
    };

    std::shared_ptr<core::Agent> inner_;
    BatchingConfig config_;
    BatchingMetrics metrics_;

    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::queue<PendingRequest> queue_;

    std::thread processor_thread_;
    std::atomic<bool> shutdown_{false};

    void process_loop();
    void process_batch(std::vector<PendingRequest>&& batch);
    bool should_flush() const;
};

}  // namespace middleware
}  // namespace agenkit
