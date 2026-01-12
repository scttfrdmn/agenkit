//! Middleware for wrapping and enhancing agent behavior.
//!
//! This module provides production-ready middleware that can be composed with any agent
//! to add cross-cutting concerns like retry logic, circuit breaking, timeouts, rate limiting,
//! caching, and batching.
//!
//! # Design Philosophy
//!
//! - **Decorator Pattern**: Each middleware wraps an agent and implements the Agent trait
//! - **Zero Overhead**: Middleware adds minimal performance overhead
//! - **Composable**: Stack multiple middleware layers easily
//! - **Type-Safe**: Full Rust type safety with generics
//! - **Production-Ready**: Battle-tested algorithms (exponential backoff, token bucket, etc.)
//!
//! # Available Middleware
//!
//! - **Retry**: Automatic retry with exponential backoff for transient failures
//! - **Circuit Breaker**: Prevent cascading failures by opening circuit after threshold
//! - **Timeout**: Enforce time limits on agent operations
//! - **Rate Limiter**: Control request rate using token bucket algorithm
//! - **Caching**: Cache responses with TTL and LRU eviction
//! - **Batching**: Aggregate multiple requests for efficient processing
//!
//! # Example
//!
//! ```rust
//! use agenkit::middleware::{RetryMiddleware, RetryConfig};
//! use agenkit::core::{Agent, Message};
//! use std::time::Duration;
//!
//! async fn example(agent: impl Agent) {
//!     // Wrap agent with retry middleware
//!     let config = RetryConfig::builder()
//!         .max_attempts(5)
//!         .initial_delay(Duration::from_millis(100))
//!         .max_delay(Duration::from_secs(2))
//!         .multiplier(2.0)
//!         .build();
//!
//!     let retry_agent = RetryMiddleware::new(agent, config);
//!
//!     // Use as normal agent - retries happen automatically
//!     let msg = Message::with_text("user", "Hello");
//!     let response = retry_agent.process(msg).await.unwrap();
//! }
//! ```

pub mod retry;
pub mod circuit_breaker;
pub mod timeout;
pub mod rate_limiter;
pub mod caching;
pub mod batching;

pub use retry::{RetryConfig, RetryConfigBuilder, RetryMiddleware, RetryMetrics};
pub use circuit_breaker::{
    CircuitBreakerConfig,
    CircuitBreakerConfigBuilder,
    CircuitBreakerMiddleware,
    CircuitBreakerMetrics,
    CircuitState,
};
pub use timeout::{TimeoutConfig, TimeoutConfigBuilder, TimeoutMiddleware, TimeoutMetrics};
pub use rate_limiter::{RateLimiterConfig, RateLimiterConfigBuilder, RateLimiterMiddleware};
pub use caching::{CachingConfig, CachingConfigBuilder, CachingMiddleware};
pub use batching::{BatchingConfig, BatchingConfigBuilder, BatchingMiddleware};
