//! Memory entry data structure.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// A single memory entry with metadata and tracking information.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    /// Unique entry identifier
    pub id: String,

    /// Text content of the memory
    pub content: String,

    /// Structured metadata (importance, tags, etc.)
    pub metadata: HashMap<String, serde_json::Value>,

    /// When this entry was created
    pub timestamp: DateTime<Utc>,

    /// Number of times this entry was accessed
    pub access_count: usize,

    /// Last time this entry was accessed (for LRU)
    pub last_accessed: Option<DateTime<Utc>>,

    /// Importance score (0.0-1.0)
    pub importance: f64,

    /// Session identifier
    pub session_id: Option<String>,
}

impl MemoryEntry {
    /// Create a new memory entry.
    pub fn new(
        content: impl Into<String>,
        metadata: HashMap<String, serde_json::Value>,
        importance: f64,
        session_id: Option<String>,
    ) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            content: content.into(),
            metadata,
            timestamp: Utc::now(),
            access_count: 0,
            last_accessed: None,
            importance: importance.max(0.0).min(1.0), // Clamp to 0.0-1.0
            session_id,
        }
    }

    /// Update access tracking.
    pub fn record_access(&mut self) {
        self.access_count += 1;
        self.last_accessed = Some(Utc::now());
    }

    /// Check if entry has expired based on TTL.
    pub fn is_expired(&self, ttl_seconds: i64) -> bool {
        let now = Utc::now();
        let age = now.signed_duration_since(self.timestamp);
        age.num_seconds() > ttl_seconds
    }

    /// Calculate relevance score for keyword search.
    pub fn calculate_relevance(&self, query: &str) -> f64 {
        let mut score: f64 = 0.0;

        // Keyword matching (0.0-0.5)
        if !query.is_empty() && self.content.to_lowercase().contains(&query.to_lowercase()) {
            score += 0.5;
        }

        // Importance (0.0-0.3)
        score += self.importance * 0.3;

        // Recency (0.0-0.2)
        let now = Utc::now();
        let age_days = now.signed_duration_since(self.timestamp).num_days() as f64;
        let recency = (1.0 - (age_days / 365.0)).max(0.0);
        score += recency * 0.2;

        score
    }

    /// Get age in seconds.
    pub fn age_seconds(&self) -> i64 {
        Utc::now()
            .signed_duration_since(self.timestamp)
            .num_seconds()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_entry_creation() {
        let entry = MemoryEntry::new(
            "test content",
            HashMap::new(),
            0.8,
            Some("session-1".to_string()),
        );

        assert!(!entry.id.is_empty());
        assert_eq!(entry.content, "test content");
        assert_eq!(entry.importance, 0.8);
        assert_eq!(entry.access_count, 0);
        assert!(entry.last_accessed.is_none());
        assert_eq!(entry.session_id, Some("session-1".to_string()));
    }

    #[test]
    fn test_importance_clamping() {
        let entry1 = MemoryEntry::new("test", HashMap::new(), 1.5, None);
        assert_eq!(entry1.importance, 1.0);

        let entry2 = MemoryEntry::new("test", HashMap::new(), -0.5, None);
        assert_eq!(entry2.importance, 0.0);
    }

    #[test]
    fn test_access_tracking() {
        let mut entry = MemoryEntry::new("test", HashMap::new(), 0.5, None);

        assert_eq!(entry.access_count, 0);
        assert!(entry.last_accessed.is_none());

        entry.record_access();

        assert_eq!(entry.access_count, 1);
        assert!(entry.last_accessed.is_some());

        entry.record_access();

        assert_eq!(entry.access_count, 2);
    }

    #[test]
    fn test_relevance_calculation() {
        let entry = MemoryEntry::new("hello world", HashMap::new(), 0.9, None);

        let score1 = entry.calculate_relevance("hello");
        assert!(score1 > 0.5); // Has keyword match + importance

        let score2 = entry.calculate_relevance("goodbye");
        assert!(score2 < 0.5); // No keyword match
    }
}
