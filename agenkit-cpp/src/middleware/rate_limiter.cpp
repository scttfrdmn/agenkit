/**
 * @file rate_limiter.cpp
 * @brief Rate limiter middleware implementation
 */

#include "agenkit/middleware/rate_limiter.hpp"
#include <algorithm>
#include <thread>

namespace agenkit {
namespace middleware {

void RateLimiterMiddleware::refill_tokens() {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        now - last_refill_
    );

    if (elapsed.count() > 0) {
        // Calculate tokens to add based on elapsed time
        double tokens_to_add = (elapsed.count() / 1000.0) * config_.rate_per_second;
        tokens_ = std::min(
            tokens_ + tokens_to_add,
            static_cast<double>(config_.capacity)
        );
        last_refill_ = now;
    }
}

bool RateLimiterMiddleware::try_consume_tokens(uint32_t tokens_needed) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Refill tokens based on time passed
    refill_tokens();

    // Check if we have enough tokens
    if (tokens_ >= tokens_needed) {
        tokens_ -= tokens_needed;
        return true;
    }

    return false;
}

bool RateLimiterMiddleware::wait_for_available_tokens(uint32_t tokens_needed) {
    auto start = std::chrono::steady_clock::now();
    auto deadline = start + config_.max_wait_time;

    while (std::chrono::steady_clock::now() < deadline) {
        if (try_consume_tokens(tokens_needed)) {
            auto end = std::chrono::steady_clock::now();
            auto wait_time = std::chrono::duration_cast<std::chrono::milliseconds>(
                end - start
            );
            if (wait_time.count() > 0) {
                metrics_.waited_requests++;
                metrics_.total_wait_time_ms += wait_time.count();
            }
            return true;
        }

        // Sleep briefly before checking again
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    return false;
}

std::future<core::Result<core::Message, core::AgentError>>
RateLimiterMiddleware::process(core::Message message) {
    metrics_.total_requests++;

    bool acquired;
    if (config_.wait_for_tokens) {
        acquired = wait_for_available_tokens(config_.tokens_per_request);
    } else {
        acquired = try_consume_tokens(config_.tokens_per_request);
    }

    if (!acquired) {
        // Rate limit exceeded
        metrics_.rejected_requests++;

        // Calculate retry-after based on token generation rate
        double tokens_needed = config_.tokens_per_request;
        double retry_after_seconds = tokens_needed / config_.rate_per_second;

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                RateLimitError(retry_after_seconds)
            )
        );
    }

    // Tokens acquired - process request
    metrics_.allowed_requests++;
    return agent_->process(message);
}

} // namespace middleware
} // namespace agenkit
