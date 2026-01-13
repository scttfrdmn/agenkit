//! Per-user rate limiting middleware with token bucket algorithm.
//!
//! Provides fine-grained rate limiting per user/client while maintaining
//! separate token buckets for fair resource allocation across users.

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;

/// Per-user rate limit error.
#[derive(Debug, Clone)]
pub struct PerUserRateLimitError {
    pub user_id: String,
    pub tokens_needed: u32,
    pub tokens_available: f64,
}

impl std::fmt::Display for PerUserRateLimitError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Rate limit exceeded for user '{}': need {} tokens, only {:.2} available",
            self.user_id, self.tokens_needed, self.tokens_available
        )
    }
}

impl std::error::Error for PerUserRateLimitError {}

/// User identifier extraction function type.
pub type UserIdExtractor = Arc<dyn Fn(&Message) -> String + Send + Sync>;

/// Configuration for per-user rate limiter.
#[derive(Clone)]
pub struct PerUserRateLimiterConfig {
    pub rate: f64,
    pub capacity: u32,
    pub tokens_per_request: u32,
    pub max_wait_timeout: Option<Duration>,
    pub user_id_extractor: UserIdExtractor,
}

impl Default for PerUserRateLimiterConfig {
    fn default() -> Self {
        Self {
            rate: 10.0,
            capacity: 10,
            tokens_per_request: 1,
            max_wait_timeout: None,
            user_id_extractor: Arc::new(|message: &Message| {
                message
                    .metadata
                    .get("user_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string()
            }),
        }
    }
}

impl PerUserRateLimiterConfig {
    pub fn builder() -> PerUserRateLimiterConfigBuilder {
        PerUserRateLimiterConfigBuilder::default()
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.rate <= 0.0 {
            return Err("rate must be positive".to_string());
        }
        if self.capacity < 1 {
            return Err("capacity must be at least 1".to_string());
        }
        if self.tokens_per_request < 1 {
            return Err("tokens_per_request must be at least 1".to_string());
        }
        if self.tokens_per_request > self.capacity {
            return Err("tokens_per_request cannot exceed capacity".to_string());
        }
        if let Some(timeout) = self.max_wait_timeout {
            if timeout.is_zero() {
                return Err("max_wait_timeout must be positive".to_string());
            }
        }
        Ok(())
    }
}

/// Builder for PerUserRateLimiterConfig.
#[derive(Default)]
pub struct PerUserRateLimiterConfigBuilder {
    rate: Option<f64>,
    capacity: Option<u32>,
    tokens_per_request: Option<u32>,
    max_wait_timeout: Option<Duration>,
    user_id_extractor: Option<UserIdExtractor>,
}

impl PerUserRateLimiterConfigBuilder {
    pub fn rate(mut self, rate: f64) -> Self {
        self.rate = Some(rate);
        self
    }

    pub fn capacity(mut self, capacity: u32) -> Self {
        self.capacity = Some(capacity);
        self
    }

    pub fn tokens_per_request(mut self, tokens: u32) -> Self {
        self.tokens_per_request = Some(tokens);
        self
    }

    pub fn max_wait_timeout(mut self, timeout: Duration) -> Self {
        self.max_wait_timeout = Some(timeout);
        self
    }

    pub fn user_id_extractor<F>(mut self, extractor: F) -> Self
    where
        F: Fn(&Message) -> String + Send + Sync + 'static,
    {
        self.user_id_extractor = Some(Arc::new(extractor));
        self
    }

    pub fn build(self) -> PerUserRateLimiterConfig {
        let default = PerUserRateLimiterConfig::default();
        PerUserRateLimiterConfig {
            rate: self.rate.unwrap_or(default.rate),
            capacity: self.capacity.unwrap_or(default.capacity),
            tokens_per_request: self.tokens_per_request.unwrap_or(default.tokens_per_request),
            max_wait_timeout: self.max_wait_timeout.or(default.max_wait_timeout),
            user_id_extractor: self.user_id_extractor.unwrap_or(default.user_id_extractor),
        }
    }
}

/// Token bucket for a single user.
#[derive(Debug, Clone)]
struct UserBucket {
    tokens: f64,
    last_update: Instant,
}

impl UserBucket {
    fn new(capacity: u32) -> Self {
        Self {
            tokens: capacity as f64,
            last_update: Instant::now(),
        }
    }
}

/// Metrics for per-user rate limiter.
#[derive(Debug, Clone, Default)]
pub struct PerUserRateLimiterMetrics {
    pub total_requests: u64,
    pub allowed_requests: u64,
    pub rejected_requests: u64,
    pub total_wait_time: Duration,
    pub active_users: usize,
}

/// Per-user rate limiter middleware.
pub struct PerUserRateLimiterMiddleware<A: Agent> {
    inner: A,
    config: PerUserRateLimiterConfig,
    buckets: Arc<Mutex<HashMap<String, UserBucket>>>,
    metrics: Arc<Mutex<PerUserRateLimiterMetrics>>,
}

impl<A: Agent> PerUserRateLimiterMiddleware<A> {
    pub fn new(agent: A, config: PerUserRateLimiterConfig) -> Result<Self, String> {
        config.validate()?;

        Ok(Self {
            inner: agent,
            config,
            buckets: Arc::new(Mutex::new(HashMap::new())),
            metrics: Arc::new(Mutex::new(PerUserRateLimiterMetrics::default())),
        })
    }

    pub fn with_defaults(agent: A) -> Result<Self, String> {
        Self::new(agent, PerUserRateLimiterConfig::default())
    }

    pub async fn get_metrics(&self) -> PerUserRateLimiterMetrics {
        self.metrics.lock().await.clone()
    }

    async fn get_user_bucket(&self, user_id: &str) -> UserBucket {
        let mut buckets = self.buckets.lock().await;

        if let Some(bucket) = buckets.get(user_id) {
            bucket.clone()
        } else {
            let bucket = UserBucket::new(self.config.capacity);
            buckets.insert(user_id.to_string(), bucket.clone());

            let mut metrics = self.metrics.lock().await;
            metrics.active_users = buckets.len();

            bucket
        }
    }

    async fn update_user_bucket(&self, user_id: &str, bucket: UserBucket) {
        let mut buckets = self.buckets.lock().await;
        buckets.insert(user_id.to_string(), bucket);
    }

    fn refill_user_tokens(&self, bucket: &mut UserBucket) {
        let now = Instant::now();
        let elapsed = now.duration_since(bucket.last_update);

        let tokens_to_add = elapsed.as_secs_f64() * self.config.rate;
        bucket.tokens = (bucket.tokens + tokens_to_add).min(self.config.capacity as f64);
        bucket.last_update = now;
    }

    async fn acquire_user_tokens(
        &self,
        user_id: &str,
        tokens_needed: u32,
    ) -> Result<(), PerUserRateLimitError> {
        let mut bucket = self.get_user_bucket(user_id).await;
        self.refill_user_tokens(&mut bucket);

        if bucket.tokens >= tokens_needed as f64 {
            bucket.tokens -= tokens_needed as f64;
            self.update_user_bucket(user_id, bucket).await;
            return Ok(());
        }

        // Calculate wait time
        let tokens_deficit = tokens_needed as f64 - bucket.tokens;
        let wait_duration = Duration::from_secs_f64(tokens_deficit / self.config.rate);

        // Check max wait timeout
        if let Some(max_timeout) = self.config.max_wait_timeout {
            if wait_duration > max_timeout {
                return Err(PerUserRateLimitError {
                    user_id: user_id.to_string(),
                    tokens_needed,
                    tokens_available: bucket.tokens,
                });
            }
        }

        // Wait for tokens
        let wait_start = Instant::now();
        tokio::time::sleep(wait_duration).await;
        let actual_wait_duration = wait_start.elapsed();

        {
            let mut metrics = self.metrics.lock().await;
            metrics.total_wait_time += actual_wait_duration;
        }

        // Re-acquire bucket and try again
        let mut bucket = self.get_user_bucket(user_id).await;
        self.refill_user_tokens(&mut bucket);

        if bucket.tokens >= tokens_needed as f64 {
            bucket.tokens -= tokens_needed as f64;
            self.update_user_bucket(user_id, bucket).await;
            Ok(())
        } else {
            Err(PerUserRateLimitError {
                user_id: user_id.to_string(),
                tokens_needed,
                tokens_available: bucket.tokens,
            })
        }
    }
}

#[async_trait]
impl<A: Agent> Agent for PerUserRateLimiterMiddleware<A> {
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
            serde_json::json!("per_user_rate_limiter"),
        );
        result.metadata.insert(
            "per_user_rate_limiter_config".to_string(),
            serde_json::json!({
                "rate": self.config.rate,
                "capacity": self.config.capacity,
                "tokens_per_request": self.config.tokens_per_request,
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        {
            let mut metrics = self.metrics.lock().await;
            metrics.total_requests += 1;
        }

        let user_id = (self.config.user_id_extractor)(&message);

        match self
            .acquire_user_tokens(&user_id, self.config.tokens_per_request)
            .await
        {
            Ok(()) => {
                {
                    let mut metrics = self.metrics.lock().await;
                    metrics.allowed_requests += 1;
                }

                self.inner.process(message).await
            }
            Err(err) => {
                {
                    let mut metrics = self.metrics.lock().await;
                    metrics.rejected_requests += 1;
                }

                Err(AgentError::ProcessingError(err.to_string()))
            }
        }
    }
}
