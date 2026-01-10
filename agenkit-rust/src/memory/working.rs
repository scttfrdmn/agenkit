//! Working memory tier (current conversation context).

use crate::memory::MemoryEntry;
use std::sync::Arc;
use thiserror::Error;
use tokio::sync::RwLock;

/// Working memory errors.
#[derive(Error, Debug)]
pub enum WorkingMemoryError {
    #[error("invalid capacity: {0}")]
    InvalidCapacity(String),

    #[error("entry not found: {0}")]
    EntryNotFound(String),
}

pub type WorkingMemoryResult<T> = Result<T, WorkingMemoryError>;

/// Working memory for current conversation context.
///
/// Implements FIFO (First-In-First-Out) eviction when over capacity.
/// All messages are kept in-memory with fast O(1) append operations.
pub struct WorkingMemory {
    max_messages: usize,
    messages: Arc<RwLock<Vec<MemoryEntry>>>,
}

impl WorkingMemory {
    /// Create a new working memory with specified capacity.
    pub fn new(max_messages: usize) -> WorkingMemoryResult<Self> {
        if max_messages == 0 {
            return Err(WorkingMemoryError::InvalidCapacity(
                "capacity must be greater than 0".to_string(),
            ));
        }

        Ok(Self {
            max_messages,
            messages: Arc::new(RwLock::new(Vec::new())),
        })
    }

    /// Store a memory entry (FIFO eviction if over capacity).
    pub async fn store(&self, mut entry: MemoryEntry) -> WorkingMemoryResult<String> {
        let mut messages = self.messages.write().await;

        // FIFO eviction: remove oldest if at capacity
        if messages.len() >= self.max_messages {
            messages.remove(0);
        }

        let entry_id = entry.id.clone();
        messages.push(entry);

        Ok(entry_id)
    }

    /// Retrieve messages (most recent first).
    pub async fn retrieve(&self, limit: usize) -> WorkingMemoryResult<Vec<MemoryEntry>> {
        let mut messages = self.messages.write().await;

        // Update access tracking
        for msg in messages.iter_mut() {
            msg.record_access();
        }

        // Return most recent first
        let mut result: Vec<MemoryEntry> = messages.iter().rev().take(limit).cloned().collect();
        result.reverse(); // Maintain chronological order
        Ok(result)
    }

    /// Get all messages.
    pub async fn get_all(&self) -> WorkingMemoryResult<Vec<MemoryEntry>> {
        let messages = self.messages.read().await;
        Ok(messages.clone())
    }

    /// Delete a specific entry by ID.
    pub async fn delete(&self, entry_id: &str) -> WorkingMemoryResult<bool> {
        let mut messages = self.messages.write().await;
        let before = messages.len();
        messages.retain(|msg| msg.id != entry_id);
        Ok(messages.len() < before)
    }

    /// Clear all messages.
    pub async fn clear(&self) -> WorkingMemoryResult<()> {
        let mut messages = self.messages.write().await;
        messages.clear();
        Ok(())
    }

    /// Get current message count.
    pub async fn count(&self) -> usize {
        let messages = self.messages.read().await;
        messages.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[tokio::test]
    async fn test_working_memory_basic_storage() {
        let memory = WorkingMemory::new(5).unwrap();

        let entry = MemoryEntry::new("test message", HashMap::new(), 0.5, None);
        let entry_id = memory.store(entry).await.unwrap();

        assert!(!entry_id.is_empty());
        assert_eq!(memory.count().await, 1);
    }

    #[tokio::test]
    async fn test_working_memory_fifo_eviction() {
        let memory = WorkingMemory::new(3).unwrap();

        // Store 4 messages
        for i in 0..4 {
            let entry = MemoryEntry::new(format!("message {}", i), HashMap::new(), 0.5, None);
            memory.store(entry).await.unwrap();
        }

        // Should only have 3 messages (oldest evicted)
        assert_eq!(memory.count().await, 3);

        let messages = memory.get_all().await.unwrap();
        // First message should be "message 1" (0 was evicted)
        assert!(messages[0].content.contains("message 1"));
    }

    #[tokio::test]
    async fn test_working_memory_retrieve() {
        let memory = WorkingMemory::new(5).unwrap();

        for i in 0..3 {
            let entry = MemoryEntry::new(format!("message {}", i), HashMap::new(), 0.5, None);
            memory.store(entry).await.unwrap();
        }

        let messages = memory.retrieve(2).await.unwrap();
        assert_eq!(messages.len(), 2);
    }

    #[tokio::test]
    async fn test_working_memory_delete() {
        let memory = WorkingMemory::new(5).unwrap();

        let entry = MemoryEntry::new("test", HashMap::new(), 0.5, None);
        let entry_id = memory.store(entry).await.unwrap();

        assert_eq!(memory.count().await, 1);

        let deleted = memory.delete(&entry_id).await.unwrap();
        assert!(deleted);
        assert_eq!(memory.count().await, 0);
    }

    #[tokio::test]
    async fn test_working_memory_clear() {
        let memory = WorkingMemory::new(5).unwrap();

        for i in 0..3 {
            let entry = MemoryEntry::new(format!("message {}", i), HashMap::new(), 0.5, None);
            memory.store(entry).await.unwrap();
        }

        assert_eq!(memory.count().await, 3);

        memory.clear().await.unwrap();
        assert_eq!(memory.count().await, 0);
    }

    #[tokio::test]
    async fn test_working_memory_invalid_capacity() {
        let result = WorkingMemory::new(0);
        assert!(result.is_err());
    }
}
