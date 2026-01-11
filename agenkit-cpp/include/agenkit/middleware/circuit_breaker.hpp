/**
 * @file circuit_breaker.hpp
 * @brief Circuit breaker middleware for cascading failure prevention
 *
 * Implements three-state circuit breaker pattern:
 * - CLOSED: Normal operation, requests pass through
 * - OPEN: Failures exceeded threshold, requests fail fast
 * - HALF_OPEN: Testing if service recovered, limited requests allowed
 *
 * Features:
 * - Three-state finite state machine
 * - Configurable failure/success thresholds
 * - Recovery timeout
 * - Detailed metrics with state transition tracking
 * - Thread-safe state management
 *
 * @example
 * @code
 * auto config = CircuitBreakerConfig::builder()
 *     .failure_threshold(5)
 *     .success_threshold(2)
 *     .recovery_timeout(std::chrono::seconds(60))
 *     .build();
 *
 * auto breaker_agent = std::make_shared<CircuitBreakerMiddleware>(agent, config);
 * auto result = breaker_agent->process(message).get();
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

/// Circuit breaker state
enum class CircuitState {
    CLOSED,      ///< Normal operation
    OPEN,        ///< Failing fast
    HALF_OPEN    ///< Testing recovery
};

/// Convert state to string
inline const char* state_to_string(CircuitState state) {
    switch (state) {
        case CircuitState::CLOSED: return "CLOSED";
        case CircuitState::OPEN: return "OPEN";
        case CircuitState::HALF_OPEN: return "HALF_OPEN";
        default: return "UNKNOWN";
    }
}

/// Circuit breaker error
class CircuitBreakerError : public core::AgentError {
public:
    explicit CircuitBreakerError(int failure_count)
        : core::AgentError(
            core::AgentErrorType::ProcessingError,
            "Circuit breaker is OPEN (failed " + std::to_string(failure_count) + " times)"
          ) {}
};

/// Circuit breaker configuration
struct CircuitBreakerConfig {
    /// Number of failures before opening circuit
    uint32_t failure_threshold = 5;

    /// Number of successes in HALF_OPEN to close circuit
    uint32_t success_threshold = 2;

    /// How long to wait before transitioning from OPEN to HALF_OPEN
    std::chrono::milliseconds recovery_timeout{60000};  // 60 seconds

    /// Validate configuration
    void validate() const {
        if (failure_threshold < 1) {
            throw std::invalid_argument("failure_threshold must be >= 1");
        }
        if (success_threshold < 1) {
            throw std::invalid_argument("success_threshold must be >= 1");
        }
        if (recovery_timeout.count() <= 0) {
            throw std::invalid_argument("recovery_timeout must be positive");
        }
    }

    /// Builder for fluent configuration
    class Builder;

    static Builder builder();
};

/// Builder implementation for CircuitBreakerConfig
class CircuitBreakerConfig::Builder {
public:
    Builder() = default;

    Builder& failure_threshold(uint32_t n) {
        config_.failure_threshold = n;
        return *this;
    }

    Builder& success_threshold(uint32_t n) {
        config_.success_threshold = n;
        return *this;
    }

    Builder& recovery_timeout(std::chrono::milliseconds duration) {
        config_.recovery_timeout = duration;
        return *this;
    }

    CircuitBreakerConfig build() {
        config_.validate();
        return config_;
    }

private:
    CircuitBreakerConfig config_;
};

inline CircuitBreakerConfig::Builder CircuitBreakerConfig::builder() {
    return Builder();
}

/// Circuit breaker metrics
struct CircuitBreakerMetrics {
    std::atomic<uint64_t> total_requests{0};
    std::atomic<uint64_t> successful_requests{0};
    std::atomic<uint64_t> failed_requests{0};
    std::atomic<uint64_t> rejected_requests{0};
    std::atomic<uint64_t> state_transitions{0};
    std::atomic<uint64_t> last_state_change_ms{0};

    /// Get snapshot of current metrics
    struct Snapshot {
        uint64_t total_requests;
        uint64_t successful_requests;
        uint64_t failed_requests;
        uint64_t rejected_requests;
        uint64_t state_transitions;
        uint64_t last_state_change_ms;
        CircuitState current_state;
        double success_rate;
        double rejection_rate;
    };

    Snapshot snapshot(CircuitState current_state) const {
        auto total = total_requests.load();
        auto success = successful_requests.load();
        auto rejected = rejected_requests.load();

        return Snapshot{
            total,
            success,
            failed_requests.load(),
            rejected,
            state_transitions.load(),
            last_state_change_ms.load(),
            current_state,
            total > 0 ? static_cast<double>(success) / total : 0.0,
            total > 0 ? static_cast<double>(rejected) / total : 0.0
        };
    }
};

/// Circuit breaker middleware - wraps an agent with circuit breaker logic
class CircuitBreakerMiddleware : public core::Agent {
public:
    /// Create circuit breaker middleware
    ///
    /// @param agent Underlying agent to wrap
    /// @param config Circuit breaker configuration
    CircuitBreakerMiddleware(
        std::shared_ptr<core::Agent> agent,
        CircuitBreakerConfig config = CircuitBreakerConfig()
    ) : agent_(std::move(agent)),
        config_(std::move(config)),
        state_(CircuitState::CLOSED),
        failure_count_(0),
        success_count_(0) {
        config_.validate();
        last_failure_time_ = std::chrono::steady_clock::time_point::min();
    }

    std::string name() const override {
        return "circuit_breaker(" + agent_->name() + ")";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /// Get current state
    CircuitState state() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return state_;
    }

    /// Get current metrics
    const CircuitBreakerMetrics& metrics() const {
        return metrics_;
    }

    /// Get configuration
    const CircuitBreakerConfig& config() const {
        return config_;
    }

private:
    std::shared_ptr<core::Agent> agent_;
    CircuitBreakerConfig config_;
    mutable CircuitBreakerMetrics metrics_;

    // State management (protected by mutex)
    mutable std::mutex mutex_;
    CircuitState state_;
    uint32_t failure_count_;
    uint32_t success_count_;
    std::chrono::steady_clock::time_point last_failure_time_;

    /// Check if we should attempt recovery
    bool should_attempt_recovery() const;

    /// Record success and potentially change state
    void record_success();

    /// Record failure and potentially change state
    void record_failure();

    /// Transition to a new state
    void transition_to_state(CircuitState new_state);
};

} // namespace middleware
} // namespace agenkit
