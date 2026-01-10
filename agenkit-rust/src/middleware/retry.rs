//! Retry middleware with exponential backoff.
//!
//! Automatically retries failed requests with configurable exponential backoff,
//! useful for handling transient failures in external APIs, network issues, or
//! temporary service unavailability.
//!
//! # When to Use
//!
//! - **External API calls**: LLM providers, databases, web services
//! - **Network instability**: Transient network errors
//! - **Rate limiting**: API returns 429 status codes
//! - **Service restarts**: Brief unavailability during deployments
//!
//! # When NOT to Use
//!
//! - **Authentication failures**: Permanent errors that won't resolve
//! - **Invalid input**: Bad request errors that need fixing
//! - **Non-idempotent operations**: Without safeguards against duplicate execution
//! - **Real-time systems**: Where latency is critical
//!
//! # Algorithm
//!
//! Uses exponential backoff with configurable parameters:
//! - `max_attempts`: Maximum number of retry attempts
//! - `initial_delay`: First retry delay (e.g., 100ms)
//! - `max_delay`: Maximum delay cap (e.g., 10s)
//! - `multiplier`: Backoff multiplier (e.g., 2.0 for doubling)
//!
//! **Delay Formula**: `min(initial_delay * multiplier^attempt, max_delay)`
//!
//! **Example**: With initial_delay=100ms, multiplier=2.0, max_delay=10s:
//! - Attempt 1: 100ms
//! - Attempt 2: 200ms
//! - Attempt 3: 400ms
//! - Attempt 4: 800ms
//! - Attempt 5: 1.6s
//!
//! # Example
//!
//! ```rust
//! use agenkit::middleware::{RetryMiddleware, RetryConfig};
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
//! // Configure retry behavior
//! let config = RetryConfig::builder()
//!     .max_attempts(5)
//!     .initial_delay(Duration::from_millis(100))
//!     .max_delay(Duration::from_secs(2))
//!     .multiplier(2.0)
//!     .build();
//!
//! let retry_agent = RetryMiddleware::new(agent, config);
//!
//! // Automatically retries on failure
//! let msg = Message::with_text("user", "Hello");
//! let response = retry_agent.process(msg).await.unwrap();
//! # }
//! ```

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::time::Duration;

/// Configuration for retry middleware.
#[derive(Debug, Clone)]
pub struct RetryConfig {
    /// Maximum number of attempts (including initial attempt).
    /// Default: 3
    pub max_attempts: u32,

    /// Initial retry delay.
    /// Default: 100ms
    pub initial_delay: Duration,

    /// Maximum retry delay (cap for exponential backoff).
    /// Default: 10 seconds
    pub max_delay: Duration,

    /// Backoff multiplier for exponential backoff.
    /// Default: 2.0 (doubles each time)
    pub multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            initial_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(10),
            multiplier: 2.0,
        }
    }
}

impl RetryConfig {
    /// Create a new builder for RetryConfig.
    pub fn builder() -> RetryConfigBuilder {
        RetryConfigBuilder::default()
    }

    /// Calculate delay for a given attempt number (0-indexed).
    fn calculate_delay(&self, attempt: u32) -> Duration {
        if attempt == 0 {
            return Duration::ZERO;
        }

        let delay_ms = self.initial_delay.as_millis() as f64
            * self.multiplier.powi((attempt - 1) as i32);

        let delay = Duration::from_millis(delay_ms as u64);
        delay.min(self.max_delay)
    }
}

/// Builder for RetryConfig.
#[derive(Debug, Default)]
pub struct RetryConfigBuilder {
    max_attempts: Option<u32>,
    initial_delay: Option<Duration>,
    max_delay: Option<Duration>,
    multiplier: Option<f64>,
}

impl RetryConfigBuilder {
    /// Set maximum number of attempts.
    pub fn max_attempts(mut self, attempts: u32) -> Self {
        self.max_attempts = Some(attempts);
        self
    }

    /// Set initial retry delay.
    pub fn initial_delay(mut self, delay: Duration) -> Self {
        self.initial_delay = Some(delay);
        self
    }

    /// Set maximum retry delay.
    pub fn max_delay(mut self, delay: Duration) -> Self {
        self.max_delay = Some(delay);
        self
    }

    /// Set backoff multiplier.
    pub fn multiplier(mut self, multiplier: f64) -> Self {
        self.multiplier = Some(multiplier);
        self
    }

    /// Build the RetryConfig.
    pub fn build(self) -> RetryConfig {
        let default = RetryConfig::default();
        RetryConfig {
            max_attempts: self.max_attempts.unwrap_or(default.max_attempts),
            initial_delay: self.initial_delay.unwrap_or(default.initial_delay),
            max_delay: self.max_delay.unwrap_or(default.max_delay),
            multiplier: self.multiplier.unwrap_or(default.multiplier),
        }
    }
}

/// Retry middleware that wraps an agent with automatic retry logic.
///
/// Uses exponential backoff to retry failed requests, giving transient
/// issues time to resolve while avoiding overwhelming failing services.
pub struct RetryMiddleware<A: Agent> {
    inner: A,
    config: RetryConfig,
}

impl<A: Agent> RetryMiddleware<A> {
    /// Create a new retry middleware with the given agent and configuration.
    pub fn new(agent: A, config: RetryConfig) -> Self {
        Self {
            inner: agent,
            config,
        }
    }

    /// Create a new retry middleware with default configuration.
    pub fn with_defaults(agent: A) -> Self {
        Self::new(agent, RetryConfig::default())
    }
}

#[async_trait]
impl<A: Agent> Agent for RetryMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    fn capabilities(&self) -> Vec<String> {
        self.inner.capabilities()
    }

    fn introspect(&self) -> IntrospectionResult {
        let mut result = self.inner.introspect();
        result
            .metadata
            .insert("middleware".to_string(), serde_json::json!("retry"));
        result.metadata.insert(
            "retry_config".to_string(),
            serde_json::json!({
                "max_attempts": self.config.max_attempts,
                "initial_delay_ms": self.config.initial_delay.as_millis(),
                "max_delay_ms": self.config.max_delay.as_millis(),
                "multiplier": self.config.multiplier,
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut last_error = None;

        for attempt in 0..self.config.max_attempts {
            // Calculate and apply delay (skip on first attempt)
            if attempt > 0 {
                let delay = self.config.calculate_delay(attempt);
                #[cfg(feature = "native")]
                tokio::time::sleep(delay).await;

                #[cfg(feature = "wasm")]
                {
                    let millis = delay.as_millis() as i32;
                    let promise = js_sys::Promise::new(&mut |resolve, _reject| {
                        let window = web_sys::window().expect("no global `window` exists");
                        window
                            .set_timeout_with_callback_and_timeout_and_arguments_0(&resolve, millis)
                            .expect("failed to set timeout");
                    });
                    wasm_bindgen_futures::JsFuture::from(promise).await.ok();
                }
            }

            // Attempt the operation
            match self.inner.process(message.clone()).await {
                Ok(response) => return Ok(response),
                Err(err) => {
                    last_error = Some(err);
                    // Continue to next attempt
                }
            }
        }

        // All attempts failed
        Err(last_error.unwrap_or_else(|| {
            AgentError::Internal("retry failed with no error".to_string())
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;

    struct FailingAgent {
        attempts: Arc<AtomicU32>,
        fail_until: u32,
    }

    impl FailingAgent {
        fn new(fail_until: u32) -> Self {
            Self {
                attempts: Arc::new(AtomicU32::new(0)),
                fail_until,
            }
        }

        fn attempt_count(&self) -> u32 {
            self.attempts.load(Ordering::SeqCst)
        }
    }

    #[async_trait]
    impl Agent for FailingAgent {
        fn name(&self) -> &str {
            "failing"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let attempt = self.attempts.fetch_add(1, Ordering::SeqCst);

            if attempt < self.fail_until {
                Err(AgentError::ProcessingError(
                    "transient failure".to_string(),
                ))
            } else {
                Ok(Message::with_text("assistant", "success"))
            }
        }
    }

    #[tokio::test]
    async fn test_retry_succeeds_on_second_attempt() {
        let agent = FailingAgent::new(1); // Fail once, then succeed
        let config = RetryConfig::builder()
            .max_attempts(3)
            .initial_delay(Duration::from_millis(10))
            .build();

        let retry_agent = RetryMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = retry_agent.process(msg).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap().content_as_str(), Some("success"));
        assert_eq!(retry_agent.inner.attempt_count(), 2); // Initial + 1 retry
    }

    #[tokio::test]
    async fn test_retry_fails_after_max_attempts() {
        let agent = FailingAgent::new(10); // Always fails
        let config = RetryConfig::builder()
            .max_attempts(3)
            .initial_delay(Duration::from_millis(10))
            .build();

        let retry_agent = RetryMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = retry_agent.process(msg).await;

        assert!(result.is_err());
        assert_eq!(retry_agent.inner.attempt_count(), 3); // All attempts used
    }

    #[tokio::test]
    async fn test_retry_succeeds_immediately() {
        let agent = FailingAgent::new(0); // Never fails
        let config = RetryConfig::builder().max_attempts(3).build();

        let retry_agent = RetryMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = retry_agent.process(msg).await;

        assert!(result.is_ok());
        assert_eq!(retry_agent.inner.attempt_count(), 1); // Only one attempt needed
    }

    #[test]
    fn test_delay_calculation() {
        let config = RetryConfig::builder()
            .initial_delay(Duration::from_millis(100))
            .max_delay(Duration::from_secs(2))
            .multiplier(2.0)
            .build();

        // Attempt 0: no delay (initial attempt)
        assert_eq!(config.calculate_delay(0), Duration::ZERO);

        // Attempt 1: 100ms
        assert_eq!(config.calculate_delay(1), Duration::from_millis(100));

        // Attempt 2: 200ms (100 * 2^1)
        assert_eq!(config.calculate_delay(2), Duration::from_millis(200));

        // Attempt 3: 400ms (100 * 2^2)
        assert_eq!(config.calculate_delay(3), Duration::from_millis(400));

        // Attempt 4: 800ms (100 * 2^3)
        assert_eq!(config.calculate_delay(4), Duration::from_millis(800));

        // Attempt 5: 1600ms (100 * 2^4)
        assert_eq!(config.calculate_delay(5), Duration::from_millis(1600));

        // Attempt 6: 2000ms (capped at max_delay)
        assert_eq!(config.calculate_delay(6), Duration::from_secs(2));
    }

    #[tokio::test]
    async fn test_introspect_includes_retry_metadata() {
        let agent = FailingAgent::new(0);
        let config = RetryConfig::builder()
            .max_attempts(5)
            .initial_delay(Duration::from_millis(100))
            .max_delay(Duration::from_secs(2))
            .multiplier(2.0)
            .build();

        let retry_agent = RetryMiddleware::new(agent, config);
        let result = retry_agent.introspect();

        assert_eq!(
            result.metadata.get("middleware"),
            Some(&serde_json::json!("retry"))
        );
        assert!(result.metadata.contains_key("retry_config"));
    }
}
