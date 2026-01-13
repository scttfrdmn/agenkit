/**
 * @file per_user_rate_limiter.hpp
 * @brief Per-user rate limiter middleware using token bucket algorithm
 *
 * Implements token bucket rate limiting with separate buckets per user,
 * enabling fair resource allocation across multiple users/tenants.
 *
 * Features:
 * - Per-user token buckets with configurable rate and capacity
 * - Custom user ID extraction from message metadata
 * - Burst capacity support per user
 * - Detailed per-user metrics
 * - Thread-safe token management
 *
 * @example
 * @code
 * auto config = PerUserRateLimiterConfig::builder()
 *     .rate_per_second(10.0)
 *     .capacity(20)
 *     .tokens_per_request(1)
 *     .max_wait_timeout(std::chrono::seconds(5))
 *     .user_id_extractor([](const core::Message& msg) -> std::string {
 *         auto it = msg.metadata.find("user_id");
 *         return it != msg.metadata.end() ? it->second.get<std::string>() : "default";
 *     })
 *     .build();
 *
 * auto limiter_agent = std::make_shared<PerUserRateLimiterMiddleware>(agent, config);
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
#include <unordered_map>
#include <functional>
#include <optional>

namespace agenkit {
namespace middleware {

/// Per-user rate limit error
class PerUserRateLimitError : public core::AgentError {
public:
    explicit PerUserRateLimitError(
        const std::string& user_id,
        uint32_t tokens_needed,
        double tokens_available
    ) : core::AgentError(
            core::AgentErrorType::ProcessingError,
            "Rate limit exceeded for user '" + user_id +
            "': need " + std::to_string(tokens_needed) +
            " tokens, only " + std::to_string(tokens_available) + " available"
          ),
          user_id_(user_id),
          tokens_needed_(tokens_needed),
          tokens_available_(tokens_available) {}

    const std::string& user_id() const { return user_id_; }
    uint32_t tokens_needed() const { return tokens_needed_; }
    double tokens_available() const { return tokens_available_; }

private:
    std::string user_id_;
    uint32_t tokens_needed_;
    double tokens_available_;
};

/// User ID extractor function type
using UserIdExtractor = std::function<std::string(const core::Message&)>;

/// Default user ID extractor (extracts from metadata["user_id"])
inline std::string default_user_id_extractor(const core::Message& message) {
    const auto& meta = message.metadata();
    if (meta.contains("user_id") && meta["user_id"].is_string()) {
        return meta["user_id"].get<std::string>();
    }
    return "";
}

/// Per-user rate limiter configuration
struct PerUserRateLimiterConfig {
    /// Token generation rate (tokens per second per user)
    double rate_per_second = 10.0;

    /// Maximum token capacity per user (burst size)
    uint32_t capacity = 10;

    /// Tokens consumed per request
    uint32_t tokens_per_request = 1;

    /// Maximum wait timeout (optional)
    std::optional<std::chrono::milliseconds> max_wait_timeout;

    /// Function to extract user ID from message
    UserIdExtractor user_id_extractor = default_user_id_extractor;

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
        if (max_wait_timeout.has_value() && max_wait_timeout->count() <= 0) {
            throw std::invalid_argument("max_wait_timeout must be positive if set");
        }
        if (!user_id_extractor) {
            throw std::invalid_argument("user_id_extractor must be set");
        }
    }

    /// Builder for fluent configuration
    class Builder;

    static Builder builder();
};

/// Builder implementation for PerUserRateLimiterConfig
class PerUserRateLimiterConfig::Builder {
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

    Builder& max_wait_timeout(std::chrono::milliseconds duration) {
        config_.max_wait_timeout = duration;
        return *this;
    }

    Builder& user_id_extractor(UserIdExtractor extractor) {
        config_.user_id_extractor = std::move(extractor);
        return *this;
    }

    PerUserRateLimiterConfig build() {
        config_.validate();
        return config_;
    }

private:
    PerUserRateLimiterConfig config_;
};

inline PerUserRateLimiterConfig::Builder PerUserRateLimiterConfig::builder() {
    return Builder();
}

/// Per-user rate limiter metrics
struct PerUserRateLimiterMetrics {
    std::atomic<uint64_t> total_requests{0};
    std::atomic<uint64_t> allowed_requests{0};
    std::atomic<uint64_t> rejected_requests{0};
    std::atomic<uint64_t> total_wait_time_ms{0};
    std::atomic<size_t> active_users{0};

    /// Get snapshot of current metrics
    struct Snapshot {
        uint64_t total_requests;
        uint64_t allowed_requests;
        uint64_t rejected_requests;
        uint64_t total_wait_time_ms;
        size_t active_users;
        double rejection_rate;
        double avg_wait_time_ms;
    };

    Snapshot snapshot() const {
        auto total = total_requests.load();
        auto rejected = rejected_requests.load();
        auto wait_time = total_wait_time_ms.load();

        return Snapshot{
            total,
            allowed_requests.load(),
            rejected,
            wait_time,
            active_users.load(),
            total > 0 ? static_cast<double>(rejected) / total : 0.0,
            total > 0 ? static_cast<double>(wait_time) / total : 0.0
        };
    }
};

/// User bucket - token bucket for a single user
struct UserBucket {
    double tokens;
    std::chrono::steady_clock::time_point last_update;

    explicit UserBucket(uint32_t capacity)
        : tokens(static_cast<double>(capacity)),
          last_update(std::chrono::steady_clock::now()) {}
};

/// Per-user rate limiter middleware
class PerUserRateLimiterMiddleware : public core::Agent {
public:
    /// Create per-user rate limiter middleware
    ///
    /// @param agent Underlying agent to wrap
    /// @param config Per-user rate limiter configuration
    PerUserRateLimiterMiddleware(
        std::shared_ptr<core::Agent> agent,
        PerUserRateLimiterConfig config = PerUserRateLimiterConfig()
    ) : agent_(std::move(agent)), config_(std::move(config)) {
        config_.validate();
    }

    std::string name() const override {
        return "per_user_rate_limiter(" + agent_->name() + ")";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /// Get current metrics
    const PerUserRateLimiterMetrics& metrics() const {
        return metrics_;
    }

    /// Get configuration
    const PerUserRateLimiterConfig& config() const {
        return config_;
    }

private:
    std::shared_ptr<core::Agent> agent_;
    PerUserRateLimiterConfig config_;
    mutable PerUserRateLimiterMetrics metrics_;

    // Per-user token buckets (protected by mutex)
    mutable std::mutex mutex_;
    std::unordered_map<std::string, UserBucket> buckets_;

    /// Get or create user bucket
    UserBucket& get_user_bucket(const std::string& user_id);

    /// Refill tokens for a user based on elapsed time
    void refill_user_tokens(UserBucket& bucket);

    /// Try to acquire tokens for a user
    bool acquire_user_tokens(const std::string& user_id, uint32_t tokens_needed);
};

} // namespace middleware
} // namespace agenkit
