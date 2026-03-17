package io.agenkit.middleware

import io.agenkit.core.Agent
import scala.concurrent.duration.*

/** Fluent extension methods that wrap an agent with middleware. */
extension (agent: Agent)
  def withRetry(maxAttempts: Int = 3): Agent =
    RetryMiddleware(agent, maxAttempts)

  def withTimeout(duration: FiniteDuration): Agent =
    TimeoutMiddleware(agent, duration)

  def withCircuitBreaker(threshold: Int = 5): Agent =
    CircuitBreakerMiddleware(agent, threshold)

  def withCaching(ttl: FiniteDuration): Agent =
    CachingMiddleware(agent, ttl)

  def withRateLimit(rps: Int): Agent =
    RateLimiterMiddleware(agent, rps)

  def withMetrics(prefix: String = ""): Agent =
    MetricsMiddleware(agent, prefix)
