/**
 * @file rate_limiter.hpp
 * @brief Rate limiter middleware using token bucket algorithm
 *
 * Implements token bucket rate limiting to control request throughput.
 *
 * Features:
 * - Token bucket algorithm with configurable rate and capacity
 * - Burst capacity support
 * - Wait vs reject modes
 * - Detailed metrics
 * - Thread-safe token management
 *
 * @example
 * @code
 * auto config = RateLimiterConfig::builder()
 *     .rate_per_second(10.0)
 *     .capacity(20)
 *     .tokens_per_request(1)
 *     .build();
 *
 * auto limiter_agent = std::make_shared<RateLimiterMiddleware>(agent, config);
 * auto result = limiter_agent->process(message).get();
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

namespace agenkit {
namespace middleware {

/// Rate limit error
class RateLimitError : public core::AgentError {
public:
    explicit RateLimitError(double retry_after_seconds)
        : core::AgentError(
            core::AgentErrorType::ProcessingError,
            "Rate limit exceeded. Retry after " +
            std::to_string(retry_after_seconds) + "s"
          ),
          retry_after_seconds_(retry_after_seconds) {}

    double retry_after_seconds() const { return retry_after_seconds_; }

private:
    double retry_after_seconds_;
};

/// Rate limiter configuration
struct RateLimiterConfig {
    /// Token generation rate (tokens per second)
    double rate_per_second = 10.0;

    /// Maximum token capacity (burst size)
    uint32_t capacity = 20;

    /// Tokens consumed per request
    uint32_t tokens_per_request = 1;

    /// Whether to wait for tokens (true) or reject immediately (false)
    bool wait_for_tokens = true;

    /// Maximum wait time if wait_for_tokens is true
    std::chrono::milliseconds max_wait_time{30000};  // 30 seconds

    /// Validate configuration
    void validate() const {
        if (rate_per_second <= 0.0) {
            throw std::invalid_argument("rate_per_second must be positive");
        }
        if (capacity < 1) {
            throw std::invalid_argument("capacity must be >= 1");
        }
        if (tokens_per_request < 1) {
            throw std::invalid_argument("tokens_per_request must be >= 1");
        }
        if (tokens_per_request > capacity) {
            throw std::invalid_argument("tokens_per_request must be <= capacity");
        }
        if (max_wait_time.count() <= 0) {
            throw std::invalid_argument("max_wait_time must be positive");
        }
    }

    /// Builder for fluent configuration
    class Builder;

    static Builder builder();
};

/// Builder implementation for RateLimiterConfig
class RateLimiterConfig::Builder {
public:
    Builder() = default;

    Builder& rate_per_second(double rate) {
        config_.rate_per_second = rate;
        return *this;
    }

    Builder& capacity(uint32_t n) {
        config_.capacity = n;
        return *this;
    }

    Builder& tokens_per_request(uint32_t n) {
        config_.tokens_per_request = n;
        return *this;
    }

    Builder& wait_for_tokens(bool wait) {
        config_.wait_for_tokens = wait;
        return *this;
    }

    Builder& max_wait_time(std::chrono::milliseconds duration) {
        config_.max_wait_time = duration;
        return *this;
    }

    RateLimiterConfig build() {
        config_.validate();
        return config_;
    }

private:
    RateLimiterConfig config_;
};

inline RateLimiterConfig::Builder RateLimiterConfig::builder() {
    return Builder();
}

/// Rate limiter metrics
struct RateLimiterMetrics {
    std::atomic<uint64_t> total_requests{0};
    std::atomic<uint64_t> allowed_requests{0};
    std::atomic<uint64_t> rejected_requests{0};
    std::atomic<uint64_t> waited_requests{0};
    std::atomic<uint64_t> total_wait_time_ms{0};

    /// Get snapshot of current metrics
    struct Snapshot {
        uint64_t total_requests;
        uint64_t allowed_requests;
        uint64_t rejected_requests;
        uint64_t waited_requests;
        uint64_t total_wait_time_ms;
        double current_tokens;
        double rejection_rate;
        double avg_wait_time_ms;
    };

    Snapshot snapshot(double current_tokens) const {
        auto total = total_requests.load();
        auto rejected = rejected_requests.load();
        auto waited = waited_requests.load();
        auto wait_time = total_wait_time_ms.load();

        return Snapshot{
            total,
            allowed_requests.load(),
            rejected,
            waited,
            wait_time,
            current_tokens,
            total > 0 ? static_cast<double>(rejected) / total : 0.0,
            waited > 0 ? static_cast<double>(wait_time) / waited : 0.0
        };
    }
};

/// Rate limiter middleware - wraps an agent with token bucket rate limiting
class RateLimiterMiddleware : public core::Agent {
public:
    /// Create rate limiter middleware
    ///
    /// @param agent Underlying agent to wrap
    /// @param config Rate limiter configuration
    RateLimiterMiddleware(
        std::shared_ptr<core::Agent> agent,
        RateLimiterConfig config = RateLimiterConfig()
    ) : agent_(std::move(agent)),
        config_(std::move(config)),
        tokens_(static_cast<double>(config.capacity)),
        last_refill_(std::chrono::steady_clock::now()) {
        config_.validate();
    }

    std::string name() const override {
        return "rate_limiter(" + agent_->name() + ")";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /// Get current metrics
    const RateLimiterMetrics& metrics() const {
        return metrics_;
    }

    /// Get configuration
    const RateLimiterConfig& config() const {
        return config_;
    }

    /// Get current token count
    double current_tokens() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return tokens_;
    }

private:
    std::shared_ptr<core::Agent> agent_;
    RateLimiterConfig config_;
    mutable RateLimiterMetrics metrics_;

    // Token bucket state (protected by mutex)
    mutable std::mutex mutex_;
    double tokens_;
    std::chrono::steady_clock::time_point last_refill_;

    /// Refill tokens based on elapsed time
    void refill_tokens();

    /// Try to consume tokens (returns true if successful)
    bool try_consume_tokens(uint32_t tokens_needed);

    /// Wait for tokens to become available
    bool wait_for_available_tokens(uint32_t tokens_needed);
};

} // namespace middleware
} // namespace agenkit
