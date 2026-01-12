/**
 * Middleware for agent wrapping.
 *
 * Provides cross-cutting concerns like retry logic, circuit breaking,
 * timeouts, caching, batching, metrics, and rate limiting.
 */

// Base middleware utilities
export { Middleware, applyMiddleware, BaseMiddleware } from './base';

// Circuit breaker
export {
  CircuitBreakerMiddleware,
  CircuitBreakerConfig,
  CircuitState,
  CircuitBreakerError,
  CircuitBreakerMetrics,
  circuitBreaker,
} from './circuit-breaker';

// Retry
export {
  RetryMiddleware,
  RetryConfig,
  RetryMetrics,
  retry,
} from './retry';

// Timeout
export {
  TimeoutMiddleware,
  TimeoutConfig,
  TimeoutError,
  TimeoutMetrics,
  timeout,
} from './timeout';

// Batching
export {
  BatchingDecorator,
  BatchingConfig,
  BatchingMetrics,
} from './batching';

// Caching
export {
  CachingDecorator,
  CachingConfig,
  CachingMetrics,
} from './caching';

// Metrics
export {
  MetricsDecorator,
  Metrics,
} from './metrics';

// Rate limiting
export {
  RateLimiterDecorator,
  RateLimiterConfig,
  RateLimiterMetrics,
  RateLimitError,
} from './rate-limiter';

// Per-user rate limiting
export {
  PerUserRateLimiterDecorator,
  PerUserRateLimiterConfig,
  PerUserRateLimiterMetrics,
  PerUserRateLimitError,
  GlobalRateLimitError,
} from './per-user-rate-limiter';
