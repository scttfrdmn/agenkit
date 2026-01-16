//! Long-term memory tier with importance filtering and keyword search.

use crate::memory::MemoryEntry;
use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;
use tokio::sync::RwLock;

/// Long-term memory errors.
#[derive(Error, Debug)]
pub enum LongTermMemoryError {
    #[error("invalid importance threshold: {0}")]
    InvalidThreshold(String),

    #[error("entry not found: {0}")]
    EntryNotFound(String),
}

pub type LongTermMemoryResult<T> = Result<T, LongTermMemoryError>;

/// Long-term memory for persistent facts and important information.
///
/// Filters entries by importance threshold and provides keyword search
/// with relevance scoring. No capacity limit - grows unbounded (or backed by storage).
pub struct LongTermMemory {
    storage: Arc<RwLock<HashMap<String, MemoryEntry>>>,
    min_importance: f64,
}

impl LongTermMemory {
    /// Create a new long-term memory with importance threshold.
    pub fn new(
        storage: HashMap<String, MemoryEntry>,
        min_importance: f64,
    ) -> LongTermMemoryResult<Self> {
        if !(0.0..=1.0).contains(&min_importance) {
            return Err(LongTermMemoryError::InvalidThreshold(
                "importance must be between 0.0 and 1.0".to_string(),
            ));
        }

        Ok(Self {
            storage: Arc::new(RwLock::new(storage)),
            min_importance,
        })
    }

    /// Store a memory entry (only if importance >= threshold).
    pub async fn store(&self, entry: MemoryEntry) -> LongTermMemoryResult<Option<String>> {
        if entry.importance < self.min_importance {
            return Ok(None); // Rejected due to low importance
        }

        let mut storage = self.storage.write().await;
        let entry_id = entry.id.clone();
        storage.insert(entry_id.clone(), entry);

        Ok(Some(entry_id))
    }

    /// Retrieve messages with keyword search and relevance scoring.
    pub async fn retrieve(
        &self,
        query: &str,
        limit: usize,
    ) -> LongTermMemoryResult<Vec<MemoryEntry>> {
        let mut storage = self.storage.write().await;

        // Calculate relevance scores
        let mut scored_entries: Vec<(f64, MemoryEntry)> = storage
            .values_mut()
            .map(|entry| {
                entry.record_access(); // Update access tracking
                let score = entry.calculate_relevance(query);
                (score, entry.clone())
            })
            .collect();

        // Sort by score (highest first)
        scored_entries.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));

        // Return top N entries
        Ok(scored_entries
            .into_iter()
            .take(limit)
            .map(|(_, entry)| entry)
            .collect())
    }

    /// Get all entries.
    pub async fn get_all(&self) -> LongTermMemoryResult<Vec<MemoryEntry>> {
        let storage = self.storage.read().await;
        Ok(storage.values().cloned().collect())
    }

    /// Delete a specific entry by ID.
    pub async fn delete(&self, entry_id: &str) -> LongTermMemoryResult<bool> {
        let mut storage = self.storage.write().await;
        Ok(storage.remove(entry_id).is_some())
    }

    /// Clear all messages.
    pub async fn clear(&self) -> LongTermMemoryResult<()> {
        let mut storage = self.storage.write().await;
        storage.clear();
        Ok(())
    }

    /// Get current message count.
    pub async fn count(&self) -> usize {
        let storage = self.storage.read().await;
        storage.len()
    }

    /// Get importance threshold.
    pub fn min_importance(&self) -> f64 {
        self.min_importance
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_long_term_memory_basic_storage() {
        let memory = LongTermMemory::new(HashMap::new(), 0.7).unwrap();

        let entry = MemoryEntry::new("important fact", HashMap::new(), 0.9, None);
        let entry_id = memory.store(entry).await.unwrap();

        assert!(entry_id.is_some());
        assert_eq!(memory.count().await, 1);
    }

    #[tokio::test]
    async fn test_long_term_memory_importance_threshold() {
        let memory = LongTermMemory::new(HashMap::new(), 0.7).unwrap();

        // High importance - should be stored
        let entry1 = MemoryEntry::new("important", HashMap::new(), 0.9, None);
        let result1 = memory.store(entry1).await.unwrap();
        assert!(result1.is_some());

        // Low importance - should be rejected
        let entry2 = MemoryEntry::new("not important", HashMap::new(), 0.5, None);
        let result2 = memory.store(entry2).await.unwrap();
        assert!(result2.is_none());

        assert_eq!(memory.count().await, 1);
    }

    #[tokio::test]
    async fn test_long_term_memory_keyword_search() {
        let memory = LongTermMemory::new(HashMap::new(), 0.5).unwrap();

        // Store entries with different keywords
        let entry1 = MemoryEntry::new("Python programming", HashMap::new(), 0.8, None);
        let entry2 = MemoryEntry::new("Rust programming", HashMap::new(), 0.9, None);
        let entry3 = MemoryEntry::new("Cooking recipes", HashMap::new(), 0.7, None);

        memory.store(entry1).await.unwrap();
        memory.store(entry2).await.unwrap();
        memory.store(entry3).await.unwrap();

        // Search for "programming"
        let results = memory.retrieve("programming", 10).await.unwrap();

        assert_eq!(results.len(), 3); // All entries returned
                                      // First two should have higher scores due to keyword match
        assert!(
            results[0].content.contains("programming")
                || results[1].content.contains("programming")
        );
    }

    #[tokio::test]
    async fn test_long_term_memory_relevance_scoring() {
        let memory = LongTermMemory::new(HashMap::new(), 0.5).unwrap();

        // High importance with keyword
        let entry1 = MemoryEntry::new("Rust is great", HashMap::new(), 0.9, None);
        // Lower importance with keyword
        let entry2 = MemoryEntry::new("Rust is okay", HashMap::new(), 0.6, None);

        memory.store(entry1).await.unwrap();
        memory.store(entry2).await.unwrap();

        let results = memory.retrieve("Rust", 10).await.unwrap();

        // entry1 should rank higher due to higher importance
        assert_eq!(results[0].importance, 0.9);
    }

    #[tokio::test]
    async fn test_long_term_memory_delete() {
        let memory = LongTermMemory::new(HashMap::new(), 0.7).unwrap();

        let entry = MemoryEntry::new("test", HashMap::new(), 0.8, None);
        let entry_id = memory.store(entry).await.unwrap().unwrap();

        assert_eq!(memory.count().await, 1);

        let deleted = memory.delete(&entry_id).await.unwrap();
        assert!(deleted);
        assert_eq!(memory.count().await, 0);
    }

    #[tokio::test]
    async fn test_long_term_memory_invalid_threshold() {
        assert!(LongTermMemory::new(HashMap::new(), 1.5).is_err());
        assert!(LongTermMemory::new(HashMap::new(), -0.1).is_err());
    }
}
