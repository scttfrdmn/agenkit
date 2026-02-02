//! Circuit breaker middleware for preventing cascading failures.
//!
//! Implements the circuit breaker pattern to protect against cascading failures
//! by automatically "opening" the circuit after a threshold of failures, giving
//! failing services time to recover.
//!
//! # Pattern
//!
//! The circuit breaker operates in three states:
//!
//! - **CLOSED** (normal): Requests pass through, failures are counted
//! - **OPEN** (failing): All requests fail fast without calling the agent
//! - **HALF_OPEN** (testing): Limited requests allowed to test recovery
//!
//! # State Transitions
//!
//! ```text
//! CLOSED --[failure threshold reached]--> OPEN
//! OPEN --[timeout elapsed]--> HALF_OPEN
//! HALF_OPEN --[success]--> CLOSED
//! HALF_OPEN --[failure]--> OPEN
//! ```
//!
//! # When to Use
//!
//! - **Cascading failure prevention**: Stop overwhelming failing services
//! - **External dependencies**: Protect against unreliable external services
//! - **Graceful degradation**: Fail fast instead of waiting for timeouts
//! - **System stability**: Maintain overall system health during partial outages
//!
//! # When NOT to Use
//!
//! - **Critical operations**: Where failure is not acceptable
//! - **Stateless operations**: Where retry is sufficient
//! - **Development/testing**: Can mask underlying issues
//!
//! # Example
//!
//! ```rust
//! use agenkit::middleware::{CircuitBreakerMiddleware, CircuitBreakerConfig};
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
//! let config = CircuitBreakerConfig::builder()
//!     .failure_threshold(5)
//!     .success_threshold(2)
//!     .timeout(Duration::from_secs(30))          // Request timeout (optional, defaults to 30s)
//!     .recovery_timeout(Duration::from_secs(60)) // Recovery timeout (optional, defaults to 60s)
//!     .build();
//!
//! let cb_agent = CircuitBreakerMiddleware::new(agent, config);
//!
//! // Circuit opens after 5 failures, closes after 2 successes in half-open state
//! let msg = Message::with_text("user", "Hello");
//! let response = cb_agent.process(msg).await;
//! # }
//! ```

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

/// Circuit breaker state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    /// Normal operation - requests pass through.
    Closed,
    /// Circuit is open - requests fail immediately.
    Open,
    /// Testing recovery - limited requests allowed.
    HalfOpen,
}

impl std::fmt::Display for CircuitState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CircuitState::Closed => write!(f, "CLOSED"),
            CircuitState::Open => write!(f, "OPEN"),
            CircuitState::HalfOpen => write!(f, "HALF_OPEN"),
        }
    }
}

/// Metrics for circuit breaker middleware.
#[derive(Debug, Clone)]
pub struct CircuitBreakerMetrics {
    /// Total number of requests attempted.
    pub total_requests: u64,

    /// Number of successful requests.
    pub successful_requests: u64,

    /// Number of failed requests.
    pub failed_requests: u64,

    /// Number of requests rejected due to open circuit.
    pub rejected_requests: u64,

    /// State transition counts (e.g., "CLOSED->OPEN": 3).
    pub state_changes: HashMap<String, u64>,

    /// Timestamp of last state change.
    pub last_state_change: Option<Instant>,

    /// Current circuit state.
    pub current_state: CircuitState,
}

impl Default for CircuitBreakerMetrics {
    fn default() -> Self {
        Self {
            total_requests: 0,
            successful_requests: 0,
            failed_requests: 0,
            rejected_requests: 0,
            state_changes: HashMap::new(),
            last_state_change: None,
            current_state: CircuitState::Closed,
        }
    }
}

/// Configuration for circuit breaker middleware.
#[derive(Debug, Clone)]
pub struct CircuitBreakerConfig {
    /// Number of consecutive failures before opening circuit.
    /// Default: 5
    pub failure_threshold: u32,

    /// Number of consecutive successes in half-open state to close circuit.
    /// Default: 2
    pub success_threshold: u32,

    /// Request timeout (how long to wait for individual requests).
    /// Default: 30 seconds
    pub timeout: Duration,

    /// Duration to wait in open state before transitioning to half-open.
    /// Default: 60 seconds
    pub recovery_timeout: Duration,
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            success_threshold: 2,
            timeout: Duration::from_secs(30),
            recovery_timeout: Duration::from_secs(60),
        }
    }
}

impl CircuitBreakerConfig {
    /// Create a new builder for CircuitBreakerConfig.
    pub fn builder() -> CircuitBreakerConfigBuilder {
        CircuitBreakerConfigBuilder::default()
    }
}

/// Builder for CircuitBreakerConfig.
#[derive(Debug, Default)]
pub struct CircuitBreakerConfigBuilder {
    failure_threshold: Option<u32>,
    success_threshold: Option<u32>,
    timeout: Option<Duration>,
    recovery_timeout: Option<Duration>,
}

impl CircuitBreakerConfigBuilder {
    /// Set failure threshold.
    pub fn failure_threshold(mut self, threshold: u32) -> Self {
        self.failure_threshold = Some(threshold);
        self
    }

    /// Set success threshold.
    pub fn success_threshold(mut self, threshold: u32) -> Self {
        self.success_threshold = Some(threshold);
        self
    }

    /// Set request timeout duration (how long to wait for individual requests).
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = Some(timeout);
        self
    }

    /// Set recovery timeout duration (how long to wait before testing recovery).
    pub fn recovery_timeout(mut self, timeout: Duration) -> Self {
        self.recovery_timeout = Some(timeout);
        self
    }

    /// Build the CircuitBreakerConfig.
    pub fn build(self) -> CircuitBreakerConfig {
        let default = CircuitBreakerConfig::default();
        CircuitBreakerConfig {
            failure_threshold: self.failure_threshold.unwrap_or(default.failure_threshold),
            success_threshold: self.success_threshold.unwrap_or(default.success_threshold),
            timeout: self.timeout.unwrap_or(default.timeout),
            recovery_timeout: self.recovery_timeout.unwrap_or(default.recovery_timeout),
        }
    }
}

/// Internal state for circuit breaker.
#[derive(Debug)]
struct CircuitBreakerState {
    state: CircuitState,
    failure_count: u32,
    success_count: u32,
    last_failure_time: Option<Instant>,
    metrics: CircuitBreakerMetrics,
}

impl CircuitBreakerState {
    fn record_state_change(&mut self, from: CircuitState, to: CircuitState) {
        let key = format!("{}->{}", from, to);
        *self.metrics.state_changes.entry(key).or_insert(0) += 1;
        self.metrics.last_state_change = Some(Instant::now());
        self.metrics.current_state = to;
    }
}

impl Default for CircuitBreakerState {
    fn default() -> Self {
        Self {
            state: CircuitState::Closed,
            failure_count: 0,
            success_count: 0,
            last_failure_time: None,
            metrics: CircuitBreakerMetrics::default(),
        }
    }
}

/// Circuit breaker middleware that implements the circuit breaker pattern.
///
/// Prevents cascading failures by opening the circuit after a threshold of failures,
/// failing fast without calling the underlying agent. After a timeout, allows limited
/// requests to test recovery.
pub struct CircuitBreakerMiddleware<A: Agent> {
    inner: A,
    config: CircuitBreakerConfig,
    state: Arc<RwLock<CircuitBreakerState>>,
}

impl<A: Agent> CircuitBreakerMiddleware<A> {
    /// Create a new circuit breaker middleware with the given agent and configuration.
    pub fn new(agent: A, config: CircuitBreakerConfig) -> Self {
        Self {
            inner: agent,
            config,
            state: Arc::new(RwLock::new(CircuitBreakerState::default())),
        }
    }

    /// Create a new circuit breaker middleware with default configuration.
    pub fn with_defaults(agent: A) -> Self {
        Self::new(agent, CircuitBreakerConfig::default())
    }

    /// Get current metrics.
    pub async fn get_metrics(&self) -> CircuitBreakerMetrics {
        self.state.read().await.metrics.clone()
    }

    /// Check if circuit should transition to half-open state.
    async fn should_attempt_reset(&self) -> bool {
        let state = self.state.read().await;
        if state.state != CircuitState::Open {
            return false;
        }

        if let Some(last_failure) = state.last_failure_time {
            let elapsed = Instant::now().duration_since(last_failure);
            elapsed >= self.config.recovery_timeout
        } else {
            false
        }
    }

    /// Record a successful request.
    async fn on_success(&self) {
        let mut state = self.state.write().await;

        match state.state {
            CircuitState::HalfOpen => {
                state.success_count += 1;
                if state.success_count >= self.config.success_threshold {
                    // Transition to closed
                    let old_state = state.state;
                    state.state = CircuitState::Closed;
                    state.failure_count = 0;
                    state.success_count = 0;
                    state.last_failure_time = None;
                    state.record_state_change(old_state, CircuitState::Closed);
                }
            }
            CircuitState::Closed => {
                // Reset failure count on success
                state.failure_count = 0;
            }
            CircuitState::Open => {
                // Should not happen, but reset if it does
                let old_state = state.state;
                state.state = CircuitState::Closed;
                state.failure_count = 0;
                state.success_count = 0;
                state.last_failure_time = None;
                state.record_state_change(old_state, CircuitState::Closed);
            }
        }
    }

    /// Record a failed request.
    async fn on_failure(&self) {
        let mut state = self.state.write().await;

        match state.state {
            CircuitState::Closed => {
                state.failure_count += 1;
                state.last_failure_time = Some(Instant::now());

                if state.failure_count >= self.config.failure_threshold {
                    // Transition to open
                    let old_state = state.state;
                    state.state = CircuitState::Open;
                    state.record_state_change(old_state, CircuitState::Open);
                }
            }
            CircuitState::HalfOpen => {
                // Transition back to open
                let old_state = state.state;
                state.state = CircuitState::Open;
                state.failure_count = self.config.failure_threshold; // Keep at threshold
                state.success_count = 0;
                state.last_failure_time = Some(Instant::now());
                state.record_state_change(old_state, CircuitState::Open);
            }
            CircuitState::Open => {
                // Update timestamp
                state.last_failure_time = Some(Instant::now());
            }
        }
    }
}

#[async_trait]
impl<A: Agent> Agent for CircuitBreakerMiddleware<A> {
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
            serde_json::json!("circuit_breaker"),
        );

        // Note: We can't await here, so we can't include current state
        // This is a limitation of the synchronous introspect() method
        result.metadata.insert(
            "circuit_breaker_config".to_string(),
            serde_json::json!({
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_ms": self.config.timeout.as_millis(),
                "recovery_timeout_ms": self.config.recovery_timeout.as_millis(),
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Increment total requests
        {
            let mut state = self.state.write().await;
            state.metrics.total_requests += 1;
        }

        // Check if we should attempt reset
        if self.should_attempt_reset().await {
            let mut state = self.state.write().await;
            let old_state = state.state;
            state.state = CircuitState::HalfOpen;
            state.success_count = 0;
            state.record_state_change(old_state, CircuitState::HalfOpen);
        }

        // Check circuit state
        {
            let is_open = {
                let state = self.state.read().await;
                state.state == CircuitState::Open
            };
            if is_open {
                let mut state_mut = self.state.write().await;
                state_mut.metrics.rejected_requests += 1;
                return Err(AgentError::ProcessingError(
                    "circuit breaker is open".to_string(),
                ));
            }
        }

        // Attempt request
        match self.inner.process(message).await {
            Ok(response) => {
                {
                    let mut state = self.state.write().await;
                    state.metrics.successful_requests += 1;
                }
                self.on_success().await;
                Ok(response)
            }
            Err(err) => {
                {
                    let mut state = self.state.write().await;
                    state.metrics.failed_requests += 1;
                }
                self.on_failure().await;
                Err(err)
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};

    struct FailingAgent {
        attempts: Arc<AtomicU32>,
        should_fail: Arc<AtomicU32>,
    }

    impl FailingAgent {
        fn new(should_fail: bool) -> Self {
            Self {
                attempts: Arc::new(AtomicU32::new(0)),
                should_fail: Arc::new(AtomicU32::new(if should_fail { 1 } else { 0 })),
            }
        }

        fn set_should_fail(&self, fail: bool) {
            self.should_fail
                .store(if fail { 1 } else { 0 }, Ordering::SeqCst);
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
            self.attempts.fetch_add(1, Ordering::SeqCst);

            if self.should_fail.load(Ordering::SeqCst) == 1 {
                Err(AgentError::ProcessingError("failure".to_string()))
            } else {
                Ok(Message::with_text("assistant", "success"))
            }
        }
    }

    #[tokio::test]
    async fn test_circuit_breaker_opens_after_threshold() {
        let agent = FailingAgent::new(true);
        let config = CircuitBreakerConfig::builder()
            .failure_threshold(3)
            .recovery_timeout(Duration::from_secs(60))
            .build();

        let cb_agent = CircuitBreakerMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // First 3 attempts should call the agent
        for _ in 0..3 {
            let _ = cb_agent.process(msg.clone()).await;
        }
        assert_eq!(cb_agent.inner.attempt_count(), 3);

        // Circuit should now be open - next attempt fails without calling agent
        let result = cb_agent.process(msg.clone()).await;
        assert!(result.is_err());
        assert_eq!(cb_agent.inner.attempt_count(), 3); // No additional call

        // Verify state
        let state = cb_agent.state.read().await;
        assert_eq!(state.state, CircuitState::Open);
    }

    #[tokio::test]
    async fn test_circuit_breaker_closes_after_success_threshold() {
        let agent = FailingAgent::new(true);
        let config = CircuitBreakerConfig::builder()
            .failure_threshold(2)
            .success_threshold(2)
            .recovery_timeout(Duration::from_millis(100))
            .build();

        let cb_agent = CircuitBreakerMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // Open the circuit
        for _ in 0..2 {
            let _ = cb_agent.process(msg.clone()).await;
        }

        // Verify circuit is open
        {
            let state = cb_agent.state.read().await;
            assert_eq!(state.state, CircuitState::Open);
        }

        // Wait for timeout to transition to half-open
        tokio::time::sleep(Duration::from_millis(150)).await;

        // Fix the agent
        cb_agent.inner.set_should_fail(false);

        // Next 2 successes should close the circuit
        for _ in 0..2 {
            let result = cb_agent.process(msg.clone()).await;
            assert!(result.is_ok());
        }

        // Verify circuit is closed
        let state = cb_agent.state.read().await;
        assert_eq!(state.state, CircuitState::Closed);
    }

    #[tokio::test]
    async fn test_circuit_breaker_half_open_failure_reopens() {
        let agent = FailingAgent::new(true);
        let config = CircuitBreakerConfig::builder()
            .failure_threshold(2)
            .recovery_timeout(Duration::from_millis(100))
            .build();

        let cb_agent = CircuitBreakerMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // Open the circuit
        for _ in 0..2 {
            let _ = cb_agent.process(msg.clone()).await;
        }

        // Wait for timeout to transition to half-open
        tokio::time::sleep(Duration::from_millis(150)).await;

        // Verify we're in half-open (by attempting a request that transitions state)
        let _ = cb_agent.process(msg.clone()).await;

        // Should be back to open due to failure
        let state = cb_agent.state.read().await;
        assert_eq!(state.state, CircuitState::Open);
    }

    #[tokio::test]
    async fn test_circuit_breaker_resets_failure_count_on_success() {
        let agent = FailingAgent::new(false);
        let config = CircuitBreakerConfig::builder().failure_threshold(3).build();

        let cb_agent = CircuitBreakerMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // Cause some failures
        cb_agent.inner.set_should_fail(true);
        for _ in 0..2 {
            let _ = cb_agent.process(msg.clone()).await;
        }

        // One success should reset counter
        cb_agent.inner.set_should_fail(false);
        let _ = cb_agent.process(msg.clone()).await;

        // Verify failure count reset
        let state = cb_agent.state.read().await;
        assert_eq!(state.failure_count, 0);
        assert_eq!(state.state, CircuitState::Closed);
    }
}
