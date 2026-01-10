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
  CircuitBreakerDecorator,
  CircuitBreakerConfig,
  CircuitBreakerState,
  CircuitBreakerError,
} from './circuit-breaker';

// Retry
export {
  RetryDecorator,
  RetryConfig,
  RetryStrategy,
  MaxRetriesExceededError,
} from './retry';

// Timeout
export {
  TimeoutDecorator,
  TimeoutConfig,
  TimeoutError,
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
