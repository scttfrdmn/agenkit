/**
 * @file middleware_properties_test.cpp
 * @brief Property-based tests for middleware behavior invariants using RapidCheck
 *
 * Verifies that RetryMiddleware and CircuitBreakerMiddleware uphold their contracts
 * under arbitrary configurations and call sequences.
 */

#include <gtest/gtest.h>
#include <rapidcheck.h>
#include <rapidcheck/gtest.h>
#include "../patterns/test_pattern_helpers.hpp"
#include "agenkit/middleware/retry.hpp"
#include "agenkit/middleware/circuit_breaker.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <atomic>
#include <memory>
#include <string>

using namespace agenkit;

namespace {

// Build a fast retry config (1ms backoffs) to keep property tests quick
middleware::RetryConfig fast_retry_config(uint32_t max_attempts) {
    return middleware::RetryConfig::builder()
        .max_attempts(max_attempts)
        .initial_backoff(std::chrono::milliseconds(1))
        .max_backoff(std::chrono::milliseconds(1))
        .backoff_multiplier(1.01)
        .enable_jitter(false)
        .build();
}

} // namespace

// 1. Retry never calls the underlying agent more than max_attempts times
RC_GTEST_PROP(MiddlewareProperties, RetryAttemptsNeverExceedMax, ()) {
    uint32_t max_attempts = *rc::gen::inRange<uint32_t>(1, 4); // 1..3

    std::atomic<int> call_count{0};
    auto counting_agent = std::make_shared<test::MockAgent>(
        "counter",
        [&call_count](const core::Message& /*msg*/) -> core::Result<core::Message, core::AgentError> {
            call_count.fetch_add(1);
            return core::Result<core::Message, core::AgentError>::err(
                core::AgentError(core::AgentErrorType::Internal, "always fail")
            );
        }
    );

    auto retry = std::make_shared<middleware::RetryMiddleware>(
        counting_agent, fast_retry_config(max_attempts)
    );
    auto msg = core::Message::with_text("user", "test");
    retry->process(msg).get();

    RC_ASSERT(call_count.load() <= static_cast<int>(max_attempts));
}

// 2. A successful agent wrapped in retry always succeeds
RC_GTEST_PROP(MiddlewareProperties, RetrySuccessOnFirstAlwaysSucceeds, (std::string text)) {
    auto agent = test::make_mock_agent("success", "ok");
    auto retry = std::make_shared<middleware::RetryMiddleware>(agent, fast_retry_config(3));
    auto msg = core::Message::with_text("user", text);
    auto result = retry->process(msg).get();
    RC_ASSERT(result.is_ok());
}

// 3. A consistently failing agent exhausts retries and returns error
RC_GTEST_PROP(MiddlewareProperties, RetryExhaustionAlwaysErrors, (std::string text)) {
    auto agent = test::make_failing_mock_agent("failing", "deliberate failure");
    auto retry = std::make_shared<middleware::RetryMiddleware>(agent, fast_retry_config(2));
    auto msg = core::Message::with_text("user", text);
    auto result = retry->process(msg).get();
    RC_ASSERT(result.is_err());
}

// 4. RetryConfig with max_attempts in [1..10] always validates successfully
RC_GTEST_PROP(MiddlewareProperties, RetryConfigMaxAttemptsBound, ()) {
    uint32_t attempts = *rc::gen::inRange<uint32_t>(1, 11); // 1..10
    middleware::RetryConfig config;
    config.max_attempts = attempts;
    // Should not throw
    EXPECT_NO_THROW(config.validate());
}

// 5. Backoff multipliers strictly above 1.0 pass validation
RC_GTEST_PROP(MiddlewareProperties, BackoffMultiplierAboveOne, ()) {
    // Map integers 1..9000 to doubles 1.001..10.0
    auto n = *rc::gen::inRange(1, 9001);
    double multiplier = 1.0 + static_cast<double>(n) / 1000.0;
    middleware::RetryConfig config;
    config.backoff_multiplier = multiplier;
    EXPECT_NO_THROW(config.validate());
}

// 6. Backoff multipliers at or below 1.0 fail validation
RC_GTEST_PROP(MiddlewareProperties, BackoffMultiplierAtOrBelowOne, ()) {
    // Map integers 1..1000 to doubles 0.001..1.0
    auto n = *rc::gen::inRange(1, 1001);
    double multiplier = static_cast<double>(n) / 1000.0;
    middleware::RetryConfig config;
    config.backoff_multiplier = multiplier;
    EXPECT_THROW(config.validate(), std::invalid_argument);
}

// 7. RetryMiddleware name() contains the wrapped agent's name
RC_GTEST_PROP(MiddlewareProperties, RetryNameContainsWrappedAgentName, (std::string name)) {
    RC_PRE(!name.empty());
    auto agent = test::make_mock_agent(name, "response");
    auto retry = std::make_shared<middleware::RetryMiddleware>(agent, fast_retry_config(1));
    RC_ASSERT(retry->name().find(name) != std::string::npos);
}

// 8. CircuitBreaker transitions to OPEN after threshold failures
RC_GTEST_PROP(MiddlewareProperties, CircuitBreakerOpenAfterThreshold, ()) {
    uint32_t threshold = *rc::gen::inRange<uint32_t>(1, 6); // 1..5

    auto failing_agent = test::make_failing_mock_agent("failing", "error");
    auto cb_config = middleware::CircuitBreakerConfig::builder()
        .failure_threshold(threshold)
        .success_threshold(1)
        .recovery_timeout(std::chrono::milliseconds(60000))
        .build();

    auto cb = std::make_shared<middleware::CircuitBreakerMiddleware>(failing_agent, cb_config);
    auto msg = core::Message::with_text("user", "test");

    for (uint32_t i = 0; i < threshold; ++i) {
        cb->process(msg).get();
    }

    RC_ASSERT(cb->state() == middleware::CircuitState::OPEN);
}

// 9. CircuitBreaker stays CLOSED after a single success
RC_GTEST_PROP(MiddlewareProperties, CircuitBreakerClosedOnSuccess, (std::string text)) {
    auto success_agent = test::make_mock_agent("success", "ok");
    auto cb_config = middleware::CircuitBreakerConfig::builder()
        .failure_threshold(5)
        .success_threshold(1)
        .recovery_timeout(std::chrono::milliseconds(60000))
        .build();

    auto cb = std::make_shared<middleware::CircuitBreakerMiddleware>(success_agent, cb_config);
    auto msg = core::Message::with_text("user", text);
    cb->process(msg).get();

    RC_ASSERT(cb->state() == middleware::CircuitState::CLOSED);
}

// 10. RetryConfig with max_attempts=0 throws on validate
RC_GTEST_PROP(MiddlewareProperties, RetryConfigInvalidMaxAttempts, ()) {
    middleware::RetryConfig config;
    config.max_attempts = 0;
    EXPECT_THROW(config.validate(), std::invalid_argument);
}

// 11. RetryConfig with initial_backoff > max_backoff throws on validate
RC_GTEST_PROP(MiddlewareProperties, RetryConfigInvalidBackoff, ()) {
    middleware::RetryConfig config;
    config.initial_backoff = std::chrono::milliseconds(1000);
    config.max_backoff = std::chrono::milliseconds(500);
    EXPECT_THROW(config.validate(), std::invalid_argument);
}

// 12. All RetryMetrics counters are non-negative after any number of calls
RC_GTEST_PROP(MiddlewareProperties, RetryMetricsNonNegative, ()) {
    auto n_calls = *rc::gen::inRange(0, 5);
    auto agent = test::make_mock_agent("agent", "response");
    auto retry = std::make_shared<middleware::RetryMiddleware>(agent, fast_retry_config(2));
    auto msg = core::Message::with_text("user", "test");

    for (int i = 0; i < n_calls; ++i) {
        retry->process(msg).get();
    }

    auto snap = retry->metrics().snapshot();
    RC_ASSERT(snap.total_attempts >= 0);
    RC_ASSERT(snap.total_retries >= 0);
    RC_ASSERT(snap.successful_on_retry >= 0);
    RC_ASSERT(snap.failed_after_retries >= 0);
}

// 13. At least one attempt is always recorded after a process() call
RC_GTEST_PROP(MiddlewareProperties, RetryTotalAttemptsAtLeastOne, (std::string text)) {
    auto agent = test::make_mock_agent("agent", "ok");
    auto retry = std::make_shared<middleware::RetryMiddleware>(agent, fast_retry_config(2));
    auto msg = core::Message::with_text("user", text);
    retry->process(msg).get();
    RC_ASSERT(retry->metrics().snapshot().total_attempts >= 1);
}

// 14. Middleware name() is never empty for any valid configuration
RC_GTEST_PROP(MiddlewareProperties, MiddlewareNameNeverEmpty, (std::string agent_name)) {
    RC_PRE(!agent_name.empty());
    auto agent = test::make_mock_agent(agent_name, "response");
    auto retry = std::make_shared<middleware::RetryMiddleware>(agent, fast_retry_config(1));
    RC_ASSERT(!retry->name().empty());
}

// 15. Retry wrapping a successful agent preserves the response content
RC_GTEST_PROP(MiddlewareProperties, SuccessPassthrough, (std::string response_text)) {
    RC_PRE(!response_text.empty());
    auto agent = test::make_mock_agent("agent", response_text);
    auto retry = std::make_shared<middleware::RetryMiddleware>(agent, fast_retry_config(3));
    auto msg = core::Message::with_text("user", "prompt");
    auto result = retry->process(msg).get();
    RC_ASSERT(result.is_ok());
    RC_ASSERT(result.unwrap().content_as_str() == response_text);
}
