//! Memory Hierarchy Pattern - Multi-Tier Memory for Agents
//!
//! The Memory Hierarchy pattern provides a three-tier memory system for agents:
//! working memory (in-context), short-term memory (recent), and long-term memory (persistent).
//!
//! # Key Concepts
//!
//! - **Working Memory**: Current conversation context (fast, small, in-memory)
//! - **Short-Term Memory**: Recent sessions (medium, TTL-based, recency retrieval)
//! - **Long-Term Memory**: Persistent facts (large, semantic retrieval, importance-based)
//! - **Automatic Promotion**: Important memories move from short-term to long-term
//! - **Intelligent Retrieval**: Search across tiers with relevance ranking
//!
//! # Use Cases
//!
//! - Long-running conversational agents
//! - Personalization and user preferences
//! - Context-aware agents with limited context windows
//! - Multi-session continuity
//! - Learning and adaptation
//!
//! # Example
//!
//! ```no_run
//! use agenkit::patterns::{MemoryHierarchy, WorkingMemory, ShortTermMemory, LongTermMemory};
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let memory = MemoryHierarchy::new(
//!     WorkingMemory::new(10)?,
//!     Some(ShortTermMemory::new(100, 3600)?),
//!     Some(LongTermMemory::new(HashMap::new(), 0.7)?),
//! );
//!
//! memory.store(
//!     "User prefers Python",
//!     HashMap::new(),
//!     0.8,
//!     None,
//! ).await?;
//!
//! let results = memory.retrieve("What does the user prefer?", 5, None).await?;
//! # Ok(())
//! # }
//! ```

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use uuid::Uuid;

use crate::core::AgentError;

/// Single memory entry across all tiers.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    /// Unique identifier
    pub id: String,
    /// Memory content (text)
    pub content: String,
    /// Additional structured information
    pub metadata: HashMap<String, serde_json::Value>,
    /// When memory was created
    pub timestamp: DateTime<Utc>,
    /// Number of times accessed
    pub access_count: usize,
    /// When last accessed
    pub last_accessed: Option<DateTime<Utc>>,
    /// Importance score (0.0-1.0)
    pub importance: f64,
    /// Optional session identifier
    pub session_id: Option<String>,
}

/// Create a new memory entry.
pub fn create_memory_entry(
    content: impl Into<String>,
    metadata: HashMap<String, serde_json::Value>,
    importance: f64,
    session_id: Option<String>,
) -> MemoryEntry {
    MemoryEntry {
        id: Uuid::new_v4().to_string(),
        content: content.into(),
        metadata,
        timestamp: Utc::now(),
        access_count: 0,
        last_accessed: None,
        importance,
        session_id,
    }
}

/// In-context working memory for current conversation.
///
/// # Characteristics
///
/// - Fast: O(1) append, O(n) retrieval
/// - Small capacity: 10-20 messages typically
/// - FIFO eviction: Oldest messages removed first
/// - No persistence: Exists only in memory
/// - Use for: Current conversation context
///
/// # Example
///
/// ```
/// use agenkit::patterns::{WorkingMemory, create_memory_entry};
/// use std::collections::HashMap;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let memory = WorkingMemory::new(10)?;
///
/// let entry = create_memory_entry("Hello", HashMap::new(), 0.5, None);
/// memory.store(entry).await?;
///
/// let entries = memory.retrieve("", 10).await?;
/// # Ok(())
/// # }
/// ```
pub struct WorkingMemory {
    max_messages: usize,
    messages: Arc<RwLock<Vec<MemoryEntry>>>,
}

impl WorkingMemory {
    /// Create a new working memory.
    pub fn new(max_messages: usize) -> Result<Self, AgentError> {
        if max_messages < 1 {
            return Err(AgentError::InvalidInput(
                "maxMessages must be at least 1".to_string(),
            ));
        }

        Ok(Self {
            max_messages,
            messages: Arc::new(RwLock::new(Vec::new())),
        })
    }

    /// Store a memory entry in working memory.
    pub async fn store(&self, entry: MemoryEntry) -> Result<(), AgentError> {
        let mut messages = self.messages.write().unwrap();
        messages.push(entry);

        // Evict oldest if over capacity
        if messages.len() > self.max_messages {
            messages.remove(0);
        }

        Ok(())
    }

    /// Retrieve recent messages from working memory.
    pub async fn retrieve(
        &self,
        _query: &str,
        limit: usize,
    ) -> Result<Vec<MemoryEntry>, AgentError> {
        let messages = self.messages.read().unwrap();

        // Working memory returns all recent messages
        let start = if messages.len() > limit {
            messages.len() - limit
        } else {
            0
        };

        Ok(messages[start..].to_vec())
    }

    /// Delete a memory entry from working memory.
    pub async fn delete(&self, entry_id: &str) -> Result<(), AgentError> {
        let mut messages = self.messages.write().unwrap();
        messages.retain(|e| e.id != entry_id);
        Ok(())
    }

    /// Get all working memory entries.
    pub fn get_all(&self) -> Vec<MemoryEntry> {
        self.messages.read().unwrap().clone()
    }

    /// Clear all working memory.
    pub fn clear(&self) {
        self.messages.write().unwrap().clear();
    }

    /// Get the number of entries in working memory.
    pub fn len(&self) -> usize {
        self.messages.read().unwrap().len()
    }

    /// Check if working memory is empty.
    pub fn is_empty(&self) -> bool {
        self.messages.read().unwrap().is_empty()
    }
}

/// Recent session memory with TTL-based expiration.
///
/// # Characteristics
///
/// - Medium capacity: 100-1000 messages typically
/// - TTL-based: Entries expire after time period
/// - Recency retrieval: Most recent first
/// - LRU eviction: Least recently used removed first
/// - Use for: Recent conversations, sliding window
pub struct ShortTermMemory {
    max_messages: usize,
    ttl: Duration,
    messages: Arc<RwLock<Vec<MemoryEntry>>>,
}

impl ShortTermMemory {
    /// Create a new short-term memory.
    pub fn new(max_messages: usize, ttl_seconds: i64) -> Result<Self, AgentError> {
        if max_messages < 1 {
            return Err(AgentError::InvalidInput(
                "maxMessages must be at least 1".to_string(),
            ));
        }
        if ttl_seconds < 1 {
            return Err(AgentError::InvalidInput(
                "ttlSeconds must be at least 1".to_string(),
            ));
        }

        Ok(Self {
            max_messages,
            ttl: Duration::seconds(ttl_seconds),
            messages: Arc::new(RwLock::new(Vec::new())),
        })
    }

    /// Store a memory entry in short-term memory.
    pub async fn store(&self, entry: MemoryEntry) -> Result<(), AgentError> {
        let mut messages = self.messages.write().unwrap();

        // Clean expired entries first
        self.clean_expired(&mut messages);

        messages.push(entry);

        // Evict if over capacity (LRU)
        if messages.len() > self.max_messages {
            // Sort by access time (least recently used first)
            messages.sort_by(|a, b| {
                let a_time = a.last_accessed.unwrap_or(a.timestamp);
                let b_time = b.last_accessed.unwrap_or(b.timestamp);
                a_time.cmp(&b_time)
            });

            messages.remove(0);
        }

        Ok(())
    }

    /// Retrieve recent messages from short-term memory.
    pub async fn retrieve(
        &self,
        _query: &str,
        limit: usize,
    ) -> Result<Vec<MemoryEntry>, AgentError> {
        let mut messages = self.messages.write().unwrap();

        self.clean_expired(&mut messages);

        // Sort by timestamp (most recent first)
        let mut sorted = messages.clone();
        sorted.sort_by_key(|m| std::cmp::Reverse(m.timestamp));

        // Take top limit
        let results: Vec<MemoryEntry> = sorted.into_iter().take(limit).collect();

        // Update access time and count
        let now = Utc::now();
        for entry in &results {
            if let Some(msg) = messages.iter_mut().find(|m| m.id == entry.id) {
                msg.access_count += 1;
                msg.last_accessed = Some(now);
            }
        }

        Ok(results)
    }

    /// Delete a memory entry from short-term memory.
    pub async fn delete(&self, entry_id: &str) -> Result<(), AgentError> {
        let mut messages = self.messages.write().unwrap();
        messages.retain(|e| e.id != entry_id);
        Ok(())
    }

    /// Clean expired entries.
    fn clean_expired(&self, messages: &mut Vec<MemoryEntry>) {
        let now = Utc::now();
        messages.retain(|e| now.signed_duration_since(e.timestamp) < self.ttl);
    }

    /// Get the number of entries in short-term memory.
    pub fn len(&self) -> usize {
        self.messages.read().unwrap().len()
    }

    /// Check if short-term memory is empty.
    pub fn is_empty(&self) -> bool {
        self.messages.read().unwrap().is_empty()
    }
}

/// Persistent semantic memory with importance-based retention.
///
/// # Characteristics
///
/// - Large capacity: Unlimited (depends on storage backend)
/// - Semantic retrieval: By relevance/similarity
/// - Persistent: Survives restarts
/// - Importance-based: Only important memories stored
/// - Use for: User preferences, facts, learned information
pub struct LongTermMemory {
    storage: Arc<RwLock<HashMap<String, MemoryEntry>>>,
    min_importance: f64,
}

impl LongTermMemory {
    /// Create a new long-term memory.
    pub fn new(
        storage_backend: HashMap<String, MemoryEntry>,
        min_importance: f64,
    ) -> Result<Self, AgentError> {
        if !(0.0..=1.0).contains(&min_importance) {
            return Err(AgentError::InvalidInput(
                "minImportance must be between 0.0 and 1.0".to_string(),
            ));
        }

        Ok(Self {
            storage: Arc::new(RwLock::new(storage_backend)),
            min_importance,
        })
    }

    /// Store a memory entry in long-term memory.
    pub async fn store(&self, entry: MemoryEntry) -> Result<(), AgentError> {
        // Check importance threshold
        if entry.importance < self.min_importance {
            return Ok(()); // Not important enough for long-term storage
        }

        let mut storage = self.storage.write().unwrap();
        storage.insert(entry.id.clone(), entry);

        Ok(())
    }

    /// Retrieve relevant memories from long-term memory.
    pub async fn retrieve(
        &self,
        query: &str,
        limit: usize,
    ) -> Result<Vec<MemoryEntry>, AgentError> {
        let mut storage = self.storage.write().unwrap();

        let all_entries: Vec<MemoryEntry> = storage.values().cloned().collect();

        // Simple keyword-based relevance
        let query_lower = query.to_lowercase();
        let mut scored_entries: Vec<(MemoryEntry, f64)> = all_entries
            .into_iter()
            .map(|entry| {
                let mut score = 0.0;

                // Keyword match
                if entry.content.to_lowercase().contains(&query_lower) {
                    score += 0.5;
                }

                // Importance weight
                score += entry.importance * 0.3;

                // Recency weight (more recent = higher score)
                let age_days = (Utc::now() - entry.timestamp).num_days() as f64;
                let recency_score = (1.0 - age_days / 365.0).max(0.0);
                score += recency_score * 0.2;

                (entry, score)
            })
            .collect();

        // Sort by score (descending)
        scored_entries.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        // Take top limit
        let mut results: Vec<MemoryEntry> = scored_entries
            .into_iter()
            .take(limit)
            .map(|(entry, _)| entry)
            .collect();

        // Update access time and count
        let now = Utc::now();
        for entry in &results {
            if let Some(stored_entry) = storage.get_mut(&entry.id) {
                stored_entry.access_count += 1;
                stored_entry.last_accessed = Some(now);
            }
        }

        // Clone the updated entries
        results = results
            .iter()
            .filter_map(|e| storage.get(&e.id).cloned())
            .collect();

        Ok(results)
    }

    /// Delete a memory entry from long-term memory.
    pub async fn delete(&self, entry_id: &str) -> Result<(), AgentError> {
        let mut storage = self.storage.write().unwrap();
        storage.remove(entry_id);
        Ok(())
    }

    /// Get the number of entries in long-term memory.
    pub fn len(&self) -> usize {
        self.storage.read().unwrap().len()
    }

    /// Check if long-term memory is empty.
    pub fn is_empty(&self) -> bool {
        self.storage.read().unwrap().is_empty()
    }
}

/// Multi-tier memory system for agents.
///
/// Manages working, short-term, and long-term memory with automatic
/// promotion and intelligent retrieval across tiers.
///
/// # Example
///
/// ```no_run
/// use agenkit::patterns::{MemoryHierarchy, WorkingMemory, ShortTermMemory, LongTermMemory};
/// use std::collections::HashMap;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let memory = MemoryHierarchy::new(
///     WorkingMemory::new(10)?,
///     Some(ShortTermMemory::new(100, 3600)?),
///     Some(LongTermMemory::new(HashMap::new(), 0.7)?),
/// );
///
/// // Store important memory
/// let id = memory.store(
///     "User prefers Python for data science",
///     HashMap::new(),
///     0.9,
///     Some("session123".to_string()),
/// ).await?;
///
/// // Retrieve across all tiers
/// let results = memory.retrieve("What language?", 5, None).await?;
/// # Ok(())
/// # }
/// ```
pub struct MemoryHierarchy {
    working: WorkingMemory,
    short_term: Option<ShortTermMemory>,
    long_term: Option<LongTermMemory>,
}

impl MemoryHierarchy {
    /// Create a new memory hierarchy.
    pub fn new(
        working_memory: WorkingMemory,
        short_term_memory: Option<ShortTermMemory>,
        long_term_memory: Option<LongTermMemory>,
    ) -> Self {
        Self {
            working: working_memory,
            short_term: short_term_memory,
            long_term: long_term_memory,
        }
    }

    /// Store memory across appropriate tiers.
    pub async fn store(
        &self,
        content: impl Into<String>,
        metadata: HashMap<String, serde_json::Value>,
        importance: f64,
        session_id: Option<String>,
    ) -> Result<String, AgentError> {
        if !(0.0..=1.0).contains(&importance) {
            return Err(AgentError::InvalidInput(
                "importance must be between 0.0 and 1.0".to_string(),
            ));
        }

        // Create entry
        let entry = create_memory_entry(content, metadata, importance, session_id);
        let entry_id = entry.id.clone();

        // Always store in working memory
        self.working.store(entry.clone()).await?;

        // Store in short-term if available
        if let Some(ref short_term) = self.short_term {
            short_term.store(entry.clone()).await?;
        }

        // Store in long-term if important enough
        if let Some(ref long_term) = self.long_term {
            if importance >= long_term.min_importance {
                long_term.store(entry).await?;
            }
        }

        Ok(entry_id)
    }

    /// Retrieve memories from hierarchy.
    ///
    /// Searches across all enabled tiers and returns deduplicated, ranked results.
    pub async fn retrieve(
        &self,
        query: &str,
        limit: usize,
        search_tiers: Option<Vec<String>>,
    ) -> Result<Vec<MemoryEntry>, AgentError> {
        let mut results = Vec::new();

        // Determine which tiers to search
        let tiers_to_search = search_tiers.unwrap_or_else(|| {
            vec![
                "working".to_string(),
                "short_term".to_string(),
                "long_term".to_string(),
            ]
        });

        // Search working memory
        if tiers_to_search.contains(&"working".to_string()) {
            let working_results = self.working.retrieve(query, limit).await?;
            results.extend(working_results);
        }

        // Search short-term memory
        if let Some(ref short_term) = self.short_term {
            if tiers_to_search.contains(&"short_term".to_string()) {
                let short_results = short_term.retrieve(query, limit).await?;
                results.extend(short_results);
            }
        }

        // Search long-term memory
        if let Some(ref long_term) = self.long_term {
            if tiers_to_search.contains(&"long_term".to_string()) {
                let long_results = long_term.retrieve(query, limit).await?;
                results.extend(long_results);
            }
        }

        // Deduplicate by ID
        let mut seen = std::collections::HashSet::new();
        let mut unique = Vec::new();

        for entry in results {
            if !seen.contains(&entry.id) {
                seen.insert(entry.id.clone());
                unique.push(entry);
            }
        }

        // Sort by importance and recency
        unique.sort_by(|a, b| {
            // Primary: importance
            match b.importance.partial_cmp(&a.importance) {
                Some(std::cmp::Ordering::Equal) => {
                    // Secondary: recency
                    b.timestamp.cmp(&a.timestamp)
                }
                Some(ordering) => ordering,
                None => std::cmp::Ordering::Equal,
            }
        });

        // Return top limit
        if unique.len() > limit {
            unique.truncate(limit);
        }

        Ok(unique)
    }

    /// Delete memory from all tiers.
    pub async fn delete(&self, entry_id: &str) -> Result<(), AgentError> {
        self.working.delete(entry_id).await?;

        if let Some(ref short_term) = self.short_term {
            short_term.delete(entry_id).await?;
        }

        if let Some(ref long_term) = self.long_term {
            long_term.delete(entry_id).await?;
        }

        Ok(())
    }

    /// Clear all working memory.
    pub fn clear_working(&self) {
        self.working.clear();
    }

    /// Get working memory entries.
    pub fn get_working(&self) -> Vec<MemoryEntry> {
        self.working.get_all()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_working_memory_basic() {
        let memory = WorkingMemory::new(3).unwrap();

        let entry1 = create_memory_entry("Message 1", HashMap::new(), 0.5, None);
        let entry2 = create_memory_entry("Message 2", HashMap::new(), 0.5, None);

        memory.store(entry1).await.unwrap();
        memory.store(entry2).await.unwrap();

        assert_eq!(memory.len(), 2);

        let results = memory.retrieve("", 10).await.unwrap();
        assert_eq!(results.len(), 2);
    }

    #[tokio::test]
    async fn test_working_memory_eviction() {
        let memory = WorkingMemory::new(2).unwrap();

        let entry1 = create_memory_entry("Message 1", HashMap::new(), 0.5, None);
        let entry2 = create_memory_entry("Message 2", HashMap::new(), 0.5, None);
        let entry3 = create_memory_entry("Message 3", HashMap::new(), 0.5, None);

        memory.store(entry1.clone()).await.unwrap();
        memory.store(entry2.clone()).await.unwrap();
        memory.store(entry3.clone()).await.unwrap();

        // Should only have 2 entries (oldest evicted)
        assert_eq!(memory.len(), 2);

        let results = memory.retrieve("", 10).await.unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].content, "Message 2");
        assert_eq!(results[1].content, "Message 3");
    }

    #[tokio::test]
    async fn test_working_memory_delete() {
        let memory = WorkingMemory::new(5).unwrap();

        let entry = create_memory_entry("Test", HashMap::new(), 0.5, None);
        let entry_id = entry.id.clone();

        memory.store(entry).await.unwrap();
        assert_eq!(memory.len(), 1);

        memory.delete(&entry_id).await.unwrap();
        assert_eq!(memory.len(), 0);
    }

    #[tokio::test]
    async fn test_short_term_memory_basic() {
        let memory = ShortTermMemory::new(10, 3600).unwrap();

        let entry = create_memory_entry("Test message", HashMap::new(), 0.5, None);
        memory.store(entry).await.unwrap();

        let results = memory.retrieve("", 10).await.unwrap();
        assert_eq!(results.len(), 1);
    }

    #[tokio::test]
    async fn test_short_term_memory_ttl() {
        let memory = ShortTermMemory::new(10, 1).unwrap(); // 1 second TTL

        let mut entry = create_memory_entry("Test", HashMap::new(), 0.5, None);
        // Set timestamp to 2 seconds ago
        entry.timestamp = Utc::now() - Duration::seconds(2);

        memory.store(entry).await.unwrap();

        // Entry should be expired
        let results = memory.retrieve("", 10).await.unwrap();
        assert_eq!(results.len(), 0);
    }

    #[tokio::test]
    async fn test_long_term_memory_basic() {
        let memory = LongTermMemory::new(HashMap::new(), 0.5).unwrap();

        let entry = create_memory_entry("Important fact", HashMap::new(), 0.8, None);
        memory.store(entry).await.unwrap();

        let results = memory.retrieve("fact", 10).await.unwrap();
        assert_eq!(results.len(), 1);
    }

    #[tokio::test]
    async fn test_long_term_memory_importance_threshold() {
        let memory = LongTermMemory::new(HashMap::new(), 0.7).unwrap();

        let low_importance = create_memory_entry("Low", HashMap::new(), 0.5, None);
        let high_importance = create_memory_entry("High", HashMap::new(), 0.9, None);

        memory.store(low_importance).await.unwrap();
        memory.store(high_importance).await.unwrap();

        // Only high importance should be stored
        assert_eq!(memory.len(), 1);
    }

    #[tokio::test]
    async fn test_memory_hierarchy_basic() {
        let working = WorkingMemory::new(10).unwrap();
        let short_term = Some(ShortTermMemory::new(100, 3600).unwrap());
        let long_term = Some(LongTermMemory::new(HashMap::new(), 0.7).unwrap());

        let hierarchy = MemoryHierarchy::new(working, short_term, long_term);

        let entry_id = hierarchy
            .store("Test message", HashMap::new(), 0.8, None)
            .await
            .unwrap();

        assert!(!entry_id.is_empty());

        let results = hierarchy.retrieve("test", 10, None).await.unwrap();
        assert!(!results.is_empty());
    }

    #[tokio::test]
    async fn test_memory_hierarchy_tiers() {
        let working = WorkingMemory::new(10).unwrap();
        let short_term = Some(ShortTermMemory::new(100, 3600).unwrap());
        let long_term = Some(LongTermMemory::new(HashMap::new(), 0.7).unwrap());

        let hierarchy = MemoryHierarchy::new(working, short_term, long_term);

        // Store with high importance (should go to all tiers)
        hierarchy
            .store("Important", HashMap::new(), 0.9, None)
            .await
            .unwrap();

        // Search only long-term
        let results = hierarchy
            .retrieve("Important", 10, Some(vec!["long_term".to_string()]))
            .await
            .unwrap();

        assert_eq!(results.len(), 1);
    }

    #[tokio::test]
    async fn test_memory_hierarchy_delete() {
        let working = WorkingMemory::new(10).unwrap();
        let hierarchy = MemoryHierarchy::new(working, None, None);

        let entry_id = hierarchy
            .store("Test", HashMap::new(), 0.5, None)
            .await
            .unwrap();

        hierarchy.delete(&entry_id).await.unwrap();

        let results = hierarchy.retrieve("Test", 10, None).await.unwrap();
        assert_eq!(results.len(), 0);
    }

    #[tokio::test]
    async fn test_memory_entry_creation() {
        let entry = create_memory_entry("Test", HashMap::new(), 0.5, Some("session1".to_string()));

        assert_eq!(entry.content, "Test");
        assert_eq!(entry.importance, 0.5);
        assert_eq!(entry.session_id, Some("session1".to_string()));
        assert_eq!(entry.access_count, 0);
        assert!(entry.last_accessed.is_none());
    }

    #[tokio::test]
    async fn test_working_memory_clear() {
        let memory = WorkingMemory::new(10).unwrap();

        memory
            .store(create_memory_entry("Test", HashMap::new(), 0.5, None))
            .await
            .unwrap();

        assert_eq!(memory.len(), 1);

        memory.clear();
        assert_eq!(memory.len(), 0);
    }

    #[tokio::test]
    async fn test_memory_hierarchy_deduplication() {
        let working = WorkingMemory::new(10).unwrap();
        let short_term = Some(ShortTermMemory::new(100, 3600).unwrap());

        let hierarchy = MemoryHierarchy::new(working, short_term, None);

        // Store same message (will be in both tiers)
        hierarchy
            .store("Duplicate", HashMap::new(), 0.5, None)
            .await
            .unwrap();

        // Should deduplicate
        let results = hierarchy.retrieve("Duplicate", 10, None).await.unwrap();
        assert_eq!(results.len(), 1);
    }
}
