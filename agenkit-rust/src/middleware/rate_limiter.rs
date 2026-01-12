//! Rate limiter middleware using token bucket algorithm.
//!
//! Controls the rate of requests to prevent overwhelming downstream services,
//! respecting API rate limits, and ensuring fair resource allocation.
//!
//! # Algorithm: Token Bucket
//!
//! The token bucket algorithm maintains a bucket of tokens that refill at a constant rate:
//! - Each request consumes one token
//! - Tokens refill at `tokens_per_second` rate
//! - Maximum bucket capacity is `capacity`
//! - Requests wait if no tokens available (up to max_wait_time)
//!
//! **Example**: 10 tokens/second, capacity=20
//! - Allows bursts up to 20 requests instantly
//! - Sustained rate limited to 10 requests/second
//! - Smooths out traffic spikes
//!
//! # When to Use
//!
//! - **API rate limits**: Stay within provider limits (OpenAI, Anthropic, etc.)
//! - **Resource protection**: Prevent overwhelming downstream services
//! - **Cost control**: Limit spend on pay-per-request APIs
//! - **Fair sharing**: Ensure fair resource allocation across clients
//!
//! # When NOT to Use
//!
//! - **No rate limits**: When downstream has no rate constraints
//! - **Single request**: For one-off operations
//! - **Already limited**: When using provider's native rate limiting
//!
//! # Example
//!
//! ```rust
//! use agenkit::middleware::{RateLimiterMiddleware, RateLimiterConfig};
//! use agenkit::core::{Agent, Message};
//! use std::time::Duration;
//!
//! # async fn example() {
//! # struct MyAgent;
//! # #[async_trait::async_trait]
//! # impl Agent for MyAgent {
//! #     fn name(&self) -> &str { "test" }
//! #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> {
//! #         Ok(Message::with_text("assistant", "ok"))
//! #     }
//! # }
//! let agent = MyAgent;
//!
//! let config = RateLimiterConfig::builder()
//!     .tokens_per_second(10.0)  // 10 requests/second
//!     .capacity(20.0)            // Allow bursts up to 20
//!     .max_wait_time(Duration::from_secs(5))
//!     .build();
//!
//! let rl_agent = RateLimiterMiddleware::new(agent, config);
//!
//! // Requests are rate-limited to 10/second
//! let msg = Message::with_text("user", "Hello");
//! let response = rl_agent.process(msg).await;
//! # }
//! ```

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;

/// Configuration for rate limiter middleware.
#[derive(Debug, Clone)]
pub struct RateLimiterConfig {
    /// Tokens refilled per second (rate limit).
    /// Default: 10.0 tokens/second
    pub tokens_per_second: f64,

    /// Maximum bucket capacity (allows bursts).
    /// Default: Same as tokens_per_second
    pub capacity: f64,

    /// Maximum time to wait for a token.
    /// Default: 30 seconds
    pub max_wait_time: Duration,
}

impl Default for RateLimiterConfig {
    fn default() -> Self {
        Self {
            tokens_per_second: 10.0,
            capacity: 10.0,
            max_wait_time: Duration::from_secs(30),
        }
    }
}

impl RateLimiterConfig {
    /// Create a new builder for RateLimiterConfig.
    pub fn builder() -> RateLimiterConfigBuilder {
        RateLimiterConfigBuilder::default()
    }
}

/// Builder for RateLimiterConfig.
#[derive(Debug, Default)]
pub struct RateLimiterConfigBuilder {
    tokens_per_second: Option<f64>,
    capacity: Option<f64>,
    max_wait_time: Option<Duration>,
}

impl RateLimiterConfigBuilder {
    /// Set tokens per second (rate limit).
    pub fn tokens_per_second(mut self, rate: f64) -> Self {
        self.tokens_per_second = Some(rate);
        self
    }

    /// Set bucket capacity (burst size).
    pub fn capacity(mut self, capacity: f64) -> Self {
        self.capacity = Some(capacity);
        self
    }

    /// Set maximum wait time.
    pub fn max_wait_time(mut self, time: Duration) -> Self {
        self.max_wait_time = Some(time);
        self
    }

    /// Build the RateLimiterConfig.
    pub fn build(self) -> RateLimiterConfig {
        let default = RateLimiterConfig::default();
        let tokens_per_second = self.tokens_per_second.unwrap_or(default.tokens_per_second);
        RateLimiterConfig {
            tokens_per_second,
            capacity: self.capacity.unwrap_or(tokens_per_second), // Default capacity = rate
            max_wait_time: self.max_wait_time.unwrap_or(default.max_wait_time),
        }
    }
}

/// Metrics for rate limiter middleware.
#[derive(Debug, Clone, Default)]
pub struct RateLimiterMetrics {
    /// Total number of requests processed.
    pub total_requests: u64,

    /// Number of requests that were allowed immediately.
    pub allowed_requests: u64,

    /// Number of requests that were rejected (exceeded max wait time).
    pub rejected_requests: u64,

    /// Number of requests that had to wait for tokens.
    pub waited_requests: u64,

    /// Total time spent waiting for tokens (in milliseconds).
    pub total_wait_time_ms: u64,

    /// Current number of tokens in the bucket.
    pub current_tokens: f64,
}

impl RateLimiterMetrics {
    /// Calculate average wait time per request (in milliseconds).
    pub fn avg_wait_time_ms(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            self.total_wait_time_ms as f64 / self.total_requests as f64
        }
    }

    /// Calculate wait rate (percentage of requests that waited).
    pub fn wait_rate(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            (self.waited_requests as f64 / self.total_requests as f64) * 100.0
        }
    }

    /// Calculate rejection rate (percentage of requests rejected).
    pub fn rejection_rate(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            (self.rejected_requests as f64 / self.total_requests as f64) * 100.0
        }
    }
}

/// Internal state for rate limiter.
#[derive(Debug)]
struct RateLimiterState {
    tokens: f64,
    last_refill: Instant,
    metrics: RateLimiterMetrics,
}

impl RateLimiterState {
    fn new(initial_tokens: f64) -> Self {
        Self {
            tokens: initial_tokens,
            last_refill: Instant::now(),
            metrics: RateLimiterMetrics {
                current_tokens: initial_tokens,
                ..Default::default()
            },
        }
    }

    /// Refill tokens based on elapsed time.
    fn refill(&mut self, tokens_per_second: f64, capacity: f64) {
        let now = Instant::now();
        let elapsed = now.duration_since(self.last_refill).as_secs_f64();
        let new_tokens = elapsed * tokens_per_second;

        self.tokens = (self.tokens + new_tokens).min(capacity);
        self.last_refill = now;
        self.metrics.current_tokens = self.tokens;
    }

    /// Try to consume a token.
    fn try_consume(&mut self) -> bool {
        if self.tokens >= 1.0 {
            self.tokens -= 1.0;
            true
        } else {
            false
        }
    }

    /// Calculate wait time until next token is available.
    fn time_until_token(&self, tokens_per_second: f64) -> Duration {
        if self.tokens >= 1.0 {
            Duration::ZERO
        } else {
            let tokens_needed = 1.0 - self.tokens;
            let seconds = tokens_needed / tokens_per_second;
            Duration::from_secs_f64(seconds)
        }
    }
}

/// Rate limiter middleware using token bucket algorithm.
///
/// Controls request rate to prevent overwhelming downstream services,
/// respecting API rate limits, and ensuring predictable resource usage.
pub struct RateLimiterMiddleware<A: Agent> {
    inner: A,
    config: RateLimiterConfig,
    state: Arc<Mutex<RateLimiterState>>,
}

impl<A: Agent> RateLimiterMiddleware<A> {
    /// Create a new rate limiter middleware with the given agent and configuration.
    pub fn new(agent: A, config: RateLimiterConfig) -> Self {
        Self {
            inner: agent,
            state: Arc::new(Mutex::new(RateLimiterState::new(config.capacity))),
            config,
        }
    }

    /// Create a new rate limiter middleware with default configuration.
    pub fn with_defaults(agent: A) -> Self {
        Self::new(agent, RateLimiterConfig::default())
    }

    /// Get current rate limiter metrics.
    pub async fn get_metrics(&self) -> RateLimiterMetrics {
        let state = self.state.lock().await;
        state.metrics.clone()
    }
}

#[async_trait]
impl<A: Agent> Agent for RateLimiterMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    fn capabilities(&self) -> Vec<String> {
        self.inner.capabilities()
    }

    fn introspect(&self) -> IntrospectionResult {
        let mut result = self.inner.introspect();
        result.metadata.insert(
            "middleware".to_string(),
            serde_json::json!("rate_limiter"),
        );
        result.metadata.insert(
            "rate_limiter_config".to_string(),
            serde_json::json!({
                "tokens_per_second": self.config.tokens_per_second,
                "capacity": self.config.capacity,
                "max_wait_time_ms": self.config.max_wait_time.as_millis(),
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        #[cfg(feature = "native")]
        {
            let start_wait = Instant::now();
            let mut waited = false;

            // Track total requests
            {
                let mut state = self.state.lock().await;
                state.metrics.total_requests += 1;
            }

            loop {
                let mut state = self.state.lock().await;

                // Refill tokens based on elapsed time
                state.refill(self.config.tokens_per_second, self.config.capacity);

                // Try to consume a token
                if state.try_consume() {
                    // Track metrics for successful acquisition
                    if waited {
                        state.metrics.waited_requests += 1;
                        let wait_time_ms = start_wait.elapsed().as_millis() as u64;
                        state.metrics.total_wait_time_ms += wait_time_ms;
                    } else {
                        state.metrics.allowed_requests += 1;
                    }
                    drop(state); // Release lock before calling inner agent
                    return self.inner.process(message).await;
                }

                // Check if we've exceeded max wait time
                if start_wait.elapsed() >= self.config.max_wait_time {
                    state.metrics.rejected_requests += 1;
                    return Err(AgentError::ProcessingError(
                        "rate limit exceeded: max wait time reached".to_string(),
                    ));
                }

                // Calculate wait time
                let wait_time = state.time_until_token(self.config.tokens_per_second);
                let remaining_time = self
                    .config
                    .max_wait_time
                    .saturating_sub(start_wait.elapsed());
                let actual_wait = wait_time.min(remaining_time);

                drop(state); // Release lock while waiting

                if actual_wait > Duration::ZERO {
                    waited = true;
                    tokio::time::sleep(actual_wait).await;
                }
            }
        }

        #[cfg(feature = "wasm")]
        {
            // WASM doesn't support tokio::time::sleep directly
            // For now, just call the inner agent without rate limiting
            // TODO: Implement rate limiting for WASM
            self.inner.process(message).await
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};

    struct CountingAgent {
        attempts: Arc<AtomicU32>,
    }

    impl CountingAgent {
        fn new() -> Self {
            Self {
                attempts: Arc::new(AtomicU32::new(0)),
            }
        }

        fn attempt_count(&self) -> u32 {
            self.attempts.load(Ordering::SeqCst)
        }
    }

    #[async_trait]
    impl Agent for CountingAgent {
        fn name(&self) -> &str {
            "counting"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            self.attempts.fetch_add(1, Ordering::SeqCst);
            Ok(Message::with_text("assistant", "success"))
        }
    }

    #[tokio::test]
    async fn test_rate_limiter_allows_within_limit() {
        let agent = CountingAgent::new();
        let config = RateLimiterConfig::builder()
            .tokens_per_second(10.0)
            .capacity(5.0)
            .build();

        let rl_agent = RateLimiterMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // Should allow up to capacity immediately
        for _ in 0..5 {
            let result = rl_agent.process(msg.clone()).await;
            assert!(result.is_ok());
        }

        assert_eq!(rl_agent.inner.attempt_count(), 5);
    }

    #[tokio::test]
    async fn test_rate_limiter_waits_when_empty() {
        let agent = CountingAgent::new();
        let config = RateLimiterConfig::builder()
            .tokens_per_second(10.0) // 10 tokens/sec = 100ms/token
            .capacity(1.0)
            .build();

        let rl_agent = RateLimiterMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // First request should succeed immediately
        let start = Instant::now();
        let result = rl_agent.process(msg.clone()).await;
        assert!(result.is_ok());

        // Second request should wait ~100ms for token
        let result = rl_agent.process(msg.clone()).await;
        let elapsed = start.elapsed();

        assert!(result.is_ok());
        assert!(elapsed >= Duration::from_millis(90)); // Allow some timing variance
        assert_eq!(rl_agent.inner.attempt_count(), 2);
    }

    #[tokio::test]
    async fn test_rate_limiter_fails_after_max_wait() {
        let agent = CountingAgent::new();
        let config = RateLimiterConfig::builder()
            .tokens_per_second(1.0) // Very slow
            .capacity(0.0) // No initial tokens
            .max_wait_time(Duration::from_millis(100))
            .build();

        let rl_agent = RateLimiterMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = rl_agent.process(msg).await;

        assert!(result.is_err());
        assert!(matches!(
            result.unwrap_err(),
            AgentError::ProcessingError(_)
        ));
    }

    #[tokio::test]
    async fn test_rate_limiter_refills_over_time() {
        let agent = CountingAgent::new();
        let config = RateLimiterConfig::builder()
            .tokens_per_second(10.0)
            .capacity(2.0)
            .build();

        let rl_agent = RateLimiterMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // Consume initial tokens
        let _ = rl_agent.process(msg.clone()).await;
        let _ = rl_agent.process(msg.clone()).await;

        // Wait for refill (200ms = 2 tokens at 10/sec)
        tokio::time::sleep(Duration::from_millis(200)).await;

        // Should have refilled ~2 tokens
        let result = rl_agent.process(msg.clone()).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_introspect_includes_rate_limiter_metadata() {
        let agent = CountingAgent::new();
        let config = RateLimiterConfig::builder()
            .tokens_per_second(5.0)
            .capacity(10.0)
            .build();

        let rl_agent = RateLimiterMiddleware::new(agent, config);
        let result = rl_agent.introspect();

        assert_eq!(
            result.metadata.get("middleware"),
            Some(&serde_json::json!("rate_limiter"))
        );
        assert!(result.metadata.contains_key("rate_limiter_config"));
    }
}
