//! Timeout middleware for enforcing time limits on agent operations.
//!
//! Automatically cancels agent operations that exceed a configured timeout,
//! preventing indefinite hangs and ensuring predictable response times.
//!
//! # When to Use
//!
//! - **External API calls**: LLM providers that may hang
//! - **Network operations**: Prevent indefinite waits on network issues
//! - **Resource protection**: Limit compute time for expensive operations
//! - **SLA enforcement**: Ensure operations complete within time bounds
//!
//! # When NOT to Use
//!
//! - **Long-running operations**: Where timeout is expected to be exceeded
//! - **Batch processing**: Where operations naturally take longer
//! - **Development/debugging**: Can mask underlying performance issues
//!
//! # Example
//!
//! ```rust
//! use agenkit::middleware::{TimeoutMiddleware, TimeoutConfig};
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
//! let config = TimeoutConfig::builder()
//!     .timeout(Duration::from_secs(30))
//!     .build();
//!
//! let timeout_agent = TimeoutMiddleware::new(agent, config);
//!
//! // Operations exceeding 30s will be cancelled
//! let msg = Message::with_text("user", "Hello");
//! let response = timeout_agent.process(msg).await;
//! # }
//! ```

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::time::Duration;

/// Configuration for timeout middleware.
#[derive(Debug, Clone)]
pub struct TimeoutConfig {
    /// Maximum duration for agent operations.
    /// Default: 30 seconds
    pub timeout: Duration,
}

impl Default for TimeoutConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
        }
    }
}

impl TimeoutConfig {
    /// Create a new builder for TimeoutConfig.
    pub fn builder() -> TimeoutConfigBuilder {
        TimeoutConfigBuilder::default()
    }
}

/// Builder for TimeoutConfig.
#[derive(Debug, Default)]
pub struct TimeoutConfigBuilder {
    timeout: Option<Duration>,
}

impl TimeoutConfigBuilder {
    /// Set timeout duration.
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = Some(timeout);
        self
    }

    /// Build the TimeoutConfig.
    pub fn build(self) -> TimeoutConfig {
        let default = TimeoutConfig::default();
        TimeoutConfig {
            timeout: self.timeout.unwrap_or(default.timeout),
        }
    }
}

/// Timeout middleware that enforces time limits on agent operations.
///
/// Operations that exceed the configured timeout are automatically cancelled,
/// returning a timeout error instead of waiting indefinitely.
pub struct TimeoutMiddleware<A: Agent> {
    inner: A,
    config: TimeoutConfig,
}

impl<A: Agent> TimeoutMiddleware<A> {
    /// Create a new timeout middleware with the given agent and configuration.
    pub fn new(agent: A, config: TimeoutConfig) -> Self {
        Self {
            inner: agent,
            config,
        }
    }

    /// Create a new timeout middleware with default configuration (30s).
    pub fn with_defaults(agent: A) -> Self {
        Self::new(agent, TimeoutConfig::default())
    }
}

#[async_trait]
impl<A: Agent> Agent for TimeoutMiddleware<A> {
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
            .insert("middleware".to_string(), serde_json::json!("timeout"));
        result.metadata.insert(
            "timeout_config".to_string(),
            serde_json::json!({
                "timeout_ms": self.config.timeout.as_millis(),
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        #[cfg(feature = "native")]
        {
            match tokio::time::timeout(self.config.timeout, self.inner.process(message)).await {
                Ok(result) => result,
                Err(_) => Err(AgentError::Timeout(format!(
                    "operation timed out after {:?}",
                    self.config.timeout
                ))),
            }
        }

        #[cfg(feature = "wasm")]
        {
            // WASM doesn't support tokio::time::timeout directly
            // For now, just call the inner agent without timeout
            // TODO: Implement timeout for WASM using Promise.race
            self.inner.process(message).await
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;

    struct SlowAgent {
        delay: Duration,
        attempts: Arc<AtomicU32>,
    }

    impl SlowAgent {
        fn new(delay: Duration) -> Self {
            Self {
                delay,
                attempts: Arc::new(AtomicU32::new(0)),
            }
        }

        fn attempt_count(&self) -> u32 {
            self.attempts.load(Ordering::SeqCst)
        }
    }

    #[async_trait]
    impl Agent for SlowAgent {
        fn name(&self) -> &str {
            "slow"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            self.attempts.fetch_add(1, Ordering::SeqCst);
            tokio::time::sleep(self.delay).await;
            Ok(Message::with_text("assistant", "success"))
        }
    }

    #[tokio::test]
    async fn test_timeout_succeeds_when_within_limit() {
        let agent = SlowAgent::new(Duration::from_millis(50));
        let config = TimeoutConfig::builder()
            .timeout(Duration::from_millis(200))
            .build();

        let timeout_agent = TimeoutMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = timeout_agent.process(msg).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap().content_as_str(), Some("success"));
        assert_eq!(timeout_agent.inner.attempt_count(), 1);
    }

    #[tokio::test]
    async fn test_timeout_fails_when_exceeds_limit() {
        let agent = SlowAgent::new(Duration::from_millis(500));
        let config = TimeoutConfig::builder()
            .timeout(Duration::from_millis(100))
            .build();

        let timeout_agent = TimeoutMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = timeout_agent.process(msg).await;

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AgentError::Timeout(_)));
        assert_eq!(timeout_agent.inner.attempt_count(), 1);
    }

    #[tokio::test]
    async fn test_timeout_with_fast_agent() {
        let agent = SlowAgent::new(Duration::ZERO);
        let config = TimeoutConfig::builder()
            .timeout(Duration::from_secs(1))
            .build();

        let timeout_agent = TimeoutMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = timeout_agent.process(msg).await;

        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_introspect_includes_timeout_metadata() {
        let agent = SlowAgent::new(Duration::ZERO);
        let config = TimeoutConfig::builder()
            .timeout(Duration::from_secs(5))
            .build();

        let timeout_agent = TimeoutMiddleware::new(agent, config);
        let result = timeout_agent.introspect();

        assert_eq!(
            result.metadata.get("middleware"),
            Some(&serde_json::json!("timeout"))
        );
        assert!(result.metadata.contains_key("timeout_config"));
    }
}
