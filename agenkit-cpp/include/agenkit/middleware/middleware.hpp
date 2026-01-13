/**
 * @file middleware.hpp
 * @brief Composable middleware for agents
 *
 * This module provides production-ready middleware components that can be
 * composed to add resilience, performance, and observability to agents.
 *
 * ## Available Middleware
 *
 * ### Resilience
 * - **Retry**: Exponential backoff for transient failures
 * - **Timeout**: Time-based request cancellation
 * - **Circuit Breaker**: Cascading failure prevention
 *
 * ### Performance
 * - **Rate Limiter**: Token bucket rate limiting
 * - **Caching**: LRU cache with TTL expiration
 * - **Batching**: Request aggregation with parallel processing
 *
 * ## Design Pattern
 *
 * All middleware uses the Decorator pattern - each middleware wraps an Agent
 * and implements the Agent interface itself. This allows transparent composition:
 *
 * @code
 * // Create base agent
 * auto agent = std::make_shared<MyAgent>();
 *
 * // Add retry with exponential backoff
 * auto retry_config = RetryConfig::builder()
 *     .max_attempts(3)
 *     .initial_backoff(std::chrono::milliseconds(100))
 *     .build();
 * agent = std::make_shared<RetryMiddleware>(agent, retry_config);
 *
 * // Add timeout
 * auto timeout_config = TimeoutConfig::builder()
 *     .default_timeout(std::chrono::seconds(30))
 *     .build();
 * agent = std::make_shared<TimeoutMiddleware>(agent, timeout_config);
 *
 * // Add circuit breaker
 * auto breaker_config = CircuitBreakerConfig::builder()
 *     .failure_threshold(5)
 *     .recovery_timeout(std::chrono::seconds(60))
 *     .build();
 * agent = std::make_shared<CircuitBreakerMiddleware>(agent, breaker_config);
 *
 * // Add rate limiting
 * auto limiter_config = RateLimiterConfig::builder()
 *     .rate_per_second(10.0)
 *     .capacity(20)
 *     .build();
 * agent = std::make_shared<RateLimiterMiddleware>(agent, limiter_config);
 *
 * // Add caching
 * auto cache_config = CachingConfig::builder()
 *     .max_cache_size(1000)
 *     .default_ttl(std::chrono::minutes(5))
 *     .build();
 * agent = std::make_shared<CachingMiddleware>(agent, cache_config);
 *
 * // Use the fully wrapped agent
 * auto result = agent->process(message).get();
 * @endcode
 *
 * ## Composition Order
 *
 * Middleware composition order matters. Recommended ordering (innermost to outermost):
 *
 * 1. **Base Agent** - Your actual agent implementation
 * 2. **Caching** - Check cache before doing any work
 * 3. **Rate Limiter** - Limit requests before expensive operations
 * 4. **Circuit Breaker** - Fail fast if service is down
 * 5. **Timeout** - Enforce time limits on operations
 * 6. **Retry** - Retry failed operations with backoff
 *
 * Example:
 * @code
 * agent = retry(timeout(circuit_breaker(rate_limiter(caching(base_agent)))))
 * @endcode
 *
 * ## Thread Safety
 *
 * All middleware implementations are thread-safe:
 * - Retry: Atomic metrics
 * - Timeout: Atomic metrics
 * - Circuit Breaker: Mutex-protected state with atomic metrics
 * - Rate Limiter: Mutex-protected token bucket with atomic metrics
 * - Caching: shared_mutex for concurrent reads with atomic metrics
 *
 * ## Metrics
 *
 * Each middleware exposes metrics for observability:
 * @code
 * auto retry_middleware = std::make_shared<RetryMiddleware>(agent);
 * // ... use middleware ...
 * auto snapshot = retry_middleware->metrics().snapshot();
 * std::cout << "Total retries: " << snapshot.total_retries << "\n";
 * std::cout << "Success rate: " << snapshot.success_rate_after_retry << "\n";
 * @endcode
 *
 * ## Error Handling
 *
 * Middleware may generate specific error types:
 * - `TimeoutError`: Request exceeded time limit
 * - `CircuitBreakerError`: Circuit is open
 * - `RateLimitError`: Rate limit exceeded
 *
 * All errors inherit from `AgentError` and can be handled uniformly:
 * @code
 * auto result = agent->process(message).get();
 * if (result.is_err()) {
 *     auto error = result.error();
 *     if (error.code() == "timeout") {
 *         // Handle timeout
 *     } else if (error.code() == "circuit_breaker_open") {
 *         // Handle circuit breaker
 *     } else if (error.code() == "rate_limit_exceeded") {
 *         // Handle rate limit
 *     }
 * }
 * @endcode
 *
 * ## Configuration Patterns
 *
 * All middleware use the Builder pattern for configuration:
 * @code
 * auto config = RetryConfig::builder()
 *     .max_attempts(5)
 *     .initial_backoff(std::chrono::milliseconds(200))
 *     .max_backoff(std::chrono::seconds(30))
 *     .backoff_multiplier(2.5)
 *     .enable_jitter(true)
 *     .build();  // Validates configuration
 * @endcode
 *
 * ## Performance Characteristics
 *
 * Middleware overhead (typical):
 * - Retry: ~0µs (only on retries)
 * - Timeout: ~1-5µs (future wait overhead)
 * - Circuit Breaker: ~1-5µs (mutex lock + state check)
 * - Rate Limiter: ~5-10µs (mutex lock + token calculation)
 * - Caching: ~1-5µs on hit (shared_mutex read), normal request on miss
 *
 * ## Integration with Patterns
 *
 * Middleware works seamlessly with all agent patterns:
 * @code
 * // Wrap a conversational agent
 * auto conversational = std::make_shared<ConversationalAgent>(adapter);
 * conversational = std::make_shared<RetryMiddleware>(conversational);
 *
 * // Wrap a ReAct agent
 * auto react = std::make_shared<ReActAgent>(adapter);
 * react = std::make_shared<TimeoutMiddleware>(react);
 *
 * // Wrap any agent that implements the Agent interface
 * @endcode
 */

#pragma once

#include "agenkit/middleware/retry.hpp"
#include "agenkit/middleware/timeout.hpp"
#include "agenkit/middleware/circuit_breaker.hpp"
#include "agenkit/middleware/rate_limiter.hpp"
#include "agenkit/middleware/per_user_rate_limiter.hpp"
#include "agenkit/middleware/caching.hpp"
#include "agenkit/middleware/batching.hpp"

namespace agenkit {

/**
 * @brief Middleware components for composable agent enhancement
 *
 * This namespace contains all middleware implementations following
 * the decorator pattern for transparent composition.
 */
namespace middleware {

// All middleware types are already defined in their respective headers

} // namespace middleware
} // namespace agenkit
