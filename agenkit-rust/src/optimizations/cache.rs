//! Caching optimizations for agents
//!
//! Provides LRU caching and async memoization to reduce redundant
//! LLM API calls and improve response times for repeated queries.

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::sync::Arc;

#[cfg(feature = "native")]
use lru::LruCache;
#[cfg(feature = "native")]
use moka::future::Cache;
#[cfg(feature = "native")]
use std::num::NonZeroUsize;
#[cfg(feature = "native")]
use tokio::sync::Mutex;

/// LRU Cache-based agent wrapper
///
/// Caches agent responses based on message content hash.
/// Useful for agents with deterministic responses.
///
/// # Example
/// ```
/// use agenkit::optimizations::CachedAgent;
/// use std::sync::Arc;
///
/// // let agent = Arc::new(MyAgent::new());
/// // let cached = CachedAgent::new(agent, 100);
/// //
/// // // First call hits the agent
/// // let response1 = cached.process(message.clone()).await?;
/// //
/// // // Second call returns cached result
/// // let response2 = cached.process(message).await?;
/// ```
#[cfg(feature = "native")]
pub struct CachedAgent {
    inner: Arc<dyn Agent>,
    cache: Arc<Mutex<LruCache<u64, Message>>>,
}

#[cfg(feature = "native")]
impl CachedAgent {
    /// Create a new cached agent with specified capacity
    ///
    /// # Arguments
    /// * `inner` - The agent to wrap with caching
    /// * `capacity` - Maximum number of cached responses
    pub fn new(inner: Arc<dyn Agent>, capacity: usize) -> Self {
        Self {
            inner,
            cache: Arc::new(Mutex::new(LruCache::new(
                NonZeroUsize::new(capacity).expect("capacity must be non-zero"),
            ))),
        }
    }

    /// Compute hash for a message
    fn hash_message(msg: &Message) -> u64 {
        let mut hasher = DefaultHasher::new();

        // Hash role
        msg.role.hash(&mut hasher);

        // Hash content (use text representation)
        if let Some(text) = msg.content_as_str() {
            text.hash(&mut hasher);
        }

        // Hash metadata keys (sorted for consistency)
        let mut keys: Vec<String> = msg.metadata.keys().cloned().collect();
        keys.sort();
        for key in &keys {
            key.hash(&mut hasher);
            if let Some(value) = msg.metadata.get(key) {
                // Hash the JSON representation
                if let Ok(json_str) = serde_json::to_string(value) {
                    json_str.hash(&mut hasher);
                }
            }
        }

        hasher.finish()
    }

    /// Get cache statistics
    pub async fn cache_stats(&self) -> (usize, usize) {
        let cache = self.cache.lock().await;
        (cache.len(), cache.cap().get())
    }

    /// Clear the cache
    pub async fn clear_cache(&self) {
        let mut cache = self.cache.lock().await;
        cache.clear();
    }
}

#[cfg(feature = "native")]
#[async_trait]
impl Agent for CachedAgent {
    fn name(&self) -> &str {
        self.inner.name()
    }

    fn capabilities(&self) -> Vec<String> {
        self.inner.capabilities()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let hash = Self::hash_message(&message);

        // Check cache
        {
            let mut cache = self.cache.lock().await;
            if let Some(cached) = cache.get(&hash) {
                return Ok(cached.clone());
            }
        }

        // Cache miss - call inner agent
        let response = self.inner.process(message).await?;

        // Store in cache
        {
            let mut cache = self.cache.lock().await;
            cache.put(hash, response.clone());
        }

        Ok(response)
    }
}

/// Async memoization wrapper using moka cache
///
/// Provides time-aware caching with automatic expiration.
/// Better for production systems with TTL requirements.
///
/// # Example
/// ```
/// use agenkit::optimizations::MemoizedAgent;
/// use std::sync::Arc;
/// use std::time::Duration;
///
/// // let agent = Arc::new(MyAgent::new());
/// // let memoized = MemoizedAgent::new(agent, 1000, Some(Duration::from_secs(300)));
/// //
/// // // Responses cached for 5 minutes
/// // let response = memoized.process(message).await?;
/// ```
#[cfg(feature = "native")]
pub struct MemoizedAgent {
    inner: Arc<dyn Agent>,
    cache: Cache<u64, Message>,
}

#[cfg(feature = "native")]
impl MemoizedAgent {
    /// Create a new memoized agent
    ///
    /// # Arguments
    /// * `inner` - The agent to wrap with memoization
    /// * `max_capacity` - Maximum number of cached responses
    /// * `time_to_live` - Optional TTL for cache entries
    pub fn new(
        inner: Arc<dyn Agent>,
        max_capacity: u64,
        time_to_live: Option<std::time::Duration>,
    ) -> Self {
        let mut builder = Cache::builder().max_capacity(max_capacity);

        if let Some(ttl) = time_to_live {
            builder = builder.time_to_live(ttl);
        }

        Self {
            inner,
            cache: builder.build(),
        }
    }

    /// Compute hash for a message
    fn hash_message(msg: &Message) -> u64 {
        let mut hasher = DefaultHasher::new();

        msg.role.hash(&mut hasher);

        if let Some(text) = msg.content_as_str() {
            text.hash(&mut hasher);
        }

        let mut keys: Vec<String> = msg.metadata.keys().cloned().collect();
        keys.sort();
        for key in &keys {
            key.hash(&mut hasher);
            if let Some(value) = msg.metadata.get(key) {
                // Hash the JSON representation
                if let Ok(json_str) = serde_json::to_string(value) {
                    json_str.hash(&mut hasher);
                }
            }
        }

        hasher.finish()
    }

    /// Get cache statistics
    pub async fn cache_stats(&self) -> (u64, u64) {
        // Sync to ensure accurate counts
        self.cache.run_pending_tasks().await;
        (self.cache.entry_count(), self.cache.weighted_size())
    }

    /// Clear the cache
    pub async fn clear_cache(&self) {
        self.cache.invalidate_all();
        self.cache.run_pending_tasks().await;
    }

    /// Get estimated cache size
    pub fn estimated_size(&self) -> u64 {
        self.cache.weighted_size()
    }
}

#[cfg(feature = "native")]
#[async_trait]
impl Agent for MemoizedAgent {
    fn name(&self) -> &str {
        self.inner.name()
    }

    fn capabilities(&self) -> Vec<String> {
        self.inner.capabilities()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let hash = Self::hash_message(&message);

        // Check cache
        if let Some(cached) = self.cache.get(&hash).await {
            return Ok(cached);
        }

        // Cache miss - call inner agent
        let response = self.inner.process(message).await?;

        // Store in cache
        self.cache.insert(hash, response.clone()).await;

        Ok(response)
    }
}

#[cfg(test)]
#[cfg(feature = "native")]
mod tests {
    use super::*;
    use crate::core::{Agent, AgentError, Message};
    use async_trait::async_trait;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;

    struct CountingAgent {
        name: String,
        call_count: Arc<AtomicUsize>,
    }

    impl CountingAgent {
        fn new(name: &str) -> (Arc<Self>, Arc<AtomicUsize>) {
            let count = Arc::new(AtomicUsize::new(0));
            let agent = Arc::new(Self {
                name: name.to_string(),
                call_count: count.clone(),
            });
            (agent, count)
        }
    }

    #[async_trait]
    impl Agent for CountingAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["count".to_string()]
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            self.call_count.fetch_add(1, Ordering::SeqCst);
            Ok(Message::with_text(
                "assistant",
                format!("Processed: {}", message.content_as_str().unwrap_or("")),
            ))
        }
    }

    #[tokio::test]
    async fn test_lru_cache_basic() {
        let (agent, count) = CountingAgent::new("test");
        let cached = CachedAgent::new(agent, 10);

        let msg = Message::with_text("user", "Hello");

        // First call should hit agent
        let _ = cached.process(msg.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 1);

        // Second call should use cache
        let _ = cached.process(msg.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 1);

        // Different message should hit agent
        let msg2 = Message::with_text("user", "World");
        let _ = cached.process(msg2).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 2);
    }

    #[tokio::test]
    async fn test_lru_cache_eviction() {
        let (agent, count) = CountingAgent::new("test");
        let cached = CachedAgent::new(agent, 2); // Small cache

        // Fill cache
        let msg1 = Message::with_text("user", "Message 1");
        let msg2 = Message::with_text("user", "Message 2");
        let msg3 = Message::with_text("user", "Message 3");

        // Add msg1 and msg2 to cache
        let _ = cached.process(msg1.clone()).await.unwrap();
        let _ = cached.process(msg2.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 2);

        // Add msg3, which evicts msg1 (LRU)
        let _ = cached.process(msg3.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 3);

        // msg1 was evicted, so it hits agent and gets re-added to cache
        // This evicts msg2 (the new LRU)
        let _ = cached.process(msg1.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 4);

        // msg3 should still be cached
        let _ = cached.process(msg3.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 4);

        // msg1 should still be cached (just added)
        let _ = cached.process(msg1).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 4);

        // msg2 was evicted when msg1 was re-added, so it hits agent
        let _ = cached.process(msg2).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 5);
    }

    #[tokio::test]
    async fn test_memoized_agent_basic() {
        let (agent, count) = CountingAgent::new("test");
        let memoized = MemoizedAgent::new(agent, 100, None);

        let msg = Message::with_text("user", "Hello");

        // First call should hit agent
        let _ = memoized.process(msg.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 1);

        // Second call should use cache
        let _ = memoized.process(msg.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 1);

        // Check cache stats
        let (entry_count, _) = memoized.cache_stats().await;
        assert!(entry_count > 0);
    }

    #[tokio::test]
    async fn test_memoized_agent_ttl() {
        use std::time::Duration;

        let (agent, count) = CountingAgent::new("test");
        let memoized = MemoizedAgent::new(agent, 100, Some(Duration::from_millis(100)));

        let msg = Message::with_text("user", "Hello");

        // First call
        let _ = memoized.process(msg.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 1);

        // Second call (cached)
        let _ = memoized.process(msg.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 1);

        // Wait for TTL expiration
        tokio::time::sleep(Duration::from_millis(150)).await;

        // Should hit agent again after expiration
        let _ = memoized.process(msg.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 2);
    }

    #[tokio::test]
    async fn test_cache_clear() {
        let (agent, count) = CountingAgent::new("test");
        let cached = CachedAgent::new(agent, 10);

        let msg = Message::with_text("user", "Hello");

        let _ = cached.process(msg.clone()).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 1);

        // Clear cache
        cached.clear_cache().await;

        // Should hit agent again
        let _ = cached.process(msg).await.unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 2);
    }
}
