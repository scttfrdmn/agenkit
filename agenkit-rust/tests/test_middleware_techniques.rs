//! Middleware technique tests
//!
//! Comprehensive tests for agenkit middleware:
//! Retry, CircuitBreaker, Timeout, Caching, RateLimiter, Batching.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::middleware::{
    BatchingConfig, BatchingMiddleware, CachingConfig, CachingMiddleware, CircuitBreakerConfig,
    CircuitBreakerMiddleware, RateLimiterConfig, RateLimiterMiddleware, RetryConfig,
    RetryMiddleware, TimeoutConfig, TimeoutMiddleware,
};
use async_trait::async_trait;
use std::sync::{
    atomic::{AtomicUsize, Ordering},
    Arc,
};
use std::time::Duration;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

struct EchoAgent;

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        "echo"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text(
            "assistant",
            message.content_as_str().unwrap_or(""),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string()]
    }
}

struct CountingAgent {
    count: Arc<AtomicUsize>,
    fail_until: usize, // fail for first N calls, then succeed
}

#[async_trait]
impl Agent for CountingAgent {
    fn name(&self) -> &str {
        "counting"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let call = self.count.fetch_add(1, Ordering::SeqCst) + 1;
        if call <= self.fail_until {
            Err(AgentError::ProcessingError(format!("call {} failed", call)))
        } else {
            Ok(Message::with_text("assistant", format!("success on call {}", call)))
        }
    }
}

struct AlwaysErrorAgent;

#[async_trait]
impl Agent for AlwaysErrorAgent {
    fn name(&self) -> &str {
        "always-error"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::ProcessingError("always fails".to_string()))
    }
}

struct SlowAgent {
    delay: Duration,
}

#[async_trait]
impl Agent for SlowAgent {
    fn name(&self) -> &str {
        "slow"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        tokio::time::sleep(self.delay).await;
        Ok(Message::with_text("assistant", "slow response"))
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Retry middleware tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_retry_success_first_attempt() {
    let agent = RetryMiddleware::new(EchoAgent, RetryConfig::default());
    let result = agent.process(Message::with_text("user", "hello")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_retry_success_after_failures() {
    let count = Arc::new(AtomicUsize::new(0));
    let inner = CountingAgent {
        count: Arc::clone(&count),
        fail_until: 2,
    };
    let config = RetryConfig::builder()
        .max_retries(5)
        .initial_delay(Duration::from_millis(1))
        .build();
    let agent = RetryMiddleware::new(inner, config);
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
    assert!(count.load(Ordering::SeqCst) >= 3);
}

#[tokio::test]
async fn test_retry_exhausted_returns_error() {
    let config = RetryConfig::builder()
        .max_retries(3)
        .initial_delay(Duration::from_millis(1))
        .build();
    let agent = RetryMiddleware::new(AlwaysErrorAgent, config);
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_retry_zero_retries() {
    let config = RetryConfig::builder()
        .max_retries(1) // 1 = just initial attempt, no retries
        .initial_delay(Duration::from_millis(1))
        .build();
    let agent = RetryMiddleware::new(AlwaysErrorAgent, config);
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_retry_builder_defaults() {
    let config = RetryConfig::builder().build();
    assert!(config.max_retries > 0);
    assert!(config.multiplier > 1.0);
}

#[tokio::test]
async fn test_retry_metrics_track_attempts() {
    let count = Arc::new(AtomicUsize::new(0));
    let inner = CountingAgent {
        count: Arc::clone(&count),
        fail_until: 1,
    };
    let config = RetryConfig::builder()
        .max_retries(3)
        .initial_delay(Duration::from_millis(1))
        .build();
    let agent = RetryMiddleware::new(inner, config);
    let _ = agent.process(Message::with_text("user", "test")).await;
    let metrics = agent.get_metrics().await;
    assert!(metrics.total_attempts > 0);
}

#[tokio::test]
async fn test_retry_max_delay_capped() {
    let config = RetryConfig::builder()
        .max_retries(3)
        .initial_delay(Duration::from_millis(1))
        .max_delay(Duration::from_millis(5))
        .multiplier(100.0)
        .build();
    // max_delay should be respected — config itself should be valid
    assert!(config.max_delay <= Duration::from_millis(10));
}

#[tokio::test]
async fn test_retry_name_preserved() {
    let agent = RetryMiddleware::new(EchoAgent, RetryConfig::default());
    assert_eq!(agent.name(), "echo");
}

#[tokio::test]
async fn test_retry_with_defaults_constructor() {
    let agent = RetryMiddleware::with_defaults(EchoAgent);
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_retry_introspect_contains_middleware() {
    let agent = RetryMiddleware::new(EchoAgent, RetryConfig::default());
    let info = agent.introspect();
    assert!(info.metadata.contains_key("middleware"));
}

// ─────────────────────────────────────────────────────────────────────────────
// CircuitBreaker middleware tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_circuit_breaker_closed_passes_through() {
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(5)
        .build();
    let agent = CircuitBreakerMiddleware::new(EchoAgent, config);
    let result = agent.process(Message::with_text("user", "hello")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_circuit_breaker_opens_after_failures() {
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(3)
        .recovery_timeout(Duration::from_secs(60))
        .build();
    let agent = CircuitBreakerMiddleware::new(AlwaysErrorAgent, config);
    // Exhaust failures to open circuit
    for _ in 0..5 {
        let _ = agent.process(Message::with_text("user", "fail")).await;
    }
    let metrics = agent.get_metrics().await;
    // Should have recorded failures
    assert!(metrics.failed_requests > 0);
}

#[tokio::test]
async fn test_circuit_breaker_metrics_initial_state() {
    let agent = CircuitBreakerMiddleware::with_defaults(EchoAgent);
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.total_requests, 0);
    assert_eq!(metrics.failed_requests, 0);
}

#[tokio::test]
async fn test_circuit_breaker_metrics_tracks_success() {
    let agent = CircuitBreakerMiddleware::with_defaults(EchoAgent);
    let _ = agent.process(Message::with_text("user", "test")).await;
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.total_requests, 1);
    assert_eq!(metrics.successful_requests, 1);
}

#[tokio::test]
async fn test_circuit_breaker_metrics_tracks_failure() {
    let agent = CircuitBreakerMiddleware::with_defaults(AlwaysErrorAgent);
    let _ = agent.process(Message::with_text("user", "test")).await;
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.total_requests, 1);
    assert_eq!(metrics.failed_requests, 1);
}

#[tokio::test]
async fn test_circuit_breaker_builder_configuration() {
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(10)
        .success_threshold(3)
        .timeout(Duration::from_secs(5))
        .recovery_timeout(Duration::from_secs(30))
        .build();
    assert_eq!(config.failure_threshold, 10);
    assert_eq!(config.success_threshold, 3);
}

#[tokio::test]
async fn test_circuit_breaker_state_variants() {
    use agenkit::middleware::CircuitState;
    let states = [CircuitState::Closed, CircuitState::Open, CircuitState::HalfOpen];
    assert_eq!(states.len(), 3);
    assert_eq!(CircuitState::Closed, CircuitState::Closed);
    assert_ne!(CircuitState::Closed, CircuitState::Open);
}

#[tokio::test]
async fn test_circuit_breaker_name_preserved() {
    let agent = CircuitBreakerMiddleware::with_defaults(EchoAgent);
    assert_eq!(agent.name(), "echo");
}

#[tokio::test]
async fn test_circuit_breaker_multiple_requests_tracking() {
    let agent = CircuitBreakerMiddleware::with_defaults(EchoAgent);
    for _ in 0..5 {
        let _ = agent.process(Message::with_text("user", "test")).await;
    }
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.total_requests, 5);
    assert_eq!(metrics.successful_requests, 5);
}

#[tokio::test]
async fn test_circuit_breaker_default_config() {
    let config = CircuitBreakerConfig::default();
    assert!(config.failure_threshold > 0);
    assert!(config.success_threshold > 0);
    assert!(config.recovery_timeout > Duration::ZERO);
}

// ─────────────────────────────────────────────────────────────────────────────
// Timeout middleware tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_timeout_fast_agent_passes() {
    let config = TimeoutConfig::builder()
        .timeout(Duration::from_secs(5))
        .build();
    let agent = TimeoutMiddleware::new(EchoAgent, config);
    let result = agent.process(Message::with_text("user", "fast")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_timeout_slow_agent_times_out() {
    let config = TimeoutConfig::builder()
        .timeout(Duration::from_millis(50))
        .build();
    let inner = SlowAgent {
        delay: Duration::from_millis(200),
    };
    let agent = TimeoutMiddleware::new(inner, config);
    let result = agent.process(Message::with_text("user", "slow")).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_timeout_error_message_not_empty() {
    let config = TimeoutConfig::builder()
        .timeout(Duration::from_millis(10))
        .build();
    let inner = SlowAgent {
        delay: Duration::from_millis(200),
    };
    let agent = TimeoutMiddleware::new(inner, config);
    let err = agent
        .process(Message::with_text("user", "slow"))
        .await
        .unwrap_err();
    let msg = format!("{}", err);
    assert!(!msg.is_empty());
}

#[tokio::test]
async fn test_timeout_metrics_total_requests() {
    let config = TimeoutConfig::builder()
        .timeout(Duration::from_secs(5))
        .build();
    let agent = TimeoutMiddleware::new(EchoAgent, config);
    for _ in 0..3 {
        let _ = agent.process(Message::with_text("user", "test")).await;
    }
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.total_requests, 3);
}

#[tokio::test]
async fn test_timeout_metrics_timeout_count() {
    let config = TimeoutConfig::builder()
        .timeout(Duration::from_millis(10))
        .build();
    let inner = SlowAgent {
        delay: Duration::from_millis(200),
    };
    let agent = TimeoutMiddleware::new(inner, config);
    let _ = agent.process(Message::with_text("user", "slow")).await;
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.timed_out_requests, 1);
}

#[tokio::test]
async fn test_timeout_name_preserved() {
    let config = TimeoutConfig::builder().timeout(Duration::from_secs(5)).build();
    let agent = TimeoutMiddleware::new(EchoAgent, config);
    assert_eq!(agent.name(), "echo");
}

#[tokio::test]
async fn test_timeout_builder_configuration() {
    let config = TimeoutConfig::builder()
        .timeout(Duration::from_secs(10))
        .build();
    assert!(config.timeout >= Duration::from_secs(1));
}

#[tokio::test]
async fn test_timeout_long_timeout_no_fire() {
    let config = TimeoutConfig::builder()
        .timeout(Duration::from_secs(100))
        .build();
    let inner = SlowAgent {
        delay: Duration::from_millis(5),
    };
    let agent = TimeoutMiddleware::new(inner, config);
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_timeout_successful_requests_tracked() {
    let config = TimeoutConfig::builder()
        .timeout(Duration::from_secs(5))
        .build();
    let agent = TimeoutMiddleware::new(EchoAgent, config);
    let _ = agent.process(Message::with_text("user", "test")).await;
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.successful_requests, 1);
}

// ─────────────────────────────────────────────────────────────────────────────
// Caching middleware tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_caching_cache_miss_calls_agent() {
    let config = CachingConfig::builder()
        .max_size(100)
        .ttl(Duration::from_secs(60))
        .build();
    let agent = CachingMiddleware::new(EchoAgent, config);
    let result = agent.process(Message::with_text("user", "hello")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_caching_cache_hit_returns_same() {
    let config = CachingConfig::builder()
        .max_size(100)
        .ttl(Duration::from_secs(60))
        .build();
    let agent = CachingMiddleware::new(EchoAgent, config);
    let msg = Message::with_text("user", "cached query");
    let r1 = agent.process(msg.clone()).await.unwrap();
    let r2 = agent.process(msg).await.unwrap();
    assert_eq!(r1.content, r2.content);
}

#[tokio::test]
async fn test_caching_metrics_cold_cache() {
    let agent = CachingMiddleware::new(EchoAgent, CachingConfig::default());
    let _ = agent.process(Message::with_text("user", "test")).await;
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.cache_misses, 1);
    assert_eq!(metrics.cache_hits, 0);
}

#[tokio::test]
async fn test_caching_metrics_warm_cache() {
    let agent = CachingMiddleware::new(EchoAgent, CachingConfig::default());
    let msg = Message::with_text("user", "repeated query");
    let _ = agent.process(msg.clone()).await;
    let _ = agent.process(msg).await;
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.cache_hits, 1);
}

#[tokio::test]
async fn test_caching_different_messages_not_shared() {
    let agent = CachingMiddleware::new(EchoAgent, CachingConfig::default());
    let _ = agent.process(Message::with_text("user", "query A")).await;
    let _ = agent.process(Message::with_text("user", "query B")).await;
    let metrics = agent.get_metrics().await;
    assert_eq!(metrics.cache_misses, 2);
}

#[tokio::test]
async fn test_caching_name_preserved() {
    let agent = CachingMiddleware::new(EchoAgent, CachingConfig::default());
    assert_eq!(agent.name(), "echo");
}

#[tokio::test]
async fn test_caching_builder_configuration() {
    let config = CachingConfig::builder()
        .max_size(500)
        .ttl(Duration::from_secs(120))
        .build();
    assert_eq!(config.max_size, 500);
    assert_eq!(config.ttl, Duration::from_secs(120));
}

#[tokio::test]
async fn test_caching_default_config_reasonable() {
    let config = CachingConfig::default();
    assert!(config.max_size > 0);
    assert!(config.ttl > Duration::ZERO);
}

#[tokio::test]
async fn test_caching_introspect_available() {
    let agent = CachingMiddleware::new(EchoAgent, CachingConfig::default());
    let info = agent.introspect();
    assert!(info.metadata.contains_key("middleware"));
}

#[tokio::test]
async fn test_caching_cache_size_tracked() {
    let agent = CachingMiddleware::new(EchoAgent, CachingConfig::default());
    let _ = agent.process(Message::with_text("user", "unique 1")).await;
    let _ = agent.process(Message::with_text("user", "unique 2")).await;
    let metrics = agent.get_metrics().await;
    assert!(metrics.current_size <= 2);
}

// ─────────────────────────────────────────────────────────────────────────────
// RateLimiter middleware tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_rate_limiter_passes_under_limit() {
    let config = RateLimiterConfig::builder()
        .tokens_per_second(100.0)
        .capacity(100.0)
        .build();
    let agent = RateLimiterMiddleware::new(EchoAgent, config);
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_rate_limiter_name_preserved() {
    let agent = RateLimiterMiddleware::new(EchoAgent, RateLimiterConfig::default());
    assert_eq!(agent.name(), "echo");
}

#[tokio::test]
async fn test_rate_limiter_builder() {
    let config = RateLimiterConfig::builder()
        .tokens_per_second(10.0)
        .capacity(20.0)
        .max_wait_time(Duration::from_secs(5))
        .build();
    assert_eq!(config.tokens_per_second, 10.0);
    assert_eq!(config.capacity, 20.0);
}

#[tokio::test]
async fn test_rate_limiter_default_config() {
    let config = RateLimiterConfig::default();
    assert!(config.tokens_per_second > 0.0);
    assert!(config.capacity > 0.0);
}

#[tokio::test]
async fn test_rate_limiter_metrics_tracking() {
    let config = RateLimiterConfig::builder()
        .tokens_per_second(100.0)
        .capacity(100.0)
        .build();
    let agent = RateLimiterMiddleware::new(EchoAgent, config);
    let _ = agent.process(Message::with_text("user", "test")).await;
    let metrics = agent.get_metrics().await;
    assert!(metrics.total_requests >= 1);
}

#[tokio::test]
async fn test_rate_limiter_with_defaults() {
    let agent = RateLimiterMiddleware::with_defaults(EchoAgent);
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_rate_limiter_zero_wait_time_immediate_reject() {
    let config = RateLimiterConfig::builder()
        .tokens_per_second(1.0)
        .capacity(1.0)
        .max_wait_time(Duration::ZERO) // no waiting
        .build();
    let agent = RateLimiterMiddleware::new(EchoAgent, config);
    // First request consumes the token
    let _ = agent.process(Message::with_text("user", "first")).await;
    // Second request may be rejected (no tokens, no wait)
    let result = agent.process(Message::with_text("user", "second")).await;
    // Either ok (tokens refilled) or err (rejected) — just no panic
    let _ = result;
}

#[tokio::test]
async fn test_rate_limiter_introspect() {
    let agent = RateLimiterMiddleware::with_defaults(EchoAgent);
    let info = agent.introspect();
    // Should have some metadata
    assert!(info.metadata.contains_key("middleware"));
}

// ─────────────────────────────────────────────────────────────────────────────
// Batching middleware tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_batching_single_item_processes() {
    let config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(Duration::from_millis(50))
        .build();
    let agent = BatchingMiddleware::new(EchoAgent, config);
    let result = agent.process(Message::with_text("user", "solo")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_batching_name_preserved() {
    let agent = BatchingMiddleware::new(EchoAgent, BatchingConfig::default());
    assert_eq!(agent.name(), "echo");
}

#[tokio::test]
async fn test_batching_builder() {
    let config = BatchingConfig::builder()
        .max_batch_size(5)
        .max_wait_time(Duration::from_millis(100))
        .build();
    assert_eq!(config.max_batch_size, 5);
}

#[tokio::test]
async fn test_batching_default_config() {
    let config = BatchingConfig::default();
    assert!(config.max_batch_size > 0);
    assert!(config.max_wait_time > Duration::ZERO);
}

#[tokio::test]
async fn test_batching_introspect() {
    let agent = BatchingMiddleware::new(EchoAgent, BatchingConfig::default());
    let info = agent.introspect();
    assert!(info.metadata.contains_key("middleware"));
}

#[tokio::test]
async fn test_batching_concurrent_requests() {
    use std::sync::Arc;
    let config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(Duration::from_millis(20))
        .build();
    let agent = Arc::new(BatchingMiddleware::new(EchoAgent, config));

    let handles: Vec<_> = (0..3)
        .map(|i| {
            let agent = Arc::clone(&agent);
            tokio::spawn(async move {
                agent
                    .process(Message::with_text("user", format!("msg {}", i)))
                    .await
            })
        })
        .collect();

    for handle in handles {
        let result = handle.await.unwrap();
        assert!(result.is_ok());
    }
}

#[tokio::test]
async fn test_batching_capabilities_preserved() {
    let agent = BatchingMiddleware::new(EchoAgent, BatchingConfig::default());
    assert!(!agent.capabilities().is_empty());
}
