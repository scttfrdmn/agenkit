//! Redis-backed memory implementation with TTL and persistence.
//!
//! Features:
//! - Persistent storage (survives restarts)
//! - TTL support (automatic expiry)
//! - Multi-instance agents (shared memory)
//! - Fast access (in-memory Redis)
//! - Scalable (Redis cluster support)
//!
//! Use cases:
//! - Production deployments
//! - Multi-instance agents
//! - When persistence needed
//! - Shared memory across agents
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::memory::RedisMemory;
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let memory = RedisMemory::new(
//!     "redis://localhost:6379",
//!     86400, // 24 hours TTL
//!     "agenkit:memory",
//! ).await?;
//!
//! // Store message with metadata
//! let mut metadata = HashMap::new();
//! metadata.insert("importance".to_string(), serde_json::json!(0.8));
//! memory.store("session-123", "user", "Hello", Some(metadata)).await?;
//!
//! // Retrieve messages
//! let messages = memory.retrieve("session-123", 10, None, None, None).await?;
//!
//! // Clear session
//! memory.clear("session-123").await?;
//! # Ok(())
//! # }
//! ```
//!
//! Redis Data Structure:
//!   Key: "agenkit:memory:{session_id}:messages"
//!   Type: Sorted Set (ZSET)
//!   Score: Timestamp (for ordering)
//!   Value: JSON(message, metadata)

use anyhow::{Context, Result};
use redis::aio::MultiplexedConnection;
use redis::{AsyncCommands, Client};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

/// Stored message format in Redis.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct StoredMessage {
    role: String,
    content: String,
    metadata: HashMap<String, serde_json::Value>,
}

/// Message returned from Redis.
#[derive(Debug, Clone)]
pub struct Message {
    pub role: String,
    pub content: String,
}

/// Redis-backed memory with TTL and persistence support.
///
/// Provides persistent storage for agent conversations with automatic
/// expiration, multi-instance support, and filtering capabilities.
pub struct RedisMemory {
    redis_url: String,
    ttl: u64,
    key_prefix: String,
    client: Client,
}

impl RedisMemory {
    /// Create a new Redis memory instance.
    ///
    /// # Arguments
    ///
    /// * `redis_url` - Redis connection URL
    /// * `ttl` - Time-to-live in seconds (0 = no expiry)
    /// * `key_prefix` - Prefix for Redis keys
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::memory::RedisMemory;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let memory = RedisMemory::new(
    ///     "redis://localhost:6379",
    ///     86400,
    ///     "agenkit:memory",
    /// ).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn new(redis_url: &str, ttl: u64, key_prefix: &str) -> Result<Self> {
        let client = Client::open(redis_url).context("Failed to create Redis client")?;

        Ok(Self {
            redis_url: redis_url.to_string(),
            ttl,
            key_prefix: key_prefix.to_string(),
            client,
        })
    }

    /// Get Redis connection.
    async fn get_connection(&self) -> Result<MultiplexedConnection> {
        self.client
            .get_multiplexed_async_connection()
            .await
            .context("Failed to get Redis connection")
    }

    /// Get Redis key for a session.
    fn session_key(&self, session_id: &str) -> String {
        format!("{}:{}:messages", self.key_prefix, session_id)
    }

    /// Serialize message and metadata to JSON string.
    fn serialize_message(
        &self,
        role: &str,
        content: &str,
        metadata: HashMap<String, serde_json::Value>,
    ) -> Result<String> {
        let data = StoredMessage {
            role: role.to_string(),
            content: content.to_string(),
            metadata,
        };
        serde_json::to_string(&data).context("Failed to serialize message")
    }

    /// Deserialize JSON string to message and metadata.
    fn deserialize_message(
        &self,
        data: &str,
    ) -> Result<(Message, HashMap<String, serde_json::Value>)> {
        let stored: StoredMessage =
            serde_json::from_str(data).context("Failed to deserialize message")?;

        let message = Message {
            role: stored.role,
            content: stored.content,
        };

        Ok((message, stored.metadata))
    }

    /// Store a message in Redis with optional metadata.
    ///
    /// # Arguments
    ///
    /// * `session_id` - Session identifier
    /// * `role` - Message role (user, assistant, system)
    /// * `content` - Message content
    /// * `metadata` - Optional metadata
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::memory::RedisMemory;
    /// # use std::collections::HashMap;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// # let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:memory").await?;
    /// let mut metadata = HashMap::new();
    /// metadata.insert("importance".to_string(), serde_json::json!(0.8));
    /// memory.store("session-123", "user", "Hello", Some(metadata)).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn store(
        &self,
        session_id: &str,
        role: &str,
        content: &str,
        metadata: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<()> {
        let mut conn = self.get_connection().await?;

        // Get timestamp
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .context("Failed to get timestamp")?
            .as_secs_f64();

        // Serialize
        let metadata = metadata.unwrap_or_default();
        let value = self.serialize_message(role, content, metadata)?;

        // Store in sorted set (score = timestamp)
        let key = self.session_key(session_id);
        conn.zadd::<_, _, _, ()>(&key, value, timestamp)
            .await
            .context("Failed to store message")?;

        // Set TTL if configured
        if self.ttl > 0 {
            conn.expire::<_, ()>(&key, self.ttl as i64)
                .await
                .context("Failed to set TTL")?;
        }

        Ok(())
    }

    /// Retrieve messages from Redis with filtering.
    ///
    /// # Arguments
    ///
    /// * `session_id` - Session identifier
    /// * `limit` - Maximum messages to return (default: 10)
    /// * `time_range` - Optional (start, end) time range in seconds
    /// * `importance_threshold` - Optional minimum importance score
    /// * `tags` - Optional list of tags to filter by
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::memory::RedisMemory;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// # let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:memory").await?;
    /// // Get recent messages
    /// let messages = memory.retrieve("session-123", 10, None, None, None).await?;
    ///
    /// // Filter by importance
    /// let important = memory.retrieve("session-123", 10, None, Some(0.7), None).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn retrieve(
        &self,
        session_id: &str,
        limit: usize,
        time_range: Option<(f64, f64)>,
        importance_threshold: Option<f64>,
        tags: Option<Vec<String>>,
    ) -> Result<Vec<Message>> {
        let mut conn = self.get_connection().await?;
        let key = self.session_key(session_id);

        // Get all messages with scores (most recent first)
        let values: Vec<(String, f64)> = conn
            .zrevrange_withscores(&key, 0, -1)
            .await
            .context("Failed to retrieve messages")?;

        if values.is_empty() {
            return Ok(Vec::new());
        }

        // Deserialize and filter
        let mut filtered = Vec::new();

        for (data, timestamp) in values {
            // Deserialize
            let (message, metadata) = match self.deserialize_message(&data) {
                Ok(result) => result,
                Err(_) => continue, // Skip malformed messages
            };

            // Time range filter
            if let Some((start, end)) = time_range {
                if timestamp < start || timestamp > end {
                    continue;
                }
            }

            // Importance threshold filter
            if let Some(threshold) = importance_threshold {
                let importance = metadata
                    .get("importance")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0);

                if importance < threshold {
                    continue;
                }
            }

            // Tags filter (any match)
            if let Some(ref required_tags) = tags {
                let message_tags = metadata
                    .get("tags")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(|s| s.to_string()))
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();

                let has_tag = required_tags.iter().any(|tag| message_tags.contains(tag));

                if !has_tag {
                    continue;
                }
            }

            filtered.push(message);

            if filtered.len() >= limit {
                break;
            }
        }

        Ok(filtered)
    }

    /// Create a summary of conversation history.
    ///
    /// Simple implementation: Returns a message with concatenated content.
    /// Production use should use LLM-based summarization.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::memory::RedisMemory;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// # let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:memory").await?;
    /// let summary = memory.summarize("session-123").await?;
    /// println!("{}", summary.content);
    /// # Ok(())
    /// # }
    /// ```
    pub async fn summarize(&self, session_id: &str) -> Result<Message> {
        let messages = self.retrieve(session_id, 100, None, None, None).await?;

        if messages.is_empty() {
            return Ok(Message {
                role: "system".to_string(),
                content: "No messages in session.".to_string(),
            });
        }

        // Simple concatenation summary
        let max_messages = std::cmp::min(messages.len(), 10);
        let mut summary_parts = Vec::new();

        for (i, msg) in messages.iter().take(max_messages).enumerate() {
            let preview = if msg.content.len() > 100 {
                format!("{}...", &msg.content[..100])
            } else {
                msg.content.clone()
            };
            summary_parts.push(format!("{}. [{}] {}", i + 1, msg.role, preview));
        }

        let summary_content = format!(
            "Session summary ({} messages):\n{}",
            messages.len(),
            summary_parts.join("\n")
        );

        Ok(Message {
            role: "system".to_string(),
            content: summary_content,
        })
    }

    /// Clear all memory for a session.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::memory::RedisMemory;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// # let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:memory").await?;
    /// memory.clear("session-123").await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn clear(&self, session_id: &str) -> Result<()> {
        let mut conn = self.get_connection().await?;
        let key = self.session_key(session_id);
        conn.del::<_, ()>(&key)
            .await
            .context("Failed to clear session")?;
        Ok(())
    }

    /// Get the number of messages stored for a session.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::memory::RedisMemory;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// # let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:memory").await?;
    /// let count = memory.get_session_count("session-123").await?;
    /// println!("Session has {} messages", count);
    /// # Ok(())
    /// # }
    /// ```
    pub async fn get_session_count(&self, session_id: &str) -> Result<usize> {
        let mut conn = self.get_connection().await?;
        let key = self.session_key(session_id);
        let count: usize = conn
            .zcard(&key)
            .await
            .context("Failed to get session count")?;
        Ok(count)
    }

    /// Get all session IDs.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::memory::RedisMemory;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// # let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:memory").await?;
    /// let sessions = memory.get_all_sessions().await?;
    /// for session in sessions {
    ///     println!("Session: {}", session);
    /// }
    /// # Ok(())
    /// # }
    /// ```
    pub async fn get_all_sessions(&self) -> Result<Vec<String>> {
        let mut conn = self.get_connection().await?;
        let pattern = format!("{}:*:messages", self.key_prefix);

        let keys: Vec<String> = conn
            .keys(&pattern)
            .await
            .context("Failed to scan sessions")?;

        let sessions: Vec<String> = keys
            .into_iter()
            .filter_map(|key| {
                // Extract session_id from key
                // Format: "agenkit:memory:{session_id}:messages"
                let parts: Vec<&str> = key.split(':').collect();
                if parts.len() >= 3 {
                    Some(parts[parts.len() - 2].to_string())
                } else {
                    None
                }
            })
            .collect();

        Ok(sessions)
    }

    /// Get memory usage statistics.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::memory::RedisMemory;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// # let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:memory").await?;
    /// let usage = memory.get_memory_usage().await?;
    /// println!("Sessions: {}, Messages: {}", usage.0, usage.1);
    /// # Ok(())
    /// # }
    /// ```
    pub async fn get_memory_usage(&self) -> Result<(usize, usize, u64)> {
        let sessions = self.get_all_sessions().await?;
        let mut total_messages = 0;

        for session_id in &sessions {
            if let Ok(count) = self.get_session_count(session_id).await {
                total_messages += count;
            }
        }

        Ok((sessions.len(), total_messages, self.ttl))
    }

    /// Get memory capabilities.
    pub fn capabilities(&self) -> Vec<&'static str> {
        vec![
            "basic_retrieval",
            "persistence",
            "ttl",
            "time_filtering",
            "importance_filtering",
            "tag_filtering",
        ]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    #[ignore] // Requires Redis server
    async fn test_basic_store_and_retrieve() {
        let memory = RedisMemory::new("redis://localhost:6379", 3600, "agenkit:test:memory")
            .await
            .unwrap();

        let session_id = "test-session-1";

        // Store message
        memory
            .store(session_id, "user", "Hello", None)
            .await
            .unwrap();

        // Retrieve
        let messages = memory
            .retrieve(session_id, 10, None, None, None)
            .await
            .unwrap();

        assert_eq!(messages.len(), 1);
        assert_eq!(messages[0].content, "Hello");
        assert_eq!(messages[0].role, "user");

        // Cleanup
        memory.clear(session_id).await.unwrap();
    }

    #[tokio::test]
    #[ignore] // Requires Redis server
    async fn test_capabilities() {
        let memory = RedisMemory::new("redis://localhost:6379", 3600, "agenkit:test:memory")
            .await
            .unwrap();

        let capabilities = memory.capabilities();
        assert!(capabilities.contains(&"basic_retrieval"));
        assert!(capabilities.contains(&"persistence"));
        assert!(capabilities.contains(&"ttl"));
    }
}
