/**
 * @file circuit_breaker.cpp
 * @brief Circuit breaker middleware implementation
 */

#include "agenkit/middleware/circuit_breaker.hpp"

namespace agenkit {
namespace middleware {

bool CircuitBreakerMiddleware::should_attempt_recovery() const {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        now - last_failure_time_
    );
    return elapsed >= config_.recovery_timeout;
}

void CircuitBreakerMiddleware::record_success() {
    std::lock_guard<std::mutex> lock(mutex_);

    metrics_.successful_requests++;

    switch (state_) {
        case CircuitState::CLOSED:
            // Reset failure count on success
            failure_count_ = 0;
            break;

        case CircuitState::HALF_OPEN:
            // Count successes in half-open state
            success_count_++;
            if (success_count_ >= config_.success_threshold) {
                // Enough successes - close the circuit
                transition_to_state(CircuitState::CLOSED);
                failure_count_ = 0;
                success_count_ = 0;
            }
            break;

        case CircuitState::OPEN:
            // Shouldn't happen (we reject in OPEN state)
            break;
    }
}

void CircuitBreakerMiddleware::record_failure() {
    std::lock_guard<std::mutex> lock(mutex_);

    metrics_.failed_requests++;
    last_failure_time_ = std::chrono::steady_clock::now();

    switch (state_) {
        case CircuitState::CLOSED:
            // Count failures in closed state
            failure_count_++;
            if (failure_count_ >= config_.failure_threshold) {
                // Too many failures - open the circuit
                transition_to_state(CircuitState::OPEN);
            }
            break;

        case CircuitState::HALF_OPEN:
            // Any failure in half-open immediately reopens circuit
            transition_to_state(CircuitState::OPEN);
            failure_count_ = config_.failure_threshold;
            success_count_ = 0;
            break;

        case CircuitState::OPEN:
            // Already open
            break;
    }
}

void CircuitBreakerMiddleware::transition_to_state(CircuitState new_state) {
    if (state_ != new_state) {
        auto old_state = state_;
        state_ = new_state;

        // Bumps both the scalar total and the keyed per-transition count (#791).
        metrics_.record_state_change(old_state, new_state);

        auto now = std::chrono::system_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()
        ).count();
        metrics_.last_state_change_ms = ms;
    }
}

std::future<core::Result<core::Message, core::AgentError>>
CircuitBreakerMiddleware::process(core::Message message) {
    metrics_.total_requests++;

    // Check current state and decide what to do
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (state_ == CircuitState::OPEN) {
            // Check if we should attempt recovery
            if (should_attempt_recovery()) {
                // Transition to half-open to test recovery
                transition_to_state(CircuitState::HALF_OPEN);
                success_count_ = 0;
            } else {
                // Still in cooldown - reject request
                metrics_.rejected_requests++;
                return core::make_ready_future(
                    core::Result<core::Message, core::AgentError>::err(
                        CircuitBreakerError(failure_count_)
                    )
                );
            }
        }
    }

    // Try the request
    auto future = agent_->process(message);
    auto result = future.get();

    // Record success or failure
    if (result.is_ok()) {
        record_success();
    } else {
        record_failure();
    }

    return core::make_ready_future(std::move(result));
}

} // namespace middleware
} // namespace agenkit
