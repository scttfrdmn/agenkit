//! Memory hierarchy orchestration across three tiers.

use crate::memory::{LongTermMemory, MemoryEntry, ShortTermMemory, WorkingMemory};
use std::collections::{HashMap, HashSet};
use thiserror::Error;

/// Memory hierarchy errors.
#[derive(Error, Debug)]
pub enum HierarchyError {
    #[error("working memory error: {0}")]
    WorkingMemoryError(String),

    #[error("short-term memory error: {0}")]
    ShortTermMemoryError(String),

    #[error("long-term memory error: {0}")]
    LongTermMemoryError(String),

    #[error("invalid tier: {0}")]
    InvalidTier(String),
}

pub type HierarchyResult<T> = Result<T, HierarchyError>;

/// Three-tier memory hierarchy orchestrator.
///
/// Automatically routes messages to appropriate tiers based on importance
/// and provides unified retrieval with deduplication and ranking.
pub struct MemoryHierarchy {
    working: WorkingMemory,
    short_term: Option<ShortTermMemory>,
    long_term: Option<LongTermMemory>,
}

impl MemoryHierarchy {
    /// Create a new memory hierarchy with specified tiers.
    pub fn new(
        working: WorkingMemory,
        short_term: Option<ShortTermMemory>,
        long_term: Option<LongTermMemory>,
    ) -> Self {
        Self {
            working,
            short_term,
            long_term,
        }
    }

    /// Store a message in appropriate tiers based on importance.
    ///
    /// # Routing Logic
    /// - Always stored in working memory
    /// - Stored in short-term if available
    /// - Stored in long-term if importance >= threshold
    pub async fn store(
        &mut self,
        content: impl Into<String>,
        metadata: HashMap<String, serde_json::Value>,
        importance: f64,
        session_id: Option<String>,
    ) -> HierarchyResult<String> {
        let entry = MemoryEntry::new(content, metadata, importance, session_id);
        let entry_id = entry.id.clone();

        // Store in working memory (always)
        self.working
            .store(entry.clone())
            .await
            .map_err(|e| HierarchyError::WorkingMemoryError(e.to_string()))?;

        // Store in short-term memory (if available)
        if let Some(ref short_term) = self.short_term {
            short_term
                .store(entry.clone())
                .await
                .map_err(|e| HierarchyError::ShortTermMemoryError(e.to_string()))?;
        }

        // Store in long-term memory (if available and importance >= threshold)
        if let Some(ref long_term) = self.long_term {
            long_term
                .store(entry)
                .await
                .map_err(|e| HierarchyError::LongTermMemoryError(e.to_string()))?;
        }

        Ok(entry_id)
    }

    /// Retrieve messages from specified tiers with deduplication and ranking.
    ///
    /// # Parameters
    /// - `query`: Keyword search query (empty for all)
    /// - `limit`: Maximum number of results
    /// - `search_tiers`: Specific tiers to search (None = all)
    ///
    /// # Returns
    /// Deduplicated, ranked results ordered by importance then recency
    pub async fn retrieve(
        &self,
        query: &str,
        limit: usize,
        search_tiers: Option<Vec<String>>,
    ) -> HierarchyResult<Vec<MemoryEntry>> {
        let mut all_entries = Vec::new();
        let mut seen_ids = HashSet::new();

        let search_all = search_tiers.is_none();
        let tiers = search_tiers.unwrap_or_else(|| vec![
            "working".to_string(),
            "short_term".to_string(),
            "long_term".to_string(),
        ]);

        // Query working memory
        if search_all || tiers.contains(&"working".to_string()) {
            let working_results = self
                .working
                .retrieve(limit)
                .await
                .map_err(|e| HierarchyError::WorkingMemoryError(e.to_string()))?;

            for entry in working_results {
                if seen_ids.insert(entry.id.clone()) {
                    all_entries.push(entry);
                }
            }
        }

        // Query short-term memory
        if (search_all || tiers.contains(&"short_term".to_string())) && self.short_term.is_some() {
            let short_term_results = self
                .short_term
                .as_ref()
                .unwrap()
                .retrieve(limit)
                .await
                .map_err(|e| HierarchyError::ShortTermMemoryError(e.to_string()))?;

            for entry in short_term_results {
                if seen_ids.insert(entry.id.clone()) {
                    all_entries.push(entry);
                }
            }
        }

        // Query long-term memory
        if (search_all || tiers.contains(&"long_term".to_string())) && self.long_term.is_some() {
            let long_term_results = self
                .long_term
                .as_ref()
                .unwrap()
                .retrieve(query, limit)
                .await
                .map_err(|e| HierarchyError::LongTermMemoryError(e.to_string()))?;

            for entry in long_term_results {
                if seen_ids.insert(entry.id.clone()) {
                    all_entries.push(entry);
                }
            }
        }

        // Rank by importance (descending), then timestamp (descending)
        all_entries.sort_by(|a, b| {
            match b.importance.partial_cmp(&a.importance) {
                Some(std::cmp::Ordering::Equal) | None => b.timestamp.cmp(&a.timestamp),
                Some(ordering) => ordering,
            }
        });

        // Return top N
        Ok(all_entries.into_iter().take(limit).collect())
    }

    /// Delete an entry from all tiers.
    pub async fn delete(&mut self, entry_id: &str) -> HierarchyResult<bool> {
        let mut deleted = false;

        // Delete from working memory
        deleted |= self
            .working
            .delete(entry_id)
            .await
            .map_err(|e| HierarchyError::WorkingMemoryError(e.to_string()))?;

        // Delete from short-term memory
        if let Some(ref short_term) = self.short_term {
            deleted |= short_term
                .delete(entry_id)
                .await
                .map_err(|e| HierarchyError::ShortTermMemoryError(e.to_string()))?;
        }

        // Delete from long-term memory
        if let Some(ref long_term) = self.long_term {
            deleted |= long_term
                .delete(entry_id)
                .await
                .map_err(|e| HierarchyError::LongTermMemoryError(e.to_string()))?;
        }

        Ok(deleted)
    }

    /// Clear working memory only.
    pub async fn clear_working(&mut self) -> HierarchyResult<()> {
        self.working
            .clear()
            .await
            .map_err(|e| HierarchyError::WorkingMemoryError(e.to_string()))
    }

    /// Clear all tiers.
    pub async fn clear_all(&mut self) -> HierarchyResult<()> {
        self.working
            .clear()
            .await
            .map_err(|e| HierarchyError::WorkingMemoryError(e.to_string()))?;

        if let Some(ref short_term) = self.short_term {
            short_term
                .clear()
                .await
                .map_err(|e| HierarchyError::ShortTermMemoryError(e.to_string()))?;
        }

        if let Some(ref long_term) = self.long_term {
            long_term
                .clear()
                .await
                .map_err(|e| HierarchyError::LongTermMemoryError(e.to_string()))?;
        }

        Ok(())
    }

    /// Get statistics for all tiers.
    pub async fn get_stats(&self) -> HashMap<String, usize> {
        let mut stats = HashMap::new();

        stats.insert("working_count".to_string(), self.working.count().await);

        if let Some(ref short_term) = self.short_term {
            stats.insert("short_term_count".to_string(), short_term.count().await);
        }

        if let Some(ref long_term) = self.long_term {
            stats.insert("long_term_count".to_string(), long_term.count().await);
        }

        stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_memory_hierarchy_store_routing() {
        let working = WorkingMemory::new(10).unwrap();
        let short_term = Some(ShortTermMemory::new(100, 3600).unwrap());
        let long_term = Some(LongTermMemory::new(HashMap::new(), 0.7).unwrap());

        let mut hierarchy = MemoryHierarchy::new(working, short_term, long_term);

        // Low importance - should go to working and short-term, but not long-term
        let _entry_id1 = hierarchy
            .store("low importance", HashMap::new(), 0.5, None)
            .await
            .unwrap();

        let stats = hierarchy.get_stats().await;
        assert_eq!(stats["working_count"], 1);
        assert_eq!(stats["short_term_count"], 1);
        assert_eq!(stats["long_term_count"], 0); // Below threshold

        // High importance - should go to all tiers
        let _entry_id2 = hierarchy
            .store("high importance", HashMap::new(), 0.9, None)
            .await
            .unwrap();

        let stats = hierarchy.get_stats().await;
        assert_eq!(stats["working_count"], 2);
        assert_eq!(stats["short_term_count"], 2);
        assert_eq!(stats["long_term_count"], 1); // Above threshold
    }

    #[tokio::test]
    async fn test_memory_hierarchy_deduplication() {
        let working = WorkingMemory::new(10).unwrap();
        let short_term = Some(ShortTermMemory::new(100, 3600).unwrap());

        let mut hierarchy = MemoryHierarchy::new(working, short_term, None);

        // Store messages (will be in both working and short-term)
        hierarchy
            .store("message 1", HashMap::new(), 0.8, None)
            .await
            .unwrap();

        // Retrieve should deduplicate
        let results = hierarchy.retrieve("", 10, None).await.unwrap();

        // Should have only 1 entry (deduplicated across tiers)
        assert_eq!(results.len(), 1);
    }

    #[tokio::test]
    async fn test_memory_hierarchy_ranking() {
        let working = WorkingMemory::new(10).unwrap();
        let mut hierarchy = MemoryHierarchy::new(working, None, None);

        // Store messages with different importance
        hierarchy
            .store("low", HashMap::new(), 0.3, None)
            .await
            .unwrap();
        hierarchy
            .store("high", HashMap::new(), 0.9, None)
            .await
            .unwrap();
        hierarchy
            .store("medium", HashMap::new(), 0.6, None)
            .await
            .unwrap();

        let results = hierarchy.retrieve("", 10, None).await.unwrap();

        // Should be ranked by importance (high, medium, low)
        assert_eq!(results[0].importance, 0.9);
        assert_eq!(results[1].importance, 0.6);
        assert_eq!(results[2].importance, 0.3);
    }

    #[tokio::test]
    async fn test_memory_hierarchy_delete() {
        let working = WorkingMemory::new(10).unwrap();
        let short_term = Some(ShortTermMemory::new(100, 3600).unwrap());
        let long_term = Some(LongTermMemory::new(HashMap::new(), 0.5).unwrap());

        let mut hierarchy = MemoryHierarchy::new(working, short_term, long_term);

        let entry_id = hierarchy
            .store("test", HashMap::new(), 0.8, None)
            .await
            .unwrap();

        let stats_before = hierarchy.get_stats().await;
        assert_eq!(stats_before["working_count"], 1);
        assert_eq!(stats_before["short_term_count"], 1);
        assert_eq!(stats_before["long_term_count"], 1);

        // Delete from all tiers
        let deleted = hierarchy.delete(&entry_id).await.unwrap();
        assert!(deleted);

        let stats_after = hierarchy.get_stats().await;
        assert_eq!(stats_after["working_count"], 0);
        assert_eq!(stats_after["short_term_count"], 0);
        assert_eq!(stats_after["long_term_count"], 0);
    }

    #[tokio::test]
    async fn test_memory_hierarchy_clear_working() {
        let working = WorkingMemory::new(10).unwrap();
        let mut hierarchy = MemoryHierarchy::new(working, None, None);

        hierarchy
            .store("test", HashMap::new(), 0.5, None)
            .await
            .unwrap();

        assert_eq!(hierarchy.get_stats().await["working_count"], 1);

        hierarchy.clear_working().await.unwrap();

        assert_eq!(hierarchy.get_stats().await["working_count"], 0);
    }

    #[tokio::test]
    async fn test_memory_hierarchy_minimal_setup() {
        let working = WorkingMemory::new(10).unwrap();
        let mut hierarchy = MemoryHierarchy::new(working, None, None);

        let entry_id = hierarchy
            .store("test", HashMap::new(), 0.5, None)
            .await
            .unwrap();

        assert!(!entry_id.is_empty());

        let results = hierarchy.retrieve("", 10, None).await.unwrap();
        assert_eq!(results.len(), 1);
    }
}
