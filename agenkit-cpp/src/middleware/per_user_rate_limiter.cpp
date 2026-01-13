/**
 * @file per_user_rate_limiter.cpp
 * @brief Per-user rate limiter middleware implementation
 */

#include "agenkit/middleware/per_user_rate_limiter.hpp"
#include <algorithm>
#include <thread>

namespace agenkit {
namespace middleware {

UserBucket& PerUserRateLimiterMiddleware::get_user_bucket(const std::string& user_id) {
    // Note: Assumes mutex is already held by caller

    auto it = buckets_.find(user_id);
    if (it != buckets_.end()) {
        return it->second;
    }

    // Create new bucket for user
    auto result = buckets_.emplace(user_id, UserBucket(config_.capacity));
    metrics_.active_users = buckets_.size();
    return result.first->second;
}

void PerUserRateLimiterMiddleware::refill_user_tokens(UserBucket& bucket) {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        now - bucket.last_update
    );

    if (elapsed.count() > 0) {
        // Calculate tokens to add based on elapsed time
        double tokens_to_add = (elapsed.count() / 1000.0) * config_.rate_per_second;
        bucket.tokens = std::min(
            bucket.tokens + tokens_to_add,
            static_cast<double>(config_.capacity)
        );
        bucket.last_update = now;
    }
}

bool PerUserRateLimiterMiddleware::acquire_user_tokens(
    const std::string& user_id,
    uint32_t tokens_needed
) {
    std::unique_lock<std::mutex> lock(mutex_);

    // Get or create user bucket
    UserBucket& bucket = get_user_bucket(user_id);

    // Refill tokens based on elapsed time
    refill_user_tokens(bucket);

    // Check if we have enough tokens immediately
    if (bucket.tokens >= tokens_needed) {
        bucket.tokens -= tokens_needed;
        return true;
    }

    // Calculate wait time needed
    double tokens_deficit = tokens_needed - bucket.tokens;
    double wait_time_seconds = tokens_deficit / config_.rate_per_second;
    auto wait_duration = std::chrono::milliseconds(
        static_cast<int64_t>(wait_time_seconds * 1000.0)
    );

    // Check if wait time exceeds max_wait_timeout
    if (config_.max_wait_timeout.has_value() &&
        wait_duration > config_.max_wait_timeout.value()) {
        return false;
    }

    // Release lock before sleeping to allow other operations
    lock.unlock();

    // Wait for tokens to refill
    auto wait_start = std::chrono::steady_clock::now();
    std::this_thread::sleep_for(wait_duration);
    auto actual_wait = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - wait_start
    );

    // Re-acquire lock and try again
    lock.lock();

    // Refill tokens based on actual elapsed time
    refill_user_tokens(bucket);

    // Try to consume tokens
    if (bucket.tokens >= tokens_needed) {
        bucket.tokens -= tokens_needed;

        // Update wait time metrics
        metrics_.total_wait_time_ms += actual_wait.count();
        return true;
    }

    // Should not happen, but handle defensively
    return false;
}

std::future<core::Result<core::Message, core::AgentError>>
PerUserRateLimiterMiddleware::process(core::Message message) {
    metrics_.total_requests++;

    // Extract user ID from message
    std::string user_id = config_.user_id_extractor(message);

    // Try to acquire tokens for this user
    bool acquired = acquire_user_tokens(user_id, config_.tokens_per_request);

    if (!acquired) {
        // Rate limit exceeded for this user
        metrics_.rejected_requests++;

        // Get current token count for error message
        double tokens_available = 0.0;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            auto it = buckets_.find(user_id);
            if (it != buckets_.end()) {
                tokens_available = it->second.tokens;
            }
        }

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                PerUserRateLimitError(
                    user_id,
                    config_.tokens_per_request,
                    tokens_available
                )
            )
        );
    }

    // Tokens acquired - process request
    metrics_.allowed_requests++;
    return agent_->process(message);
}

} // namespace middleware
} // namespace agenkit
