#pragma once

#include "agenkit/core/agent.hpp"
#include <atomic>
#include <chrono>
#include <functional>
#include <memory>
#include <mutex>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

namespace agenkit {
namespace infrastructure {

/// Jitter types for retry backoff.
enum class JitterType {
    None,
    Full,
    Equal,
    Decorrelated
};

/// Error classification for retry strategies.
enum class ErrorClass {
    Transient,
    RateLimit,
    Timeout,
    ServerError,
    ClientError,
    Unknown
};

/// Retry strategy for specific error class.
struct ErrorStrategy {
    ErrorClass error_class;
    int max_attempts;
    std::chrono::milliseconds initial_backoff;
    std::chrono::milliseconds max_backoff;
    double backoff_multiplier;
    bool should_retry;
};

/// Retry budget to limit costs.
struct RetryBudget {
    double max_cost;
    double current_cost;
    int64_t max_retries_per_hour;
    int64_t retry_count;
    std::chrono::steady_clock::time_point window_start;
    std::mutex mutex;
};

/// Enhanced retry configuration.
struct EnhancedRetryConfig {
    // Basic retry settings
    int max_attempts;
    std::chrono::milliseconds initial_backoff;
    std::chrono::milliseconds max_backoff;
    double backoff_multiplier;

    // Jitter settings
    JitterType jitter_type;
    double jitter_min_ratio;

    // Error-specific strategies
    std::unordered_map<ErrorClass, ErrorStrategy> error_strategies;
    std::function<ErrorClass(const std::exception&)> error_classifier;

    // Budget settings
    bool enable_budget;
    std::function<double(const Message&)> cost_tracker;
    double max_cost_per_hour;
    int64_t max_retries_per_hour;

    // Backpressure detection
    bool enable_backpressure;
    double backpressure_threshold;
    int backpressure_window;

    EnhancedRetryConfig();
};

/// Enhanced retry metrics.
struct EnhancedRetryMetrics {
    std::atomic<uint64_t> total_attempts{0};
    std::atomic<uint64_t> successful_first_attempt{0};
    std::atomic<uint64_t> successful_on_retry{0};
    std::atomic<uint64_t> failed_after_retries{0};
    std::atomic<uint64_t> total_retries{0};
    std::atomic<double> total_jitter_added{0.0};
    std::atomic<uint64_t> budget_exceeded_count{0};
    std::atomic<uint64_t> backpressure_detected{0};
    std::unordered_map<ErrorClass, uint64_t> error_class_counts;
    std::vector<bool> recent_results;
    std::mutex mutex;
};

/// Enhanced retry decorator wraps an agent with enhanced retry logic.
class EnhancedRetryDecorator : public Agent {
public:
    EnhancedRetryDecorator(
        std::shared_ptr<Agent> agent,
        const EnhancedRetryConfig& config = EnhancedRetryConfig()
    );

    std::string name() const override;
    std::vector<std::string> capabilities() const override;
    Message process(const Message& message) override;

    EnhancedRetryMetrics get_metrics() const;

private:
    ErrorClass classify_error(const std::exception& error) const;
    ErrorStrategy get_strategy(ErrorClass error_class) const;
    std::chrono::milliseconds calculate_backoff(
        std::chrono::milliseconds base_backoff,
        int attempt
    );
    bool check_budget(double cost);
    bool check_backpressure();

    std::shared_ptr<Agent> agent_;
    EnhancedRetryConfig config_;
    EnhancedRetryMetrics metrics_;
    RetryBudget budget_;
    std::mt19937 rng_;
};

} // namespace infrastructure
} // namespace agenkit
