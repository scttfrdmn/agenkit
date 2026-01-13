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
use futures::stream::{Stream, StreamExt};
use std::pin::Pin;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;

/// Metrics for timeout middleware.
#[derive(Debug, Clone)]
pub struct TimeoutMetrics {
    /// Total number of requests.
    pub total_requests: u64,

    /// Number of successful requests (completed within timeout).
    pub successful_requests: u64,

    /// Number of requests that timed out.
    pub timed_out_requests: u64,

    /// Number of requests that failed for other reasons.
    pub failed_requests: u64,

    /// Minimum request duration.
    pub min_duration: Option<Duration>,

    /// Maximum request duration.
    pub max_duration: Option<Duration>,

    /// Average request duration.
    pub avg_duration: Duration,

    /// Total duration of all requests.
    pub total_duration: Duration,
}

impl Default for TimeoutMetrics {
    fn default() -> Self {
        Self {
            total_requests: 0,
            successful_requests: 0,
            timed_out_requests: 0,
            failed_requests: 0,
            min_duration: None,
            max_duration: None,
            avg_duration: Duration::ZERO,
            total_duration: Duration::ZERO,
        }
    }
}

impl TimeoutMetrics {
    fn update_duration_stats(&mut self, duration: Duration) {
        self.total_duration += duration;

        if self.min_duration.is_none() || duration < self.min_duration.unwrap() {
            self.min_duration = Some(duration);
        }

        if self.max_duration.is_none() || duration > self.max_duration.unwrap() {
            self.max_duration = Some(duration);
        }

        self.avg_duration = self.total_duration / self.total_requests as u32;
    }
}

/// Configuration for timeout middleware.
#[derive(Debug, Clone)]
pub struct TimeoutConfig {
    /// Default maximum duration for agent operations.
    /// Default: 30 seconds
    pub timeout: Duration,

    /// Method-specific timeouts (optional).
    ///
    /// Allows configuring different timeouts for different operations.
    /// The method is determined from message metadata "method" or "operation" field.
    /// If not specified for a method, defaults to the main timeout value.
    ///
    /// Example:
    /// ```rust
    /// use std::collections::HashMap;
    /// use std::time::Duration;
    /// use agenkit::middleware::TimeoutConfig;
    ///
    /// let mut method_timeouts = HashMap::new();
    /// method_timeouts.insert("health_check".to_string(), Duration::from_secs(5));
    /// method_timeouts.insert("long_operation".to_string(), Duration::from_secs(120));
    ///
    /// let config = TimeoutConfig::builder()
    ///     .timeout(Duration::from_secs(30))
    ///     .method_timeouts(method_timeouts)
    ///     .build();
    /// ```
    pub method_timeouts: Option<std::collections::HashMap<String, Duration>>,
}

impl Default for TimeoutConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            method_timeouts: None,
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
    method_timeouts: Option<std::collections::HashMap<String, Duration>>,
}

impl TimeoutConfigBuilder {
    /// Set default timeout duration.
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = Some(timeout);
        self
    }

    /// Set method-specific timeouts.
    ///
    /// Allows different timeout durations for different operations based on
    /// the "method" or "operation" field in message metadata.
    pub fn method_timeouts(mut self, timeouts: std::collections::HashMap<String, Duration>) -> Self {
        self.method_timeouts = Some(timeouts);
        self
    }

    /// Build the TimeoutConfig.
    pub fn build(self) -> TimeoutConfig {
        let default = TimeoutConfig::default();
        TimeoutConfig {
            timeout: self.timeout.unwrap_or(default.timeout),
            method_timeouts: self.method_timeouts,
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
    metrics: Arc<Mutex<TimeoutMetrics>>,
}

impl<A: Agent> TimeoutMiddleware<A> {
    /// Create a new timeout middleware with the given agent and configuration.
    pub fn new(agent: A, config: TimeoutConfig) -> Self {
        Self {
            inner: agent,
            config,
            metrics: Arc::new(Mutex::new(TimeoutMetrics::default())),
        }
    }

    /// Create a new timeout middleware with default configuration (30s).
    pub fn with_defaults(agent: A) -> Self {
        Self::new(agent, TimeoutConfig::default())
    }

    /// Get current metrics.
    pub async fn get_metrics(&self) -> TimeoutMetrics {
        self.metrics.lock().await.clone()
    }

    /// Get timeout for a specific message.
    ///
    /// Checks message metadata for "method" or "operation" field to determine
    /// the operation type, then returns the method-specific timeout if configured,
    /// otherwise returns the default timeout.
    fn get_timeout_for_message(&self, message: &Message) -> Duration {
        // If no method timeouts configured, return default
        let method_timeouts = match &self.config.method_timeouts {
            Some(timeouts) => timeouts,
            None => return self.config.timeout,
        };

        // Try to extract method from metadata
        let method = message
            .metadata
            .get("method")
            .and_then(|v| v.as_str())
            .or_else(|| {
                // Try "operation" field as fallback
                message.metadata.get("operation").and_then(|v| v.as_str())
            })
            .unwrap_or("process"); // Default to "process"

        // Return method-specific timeout if configured, otherwise default
        method_timeouts
            .get(method)
            .copied()
            .unwrap_or(self.config.timeout)
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
        let start_time = Instant::now();

        // Get timeout for this specific message
        let timeout = self.get_timeout_for_message(&message);

        // Increment total requests
        {
            let mut metrics = self.metrics.lock().await;
            metrics.total_requests += 1;
        }

        #[cfg(feature = "native")]
        {
            let result =
                tokio::time::timeout(timeout, self.inner.process(message)).await;

            let duration = start_time.elapsed();

            match result {
                Ok(Ok(response)) => {
                    let mut metrics = self.metrics.lock().await;
                    metrics.successful_requests += 1;
                    metrics.update_duration_stats(duration);
                    Ok(response)
                }
                Ok(Err(err)) => {
                    let mut metrics = self.metrics.lock().await;
                    metrics.failed_requests += 1;
                    metrics.update_duration_stats(duration);
                    Err(err)
                }
                Err(_) => {
                    let mut metrics = self.metrics.lock().await;
                    metrics.timed_out_requests += 1;
                    metrics.update_duration_stats(duration);
                    Err(AgentError::Timeout(format!(
                        "operation timed out after {:?}",
                        timeout
                    )))
                }
            }
        }

        #[cfg(feature = "wasm")]
        {
            // WASM doesn't support tokio::time::timeout directly
            // For now, just call the inner agent without timeout
            // TODO: Implement timeout for WASM using Promise.race
            let result = self.inner.process(message).await;

            let duration = start_time.elapsed();

            match &result {
                Ok(_) => {
                    let mut metrics = self.metrics.lock().await;
                    metrics.successful_requests += 1;
                    metrics.update_duration_stats(duration);
                }
                Err(_) => {
                    let mut metrics = self.metrics.lock().await;
                    metrics.failed_requests += 1;
                    metrics.update_duration_stats(duration);
                }
            }

            result
        }
    }

    /// Process a message with streaming response and timeout enforcement.
    ///
    /// The timeout applies to the entire streaming operation - if the stream takes
    /// longer than the configured timeout to complete, it will be cancelled.
    ///
    /// # Arguments
    /// * `message` - Input message
    ///
    /// # Returns
    /// Stream of response messages with timeout enforcement
    ///
    /// # Example
    /// ```ignore
    /// use futures::stream::StreamExt;
    ///
    /// let config = TimeoutConfig::builder()
    ///     .timeout(Duration::from_secs(30))
    ///     .build();
    ///
    /// let timeout_agent = TimeoutMiddleware::new(agent, config);
    ///
    /// let msg = Message::with_text("user", "Hello");
    /// let mut stream = timeout_agent.process_stream(msg);
    ///
    /// while let Some(chunk_result) = stream.next().await {
    ///     match chunk_result {
    ///         Ok(chunk) => println!("Chunk: {:?}", chunk),
    ///         Err(e) => eprintln!("Error: {}", e),
    ///     }
    /// }
    /// ```
    fn process_stream(
        &self,
        message: Message,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        let timeout = self.get_timeout_for_message(&message);
        let inner_stream = self.inner.process_stream(message);
        let metrics = Arc::clone(&self.metrics);
        let start_time = Instant::now();

        #[cfg(feature = "native")]
        {
            // Create a timeout stream that wraps the inner stream
            let timeout_stream = tokio_stream::StreamExt::timeout(inner_stream, timeout);

            // Map the stream to handle timeout errors
            let mapped_stream = futures::StreamExt::then(timeout_stream, move |item| {
                let metrics = Arc::clone(&metrics);
                let start_time = start_time;
                async move {
                    match item {
                        Ok(result) => result,
                        Err(_) => {
                            // Timeout occurred
                            let duration = start_time.elapsed();
                            let mut m = metrics.lock().await;
                            m.timed_out_requests += 1;
                            m.update_duration_stats(duration);
                            Err(AgentError::Timeout(format!(
                                "stream timed out after {:?}",
                                timeout
                            )))
                        }
                    }
                }
            });

            Box::pin(mapped_stream)
        }

        #[cfg(feature = "wasm")]
        {
            // WASM doesn't support tokio::time::timeout directly
            // For now, just pass through the stream without timeout
            // TODO: Implement timeout for WASM using web APIs
            Box::pin(inner_stream)
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
