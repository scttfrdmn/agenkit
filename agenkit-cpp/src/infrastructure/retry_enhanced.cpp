#include "agenkit/infrastructure/retry_enhanced.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace agenkit {
namespace infrastructure {

EnhancedRetryConfig::EnhancedRetryConfig()
    : max_attempts(3)
    , initial_backoff(1000)
    , max_backoff(30000)
    , backoff_multiplier(2.0)
    , jitter_type(JitterType::Full)
    , jitter_min_ratio(0.5)
    , enable_budget(false)
    , max_cost_per_hour(100.0)
    , max_retries_per_hour(1000)
    , enable_backpressure(true)
    , backpressure_threshold(0.5)
    , backpressure_window(100)
{
    // Default error strategies
    error_strategies[ErrorClass::Transient] = ErrorStrategy{
        ErrorClass::Transient,
        5,
        std::chrono::milliseconds(100),
        std::chrono::milliseconds(5000),
        2.0,
        true
    };

    error_strategies[ErrorClass::RateLimit] = ErrorStrategy{
        ErrorClass::RateLimit,
        10,
        std::chrono::milliseconds(60000),
        std::chrono::milliseconds(300000),
        1.5,
        true
    };

    error_strategies[ErrorClass::Timeout] = ErrorStrategy{
        ErrorClass::Timeout,
        3,
        std::chrono::milliseconds(2000),
        std::chrono::milliseconds(30000),
        2.0,
        true
    };

    error_strategies[ErrorClass::ServerError] = ErrorStrategy{
        ErrorClass::ServerError,
        3,
        std::chrono::milliseconds(5000),
        std::chrono::milliseconds(60000),
        2.0,
        true
    };

    error_strategies[ErrorClass::ClientError] = ErrorStrategy{
        ErrorClass::ClientError,
        1,
        std::chrono::milliseconds(0),
        std::chrono::milliseconds(0),
        1.0,
        false
    };
}

EnhancedRetryDecorator::EnhancedRetryDecorator(
    std::shared_ptr<Agent> agent,
    const EnhancedRetryConfig& config
) : agent_(std::move(agent))
  , config_(config)
  , rng_(std::random_device{}())
{
    budget_.max_cost = config_.max_cost_per_hour;
    budget_.current_cost = 0.0;
    budget_.max_retries_per_hour = config_.max_retries_per_hour;
    budget_.retry_count = 0;
    budget_.window_start = std::chrono::steady_clock::now();
}

std::string EnhancedRetryDecorator::name() const {
    return agent_->name();
}

std::vector<std::string> EnhancedRetryDecorator::capabilities() const {
    return agent_->capabilities();
}

ErrorClass EnhancedRetryDecorator::classify_error(const std::exception& error) const {
    if (config_.error_classifier) {
        return config_.error_classifier(error);
    }

    // Default classification
    std::string err_str = error.what();
    std::transform(err_str.begin(), err_str.end(), err_str.begin(), ::tolower);

    if (err_str.find("rate limit") != std::string::npos || err_str.find("429") != std::string::npos) {
        return ErrorClass::RateLimit;
    } else if (err_str.find("timeout") != std::string::npos || err_str.find("timed out") != std::string::npos) {
        return ErrorClass::Timeout;
    } else if (err_str.find("500") != std::string::npos || err_str.find("502") != std::string::npos || err_str.find("503") != std::string::npos) {
        return ErrorClass::ServerError;
    } else if (err_str.find("400") != std::string::npos || err_str.find("401") != std::string::npos ||
               err_str.find("403") != std::string::npos || err_str.find("404") != std::string::npos) {
        return ErrorClass::ClientError;
    }

    return ErrorClass::Unknown;
}

ErrorStrategy EnhancedRetryDecorator::get_strategy(ErrorClass error_class) const {
    auto it = config_.error_strategies.find(error_class);
    if (it != config_.error_strategies.end()) {
        return it->second;
    }

    // Default strategy
    return ErrorStrategy{
        error_class,
        config_.max_attempts,
        config_.initial_backoff,
        config_.max_backoff,
        config_.backoff_multiplier,
        true
    };
}

std::chrono::milliseconds EnhancedRetryDecorator::calculate_backoff(
    std::chrono::milliseconds base_backoff,
    int attempt
) {
    double base_ms = base_backoff.count();
    std::uniform_real_distribution<> dis(0.0, 1.0);

    double jittered_ms;
    switch (config_.jitter_type) {
        case JitterType::None:
            jittered_ms = base_ms;
            break;

        case JitterType::Full:
            jittered_ms = dis(rng_) * base_ms;
            metrics_.total_jitter_added.fetch_add(
                (base_ms - jittered_ms) / 1000.0,
                std::memory_order_relaxed
            );
            break;

        case JitterType::Equal: {
            double min_backoff = base_ms * config_.jitter_min_ratio;
            jittered_ms = min_backoff + dis(rng_) * (base_ms - min_backoff);
            metrics_.total_jitter_added.fetch_add(
                (base_ms - jittered_ms) / 1000.0,
                std::memory_order_relaxed
            );
            break;
        }

        case JitterType::Decorrelated: {
            if (attempt == 1) {
                jittered_ms = base_ms;
            } else {
                auto previous = calculate_backoff(base_backoff, attempt - 1);
                double previous_ms = previous.count();
                jittered_ms = dis(rng_) * previous_ms * 3.0 + base_ms;
                if (jittered_ms > config_.max_backoff.count()) {
                    jittered_ms = config_.max_backoff.count();
                }
            }
            break;
        }

        default:
            jittered_ms = base_ms;
    }

    return std::chrono::milliseconds(static_cast<int64_t>(jittered_ms));
}

bool EnhancedRetryDecorator::check_budget(double cost) {
    if (!config_.enable_budget) {
        return true;
    }

    std::lock_guard<std::mutex> lock(budget_.mutex);

    // Reset window if hour has passed
    auto now = std::chrono::steady_clock::now();
    if (std::chrono::duration_cast<std::chrono::hours>(now - budget_.window_start).count() >= 1) {
        budget_.current_cost = 0.0;
        budget_.retry_count = 0;
        budget_.window_start = now;
    }

    // Check cost budget
    if (budget_.current_cost + cost > budget_.max_cost) {
        metrics_.budget_exceeded_count++;
        return false;
    }

    // Check retry count budget
    if (budget_.retry_count >= budget_.max_retries_per_hour) {
        metrics_.budget_exceeded_count++;
        return false;
    }

    return true;
}

bool EnhancedRetryDecorator::check_backpressure() {
    if (!config_.enable_backpressure) {
        return false;
    }

    std::lock_guard<std::mutex> lock(metrics_.mutex);

    if (metrics_.recent_results.size() < static_cast<size_t>(config_.backpressure_window)) {
        return false;
    }

    // Calculate failure rate
    int failures = 0;
    for (bool success : metrics_.recent_results) {
        if (!success) {
            failures++;
        }
    }

    double failure_rate = static_cast<double>(failures) / metrics_.recent_results.size();

    if (failure_rate > config_.backpressure_threshold) {
        metrics_.backpressure_detected++;
        return true;
    }

    return false;
}

Message EnhancedRetryDecorator::process(const Message& message) {
    std::exception_ptr last_error;
    ErrorClass error_class = ErrorClass::Unknown;
    ErrorStrategy strategy = get_strategy(error_class);

    for (int attempt = 1; attempt <= config_.max_attempts; ++attempt) {
        metrics_.total_attempts++;

        // Check budget before attempt
        if (config_.enable_budget && config_.cost_tracker) {
            double estimated_cost = config_.cost_tracker(message);
            if (!check_budget(estimated_cost)) {
                throw std::runtime_error("Retry budget exceeded");
            }
        }

        // Check backpressure
        if (check_backpressure()) {
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }

        try {
            // Process message
            Message response = agent_->process(message);

            // Success
            if (attempt == 1) {
                metrics_.successful_first_attempt++;
            } else {
                metrics_.successful_on_retry++;
            }

            {
                std::lock_guard<std::mutex> lock(metrics_.mutex);
                metrics_.recent_results.push_back(true);
                if (metrics_.recent_results.size() > static_cast<size_t>(config_.backpressure_window)) {
                    metrics_.recent_results.erase(metrics_.recent_results.begin());
                }
            }

            // Track cost
            if (config_.enable_budget && config_.cost_tracker) {
                double cost = config_.cost_tracker(message);
                std::lock_guard<std::mutex> lock(budget_.mutex);
                budget_.current_cost += cost;
            }

            return response;
        } catch (const std::exception& e) {
            // Failure
            last_error = std::current_exception();

            // Track failure for backpressure
            {
                std::lock_guard<std::mutex> lock(metrics_.mutex);
                metrics_.recent_results.push_back(false);
                if (metrics_.recent_results.size() > static_cast<size_t>(config_.backpressure_window)) {
                    metrics_.recent_results.erase(metrics_.recent_results.begin());
                }
            }

            // Classify error
            error_class = classify_error(e);
            {
                std::lock_guard<std::mutex> lock(metrics_.mutex);
                metrics_.error_class_counts[error_class]++;
            }

            // Get strategy for error class
            strategy = get_strategy(error_class);

            // Check if should retry
            if (!strategy.should_retry) {
                metrics_.failed_after_retries++;
                std::rethrow_exception(last_error);
            }

            // Check if exceeded max attempts for this error class
            if (attempt >= strategy.max_attempts) {
                break;
            }

            // Track retry
            metrics_.total_retries++;
            {
                std::lock_guard<std::mutex> lock(budget_.mutex);
                budget_.retry_count++;
            }

            // Calculate backoff with jitter
            auto base_backoff_ms = std::chrono::milliseconds(
                static_cast<int64_t>(
                    strategy.initial_backoff.count() *
                    std::pow(strategy.backoff_multiplier, attempt - 1)
                )
            );
            if (base_backoff_ms > strategy.max_backoff) {
                base_backoff_ms = strategy.max_backoff;
            }
            auto backoff = calculate_backoff(base_backoff_ms, attempt);

            // Sleep with backoff
            std::this_thread::sleep_for(backoff);
        }
    }

    // All attempts failed
    metrics_.failed_after_retries++;
    if (last_error) {
        std::rethrow_exception(last_error);
    }
    throw std::runtime_error("Max retry attempts exceeded");
}

EnhancedRetryMetrics EnhancedRetryDecorator::get_metrics() const {
    return metrics_;
}

} // namespace infrastructure
} // namespace agenkit
