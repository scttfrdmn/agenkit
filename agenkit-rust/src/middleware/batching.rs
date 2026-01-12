//! Batching middleware for aggregating multiple requests.
//!
//! Collects multiple requests and processes them together in a single batch,
//! reducing overhead for operations that benefit from batch processing.
//!
//! # Use Cases
//!
//! - **LLM APIs with batch endpoints**: OpenAI, Anthropic batch APIs
//! - **Database operations**: Batch inserts/updates
//! - **Vector databases**: Batch embeddings/searches
//! - **Analytics**: Aggregate multiple events
//!
//! # How It Works
//!
//! 1. Requests are collected in a queue
//! 2. Batch is flushed when:
//!    - Batch size reaches `max_batch_size`, OR
//!    - `max_wait_time` elapses since first request
//! 3. All requests in batch are processed together
//! 4. Individual responses are returned to callers
//!
//! # When to Use
//!
//! - **High throughput**: Many concurrent requests
//! - **Batch-optimized APIs**: APIs with batch endpoints
//! - **Cost efficiency**: Batch discounts from providers
//! - **Performance**: Amortize setup costs across requests
//!
//! # When NOT to Use
//!
//! - **Low latency requirements**: Batching adds delay
//! - **Single requests**: Overhead without benefit
//! - **No batch support**: Agent doesn't support batching
//! - **Complex routing**: Requests need individual handling
//!
//! # Example
//!
//! ```rust
//! use agenkit::middleware::{BatchingMiddleware, BatchingConfig};
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
//! let config = BatchingConfig::builder()
//!     .max_batch_size(10)
//!     .max_wait_time(Duration::from_millis(100))
//!     .build();
//!
//! let batch_agent = BatchingMiddleware::new(agent, config);
//!
//! // Multiple concurrent requests are batched together
//! let msg = Message::with_text("user", "Hello");
//! let response = batch_agent.process(msg).await;
//! # }
//! ```

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{oneshot, Mutex};

/// Configuration for batching middleware.
#[derive(Debug, Clone)]
pub struct BatchingConfig {
    /// Maximum number of requests in a batch.
    /// Default: 10
    pub max_batch_size: usize,

    /// Maximum time to wait for batch to fill.
    /// Default: 100ms
    pub max_wait_time: Duration,
}

impl Default for BatchingConfig {
    fn default() -> Self {
        Self {
            max_batch_size: 10,
            max_wait_time: Duration::from_millis(100),
        }
    }
}

impl BatchingConfig {
    /// Create a new builder for BatchingConfig.
    pub fn builder() -> BatchingConfigBuilder {
        BatchingConfigBuilder::default()
    }
}

/// Builder for BatchingConfig.
#[derive(Debug, Default)]
pub struct BatchingConfigBuilder {
    max_batch_size: Option<usize>,
    max_wait_time: Option<Duration>,
}

impl BatchingConfigBuilder {
    /// Set maximum batch size.
    pub fn max_batch_size(mut self, size: usize) -> Self {
        self.max_batch_size = Some(size);
        self
    }

    /// Set maximum wait time.
    pub fn max_wait_time(mut self, time: Duration) -> Self {
        self.max_wait_time = Some(time);
        self
    }

    /// Build the BatchingConfig.
    pub fn build(self) -> BatchingConfig {
        let default = BatchingConfig::default();
        BatchingConfig {
            max_batch_size: self.max_batch_size.unwrap_or(default.max_batch_size),
            max_wait_time: self.max_wait_time.unwrap_or(default.max_wait_time),
        }
    }
}

/// Metrics for batching middleware.
#[derive(Debug, Clone, Default)]
pub struct BatchingMetrics {
    /// Total number of requests processed.
    pub total_requests: u64,

    /// Total number of batches processed.
    pub total_batches: u64,

    /// Number of successful batches (all requests succeeded).
    pub successful_batches: u64,

    /// Number of failed batches (all requests failed).
    pub failed_batches: u64,

    /// Number of partial batches (mixed success/failure).
    pub partial_batches: u64,

    /// Minimum batch size observed.
    pub min_batch_size: Option<usize>,

    /// Maximum batch size observed.
    pub max_batch_size: Option<usize>,

    /// Total batch size (for calculating average).
    pub total_batch_size: u64,

    /// Total wait time (milliseconds) across all requests.
    pub total_wait_time_ms: u64,
}

impl BatchingMetrics {
    /// Calculate average batch size.
    pub fn avg_batch_size(&self) -> f64 {
        if self.total_batches == 0 {
            0.0
        } else {
            self.total_batch_size as f64 / self.total_batches as f64
        }
    }

    /// Calculate average wait time per request (milliseconds).
    pub fn avg_wait_time_ms(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            self.total_wait_time_ms as f64 / self.total_requests as f64
        }
    }

    /// Calculate throughput improvement (requests / batches).
    pub fn throughput_improvement(&self) -> f64 {
        if self.total_batches == 0 {
            1.0
        } else {
            self.total_requests as f64 / self.total_batches as f64
        }
    }
}

/// Request in the batch queue.
struct BatchRequest {
    message: Message,
    response_tx: oneshot::Sender<Result<Message, AgentError>>,
    enqueued_at: Instant,
}

/// Batch state.
struct BatchState {
    queue: VecDeque<BatchRequest>,
    first_request_time: Option<Instant>,
    metrics: BatchingMetrics,
}

impl BatchState {
    fn new() -> Self {
        Self {
            queue: VecDeque::new(),
            first_request_time: None,
            metrics: BatchingMetrics::default(),
        }
    }

    fn add(&mut self, request: BatchRequest) {
        if self.queue.is_empty() {
            self.first_request_time = Some(Instant::now());
        }
        self.metrics.total_requests += 1;
        self.queue.push_back(request);
    }

    fn should_flush(&self, config: &BatchingConfig) -> bool {
        if self.queue.is_empty() {
            return false;
        }

        // Flush if batch is full
        if self.queue.len() >= config.max_batch_size {
            return true;
        }

        // Flush if max wait time exceeded
        if let Some(first_time) = self.first_request_time {
            if first_time.elapsed() >= config.max_wait_time {
                return true;
            }
        }

        false
    }

    fn drain(&mut self) -> Vec<BatchRequest> {
        self.first_request_time = None;
        self.queue.drain(..).collect()
    }

    fn len(&self) -> usize {
        self.queue.len()
    }

    fn get_metrics(&self) -> BatchingMetrics {
        self.metrics.clone()
    }
}

/// Batching middleware that aggregates multiple requests.
///
/// Collects requests and processes them together when batch size or
/// wait time threshold is reached, reducing per-request overhead.
pub struct BatchingMiddleware<A: Agent + 'static> {
    inner: Arc<A>,
    config: BatchingConfig,
    state: Arc<Mutex<BatchState>>,
    flush_handle: Arc<Mutex<Option<tokio::task::JoinHandle<()>>>>,
}

impl<A: Agent + 'static> BatchingMiddleware<A> {
    /// Create a new batching middleware with the given agent and configuration.
    pub fn new(agent: A, config: BatchingConfig) -> Self {
        let middleware = Self {
            inner: Arc::new(agent),
            config: config.clone(),
            state: Arc::new(Mutex::new(BatchState::new())),
            flush_handle: Arc::new(Mutex::new(None)),
        };

        // Start background flush task
        middleware.start_flush_task();

        middleware
    }

    /// Create a new batching middleware with default configuration.
    pub fn with_defaults(agent: A) -> Self {
        Self::new(agent, BatchingConfig::default())
    }

    /// Get current batching metrics.
    pub async fn get_metrics(&self) -> BatchingMetrics {
        let state = self.state.lock().await;
        state.get_metrics()
    }

    /// Start background task that periodically flushes batches.
    fn start_flush_task(&self) {
        let inner = Arc::clone(&self.inner);
        let state = Arc::clone(&self.state);
        let config = self.config.clone();

        let handle = tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_millis(10));

            loop {
                interval.tick().await;

                let should_flush = {
                    let state = state.lock().await;
                    state.should_flush(&config)
                };

                if should_flush {
                    Self::flush_batch(Arc::clone(&inner), Arc::clone(&state)).await;
                }
            }
        });

        let handle_clone = Arc::clone(&self.flush_handle);
        tokio::spawn(async move {
            let mut guard = handle_clone.lock().await;
            *guard = Some(handle);
        });
    }

    /// Flush the current batch.
    async fn flush_batch(inner: Arc<A>, state: Arc<Mutex<BatchState>>) {
        let requests = {
            let mut state = state.lock().await;
            if state.len() == 0 {
                return;
            }
            state.drain()
        };

        let batch_size = requests.len();
        if batch_size == 0 {
            return;
        }

        let batch_start = Instant::now();
        let mut successes = 0;
        let mut failures = 0;
        let mut total_wait_time_ms = 0u64;

        // Process requests in parallel using JoinSet
        let mut join_set = tokio::task::JoinSet::new();

        for request in requests {
            let inner_clone = Arc::clone(&inner);
            let wait_time_ms = request.enqueued_at.elapsed().as_millis() as u64;

            join_set.spawn(async move {
                let result = inner_clone.process(request.message).await;
                let is_success = result.is_ok();
                // Send result to waiting caller (ignore if receiver dropped)
                let _ = request.response_tx.send(result);
                (is_success, wait_time_ms)
            });
        }

        // Wait for all tasks to complete and collect results
        while let Some(task_result) = join_set.join_next().await {
            if let Ok((is_success, wait_ms)) = task_result {
                if is_success {
                    successes += 1;
                } else {
                    failures += 1;
                }
                total_wait_time_ms += wait_ms;
            }
        }

        // Update batch metrics
        {
            let mut state = state.lock().await;
            state.metrics.total_batches += 1;
            state.metrics.total_batch_size += batch_size as u64;
            state.metrics.total_wait_time_ms += total_wait_time_ms;

            // Update min/max batch size
            state.metrics.min_batch_size = Some(
                state
                    .metrics
                    .min_batch_size
                    .map_or(batch_size, |min| min.min(batch_size)),
            );
            state.metrics.max_batch_size = Some(
                state
                    .metrics
                    .max_batch_size
                    .map_or(batch_size, |max| max.max(batch_size)),
            );

            // Classify batch outcome
            if failures == 0 {
                state.metrics.successful_batches += 1;
            } else if successes == 0 {
                state.metrics.failed_batches += 1;
            } else {
                state.metrics.partial_batches += 1;
            }
        }
    }
}

impl<A: Agent + 'static> Drop for BatchingMiddleware<A> {
    fn drop(&mut self) {
        // Cancel background flush task
        let handle = Arc::clone(&self.flush_handle);
        tokio::spawn(async move {
            let mut guard = handle.lock().await;
            if let Some(h) = guard.take() {
                h.abort();
            }
        });
    }
}

#[async_trait]
impl<A: Agent + 'static> Agent for BatchingMiddleware<A> {
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
            .insert("middleware".to_string(), serde_json::json!("batching"));
        result.metadata.insert(
            "batching_config".to_string(),
            serde_json::json!({
                "max_batch_size": self.config.max_batch_size,
                "max_wait_time_ms": self.config.max_wait_time.as_millis(),
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let (tx, rx) = oneshot::channel();

        let request = BatchRequest {
            message,
            response_tx: tx,
            enqueued_at: Instant::now(),
        };

        // Add to batch queue
        {
            let mut state = self.state.lock().await;
            state.add(request);

            // Immediate flush if batch is full
            if state.should_flush(&self.config) {
                drop(state); // Release lock before flush
                Self::flush_batch(Arc::clone(&self.inner), Arc::clone(&self.state)).await;
            }
        }

        // Wait for response
        match rx.await {
            Ok(result) => result,
            Err(_) => Err(AgentError::Internal(
                "batch processing failed: channel closed".to_string(),
            )),
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

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            self.attempts.fetch_add(1, Ordering::SeqCst);
            Ok(Message::with_text(
                "assistant",
                format!("echo: {}", message.content_as_str().unwrap_or("")),
            ))
        }
    }

    #[tokio::test]
    async fn test_batching_single_request() {
        let agent = CountingAgent::new();
        let config = BatchingConfig::builder()
            .max_batch_size(10)
            .max_wait_time(Duration::from_millis(50))
            .build();

        let batch_agent = BatchingMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = batch_agent.process(msg).await;

        assert!(result.is_ok());
        assert_eq!(
            result.unwrap().content_as_str(),
            Some("echo: test")
        );
    }

    #[tokio::test]
    async fn test_batching_multiple_concurrent_requests() {
        let agent = CountingAgent::new();
        let config = BatchingConfig::builder()
            .max_batch_size(5)
            .max_wait_time(Duration::from_millis(100))
            .build();

        let batch_agent = Arc::new(BatchingMiddleware::new(agent, config));

        // Spawn multiple concurrent requests
        let mut handles = vec![];
        for i in 0..5 {
            let agent_clone = Arc::clone(&batch_agent);
            let handle = tokio::spawn(async move {
                let msg = Message::with_text("user", format!("test{}", i));
                agent_clone.process(msg).await
            });
            handles.push(handle);
        }

        // Wait for all to complete
        for handle in handles {
            let result = handle.await.unwrap();
            assert!(result.is_ok());
        }

        // All 5 requests should have been processed
        assert_eq!(batch_agent.inner.attempt_count(), 5);
    }

    #[tokio::test]
    async fn test_batching_flushes_on_size() {
        let agent = CountingAgent::new();
        let config = BatchingConfig::builder()
            .max_batch_size(3)
            .max_wait_time(Duration::from_secs(10)) // Long timeout
            .build();

        let batch_agent = Arc::new(BatchingMiddleware::new(agent, config));

        // Send 3 requests quickly
        let mut handles = vec![];
        for i in 0..3 {
            let agent_clone = Arc::clone(&batch_agent);
            let handle = tokio::spawn(async move {
                let msg = Message::with_text("user", format!("test{}", i));
                agent_clone.process(msg).await
            });
            handles.push(handle);
        }

        // Should flush immediately when batch size reached
        for handle in handles {
            let result = handle.await.unwrap();
            assert!(result.is_ok());
        }

        assert_eq!(batch_agent.inner.attempt_count(), 3);
    }

    #[tokio::test]
    async fn test_batching_flushes_on_timeout() {
        let agent = CountingAgent::new();
        let config = BatchingConfig::builder()
            .max_batch_size(100) // Large batch size
            .max_wait_time(Duration::from_millis(50))
            .build();

        let batch_agent = BatchingMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");
        let result = batch_agent.process(msg).await;

        // Should flush due to timeout
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_introspect_includes_batching_metadata() {
        let agent = CountingAgent::new();
        let config = BatchingConfig::builder()
            .max_batch_size(10)
            .max_wait_time(Duration::from_millis(100))
            .build();

        let batch_agent = BatchingMiddleware::new(agent, config);
        let result = batch_agent.introspect();

        assert_eq!(
            result.metadata.get("middleware"),
            Some(&serde_json::json!("batching"))
        );
        assert!(result.metadata.contains_key("batching_config"));
    }
}
