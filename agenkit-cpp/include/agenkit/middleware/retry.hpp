/**
 * @file retry.hpp
 * @brief Retry middleware with exponential backoff
 *
 * Implements automatic retries with configurable exponential backoff for transient failures.
 *
 * Features:
 * - Exponential backoff with jitter
 * - Configurable retry predicate
 * - Detailed metrics
 * - Thread-safe operations
 *
 * @example
 * @code
 * auto config = RetryConfig::builder()
 *     .max_attempts(3)
 *     .initial_backoff(std::chrono::milliseconds(100))
 *     .max_backoff(std::chrono::seconds(10))
 *     .build();
 *
 * auto retry_agent = std::make_shared<RetryMiddleware>(agent, config);
 * auto result = retry_agent->process(message).get();
 * @endcode
 */

#pragma once

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <chrono>
#include <functional>
#include <memory>
#include <random>
#include <thread>
#include <atomic>

namespace agenkit {
namespace middleware {

/// Retry configuration
struct RetryConfig {
    /// Maximum number of attempts (including initial attempt)
    uint32_t max_attempts = 3;

    /// Initial backoff duration
    std::chrono::milliseconds initial_backoff{100};

    /// Maximum backoff duration
    std::chrono::milliseconds max_backoff{10000};

    /// Backoff multiplier (must be > 1.0)
    double backoff_multiplier = 2.0;

    /// Whether to add jitter to backoff (recommended)
    bool enable_jitter = true;

    /// Custom retry predicate (defaults to retrying on all errors)
    std::function<bool(const core::AgentError&)> should_retry = nullptr;

    /// Validate configuration
    void validate() const {
        if (max_attempts < 1) {
            throw std::invalid_argument("max_attempts must be >= 1");
        }
        if (backoff_multiplier <= 1.0) {
            throw std::invalid_argument("backoff_multiplier must be > 1.0");
        }
        if (initial_backoff.count() <= 0) {
            throw std::invalid_argument("initial_backoff must be positive");
        }
        if (max_backoff < initial_backoff) {
            throw std::invalid_argument("max_backoff must be >= initial_backoff");
        }
    }

    /// Builder for fluent configuration
    class Builder;

    static Builder builder();
};

/// Builder implementation for RetryConfig
class RetryConfig::Builder {
public:
    Builder() = default;

    Builder& max_attempts(uint32_t n) {
        config_.max_attempts = n;
        return *this;
    }

    Builder& initial_backoff(std::chrono::milliseconds duration) {
        config_.initial_backoff = duration;
        return *this;
    }

    Builder& max_backoff(std::chrono::milliseconds duration) {
        config_.max_backoff = duration;
        return *this;
    }

    Builder& backoff_multiplier(double multiplier) {
        config_.backoff_multiplier = multiplier;
        return *this;
    }

    Builder& enable_jitter(bool enable) {
        config_.enable_jitter = enable;
        return *this;
    }

    Builder& should_retry(std::function<bool(const core::AgentError&)> predicate) {
        config_.should_retry = std::move(predicate);
        return *this;
    }

    RetryConfig build() {
        config_.validate();
        return config_;
    }

private:
    RetryConfig config_;
};

inline RetryConfig::Builder RetryConfig::builder() {
    return Builder();
}

/// Retry metrics
struct RetryMetrics {
    std::atomic<uint64_t> total_attempts{0};
    std::atomic<uint64_t> total_retries{0};
    std::atomic<uint64_t> successful_on_retry{0};
    std::atomic<uint64_t> failed_after_retries{0};
    std::atomic<uint64_t> total_backoff_ms{0};

    /// Get snapshot of current metrics
    struct Snapshot {
        uint64_t total_attempts;
        uint64_t total_retries;
        uint64_t successful_on_retry;
        uint64_t failed_after_retries;
        uint64_t total_backoff_ms;
        double avg_retries_per_request;
        double success_rate_after_retry;
    };

    Snapshot snapshot() const {
        auto attempts = total_attempts.load();
        auto retries = total_retries.load();
        auto success = successful_on_retry.load();
        auto failed = failed_after_retries.load();

        return Snapshot{
            attempts,
            retries,
            success,
            failed,
            total_backoff_ms.load(),
            attempts > 0 ? static_cast<double>(retries) / attempts : 0.0,
            retries > 0 ? static_cast<double>(success) / retries : 0.0
        };
    }
};

/// Retry middleware - wraps an agent with retry logic
class RetryMiddleware : public core::Agent {
public:
    /// Create retry middleware
    ///
    /// @param agent Underlying agent to wrap
    /// @param config Retry configuration
    RetryMiddleware(
        std::shared_ptr<core::Agent> agent,
        RetryConfig config = RetryConfig()
    ) : agent_(std::move(agent)), config_(std::move(config)) {
        config_.validate();

        // Use default retry predicate if none provided
        if (!config_.should_retry) {
            config_.should_retry = [](const core::AgentError&) { return true; };
        }
    }

    std::string name() const override {
        return "retry(" + agent_->name() + ")";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /// Get current metrics
    const RetryMetrics& metrics() const {
        return metrics_;
    }

    /// Get configuration
    const RetryConfig& config() const {
        return config_;
    }

private:
    std::shared_ptr<core::Agent> agent_;
    RetryConfig config_;
    mutable RetryMetrics metrics_;
    std::mt19937 rng_{std::random_device{}()};

    /// Calculate backoff with jitter
    std::chrono::milliseconds calculate_backoff(uint32_t attempt);
};

} // namespace middleware
} // namespace agenkit
