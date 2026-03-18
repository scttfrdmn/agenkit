/**
 * @file test_middleware.cpp
 * @brief Comprehensive tests for middleware infrastructure
 */

#include <gtest/gtest.h>
#include "agenkit/middleware/middleware.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <thread>
#include <chrono>
#include <random>

using namespace agenkit;
using namespace agenkit::middleware;
using namespace agenkit::core;

// ============================================================================
// Test Agent
// ============================================================================

/// Simple test agent for middleware testing
class TestAgent : public Agent {
public:
    TestAgent(
        double failure_rate = 0.0,
        std::chrono::milliseconds delay = std::chrono::milliseconds(0),
        bool deterministic = true
    ) : failure_rate_(failure_rate),
        delay_(delay),
        rng_(deterministic ? 42 : std::random_device{}()) {}

    std::string name() const override {
        return "test_agent";
    }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        request_count_++;

        if (delay_.count() > 0) {
            // Truly async so timeout middleware can observe the delay
            return std::async(std::launch::async,
                [this, msg = std::move(message)]() mutable -> Result<Message, AgentError> {
                    std::this_thread::sleep_for(delay_);
                    return make_response(std::move(msg));
                });
        }

        return make_ready_future(make_response(std::move(message)));
    }

    int request_count() const { return request_count_; }
    void reset_count() { request_count_ = 0; }

private:
    Result<Message, AgentError> make_response(Message message) {
        std::lock_guard<std::mutex> lock(rng_mutex_);
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        if (dist(rng_) < failure_rate_) {
            return Result<Message, AgentError>::err(
                AgentError(AgentErrorType::ProcessingError, "Simulated failure")
            );
        }
        auto response = Message::with_text(
            "assistant",
            "Processed: " + message.content_as_str()
        );
        return Result<Message, AgentError>::ok(response);
    }

    double failure_rate_;
    std::chrono::milliseconds delay_;
    std::mt19937 rng_;
    mutable std::mutex rng_mutex_;
    std::atomic<int> request_count_{0};
};

/// Agent that fails exactly N times then always succeeds
class FailNThenSucceed : public Agent {
    int fail_n_;
    std::atomic<int> count_{0};
public:
    explicit FailNThenSucceed(int n) : fail_n_(n) {}
    std::string name() const override { return "fail_n_then_succeed"; }
    int call_count() const { return count_.load(); }

    std::future<Result<Message, AgentError>> process(Message) override {
        int n = ++count_;
        if (n <= fail_n_) {
            return make_ready_future(Result<Message, AgentError>::err(
                AgentError(AgentErrorType::ProcessingError, "deliberate fail")));
        }
        return make_ready_future(Result<Message, AgentError>::ok(
            Message::with_text("assistant", "success")));
    }
};

// ============================================================================
// RetryMiddleware Tests
// ============================================================================

TEST(RetryMiddlewareTest, SuccessfulOnFirstAttempt) {
    auto agent = std::make_shared<TestAgent>(0.0);  // No failures

    auto config = RetryConfig::builder()
        .max_attempts(3)
        .initial_backoff(std::chrono::milliseconds(10))
        .build();

    auto retry_agent = std::make_shared<RetryMiddleware>(agent, config);

    auto message = Message::with_text("user", "test");
    auto result = retry_agent->process(message).get();

    EXPECT_TRUE(result.is_ok());
    EXPECT_EQ(agent->request_count(), 1);  // Only one attempt needed

    auto metrics = retry_agent->metrics().snapshot();
    EXPECT_EQ(metrics.total_retries, 0);
    EXPECT_EQ(metrics.successful_on_retry, 0);
}

TEST(RetryMiddlewareTest, SuccessfulAfterRetries) {
    auto agent = std::make_shared<FailNThenSucceed>(2);  // fails 2x, then succeeds

    auto config = RetryConfig::builder()
        .max_attempts(5)
        .initial_backoff(std::chrono::milliseconds(1))
        .max_backoff(std::chrono::milliseconds(10))
        .build();

    auto retry_agent = std::make_shared<RetryMiddleware>(agent, config);

    auto message = Message::with_text("user", "test");
    auto result = retry_agent->process(message).get();

    EXPECT_TRUE(result.is_ok());
    EXPECT_GT(agent->call_count(), 1);  // Multiple attempts (2 failures + 1 success)

    auto metrics = retry_agent->metrics().snapshot();
    EXPECT_GT(metrics.total_retries, 0);
}

TEST(RetryMiddlewareTest, FailAfterMaxAttempts) {
    auto agent = std::make_shared<TestAgent>(1.0);  // Always fails

    auto config = RetryConfig::builder()
        .max_attempts(3)
        .initial_backoff(std::chrono::milliseconds(1))
        .build();

    auto retry_agent = std::make_shared<RetryMiddleware>(agent, config);

    auto message = Message::with_text("user", "test");
    auto result = retry_agent->process(message).get();

    EXPECT_TRUE(result.is_err());
    EXPECT_EQ(agent->request_count(), 3);  // All attempts used

    auto metrics = retry_agent->metrics().snapshot();
    EXPECT_EQ(metrics.total_retries, 2);  // 3 attempts = 2 retries
    EXPECT_EQ(metrics.failed_after_retries, 1);
}

TEST(RetryMiddlewareTest, ExponentialBackoff) {
    auto agent = std::make_shared<TestAgent>(0.6, std::chrono::milliseconds(0), true);

    auto config = RetryConfig::builder()
        .max_attempts(5)
        .initial_backoff(std::chrono::milliseconds(10))
        .max_backoff(std::chrono::milliseconds(100))
        .backoff_multiplier(2.0)
        .build();

    auto retry_agent = std::make_shared<RetryMiddleware>(agent, config);

    auto start = std::chrono::steady_clock::now();
    auto message = Message::with_text("user", "test");
    retry_agent->process(message).get();
    auto elapsed = std::chrono::steady_clock::now() - start;

    // Should have some backoff delay
    EXPECT_GT(elapsed.count(), 0);
}

TEST(RetryMiddlewareTest, Metrics) {
    auto agent = std::make_shared<TestAgent>(0.3, std::chrono::milliseconds(0), true);

    auto config = RetryConfig::builder()
        .max_attempts(3)
        .initial_backoff(std::chrono::milliseconds(1))
        .build();

    auto retry_agent = std::make_shared<RetryMiddleware>(agent, config);

    // Make multiple requests
    for (int i = 0; i < 10; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        retry_agent->process(message).get();
    }

    auto metrics = retry_agent->metrics().snapshot();
    EXPECT_EQ(metrics.total_attempts, 10);
    EXPECT_GT(metrics.avg_retries_per_request, 0.0);
}

// ============================================================================
// TimeoutMiddleware Tests
// ============================================================================

TEST(TimeoutMiddlewareTest, SuccessBeforeTimeout) {
    auto agent = std::make_shared<TestAgent>(0.0, std::chrono::milliseconds(10));

    auto config = TimeoutConfig::builder()
        .default_timeout(std::chrono::milliseconds(100))
        .build();

    auto timeout_agent = std::make_shared<TimeoutMiddleware>(agent, config);

    auto message = Message::with_text("user", "test");
    auto result = timeout_agent->process(message).get();

    EXPECT_TRUE(result.is_ok());

    auto metrics = timeout_agent->metrics().snapshot();
    EXPECT_EQ(metrics.timed_out_requests, 0);
}

TEST(TimeoutMiddlewareTest, TimeoutOccurs) {
    auto agent = std::make_shared<TestAgent>(0.0, std::chrono::milliseconds(200));

    auto config = TimeoutConfig::builder()
        .default_timeout(std::chrono::milliseconds(50))
        .build();

    auto timeout_agent = std::make_shared<TimeoutMiddleware>(agent, config);

    auto message = Message::with_text("user", "test");
    auto result = timeout_agent->process(message).get();

    EXPECT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err().type(), AgentErrorType::Timeout);

    auto metrics = timeout_agent->metrics().snapshot();
    EXPECT_EQ(metrics.timed_out_requests, 1);
    EXPECT_GT(metrics.timeout_rate, 0.0);
}

TEST(TimeoutMiddlewareTest, MultipleRequests) {
    auto agent = std::make_shared<TestAgent>(0.0, std::chrono::milliseconds(30));

    auto config = TimeoutConfig::builder()
        .default_timeout(std::chrono::milliseconds(50))
        .build();

    auto timeout_agent = std::make_shared<TimeoutMiddleware>(agent, config);

    int successes = 0;
    for (int i = 0; i < 5; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        auto result = timeout_agent->process(message).get();
        if (result.is_ok()) {
            successes++;
        }
    }

    EXPECT_EQ(successes, 5);

    auto metrics = timeout_agent->metrics().snapshot();
    EXPECT_EQ(metrics.total_requests, 5);
    EXPECT_EQ(metrics.timed_out_requests, 0);
}

// ============================================================================
// CircuitBreakerMiddleware Tests
// ============================================================================

TEST(CircuitBreakerTest, InitiallyClosedState) {
    auto agent = std::make_shared<TestAgent>();

    auto config = CircuitBreakerConfig::builder()
        .failure_threshold(3)
        .success_threshold(2)
        .recovery_timeout(std::chrono::milliseconds(100))
        .build();

    auto breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);

    EXPECT_EQ(breaker->state(), CircuitState::CLOSED);
}

TEST(CircuitBreakerTest, TransitionToOpen) {
    auto agent = std::make_shared<TestAgent>(1.0);  // Always fails

    auto config = CircuitBreakerConfig::builder()
        .failure_threshold(3)
        .success_threshold(2)
        .recovery_timeout(std::chrono::milliseconds(100))
        .build();

    auto breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);

    // Make requests until circuit opens
    for (int i = 0; i < 3; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        breaker->process(message).get();
    }

    EXPECT_EQ(breaker->state(), CircuitState::OPEN);
}

TEST(CircuitBreakerTest, RejectWhenOpen) {
    auto agent = std::make_shared<TestAgent>(1.0);

    auto config = CircuitBreakerConfig::builder()
        .failure_threshold(2)
        .success_threshold(2)
        .recovery_timeout(std::chrono::milliseconds(100))
        .build();

    auto breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);

    // Open the circuit
    for (int i = 0; i < 2; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        breaker->process(message).get();
    }

    EXPECT_EQ(breaker->state(), CircuitState::OPEN);

    // Next request should be rejected immediately
    auto message = Message::with_text("user", "test");
    auto result = breaker->process(message).get();

    EXPECT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err().type(), AgentErrorType::ProcessingError);

    auto metrics = breaker->metrics().snapshot(breaker->state());
    EXPECT_GT(metrics.rejected_requests, 0);
}

TEST(CircuitBreakerTest, TransitionToHalfOpen) {
    // Fails first 2 requests (opens circuit), then succeeds (for half-open recovery)
    auto agent = std::make_shared<FailNThenSucceed>(2);

    auto config = CircuitBreakerConfig::builder()
        .failure_threshold(2)
        .success_threshold(3)  // need 3 successes to close; 1 success leaves in HALF_OPEN
        .recovery_timeout(std::chrono::milliseconds(50))
        .build();

    auto breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);

    // Open the circuit (2 failures)
    for (int i = 0; i < 2; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        breaker->process(message).get();
    }

    EXPECT_EQ(breaker->state(), CircuitState::OPEN);

    // Wait for recovery timeout
    std::this_thread::sleep_for(std::chrono::milliseconds(60));

    // Next request: transitions to HALF_OPEN, agent now succeeds (1 of 3 needed -> stays HALF_OPEN)
    auto message = Message::with_text("user", "test");
    breaker->process(message).get();

    EXPECT_EQ(breaker->state(), CircuitState::HALF_OPEN);
}

TEST(CircuitBreakerTest, RecoveryToClosedState) {
    auto agent = std::make_shared<TestAgent>(1.0);

    auto config = CircuitBreakerConfig::builder()
        .failure_threshold(2)
        .success_threshold(2)
        .recovery_timeout(std::chrono::milliseconds(50))
        .build();

    auto breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);

    // Open the circuit
    for (int i = 0; i < 2; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        breaker->process(message).get();
    }

    EXPECT_EQ(breaker->state(), CircuitState::OPEN);

    // Wait for recovery
    std::this_thread::sleep_for(std::chrono::milliseconds(60));

    // Change agent to succeed
    agent = std::make_shared<TestAgent>(0.0);
    breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);

    // Open it first
    auto failing_agent = std::make_shared<TestAgent>(1.0);
    auto temp_breaker = std::make_shared<CircuitBreakerMiddleware>(failing_agent, config);
    for (int i = 0; i < 2; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        temp_breaker->process(message).get();
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(60));

    // Now use successful agent
    breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);
    auto metrics_before = breaker->metrics().snapshot(breaker->state());

    // Make successful requests
    for (int i = 0; i < 3; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        breaker->process(message).get();
    }

    EXPECT_EQ(breaker->state(), CircuitState::CLOSED);
}

TEST(CircuitBreakerTest, Metrics) {
    auto agent = std::make_shared<TestAgent>(0.5, std::chrono::milliseconds(0), true);

    auto config = CircuitBreakerConfig::builder()
        .failure_threshold(3)
        .success_threshold(2)
        .recovery_timeout(std::chrono::milliseconds(100))
        .build();

    auto breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);

    // Make several requests
    for (int i = 0; i < 10; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        breaker->process(message).get();
    }

    auto metrics = breaker->metrics().snapshot(breaker->state());
    EXPECT_EQ(metrics.total_requests, 10);
    EXPECT_GE(metrics.state_transitions, 0);
}

// ============================================================================
// RateLimiterMiddleware Tests
// ============================================================================

TEST(RateLimiterTest, AllowWithinCapacity) {
    auto agent = std::make_shared<TestAgent>();

    auto config = RateLimiterConfig::builder()
        .rate_per_second(10.0)
        .capacity(10)
        .wait_for_tokens(false)
        .build();

    auto limiter = std::make_shared<RateLimiterMiddleware>(agent, config);

    // Make requests within capacity
    int successes = 0;
    for (int i = 0; i < 5; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        auto result = limiter->process(message).get();
        if (result.is_ok()) {
            successes++;
        }
    }

    EXPECT_EQ(successes, 5);

    auto metrics = limiter->metrics().snapshot(limiter->current_tokens());
    EXPECT_EQ(metrics.rejected_requests, 0);
}

TEST(RateLimiterTest, RejectOverCapacity) {
    auto agent = std::make_shared<TestAgent>();

    auto config = RateLimiterConfig::builder()
        .rate_per_second(5.0)
        .capacity(5)
        .tokens_per_request(1)
        .wait_for_tokens(false)
        .build();

    auto limiter = std::make_shared<RateLimiterMiddleware>(agent, config);

    int rejections = 0;
    for (int i = 0; i < 10; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        auto result = limiter->process(message).get();
        if (result.is_err() && result.unwrap_err().type() == AgentErrorType::ProcessingError) {
            rejections++;
        }
    }

    EXPECT_GT(rejections, 0);

    auto metrics = limiter->metrics().snapshot(limiter->current_tokens());
    EXPECT_GT(metrics.rejected_requests, 0);
    EXPECT_GT(metrics.rejection_rate, 0.0);
}

TEST(RateLimiterTest, TokenRefill) {
    auto agent = std::make_shared<TestAgent>();

    auto config = RateLimiterConfig::builder()
        .rate_per_second(10.0)  // 10 tokens/sec = 1 token per 100ms
        .capacity(5)
        .wait_for_tokens(false)
        .build();

    auto limiter = std::make_shared<RateLimiterMiddleware>(agent, config);

    // Exhaust tokens
    for (int i = 0; i < 5; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        limiter->process(message).get();
    }

    // Wait for refill
    std::this_thread::sleep_for(std::chrono::milliseconds(150));

    // Should succeed now
    auto message = Message::with_text("user", "test_after_refill");
    auto result = limiter->process(message).get();

    EXPECT_TRUE(result.is_ok());
}

TEST(RateLimiterTest, BurstCapacity) {
    auto agent = std::make_shared<TestAgent>();

    auto config = RateLimiterConfig::builder()
        .rate_per_second(1.0)  // Slow rate
        .capacity(10)          // But large burst
        .wait_for_tokens(false)
        .build();

    auto limiter = std::make_shared<RateLimiterMiddleware>(agent, config);

    // Can burst up to capacity
    int successes = 0;
    for (int i = 0; i < 10; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        auto result = limiter->process(message).get();
        if (result.is_ok()) {
            successes++;
        }
    }

    EXPECT_EQ(successes, 10);
}

TEST(RateLimiterTest, Metrics) {
    auto agent = std::make_shared<TestAgent>();

    auto config = RateLimiterConfig::builder()
        .rate_per_second(5.0)
        .capacity(5)
        .wait_for_tokens(false)
        .build();

    auto limiter = std::make_shared<RateLimiterMiddleware>(agent, config);

    for (int i = 0; i < 10; i++) {
        auto message = Message::with_text("user", "test" + std::to_string(i));
        limiter->process(message).get();
    }

    auto metrics = limiter->metrics().snapshot(limiter->current_tokens());
    EXPECT_EQ(metrics.total_requests, 10);
    EXPECT_GE(metrics.current_tokens, 0.0);
    EXPECT_LE(metrics.current_tokens, 5.0);
}

// ============================================================================
// CachingMiddleware Tests
// ============================================================================

TEST(CachingMiddlewareTest, CacheMiss) {
    auto agent = std::make_shared<TestAgent>();

    auto config = CachingConfig::builder()
        .max_cache_size(10)
        .default_ttl(std::chrono::seconds(60))
        .build();

    auto caching = std::make_shared<CachingMiddleware>(agent, config);

    auto message = Message::with_text("user", "test");
    auto result = caching->process(message).get();

    EXPECT_TRUE(result.is_ok());
    EXPECT_EQ(agent->request_count(), 1);

    auto metrics = caching->metrics().snapshot(caching->cache_size());
    EXPECT_EQ(metrics.cache_misses, 1);
}

TEST(CachingMiddlewareTest, CacheHit) {
    auto agent = std::make_shared<TestAgent>();

    auto config = CachingConfig::builder()
        .max_cache_size(10)
        .default_ttl(std::chrono::seconds(60))
        .build();

    auto caching = std::make_shared<CachingMiddleware>(agent, config);

    auto message = Message::with_text("user", "test");

    // First request - cache miss
    caching->process(message).get();

    // Second request - cache hit
    caching->process(message).get();

    EXPECT_EQ(agent->request_count(), 1);  // Only called once

    auto metrics = caching->metrics().snapshot(caching->cache_size());
    EXPECT_EQ(metrics.cache_hits, 1);
    EXPECT_EQ(metrics.cache_misses, 1);
    EXPECT_GT(metrics.hit_rate, 0.0);
}

TEST(CachingMiddlewareTest, LRUEviction) {
    auto agent = std::make_shared<TestAgent>();

    auto config = CachingConfig::builder()
        .max_cache_size(3)
        .default_ttl(std::chrono::seconds(60))
        .build();

    auto caching = std::make_shared<CachingMiddleware>(agent, config);

    // Fill cache
    caching->process(Message::with_text("user", "A")).get();
    caching->process(Message::with_text("user", "B")).get();
    caching->process(Message::with_text("user", "C")).get();

    // Access A to make it recently used
    caching->process(Message::with_text("user", "A")).get();

    // Add D - should evict B (least recently used)
    caching->process(Message::with_text("user", "D")).get();

    EXPECT_EQ(caching->cache_size(), 3);

    auto metrics = caching->metrics().snapshot(caching->cache_size());
    EXPECT_GT(metrics.cache_evictions, 0);
}

TEST(CachingMiddlewareTest, TTLExpiration) {
    auto agent = std::make_shared<TestAgent>();

    auto config = CachingConfig::builder()
        .max_cache_size(10)
        .default_ttl(std::chrono::milliseconds(50))
        .build();

    auto caching = std::make_shared<CachingMiddleware>(agent, config);

    auto message = Message::with_text("user", "test");

    // First request
    caching->process(message).get();

    // Wait for TTL to expire
    std::this_thread::sleep_for(std::chrono::milliseconds(60));

    // Second request - should be cache miss (expired)
    caching->process(message).get();

    EXPECT_EQ(agent->request_count(), 2);  // Called twice

    auto metrics = caching->metrics().snapshot(caching->cache_size());
    EXPECT_EQ(metrics.cache_misses, 2);
}

TEST(CachingMiddlewareTest, HitRate) {
    auto agent = std::make_shared<TestAgent>();

    auto config = CachingConfig::builder()
        .max_cache_size(10)
        .default_ttl(std::chrono::seconds(60))
        .build();

    auto caching = std::make_shared<CachingMiddleware>(agent, config);

    // Make 3 unique requests (misses)
    caching->process(Message::with_text("user", "A")).get();
    caching->process(Message::with_text("user", "B")).get();
    caching->process(Message::with_text("user", "C")).get();

    // Repeat them (hits)
    caching->process(Message::with_text("user", "A")).get();
    caching->process(Message::with_text("user", "B")).get();
    caching->process(Message::with_text("user", "C")).get();

    auto metrics = caching->metrics().snapshot(caching->cache_size());
    EXPECT_EQ(metrics.cache_hits, 3);
    EXPECT_EQ(metrics.cache_misses, 3);
    EXPECT_DOUBLE_EQ(metrics.hit_rate, 0.5);  // 50% hit rate
}

// ============================================================================
// Middleware Composition Tests
// ============================================================================

TEST(MiddlewareCompositionTest, RetryWithTimeout) {
    auto agent = std::make_shared<TestAgent>(0.0, std::chrono::milliseconds(200));

    // Timeout first, then retry
    auto timeout_config = TimeoutConfig::builder()
        .default_timeout(std::chrono::milliseconds(50))
        .build();
    auto timeout_agent = std::make_shared<TimeoutMiddleware>(agent, timeout_config);

    auto retry_config = RetryConfig::builder()
        .max_attempts(3)
        .initial_backoff(std::chrono::milliseconds(1))
        .build();
    auto retry_agent = std::make_shared<RetryMiddleware>(timeout_agent, retry_config);

    auto message = Message::with_text("user", "test");
    auto result = retry_agent->process(message).get();

    // Should timeout on all attempts
    EXPECT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err().type(), AgentErrorType::Timeout);
}

TEST(MiddlewareCompositionTest, CachingWithRateLimiter) {
    auto agent = std::make_shared<TestAgent>();

    // Caching innermost
    auto cache_config = CachingConfig::builder()
        .max_cache_size(10)
        .default_ttl(std::chrono::seconds(60))
        .build();
    auto caching = std::make_shared<CachingMiddleware>(agent, cache_config);

    // Rate limiter outermost
    auto limiter_config = RateLimiterConfig::builder()
        .rate_per_second(5.0)
        .capacity(5)
        .wait_for_tokens(false)
        .build();
    auto composed = std::make_shared<RateLimiterMiddleware>(caching, limiter_config);

    // First 5 should succeed (within rate limit)
    for (int i = 0; i < 5; i++) {
        auto message = Message::with_text("user", "test");
        auto result = composed->process(message).get();
        EXPECT_TRUE(result.is_ok());
    }

    // Next should be rate limited
    auto message = Message::with_text("user", "test");
    auto result = composed->process(message).get();
    EXPECT_TRUE(result.is_err());

    // Agent should only be called once (cached)
    EXPECT_EQ(agent->request_count(), 1);
}

TEST(MiddlewareCompositionTest, FullStack) {
    auto agent = std::make_shared<TestAgent>(0.1, std::chrono::milliseconds(5));

    // Build full stack: Caching -> Rate Limiter -> Circuit Breaker -> Timeout -> Retry
    std::shared_ptr<Agent> composed = agent;

    auto cache_config = CachingConfig::builder()
        .max_cache_size(100)
        .default_ttl(std::chrono::minutes(5))
        .build();
    auto caching = std::make_shared<CachingMiddleware>(composed, cache_config);
    composed = caching;

    auto limiter_config = RateLimiterConfig::builder()
        .rate_per_second(20.0)
        .capacity(20)
        .build();
    auto limiter = std::make_shared<RateLimiterMiddleware>(composed, limiter_config);
    composed = limiter;

    auto breaker_config = CircuitBreakerConfig::builder()
        .failure_threshold(10)
        .recovery_timeout(std::chrono::seconds(60))
        .build();
    auto breaker = std::make_shared<CircuitBreakerMiddleware>(composed, breaker_config);
    composed = breaker;

    auto timeout_config = TimeoutConfig::builder()
        .default_timeout(std::chrono::seconds(1))
        .build();
    auto timeout_agent = std::make_shared<TimeoutMiddleware>(composed, timeout_config);
    composed = timeout_agent;

    auto retry_config = RetryConfig::builder()
        .max_attempts(3)
        .initial_backoff(std::chrono::milliseconds(10))
        .build();
    auto retry = std::make_shared<RetryMiddleware>(composed, retry_config);
    composed = retry;

    // Make requests
    int successes = 0;
    for (int i = 0; i < 10; i++) {
        auto message = Message::with_text("user", "request" + std::to_string(i % 3));
        auto result = composed->process(message).get();
        if (result.is_ok()) {
            successes++;
        }
    }

    EXPECT_GT(successes, 0);
    EXPECT_EQ(breaker->state(), CircuitState::CLOSED);
}

// ============================================================================
// Thread Safety Tests
// ============================================================================

TEST(MiddlewareThreadSafetyTest, ConcurrentRetry) {
    auto agent = std::make_shared<TestAgent>(0.2, std::chrono::milliseconds(1));

    auto config = RetryConfig::builder()
        .max_attempts(3)
        .initial_backoff(std::chrono::milliseconds(1))
        .build();

    auto retry_agent = std::make_shared<RetryMiddleware>(agent, config);

    std::vector<std::thread> threads;
    std::atomic<int> successes{0};

    for (int t = 0; t < 5; t++) {
        threads.emplace_back([&retry_agent, &successes]() {
            for (int i = 0; i < 10; i++) {
                auto message = Message::with_text("user", "test");
                auto result = retry_agent->process(message).get();
                if (result.is_ok()) {
                    successes++;
                }
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    EXPECT_GT(successes.load(), 0);
}

TEST(MiddlewareThreadSafetyTest, ConcurrentCaching) {
    auto agent = std::make_shared<TestAgent>();

    auto config = CachingConfig::builder()
        .max_cache_size(50)
        .default_ttl(std::chrono::seconds(60))
        .build();

    auto caching = std::make_shared<CachingMiddleware>(agent, config);

    std::vector<std::thread> threads;

    for (int t = 0; t < 10; t++) {
        threads.emplace_back([&caching, t]() {
            for (int i = 0; i < 20; i++) {
                auto key = "key" + std::to_string(i % 5);
                auto message = Message::with_text("user", key);
                caching->process(message).get();
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    // Should have high hit rate due to repeated keys
    auto metrics = caching->metrics().snapshot(caching->cache_size());
    EXPECT_GT(metrics.hit_rate, 0.5);
}

TEST(MiddlewareThreadSafetyTest, ConcurrentCircuitBreaker) {
    auto agent = std::make_shared<TestAgent>(0.3, std::chrono::milliseconds(1));

    auto config = CircuitBreakerConfig::builder()
        .failure_threshold(10)
        .success_threshold(3)
        .recovery_timeout(std::chrono::milliseconds(100))
        .build();

    auto breaker = std::make_shared<CircuitBreakerMiddleware>(agent, config);

    std::vector<std::thread> threads;

    for (int t = 0; t < 5; t++) {
        threads.emplace_back([&breaker]() {
            for (int i = 0; i < 20; i++) {
                auto message = Message::with_text("user", "test");
                breaker->process(message).get();
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    // Should complete without crashes
    auto metrics = breaker->metrics().snapshot(breaker->state());
    EXPECT_EQ(metrics.total_requests, 100);
}

// ============================================================================
// MetricsMiddleware Tests
// ============================================================================

TEST(MetricsMiddlewareTest, InitialMetricsAreZero) {
    auto agent = std::make_shared<TestAgent>();
    auto metrics = std::make_shared<MetricsMiddleware>(agent);

    auto snap = metrics->get_metrics();
    EXPECT_EQ(snap.total_requests, 0u);
    EXPECT_EQ(snap.success_requests, 0u);
    EXPECT_EQ(snap.error_requests, 0u);
    EXPECT_EQ(snap.in_flight, 0u);
    EXPECT_DOUBLE_EQ(snap.avg_latency_ms, 0.0);
}

TEST(MetricsMiddlewareTest, CountsSuccessfulRequests) {
    auto agent = std::make_shared<TestAgent>(0.0); // 0% failure
    auto metrics = std::make_shared<MetricsMiddleware>(agent);

    auto msg = Message::with_text("user", "hello");
    metrics->process(msg).get();
    metrics->process(msg).get();

    auto snap = metrics->get_metrics();
    EXPECT_EQ(snap.total_requests, 2u);
    EXPECT_EQ(snap.success_requests, 2u);
    EXPECT_EQ(snap.error_requests, 0u);
    EXPECT_DOUBLE_EQ(snap.success_rate(), 1.0);
}

TEST(MetricsMiddlewareTest, CountsErrorRequests) {
    auto agent = std::make_shared<TestAgent>(1.0); // 100% failure
    auto metrics = std::make_shared<MetricsMiddleware>(agent);

    auto msg = Message::with_text("user", "hello");
    metrics->process(msg).get();
    metrics->process(msg).get();

    auto snap = metrics->get_metrics();
    EXPECT_EQ(snap.total_requests, 2u);
    EXPECT_EQ(snap.success_requests, 0u);
    EXPECT_EQ(snap.error_requests, 2u);
    EXPECT_DOUBLE_EQ(snap.success_rate(), 0.0);
}

TEST(MetricsMiddlewareTest, TracksLatency) {
    // Use a 5ms delay agent so latency is measurable
    auto agent = std::make_shared<TestAgent>(0.0, std::chrono::milliseconds(5));
    auto metrics = std::make_shared<MetricsMiddleware>(agent);

    auto msg = Message::with_text("user", "hello");
    metrics->process(msg).get();
    metrics->process(msg).get();
    metrics->process(msg).get();

    auto snap = metrics->get_metrics();
    EXPECT_GT(snap.min_latency_ms, 0.0);
    EXPECT_GE(snap.max_latency_ms, snap.min_latency_ms);
    EXPECT_GE(snap.avg_latency_ms, snap.min_latency_ms);
    EXPECT_LE(snap.avg_latency_ms, snap.max_latency_ms);
}

TEST(MetricsMiddlewareTest, ResetClearsAllCounters) {
    auto agent = std::make_shared<TestAgent>(0.0);
    auto metrics = std::make_shared<MetricsMiddleware>(agent);

    auto msg = Message::with_text("user", "hello");
    metrics->process(msg).get();
    metrics->process(msg).get();

    metrics->reset_metrics();

    auto snap = metrics->get_metrics();
    EXPECT_EQ(snap.total_requests, 0u);
    EXPECT_EQ(snap.success_requests, 0u);
    EXPECT_EQ(snap.error_requests, 0u);
    EXPECT_DOUBLE_EQ(snap.avg_latency_ms, 0.0);
}

TEST(MetricsMiddlewareTest, DelegatesAgentName) {
    auto agent = std::make_shared<TestAgent>();
    auto metrics = std::make_shared<MetricsMiddleware>(agent);
    EXPECT_EQ(metrics->name(), "test_agent");
}

TEST(MetricsMiddlewareTest, InFlightIsZeroAfterCompletion) {
    auto agent = std::make_shared<TestAgent>(0.0);
    auto metrics = std::make_shared<MetricsMiddleware>(agent);

    auto msg = Message::with_text("user", "hello");
    metrics->process(msg).get();

    auto snap = metrics->get_metrics();
    EXPECT_EQ(snap.in_flight, 0u);
}

TEST(MetricsMiddlewareTest, MixedSuccessAndErrors) {
    // Use 50% failure with deterministic seed
    auto agent = std::make_shared<TestAgent>(0.5, std::chrono::milliseconds(0), true);
    auto metrics = std::make_shared<MetricsMiddleware>(agent);

    auto msg = Message::with_text("user", "hello");
    for (int i = 0; i < 10; i++) {
        metrics->process(msg).get();
    }

    auto snap = metrics->get_metrics();
    EXPECT_EQ(snap.total_requests, 10u);
    EXPECT_EQ(snap.success_requests + snap.error_requests, 10u);
    EXPECT_GE(snap.success_rate(), 0.0);
    EXPECT_LE(snap.success_rate(), 1.0);
}
