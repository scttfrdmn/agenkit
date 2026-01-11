/**
 * @file middleware_example.cpp
 * @brief Demonstrates middleware composition and usage
 *
 * This example shows:
 * 1. Individual middleware usage (Retry, Timeout, Circuit Breaker)
 * 2. Resource protection middleware (Rate Limiter, Caching)
 * 3. Full middleware composition
 * 4. Metrics collection and reporting
 * 5. Error handling patterns
 */

#include <agenkit/middleware/middleware.hpp>
#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>
#include <iostream>
#include <iomanip>
#include <random>

using namespace agenkit;
using namespace agenkit::middleware;
using namespace agenkit::core;

void print_separator() {
    std::cout << "\n" << std::string(60, '=') << "\n\n";
}

/// Simple test agent that can simulate failures
class TestAgent : public Agent {
public:
    TestAgent(
        double failure_rate = 0.0,
        std::chrono::milliseconds delay = std::chrono::milliseconds(0)
    ) : failure_rate_(failure_rate),
        delay_(delay),
        rng_(std::random_device{}()) {}

    std::string name() const override {
        return "test_agent";
    }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        request_count_++;

        // Simulate delay
        if (delay_.count() > 0) {
            std::this_thread::sleep_for(delay_);
        }

        // Simulate random failures
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        if (dist(rng_) < failure_rate_) {
            return make_ready_future(
                Result<Message, AgentError>::err(
                    AgentError(AgentErrorType::ProcessingError, "Simulated failure")
                )
            );
        }

        // Success
        auto response = Message::with_text(
            "assistant",
            "Processed: " + message.content_as_str()
        );
        return make_ready_future(Result<Message, AgentError>::ok(response));
    }

    int request_count() const { return request_count_; }
    void reset_count() { request_count_ = 0; }

private:
    double failure_rate_;
    std::chrono::milliseconds delay_;
    std::mt19937 rng_;
    std::atomic<int> request_count_{0};
};

void example_retry_middleware() {
    std::cout << "=== Retry Middleware Example ===\n\n";

    // Create agent with 30% failure rate
    auto agent = std::make_shared<TestAgent>(0.3);

    // Wrap with retry middleware
    auto retry_config = RetryConfig::builder()
        .max_attempts(3)
        .initial_backoff(std::chrono::milliseconds(50))
        .max_backoff(std::chrono::milliseconds(500))
        .build();

    auto retry_agent = std::make_shared<RetryMiddleware>(agent, retry_config);

    std::cout << "Testing retry middleware with 30% failure rate...\n";
    std::cout << "Config: max_attempts=" << retry_config.max_attempts << "\n\n";

    // Try 10 requests
    int successes = 0;
    for (int i = 0; i < 10; i++) {
        auto message = Message::with_text("user", "Request " + std::to_string(i));
        auto result = retry_agent->process(message).get();

        if (result.is_ok()) {
            successes++;
        }
    }

    std::cout << "Results:\n";
    std::cout << "  Successes: " << successes << "/10\n";
    std::cout << "  Total attempts: " << agent->request_count() << "\n";

    auto metrics = retry_agent->metrics().snapshot();
    std::cout << "\nMetrics:\n";
    std::cout << "  Total retries: " << metrics.total_retries << "\n";
    std::cout << "  Successful on retry: " << metrics.successful_on_retry << "\n";
    std::cout << "  Failed after retries: " << metrics.failed_after_retries << "\n";
    std::cout << "  Avg retries per request: " << std::fixed << std::setprecision(2)
              << metrics.avg_retries_per_request << "\n";
}

void example_timeout_middleware() {
    print_separator();
    std::cout << "=== Timeout Middleware Example ===\n\n";

    // Create slow agent (500ms delay)
    auto agent = std::make_shared<TestAgent>(0.0, std::chrono::milliseconds(500));

    // Wrap with timeout (300ms)
    auto timeout_config = TimeoutConfig::builder()
        .default_timeout(std::chrono::milliseconds(300))
        .build();

    auto timeout_agent = std::make_shared<TimeoutMiddleware>(agent, timeout_config);

    std::cout << "Testing timeout with 500ms delay and 300ms timeout...\n\n";

    auto message = Message::with_text("user", "Slow request");
    auto result = timeout_agent->process(message).get();

    std::cout << "Result: ";
    if (result.is_err()) {
        std::cout << "TIMEOUT (as expected)\n";
        std::cout << "Error: " << result.unwrap_err().message() << "\n";
    } else {
        std::cout << "SUCCESS (unexpected)\n";
    }

    auto metrics = timeout_agent->metrics().snapshot();
    std::cout << "\nMetrics:\n";
    std::cout << "  Total requests: " << metrics.total_requests << "\n";
    std::cout << "  Timed out: " << metrics.timed_out_requests << "\n";
    std::cout << "  Timeout rate: " << std::fixed << std::setprecision(2)
              << (metrics.timeout_rate * 100.0) << "%\n";
}

void example_circuit_breaker_middleware() {
    print_separator();
    std::cout << "=== Circuit Breaker Middleware Example ===\n\n";

    // Create agent with 100% failure rate
    auto agent = std::make_shared<TestAgent>(1.0);

    // Wrap with circuit breaker
    auto breaker_config = CircuitBreakerConfig::builder()
        .failure_threshold(3)
        .success_threshold(2)
        .recovery_timeout(std::chrono::milliseconds(100))
        .build();

    auto breaker_agent = std::make_shared<CircuitBreakerMiddleware>(agent, breaker_config);

    std::cout << "Testing circuit breaker with 100% failure rate...\n";
    std::cout << "Config: failure_threshold=" << breaker_config.failure_threshold << "\n\n";

    // Make requests until circuit opens
    for (int i = 0; i < 5; i++) {
        auto message = Message::with_text("user", "Request " + std::to_string(i));
        auto result = breaker_agent->process(message).get();

        std::cout << "Request " << i << ": ";
        if (result.is_err()) {
            auto error = result.unwrap_err();
            std::cout << "FAILED - " << core::to_string(error.type());
            std::cout << "\n";
        } else {
            std::cout << "SUCCESS\n";
        }

        std::cout << "  State: " << state_to_string(breaker_agent->state()) << "\n";
    }

    auto metrics = breaker_agent->metrics().snapshot(breaker_agent->state());
    std::cout << "\nMetrics:\n";
    std::cout << "  Total requests: " << metrics.total_requests << "\n";
    std::cout << "  Rejected (circuit open): " << metrics.rejected_requests << "\n";
    std::cout << "  State transitions: " << metrics.state_transitions << "\n";
    std::cout << "  Final state: " << state_to_string(metrics.current_state) << "\n";
}

void example_rate_limiter_middleware() {
    print_separator();
    std::cout << "=== Rate Limiter Middleware Example ===\n\n";

    auto agent = std::make_shared<TestAgent>();

    // Configure rate limiter: 5 requests/second, burst of 10
    auto limiter_config = RateLimiterConfig::builder()
        .rate_per_second(5.0)
        .capacity(10)
        .tokens_per_request(1)
        .wait_for_tokens(false)  // Reject immediately
        .build();

    auto limiter_agent = std::make_shared<RateLimiterMiddleware>(agent, limiter_config);

    std::cout << "Testing rate limiter (5 req/s, burst 10)...\n";
    std::cout << "Sending 15 rapid requests...\n\n";

    int allowed = 0;
    int rejected = 0;

    for (int i = 0; i < 15; i++) {
        auto message = Message::with_text("user", "Request " + std::to_string(i));
        auto result = limiter_agent->process(message).get();

        if (result.is_ok()) {
            allowed++;
        } else {
            rejected++;
            if (i < 5) {  // Only print first few rejections
                std::cout << "Request " << i << " REJECTED: "
                          << result.unwrap_err().message() << "\n";
            }
        }
    }

    std::cout << "\nResults:\n";
    std::cout << "  Allowed: " << allowed << "\n";
    std::cout << "  Rejected: " << rejected << "\n";

    auto metrics = limiter_agent->metrics().snapshot(limiter_agent->current_tokens());
    std::cout << "\nMetrics:\n";
    std::cout << "  Total requests: " << metrics.total_requests << "\n";
    std::cout << "  Rejection rate: " << std::fixed << std::setprecision(2)
              << (metrics.rejection_rate * 100.0) << "%\n";
    std::cout << "  Current tokens: " << std::setprecision(1) << metrics.current_tokens << "\n";
}

void example_caching_middleware() {
    print_separator();
    std::cout << "=== Caching Middleware Example ===\n\n";

    auto agent = std::make_shared<TestAgent>();

    // Configure caching with small size for demo
    auto cache_config = CachingConfig::builder()
        .max_cache_size(5)
        .default_ttl(std::chrono::seconds(10))
        .build();

    auto cached_agent = std::make_shared<CachingMiddleware>(agent, cache_config);

    std::cout << "Testing caching middleware (max size: 5)...\n\n";

    // Make repeated requests
    std::vector<std::string> requests = {"A", "B", "C", "A", "B", "D", "A", "E"};

    for (size_t i = 0; i < requests.size(); i++) {
        auto message = Message::with_text("user", requests[i]);
        auto result = cached_agent->process(message).get();

        std::cout << "Request '" << requests[i] << "': ";
        if (result.is_ok()) {
            std::cout << "SUCCESS\n";
        }
    }

    std::cout << "\nCache Statistics:\n";
    std::cout << "  Agent was called: " << agent->request_count() << " times\n";
    std::cout << "  Total requests: " << requests.size() << "\n";
    std::cout << "  Cache hits: " << (requests.size() - agent->request_count()) << "\n";

    auto metrics = cached_agent->metrics().snapshot(cached_agent->cache_size());
    std::cout << "\nMetrics:\n";
    std::cout << "  Total requests: " << metrics.total_requests << "\n";
    std::cout << "  Cache hits: " << metrics.cache_hits << "\n";
    std::cout << "  Cache misses: " << metrics.cache_misses << "\n";
    std::cout << "  Hit rate: " << std::fixed << std::setprecision(2)
              << (metrics.hit_rate * 100.0) << "%\n";
    std::cout << "  Current cache size: " << metrics.current_cache_size << "\n";
    std::cout << "  Evictions: " << metrics.cache_evictions << "\n";
}

void example_composed_middleware() {
    print_separator();
    std::cout << "=== Composed Middleware Example ===\n\n";

    auto agent = std::make_shared<TestAgent>(0.2, std::chrono::milliseconds(10));

    std::cout << "Building middleware stack:\n";
    std::cout << "  1. Base agent (20% failure rate, 10ms delay)\n";
    std::cout << "  2. + Caching\n";
    std::cout << "  3. + Rate Limiter (10 req/s)\n";
    std::cout << "  4. + Circuit Breaker (threshold: 5)\n";
    std::cout << "  5. + Timeout (1s)\n";
    std::cout << "  6. + Retry (3 attempts)\n\n";

    // Build middleware stack from inside out
    std::shared_ptr<Agent> composed = agent;

    // 1. Caching (innermost - check cache first)
    auto cache_config = CachingConfig::builder()
        .max_cache_size(100)
        .default_ttl(std::chrono::minutes(5))
        .build();
    auto caching = std::make_shared<CachingMiddleware>(composed, cache_config);
    composed = caching;

    // 2. Rate limiter
    auto limiter_config = RateLimiterConfig::builder()
        .rate_per_second(10.0)
        .capacity(20)
        .build();
    auto rate_limiter = std::make_shared<RateLimiterMiddleware>(composed, limiter_config);
    composed = rate_limiter;

    // 3. Circuit breaker
    auto breaker_config = CircuitBreakerConfig::builder()
        .failure_threshold(5)
        .recovery_timeout(std::chrono::seconds(60))
        .build();
    auto circuit_breaker = std::make_shared<CircuitBreakerMiddleware>(composed, breaker_config);
    composed = circuit_breaker;

    // 4. Timeout
    auto timeout_config = TimeoutConfig::builder()
        .default_timeout(std::chrono::seconds(1))
        .build();
    auto timeout = std::make_shared<TimeoutMiddleware>(composed, timeout_config);
    composed = timeout;

    // 5. Retry (outermost - retry failed operations)
    auto retry_config = RetryConfig::builder()
        .max_attempts(3)
        .initial_backoff(std::chrono::milliseconds(100))
        .build();
    auto retry = std::make_shared<RetryMiddleware>(composed, retry_config);
    composed = retry;

    std::cout << "Agent name: " << composed->name() << "\n\n";

    // Make some requests
    std::cout << "Making 20 requests...\n";
    int successes = 0;
    for (int i = 0; i < 20; i++) {
        auto message = Message::with_text("user", "Request " + std::to_string(i % 5));
        auto result = composed->process(message).get();
        if (result.is_ok()) {
            successes++;
        }
    }

    std::cout << "\nResults: " << successes << "/20 successful\n";

    // Print metrics from each middleware layer
    std::cout << "\nRetry Metrics:\n";
    auto retry_metrics = retry->metrics().snapshot();
    std::cout << "  Total retries: " << retry_metrics.total_retries << "\n";
    std::cout << "  Successful on retry: " << retry_metrics.successful_on_retry << "\n";

    std::cout << "\nTimeout Metrics:\n";
    auto timeout_metrics = timeout->metrics().snapshot();
    std::cout << "  Timed out: " << timeout_metrics.timed_out_requests << "\n";

    std::cout << "\nCircuit Breaker Metrics:\n";
    auto breaker_metrics = circuit_breaker->metrics().snapshot(circuit_breaker->state());
    std::cout << "  Current state: " << state_to_string(breaker_metrics.current_state) << "\n";
    std::cout << "  Rejected: " << breaker_metrics.rejected_requests << "\n";

    std::cout << "\nRate Limiter Metrics:\n";
    auto limiter_metrics = rate_limiter->metrics().snapshot(rate_limiter->current_tokens());
    std::cout << "  Rejected: " << limiter_metrics.rejected_requests << "\n";
    std::cout << "  Current tokens: " << std::fixed << std::setprecision(1)
              << limiter_metrics.current_tokens << "\n";

    std::cout << "\nCaching Metrics:\n";
    auto cache_metrics = caching->metrics().snapshot(caching->cache_size());
    std::cout << "  Hits: " << cache_metrics.cache_hits << "\n";
    std::cout << "  Misses: " << cache_metrics.cache_misses << "\n";
    std::cout << "  Hit rate: " << std::setprecision(2)
              << (cache_metrics.hit_rate * 100.0) << "%\n";
}

int main() {
    std::cout << "Agenkit C++ Middleware Examples\n";
    std::cout << "================================\n";

    try {
        example_retry_middleware();
        example_timeout_middleware();
        example_circuit_breaker_middleware();
        example_rate_limiter_middleware();
        example_caching_middleware();
        example_composed_middleware();

        print_separator();
        std::cout << "=== All Examples Completed ===\n\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}
