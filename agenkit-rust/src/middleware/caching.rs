//! Caching middleware with LRU eviction and TTL support.
//!
//! Caches agent responses to avoid redundant processing of identical requests,
//! reducing latency, cost, and load on downstream services.
//!
//! # Features
//!
//! - **LRU Eviction**: Least Recently Used items evicted when cache is full
//! - **TTL Support**: Entries expire after configured time-to-live
//! - **Thread-Safe**: Uses RwLock for concurrent access
//! - **Configurable**: Adjustable size and TTL
//!
//! # When to Use
//!
//! - **Expensive operations**: LLM calls, database queries, API requests
//! - **Repeated queries**: Same questions asked frequently
//! - **Cost reduction**: Avoid paying for duplicate API calls
//! - **Latency improvement**: Instant response from cache
//!
//! # When NOT to Use
//!
//! - **Dynamic content**: Responses change frequently
//! - **User-specific**: Responses vary per user/context
//! - **Side effects**: Operations that modify state
//! - **Real-time data**: Need fresh data every time
//!
//! # Cache Key
//!
//! Cache key is generated from message content (JSON serialization).
//! Messages with identical content share the same cache entry.
//!
//! # Example
//!
//! ```rust
//! use agenkit::middleware::{CachingMiddleware, CachingConfig};
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
//! let config = CachingConfig::builder()
//!     .max_size(1000)
//!     .ttl(Duration::from_secs(300))  // 5 minutes
//!     .build();
//!
//! let cache_agent = CachingMiddleware::new(agent, config);
//!
//! // First call: hits agent
//! let msg = Message::with_text("user", "What is 2+2?");
//! let response1 = cache_agent.process(msg.clone()).await;
//!
//! // Second call: served from cache
//! let response2 = cache_agent.process(msg).await;
//! # }
//! ```

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

/// Configuration for caching middleware.
#[derive(Debug, Clone)]
pub struct CachingConfig {
    /// Maximum number of entries in cache.
    /// Default: 1000
    pub max_size: usize,

    /// Time-to-live for cache entries.
    /// Default: 5 minutes
    pub ttl: Duration,
}

impl Default for CachingConfig {
    fn default() -> Self {
        Self {
            max_size: 1000,
            ttl: Duration::from_secs(300), // 5 minutes
        }
    }
}

impl CachingConfig {
    /// Create a new builder for CachingConfig.
    pub fn builder() -> CachingConfigBuilder {
        CachingConfigBuilder::default()
    }
}

/// Builder for CachingConfig.
#[derive(Debug, Default)]
pub struct CachingConfigBuilder {
    max_size: Option<usize>,
    ttl: Option<Duration>,
}

impl CachingConfigBuilder {
    /// Set maximum cache size.
    pub fn max_size(mut self, size: usize) -> Self {
        self.max_size = Some(size);
        self
    }

    /// Set time-to-live for cache entries.
    pub fn ttl(mut self, ttl: Duration) -> Self {
        self.ttl = Some(ttl);
        self
    }

    /// Build the CachingConfig.
    pub fn build(self) -> CachingConfig {
        let default = CachingConfig::default();
        CachingConfig {
            max_size: self.max_size.unwrap_or(default.max_size),
            ttl: self.ttl.unwrap_or(default.ttl),
        }
    }
}

/// Metrics for caching middleware.
#[derive(Debug, Clone, Default)]
pub struct CachingMetrics {
    /// Total number of requests processed.
    pub total_requests: u64,

    /// Number of cache hits.
    pub cache_hits: u64,

    /// Number of cache misses.
    pub cache_misses: u64,

    /// Number of evictions (LRU + expired).
    pub evictions: u64,

    /// Current cache size.
    pub current_size: usize,
}

impl CachingMetrics {
    /// Calculate cache hit rate (percentage).
    pub fn hit_rate(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            (self.cache_hits as f64 / self.total_requests as f64) * 100.0
        }
    }

    /// Calculate cache miss rate (percentage).
    pub fn miss_rate(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            (self.cache_misses as f64 / self.total_requests as f64) * 100.0
        }
    }
}

/// Cache entry with value and metadata.
#[derive(Debug, Clone)]
struct CacheEntry {
    value: Message,
    inserted_at: Instant,
    last_accessed: Instant,
}

impl CacheEntry {
    fn new(value: Message) -> Self {
        let now = Instant::now();
        Self {
            value,
            inserted_at: now,
            last_accessed: now,
        }
    }

    fn is_expired(&self, ttl: Duration) -> bool {
        self.inserted_at.elapsed() >= ttl
    }

    fn touch(&mut self) {
        self.last_accessed = Instant::now();
    }
}

/// Generate cache key from message.
fn cache_key(message: &Message) -> u64 {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    // Hash the JSON representation of the message
    if let Ok(json) = serde_json::to_string(message) {
        json.hash(&mut hasher);
    }
    hasher.finish()
}

/// LRU cache implementation.
#[derive(Debug)]
struct LruCache {
    entries: HashMap<u64, CacheEntry>,
    max_size: usize,
    ttl: Duration,
    metrics: CachingMetrics,
}

impl LruCache {
    fn new(max_size: usize, ttl: Duration) -> Self {
        Self {
            entries: HashMap::new(),
            max_size,
            ttl,
            metrics: CachingMetrics::default(),
        }
    }

    fn get(&mut self, key: u64) -> Option<Message> {
        // Check if entry exists and is not expired
        let is_expired = if let Some(entry) = self.entries.get(&key) {
            entry.is_expired(self.ttl)
        } else {
            return None;
        };

        if is_expired {
            self.entries.remove(&key);
            self.metrics.current_size = self.entries.len();
            return None;
        }

        // Entry exists and is valid - touch it and return
        let result = if let Some(entry) = self.entries.get_mut(&key) {
            entry.touch();
            Some(entry.value.clone())
        } else {
            None
        };

        // Update metrics after releasing mutable borrow
        if result.is_some() {
            self.metrics.cache_hits += 1;
            self.metrics.current_size = self.entries.len();
        }

        result
    }

    fn insert(&mut self, key: u64, value: Message) {
        // Evict expired entries
        self.evict_expired();

        // Evict LRU entry if at capacity
        if self.entries.len() >= self.max_size && !self.entries.contains_key(&key) {
            self.evict_lru();
        }

        self.entries.insert(key, CacheEntry::new(value));
        self.metrics.current_size = self.entries.len();
    }

    fn evict_expired(&mut self) {
        let expired_keys: Vec<u64> = self
            .entries
            .iter()
            .filter(|(_, entry)| entry.is_expired(self.ttl))
            .map(|(k, _)| *k)
            .collect();

        let eviction_count = expired_keys.len();
        for key in expired_keys {
            self.entries.remove(&key);
        }

        if eviction_count > 0 {
            self.metrics.evictions += eviction_count as u64;
            self.metrics.current_size = self.entries.len();
        }
    }

    fn evict_lru(&mut self) {
        if let Some((&lru_key, _)) = self
            .entries
            .iter()
            .min_by_key(|(_, entry)| entry.last_accessed)
        {
            self.entries.remove(&lru_key);
            self.metrics.evictions += 1;
            self.metrics.current_size = self.entries.len();
        }
    }

    fn size(&self) -> usize {
        self.entries.len()
    }

    fn get_metrics(&self) -> CachingMetrics {
        self.metrics.clone()
    }
}

/// Caching middleware with LRU eviction and TTL support.
///
/// Caches agent responses to avoid redundant processing, improving
/// latency and reducing cost for repeated queries.
pub struct CachingMiddleware<A: Agent> {
    inner: A,
    config: CachingConfig,
    cache: Arc<RwLock<LruCache>>,
}

impl<A: Agent> CachingMiddleware<A> {
    /// Create a new caching middleware with the given agent and configuration.
    pub fn new(agent: A, config: CachingConfig) -> Self {
        Self {
            inner: agent,
            cache: Arc::new(RwLock::new(LruCache::new(config.max_size, config.ttl))),
            config,
        }
    }

    /// Create a new caching middleware with default configuration.
    pub fn with_defaults(agent: A) -> Self {
        Self::new(agent, CachingConfig::default())
    }

    /// Get current caching metrics.
    pub async fn get_metrics(&self) -> CachingMetrics {
        let cache = self.cache.read().await;
        cache.get_metrics()
    }
}

#[async_trait]
impl<A: Agent> Agent for CachingMiddleware<A> {
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
            .insert("middleware".to_string(), serde_json::json!("caching"));
        result.metadata.insert(
            "caching_config".to_string(),
            serde_json::json!({
                "max_size": self.config.max_size,
                "ttl_ms": self.config.ttl.as_millis(),
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let key = cache_key(&message);

        // Track total requests and try to get from cache
        {
            let mut cache = self.cache.write().await;
            cache.metrics.total_requests += 1;
            if let Some(cached) = cache.get(key) {
                return Ok(cached);
            }
        }

        // Cache miss - track and call inner agent
        {
            let mut cache = self.cache.write().await;
            cache.metrics.cache_misses += 1;
        }

        let response = self.inner.process(message).await?;

        // Store in cache
        {
            let mut cache = self.cache.write().await;
            cache.insert(key, response.clone());
        }

        Ok(response)
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
            let count = self.attempts.fetch_add(1, Ordering::SeqCst);
            Ok(Message::with_text(
                "assistant",
                format!("call {}", count + 1),
            ))
        }
    }

    #[tokio::test]
    async fn test_caching_returns_cached_response() {
        let agent = CountingAgent::new();
        let config = CachingConfig::builder().max_size(10).build();

        let cache_agent = CachingMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // First call - cache miss
        let result1 = cache_agent.process(msg.clone()).await.unwrap();
        assert_eq!(result1.content_as_str(), Some("call 1"));

        // Second call - cache hit
        let result2 = cache_agent.process(msg.clone()).await.unwrap();
        assert_eq!(result2.content_as_str(), Some("call 1")); // Same response

        // Agent was only called once
        assert_eq!(cache_agent.inner.attempt_count(), 1);
    }

    #[tokio::test]
    async fn test_caching_different_messages() {
        let agent = CountingAgent::new();
        let config = CachingConfig::builder().max_size(10).build();

        let cache_agent = CachingMiddleware::new(agent, config);

        let msg1 = Message::with_text("user", "test1");
        let msg2 = Message::with_text("user", "test2");

        // Different messages should not hit cache
        let result1 = cache_agent.process(msg1).await.unwrap();
        let result2 = cache_agent.process(msg2).await.unwrap();

        assert_eq!(result1.content_as_str(), Some("call 1"));
        assert_eq!(result2.content_as_str(), Some("call 2"));
        assert_eq!(cache_agent.inner.attempt_count(), 2);
    }

    #[tokio::test]
    async fn test_caching_ttl_expiration() {
        let agent = CountingAgent::new();
        let config = CachingConfig::builder()
            .ttl(Duration::from_millis(100))
            .build();

        let cache_agent = CachingMiddleware::new(agent, config);

        let msg = Message::with_text("user", "test");

        // First call
        let result1 = cache_agent.process(msg.clone()).await.unwrap();
        assert_eq!(result1.content_as_str(), Some("call 1"));

        // Wait for TTL to expire
        tokio::time::sleep(Duration::from_millis(150)).await;

        // Second call - cache expired
        let result2 = cache_agent.process(msg.clone()).await.unwrap();
        assert_eq!(result2.content_as_str(), Some("call 2"));

        assert_eq!(cache_agent.inner.attempt_count(), 2);
    }

    #[tokio::test]
    async fn test_caching_lru_eviction() {
        let agent = CountingAgent::new();
        let config = CachingConfig::builder().max_size(2).build();

        let cache_agent = CachingMiddleware::new(agent, config);

        let msg1 = Message::with_text("user", "test1");
        let msg2 = Message::with_text("user", "test2");
        let msg3 = Message::with_text("user", "test3");

        // Fill cache
        let _ = cache_agent.process(msg1.clone()).await;
        let _ = cache_agent.process(msg2.clone()).await;

        // Access msg1 to make it more recent
        let _ = cache_agent.process(msg1.clone()).await;

        // Add msg3 - should evict msg2 (LRU)
        let _ = cache_agent.process(msg3.clone()).await;

        // msg1 should still be cached
        let _ = cache_agent.process(msg1.clone()).await;

        // msg2 should not be cached
        let _ = cache_agent.process(msg2.clone()).await;

        // Verify: 1 (msg1), 2 (msg2), 3 (msg1 cached), 4 (msg3), 5 (msg1 cached), 6 (msg2 not cached)
        // Total calls: 4 (msg1, msg2, msg3, msg2 again)
        assert_eq!(cache_agent.inner.attempt_count(), 4);
    }

    #[tokio::test]
    async fn test_introspect_includes_caching_metadata() {
        let agent = CountingAgent::new();
        let config = CachingConfig::builder().max_size(100).build();

        let cache_agent = CachingMiddleware::new(agent, config);
        let result = cache_agent.introspect();

        assert_eq!(
            result.metadata.get("middleware"),
            Some(&serde_json::json!("caching"))
        );
        assert!(result.metadata.contains_key("caching_config"));
    }
}
