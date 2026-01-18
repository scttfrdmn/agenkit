//! Memory systems for AI agents with three-tier hierarchy.
//!
//! This module provides a comprehensive memory management system for AI agents with
//! short-term, working, and long-term memory capabilities. It supports automatic
//! tier routing, TTL-based expiration, importance-based filtering, and session isolation.
//!
//! # Architecture
//!
//! ## Three-Tier Hierarchy
//!
//! 1. **Working Memory**: Current conversation context (5-20 messages)
//!    - FIFO eviction when over capacity
//!    - In-memory only
//!    - O(1) store, O(n) retrieve
//!
//! 2. **Short-Term Memory**: Recent sessions (100-1000 messages)
//!    - TTL-based expiration (1-24 hours)
//!    - LRU eviction when over capacity
//!    - In-memory with access tracking
//!
//! 3. **Long-Term Memory**: Persistent facts (unlimited)
//!    - Importance threshold filtering (0.6-0.9)
//!    - Keyword/semantic search with scoring
//!    - HashMap-based storage
//!
//! # Example
//!
//! ```rust
//! use agenkit::memory::{MemoryHierarchy, WorkingMemory, ShortTermMemory, LongTermMemory};
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Create three-tier hierarchy
//! let working = WorkingMemory::new(10)?;
//! let short_term = Some(ShortTermMemory::new(100, 3600)?); // 1 hour TTL
//! let long_term = Some(LongTermMemory::new(HashMap::new(), 0.7)?);
//!
//! let mut hierarchy = MemoryHierarchy::new(working, short_term, long_term);
//!
//! // Store message with importance
//! let entry_id = hierarchy.store(
//!     "User said hello",
//!     HashMap::new(),
//!     0.8,
//!     Some("session-1".to_string()),
//! ).await?;
//!
//! // Retrieve recent messages
//! let messages = hierarchy.retrieve("", 10, None).await?;
//!
//! // Delete specific entry
//! hierarchy.delete(&entry_id).await?;
//! # Ok(())
//! # }
//! ```

pub mod entry;
pub mod hierarchy;
pub mod long_term;
pub mod short_term;
pub mod vector_memory;
pub mod working;

pub use entry::MemoryEntry;
pub use hierarchy::MemoryHierarchy;
pub use long_term::LongTermMemory;
pub use short_term::ShortTermMemory;
pub use vector_memory::{
    DistanceMetric, EmbeddingProvider, InMemoryVectorStore, MessageSearchResult,
    MessageWithMetadata, SearchOptions, StoreBatchItem, VectorMemory, VectorStore, VectorStoreItem,
};
pub use working::WorkingMemory;
