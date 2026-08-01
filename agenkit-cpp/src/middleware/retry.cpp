/**
 * @file retry.cpp
 * @brief Retry middleware implementation
 */

#include "agenkit/middleware/retry.hpp"
#include <cmath>
#include <algorithm>

namespace agenkit {
namespace middleware {

std::chrono::milliseconds RetryMiddleware::calculate_backoff(uint32_t attempt) {
    // Calculate exponential backoff: initial * (multiplier ^ attempt)
    double backoff_ms = config_.initial_backoff.count() *
                        std::pow(config_.backoff_multiplier, static_cast<double>(attempt));

    // Clamp to max_backoff
    backoff_ms = std::min(backoff_ms, static_cast<double>(config_.max_backoff.count()));

    // Add jitter if enabled (0-50% of the calculated backoff)
    if (config_.enable_jitter) {
        std::uniform_real_distribution<double> dist(0.0, 0.5);
        double jitter_factor = dist(rng_);
        backoff_ms = backoff_ms * (1.0 + jitter_factor);
    }

    return std::chrono::milliseconds(static_cast<int64_t>(backoff_ms));
}

std::future<core::Result<core::Message, core::AgentError>>
RetryMiddleware::process(core::Message message) {
    metrics_.total_attempts++;

    bool had_retry = false;
    core::Result<core::Message, core::AgentError> last_result =
        core::Result<core::Message, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::Internal, "No attempts made")
        );

    for (uint32_t attempt = 0; attempt < config_.max_attempts; ++attempt) {
        // Try the operation
        auto future = agent_->process(message);
        auto result = future.get();

        // Success - return immediately
        if (result.is_ok()) {
            if (had_retry) {
                metrics_.successful_on_retry++;
            }
            return core::make_ready_future(std::move(result));
        }

        // Got error - save for potential return
        last_result = std::move(result);

        // Don't retry if we're on the last attempt
        if (attempt + 1 >= config_.max_attempts) {
            break;
        }

        // Check retry predicate
        if (!config_.should_retry(last_result.unwrap_err())) {
            break;
        }

        // We're retrying
        had_retry = true;
        metrics_.total_retries++;

        // Calculate and apply backoff
        auto backoff = calculate_backoff(attempt);
        metrics_.total_backoff_ms += backoff.count();

        std::this_thread::sleep_for(backoff);
    }

    // All retries exhausted
    metrics_.failed_after_retries++;
    return core::make_ready_future(std::move(last_result));
}

} // namespace middleware
} // namespace agenkit
