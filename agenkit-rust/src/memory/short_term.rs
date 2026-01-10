//! Short-term memory tier with TTL and LRU eviction.

use crate::memory::MemoryEntry;
use std::sync::Arc;
use thiserror::Error;
use tokio::sync::RwLock;

/// Short-term memory errors.
#[derive(Error, Debug)]
pub enum ShortTermMemoryError {
    #[error("invalid capacity: {0}")]
    InvalidCapacity(String),

    #[error("invalid TTL: {0}")]
    InvalidTTL(String),

    #[error("entry not found: {0}")]
    EntryNotFound(String),
}

pub type ShortTermMemoryResult<T> = Result<T, ShortTermMemoryError>;

/// Short-term memory for recent sessions.
///
/// Implements TTL-based expiration and LRU (Least Recently Used) eviction
/// when over capacity. Entries are automatically cleaned up based on age.
pub struct ShortTermMemory {
    max_messages: usize,
    ttl_seconds: i64,
    messages: Arc<RwLock<Vec<MemoryEntry>>>,
}

impl ShortTermMemory {
    /// Create a new short-term memory with capacity and TTL.
    pub fn new(max_messages: usize, ttl_seconds: i64) -> ShortTermMemoryResult<Self> {
        if max_messages == 0 {
            return Err(ShortTermMemoryError::InvalidCapacity(
                "capacity must be greater than 0".to_string(),
            ));
        }

        if ttl_seconds <= 0 {
            return Err(ShortTermMemoryError::InvalidTTL(
                "TTL must be greater than 0".to_string(),
            ));
        }

        Ok(Self {
            max_messages,
            ttl_seconds,
            messages: Arc::new(RwLock::new(Vec::new())),
        })
    }

    /// Clean expired entries.
    async fn clean_expired(&self, messages: &mut Vec<MemoryEntry>) {
        messages.retain(|entry| !entry.is_expired(self.ttl_seconds));
    }

    /// Evict least recently used entries if over capacity.
    async fn evict_lru(&self, messages: &mut Vec<MemoryEntry>) {
        if messages.len() <= self.max_messages {
            return;
        }

        // Sort by last_accessed (oldest first)
        messages.sort_by(|a, b| {
            match (a.last_accessed, b.last_accessed) {
                (Some(a_time), Some(b_time)) => a_time.cmp(&b_time),
                (None, Some(_)) => std::cmp::Ordering::Less, // Never accessed = oldest
                (Some(_), None) => std::cmp::Ordering::Greater,
                (None, None) => a.timestamp.cmp(&b.timestamp), // Fallback to creation time
            }
        });

        // Remove oldest entries
        let to_remove = messages.len() - self.max_messages;
        messages.drain(0..to_remove);
    }

    /// Store a memory entry (with TTL cleanup and LRU eviction).
    pub async fn store(&self, entry: MemoryEntry) -> ShortTermMemoryResult<String> {
        let mut messages = self.messages.write().await;

        // Clean expired entries
        self.clean_expired(&mut messages).await;

        // Add new entry
        let entry_id = entry.id.clone();
        messages.push(entry);

        // Evict LRU if over capacity
        self.evict_lru(&mut messages).await;

        Ok(entry_id)
    }

    /// Retrieve recent, non-expired messages.
    pub async fn retrieve(&self, limit: usize) -> ShortTermMemoryResult<Vec<MemoryEntry>> {
        let mut messages = self.messages.write().await;

        // Clean expired entries
        self.clean_expired(&mut messages).await;

        // Update access tracking
        for msg in messages.iter_mut() {
            msg.record_access();
        }

        // Sort by timestamp (most recent first)
        messages.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));

        // Return top N
        Ok(messages.iter().take(limit).cloned().collect())
    }

    /// Get all non-expired messages.
    pub async fn get_all(&self) -> ShortTermMemoryResult<Vec<MemoryEntry>> {
        let mut messages = self.messages.write().await;

        // Clean expired entries
        self.clean_expired(&mut messages).await;

        Ok(messages.clone())
    }

    /// Delete a specific entry by ID.
    pub async fn delete(&self, entry_id: &str) -> ShortTermMemoryResult<bool> {
        let mut messages = self.messages.write().await;
        let before = messages.len();
        messages.retain(|msg| msg.id != entry_id);
        Ok(messages.len() < before)
    }

    /// Clear all messages.
    pub async fn clear(&self) -> ShortTermMemoryResult<()> {
        let mut messages = self.messages.write().await;
        messages.clear();
        Ok(())
    }

    /// Get current message count (excluding expired).
    pub async fn count(&self) -> usize {
        let mut messages = self.messages.write().await;
        self.clean_expired(&mut messages).await;
        messages.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use tokio::time::{sleep, Duration};

    #[tokio::test]
    async fn test_short_term_memory_basic_storage() {
        let memory = ShortTermMemory::new(10, 3600).unwrap();

        let entry = MemoryEntry::new("test message", HashMap::new(), 0.5, None);
        let entry_id = memory.store(entry).await.unwrap();

        assert!(!entry_id.is_empty());
        assert_eq!(memory.count().await, 1);
    }

    #[tokio::test]
    async fn test_short_term_memory_ttl_expiration() {
        let memory = ShortTermMemory::new(10, 1).unwrap(); // 1 second TTL

        let entry = MemoryEntry::new("test message", HashMap::new(), 0.5, None);
        memory.store(entry).await.unwrap();

        assert_eq!(memory.count().await, 1);

        // Wait for TTL to expire
        sleep(Duration::from_secs(2)).await;

        // Should be cleaned up
        assert_eq!(memory.count().await, 0);
    }

    #[tokio::test]
    async fn test_short_term_memory_lru_eviction() {
        let memory = ShortTermMemory::new(3, 3600).unwrap();

        // Store 3 messages
        for i in 0..3 {
            let entry = MemoryEntry::new(format!("message {}", i), HashMap::new(), 0.5, None);
            memory.store(entry).await.unwrap();
        }

        // Access first two messages (making them recently used)
        {
            let mut messages = memory.messages.write().await;
            messages[0].record_access();
            messages[1].record_access();
        }

        // Add 4th message (should evict message 2 which hasn't been accessed)
        let entry = MemoryEntry::new("message 3", HashMap::new(), 0.5, None);
        memory.store(entry).await.unwrap();

        assert_eq!(memory.count().await, 3);

        let messages = memory.get_all().await.unwrap();
        // Should have messages 0, 1, and 3 (2 was evicted)
        let contents: Vec<String> = messages.iter().map(|m| m.content.clone()).collect();
        assert!(contents.contains(&"message 0".to_string()));
        assert!(contents.contains(&"message 1".to_string()));
        assert!(contents.contains(&"message 3".to_string()));
    }

    #[tokio::test]
    async fn test_short_term_memory_delete() {
        let memory = ShortTermMemory::new(10, 3600).unwrap();

        let entry = MemoryEntry::new("test", HashMap::new(), 0.5, None);
        let entry_id = memory.store(entry).await.unwrap();

        assert_eq!(memory.count().await, 1);

        let deleted = memory.delete(&entry_id).await.unwrap();
        assert!(deleted);
        assert_eq!(memory.count().await, 0);
    }

    #[tokio::test]
    async fn test_short_term_memory_invalid_params() {
        assert!(ShortTermMemory::new(0, 3600).is_err());
        assert!(ShortTermMemory::new(10, 0).is_err());
        assert!(ShortTermMemory::new(10, -1).is_err());
    }
}
