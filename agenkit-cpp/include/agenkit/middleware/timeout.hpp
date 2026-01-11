/**
 * @file timeout.hpp
 * @brief Timeout middleware for time-based request cancellation
 *
 * Implements configurable timeout with detailed metrics.
 *
 * Features:
 * - Configurable default timeout
 * - Method-specific timeouts (via message metadata)
 * - Request duration tracking
 * - Thread-safe metrics
 *
 * @example
 * @code
 * auto config = TimeoutConfig::builder()
 *     .default_timeout(std::chrono::seconds(30))
 *     .build();
 *
 * auto timeout_agent = std::make_shared<TimeoutMiddleware>(agent, config);
 * auto result = timeout_agent->process(message).get();
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
#include <shared_mutex>
#include <map>

namespace agenkit {
namespace middleware {

/// Timeout error
class TimeoutError : public core::AgentError {
public:
    explicit TimeoutError(std::chrono::milliseconds duration)
        : core::AgentError(
            core::AgentErrorType::Timeout,
            "Request timed out after " + std::to_string(duration.count() / 1000.0) + "s"
          ) {}
};

/// Timeout configuration
struct TimeoutConfig {
    /// Default timeout for all requests
    std::chrono::milliseconds default_timeout{30000};  // 30 seconds

    /// Method-specific timeouts (optional)
    std::map<std::string, std::chrono::milliseconds> method_timeouts;

    /// Validate configuration
    void validate() const {
        if (default_timeout.count() <= 0) {
            throw std::invalid_argument("default_timeout must be positive");
        }
        for (const auto& [method, timeout] : method_timeouts) {
            if (timeout.count() <= 0) {
                throw std::invalid_argument(
                    "method_timeout for '" + method + "' must be positive"
                );
            }
        }
    }

    /// Builder for fluent configuration
    class Builder;

    static Builder builder();
};

/// Builder implementation for TimeoutConfig
class TimeoutConfig::Builder {
public:
    Builder() = default;

    Builder& default_timeout(std::chrono::milliseconds duration) {
        config_.default_timeout = duration;
        return *this;
    }

    Builder& method_timeout(const std::string& method, std::chrono::milliseconds duration) {
        config_.method_timeouts[method] = duration;
        return *this;
    }

    TimeoutConfig build() {
        config_.validate();
        return config_;
    }

private:
    TimeoutConfig config_;
};

inline TimeoutConfig::Builder TimeoutConfig::builder() {
    return Builder();
}

/// Timeout metrics
struct TimeoutMetrics {
    std::atomic<uint64_t> total_requests{0};
    std::atomic<uint64_t> successful_requests{0};
    std::atomic<uint64_t> timed_out_requests{0};
    std::atomic<uint64_t> failed_requests{0};
    std::atomic<uint64_t> total_duration_ms{0};
    std::atomic<uint64_t> min_duration_ms{std::numeric_limits<uint64_t>::max()};
    std::atomic<uint64_t> max_duration_ms{0};

    /// Get snapshot of current metrics
    struct Snapshot {
        uint64_t total_requests;
        uint64_t successful_requests;
        uint64_t timed_out_requests;
        uint64_t failed_requests;
        uint64_t total_duration_ms;
        uint64_t min_duration_ms;
        uint64_t max_duration_ms;
        double avg_duration_ms;
        double timeout_rate;
        double error_rate;
    };

    Snapshot snapshot() const {
        auto total = total_requests.load();
        auto timeouts = timed_out_requests.load();
        auto failures = failed_requests.load();
        auto duration = total_duration_ms.load();

        return Snapshot{
            total,
            successful_requests.load(),
            timeouts,
            failures,
            duration,
            min_duration_ms.load(),
            max_duration_ms.load(),
            total > 0 ? static_cast<double>(duration) / total : 0.0,
            total > 0 ? static_cast<double>(timeouts) / total : 0.0,
            total > 0 ? static_cast<double>(failures) / total : 0.0
        };
    }

    void update_duration(uint64_t duration_ms) {
        total_duration_ms += duration_ms;

        // Update min (using compare_exchange loop for atomicity)
        uint64_t current_min = min_duration_ms.load();
        while (duration_ms < current_min &&
               !min_duration_ms.compare_exchange_weak(current_min, duration_ms)) {
            // Loop until update succeeds
        }

        // Update max
        uint64_t current_max = max_duration_ms.load();
        while (duration_ms > current_max &&
               !max_duration_ms.compare_exchange_weak(current_max, duration_ms)) {
            // Loop until update succeeds
        }
    }
};

/// Timeout middleware - wraps an agent with timeout logic
class TimeoutMiddleware : public core::Agent {
public:
    /// Create timeout middleware
    ///
    /// @param agent Underlying agent to wrap
    /// @param config Timeout configuration
    TimeoutMiddleware(
        std::shared_ptr<core::Agent> agent,
        TimeoutConfig config = TimeoutConfig()
    ) : agent_(std::move(agent)), config_(std::move(config)) {
        config_.validate();
    }

    std::string name() const override {
        return "timeout(" + agent_->name() + ")";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /// Get current metrics
    const TimeoutMetrics& metrics() const {
        return metrics_;
    }

    /// Get configuration
    const TimeoutConfig& config() const {
        return config_;
    }

private:
    std::shared_ptr<core::Agent> agent_;
    TimeoutConfig config_;
    mutable TimeoutMetrics metrics_;

    /// Get timeout for a specific message
    std::chrono::milliseconds get_timeout_for_message(const core::Message& message) const;
};

} // namespace middleware
} // namespace agenkit
