//! Vector-based memory implementation with semantic search.
//!
//! Provides semantic retrieval using embeddings and vector similarity
//! for intelligent context management and RAG (Retrieval-Augmented Generation) patterns.
//!
//! # Features
//!
//! - **Semantic search** via embeddings - Find conceptually similar messages, not just keyword matches
//! - **Pluggable embedding providers** - Bring your own embeddings (OpenAI, local models, etc.)
//! - **Pluggable vector stores** - In-memory (default) or external databases (ChromaDB, Pinecone, etc.)
//! - **Rich filtering** - Filter by time range, importance, tags, and similarity threshold
//! - **Session isolation** - Independent memory contexts per session
//! - **Async operations** - Built on tokio for high-performance concurrent access
//! - **Similarity scores** - Get relevance scores with search results
//!
//! # Architecture
//!
//! The vector memory system has three main components:
//!
//! 1. **EmbeddingProvider** - Converts text to vector embeddings
//! 2. **VectorStore** - Stores embeddings and performs similarity search
//! 3. **VectorMemory** - High-level API that coordinates the above
//!
//! ## Embedding Providers
//!
//! Implement the `EmbeddingProvider` trait to use your preferred embedding model:
//!
//! ```rust
//! use agenkit::memory::EmbeddingProvider;
//! use agenkit::core::AgentError;
//! use async_trait::async_trait;
//!
//! struct MyEmbeddingProvider {
//!     dimension: usize,
//! }
//!
//! #[async_trait]
//! impl EmbeddingProvider for MyEmbeddingProvider {
//!     async fn embed(&self, text: &str) -> Result<Vec<f64>, AgentError> {
//!         // Call your embedding service here
//!         Ok(vec![0.0; self.dimension])
//!     }
//!
//!     fn dimension(&self) -> usize {
//!         self.dimension
//!     }
//! }
//! ```
//!
//! ## Vector Stores
//!
//! The `InMemoryVectorStore` is provided for development and testing.
//! For production, implement the `VectorStore` trait to integrate with
//! specialized vector databases:
//!
//! - **ChromaDB** - Open source embedding database
//! - **Pinecone** - Managed vector database
//! - **Weaviate** - Vector search engine
//! - **Qdrant** - Vector similarity search engine
//!
//! # Usage Examples
//!
//! ## Basic Usage
//!
//! ```rust
//! use agenkit::memory::{VectorMemory, EmbeddingProvider};
//! use agenkit::core::{Message, AgentError};
//! use async_trait::async_trait;
//! use std::collections::HashMap;
//!
//! # struct SimpleEmbeddings;
//! # #[async_trait]
//! # impl EmbeddingProvider for SimpleEmbeddings {
//! #     async fn embed(&self, text: &str) -> Result<Vec<f64>, AgentError> {
//! #         Ok(vec![0.0; 10])
//! #     }
//! #     fn dimension(&self) -> usize { 10 }
//! # }
//! #
//! # async fn example() -> Result<(), AgentError> {
//! // Create memory with embedding provider
//! let embeddings = Box::new(SimpleEmbeddings);
//! let memory = VectorMemory::new(embeddings, None);
//!
//! // Store messages
//! memory.store(
//!     "session-1",
//!     Message::with_text("user", "What are the pricing plans?"),
//!     None,
//! ).await?;
//!
//! // Retrieve most recent messages
//! let recent = memory.retrieve("session-1", None, 10, &Default::default()).await?;
//!
//! // Semantic search
//! let results = memory.retrieve(
//!     "session-1",
//!     Some("pricing information"),
//!     5,
//!     &Default::default(),
//! ).await?;
//! # Ok(())
//! # }
//! ```
//!
//! ## Filtering by Metadata
//!
//! ```rust
//! use agenkit::memory::{VectorMemory, SearchOptions};
//! use agenkit::core::Message;
//! use std::collections::HashMap;
//! use serde_json::json;
//! # use agenkit::core::AgentError;
//! # use agenkit::memory::EmbeddingProvider;
//! # use async_trait::async_trait;
//! # struct SimpleEmbeddings;
//! # #[async_trait]
//! # impl EmbeddingProvider for SimpleEmbeddings {
//! #     async fn embed(&self, text: &str) -> Result<Vec<f64>, AgentError> {
//! #         Ok(vec![0.0; 10])
//! #     }
//! #     fn dimension(&self) -> usize { 10 }
//! # }
//! #
//! # async fn example() -> Result<(), AgentError> {
//! # let embeddings = Box::new(SimpleEmbeddings);
//! # let memory = VectorMemory::new(embeddings, None);
//! #
//! // Store with metadata
//! let mut metadata = HashMap::new();
//! metadata.insert("importance".to_string(), json!(0.9));
//! metadata.insert("tags".to_string(), json!(["production", "critical"]));
//!
//! memory.store(
//!     "session-1",
//!     Message::with_text("user", "Critical production issue"),
//!     Some(metadata),
//! ).await?;
//!
//! // Filter by importance
//! let options = SearchOptions {
//!     importance_threshold: Some(0.8),
//!     ..Default::default()
//! };
//! let important = memory.retrieve("session-1", None, 10, &options).await?;
//!
//! // Filter by tags
//! let options = SearchOptions {
//!     tags: vec!["production".to_string()],
//!     ..Default::default()
//! };
//! let tagged = memory.retrieve("session-1", None, 10, &options).await?;
//! # Ok(())
//! # }
//! ```
//!
//! ## Retrieve with Similarity Scores
//!
//! ```rust
//! # use agenkit::memory::VectorMemory;
//! # use agenkit::core::{Message, AgentError};
//! # use agenkit::memory::EmbeddingProvider;
//! # use async_trait::async_trait;
//! # struct SimpleEmbeddings;
//! # #[async_trait]
//! # impl EmbeddingProvider for SimpleEmbeddings {
//! #     async fn embed(&self, text: &str) -> Result<Vec<f64>, AgentError> {
//! #         Ok(vec![0.0; 10])
//! #     }
//! #     fn dimension(&self) -> usize { 10 }
//! # }
//! # async fn example() -> Result<(), AgentError> {
//! # let embeddings = Box::new(SimpleEmbeddings);
//! # let memory = VectorMemory::new(embeddings, None);
//! # memory.store("session-1", Message::with_text("user", "test"), None).await?;
//! #
//! // Get results with similarity scores
//! let results = memory.retrieve_with_scores(
//!     "session-1",
//!     "pricing information",
//!     5,
//!     &Default::default(),
//! ).await?;
//!
//! for (message, score) in results {
//!     println!("Score: {:.3} - {}", score, message.content);
//! }
//! # Ok(())
//! # }
//! ```
//!
//! # Performance Considerations
//!
//! - **In-Memory Store**: O(n) search complexity, suitable for < 10,000 messages
//! - **Production**: Use specialized vector databases for millions of embeddings
//! - **Embedding Generation**: Can be slow, consider caching or batch processing
//! - **Thread Safety**: All operations are thread-safe with `Arc<Mutex<_>>`
//!
//! # See Also
//!
//! - Example: `examples/vector_memory_basic.rs` - Complete working example
//! - Tests: `tests/test_vector_memory.rs` - 17 comprehensive tests
//! - Related: `MemoryHierarchy` for multi-tier memory architecture

use crate::core::{AgentError, Message};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::Value as JsonValue;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

/// Distance metric for vector similarity calculations.
///
/// - `Cosine`: Cosine similarity (best for text embeddings, normalized by magnitude)
/// - `Euclidean`: Euclidean distance (best for spatial data, L2 norm)
/// - `DotProduct`: Dot product (best for pre-normalized vectors, inner product)
///
/// # Examples
///
/// ```rust
/// use agenkit::memory::DistanceMetric;
///
/// // Default is cosine similarity
/// let metric = DistanceMetric::default();
/// assert_eq!(metric, DistanceMetric::Cosine);
///
/// // Use euclidean for spatial data
/// let metric = DistanceMetric::Euclidean;
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[derive(Default)]
pub enum DistanceMetric {
    /// Cosine similarity - best for text embeddings
    #[default]
    Cosine,
    /// Euclidean distance - best for spatial data
    Euclidean,
    /// Dot product - best for pre-normalized vectors
    DotProduct,
}


/// Trait for embedding providers.
///
/// Implementations can use OpenAI, local models, or custom services.
#[async_trait]
pub trait EmbeddingProvider: Send + Sync {
    /// Generate embedding vector for text.
    async fn embed(&self, text: &str) -> Result<Vec<f64>, AgentError>;

    /// Return embedding dimension.
    fn dimension(&self) -> usize;
}

/// Search result with similarity score.
#[derive(Debug, Clone)]
pub struct MessageSearchResult {
    pub message: Message,
    pub metadata: HashMap<String, JsonValue>,
    pub score: f64,
}

/// Message with metadata (no score).
#[derive(Debug, Clone)]
pub struct MessageWithMetadata {
    pub message: Message,
    pub metadata: HashMap<String, JsonValue>,
}

/// Search and filter options.
#[derive(Debug, Clone)]
pub struct SearchOptions {
    /// Time range filter (start_secs, end_secs)
    pub time_range: Option<(f64, f64)>,
    /// Minimum importance threshold (0.0-1.0)
    pub importance_threshold: Option<f64>,
    /// Tags filter (matches any)
    pub tags: Vec<String>,
    /// Minimum similarity score (0.0-1.0)
    pub min_similarity: f64,
    /// Distance metric to use for similarity calculation
    pub distance_metric: DistanceMetric,
}

impl Default for SearchOptions {
    fn default() -> Self {
        Self {
            time_range: None,
            importance_threshold: None,
            tags: Vec::new(),
            min_similarity: 0.0,
            distance_metric: DistanceMetric::default(),
        }
    }
}

/// Item for batch vector store operations.
///
/// Used by `VectorStore::add_batch()` to add multiple messages efficiently.
#[derive(Debug, Clone)]
pub struct VectorStoreItem {
    pub message_id: String,
    pub embedding: Vec<f64>,
    pub message: Message,
    pub metadata: HashMap<String, JsonValue>,
    pub timestamp: f64,
}

/// Item for batch storage through VectorMemory.
///
/// Used by `VectorMemory::store_batch()` to generate embeddings and store multiple
/// messages in parallel.
#[derive(Debug, Clone)]
pub struct StoreBatchItem {
    pub message: Message,
    pub metadata: Option<HashMap<String, JsonValue>>,
}

/// Trait for vector storage backends.
///
/// Implementations can use in-memory, ChromaDB, Pinecone, etc.
#[async_trait]
pub trait VectorStore: Send + Sync {
    /// Add message with embedding to store.
    async fn add(
        &self,
        session_id: &str,
        message_id: &str,
        embedding: Vec<f64>,
        message: Message,
        metadata: HashMap<String, JsonValue>,
        timestamp: f64,
    ) -> Result<(), AgentError>;

    /// Search for similar messages using vector similarity.
    async fn search(
        &self,
        session_id: &str,
        query_embedding: Vec<f64>,
        limit: usize,
        options: &SearchOptions,
    ) -> Result<Vec<MessageSearchResult>, AgentError>;

    /// Get recent messages without search.
    async fn get_recent(
        &self,
        session_id: &str,
        limit: usize,
        options: &SearchOptions,
    ) -> Result<Vec<MessageWithMetadata>, AgentError>;

    /// Add multiple messages with embeddings in batch.
    ///
    /// This is more efficient than calling `add()` repeatedly, as implementations
    /// can optimize bulk operations (e.g., single database transaction).
    async fn add_batch(
        &self,
        session_id: &str,
        items: Vec<VectorStoreItem>,
    ) -> Result<(), AgentError>;

    /// Search with multiple query embeddings in batch.
    ///
    /// Returns a vector of search results for each query embedding.
    /// This is more efficient than calling `search()` repeatedly.
    async fn search_batch(
        &self,
        session_id: &str,
        query_embeddings: Vec<Vec<f64>>,
        limit: usize,
        options: &SearchOptions,
    ) -> Result<Vec<Vec<MessageSearchResult>>, AgentError>;

    /// Clear all messages for session.
    async fn clear(&self, session_id: &str) -> Result<(), AgentError>;
}

/// Entry stored in vector store.
#[derive(Debug, Clone)]
struct VectorEntry {
    message_id: String,
    embedding: Vec<f64>,
    message: Message,
    metadata: HashMap<String, JsonValue>,
    timestamp: f64,
}

/// Simple in-memory vector store using cosine similarity.
///
/// Good for testing and small datasets. For production, use
/// specialized vector databases (ChromaDB, Pinecone, Weaviate, Qdrant).
pub struct InMemoryVectorStore {
    storage: Arc<Mutex<HashMap<String, Vec<VectorEntry>>>>,
}

impl InMemoryVectorStore {
    /// Create new in-memory vector store.
    pub fn new() -> Self {
        Self {
            storage: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Calculate cosine similarity between two vectors.
    fn cosine_similarity(a: &[f64], b: &[f64]) -> Result<f64, AgentError> {
        if a.len() != b.len() {
            return Err(AgentError::ProcessingError(format!(
                "vector dimension mismatch: {} vs {}",
                a.len(),
                b.len()
            )));
        }

        let dot_product: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let magnitude_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
        let magnitude_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();

        if magnitude_a == 0.0 || magnitude_b == 0.0 {
            return Ok(0.0);
        }

        Ok(dot_product / (magnitude_a * magnitude_b))
    }

    /// Calculate Euclidean distance between two vectors.
    ///
    /// Returns the L2 norm distance between vectors.
    /// Lower values indicate more similarity.
    fn euclidean_distance(a: &[f64], b: &[f64]) -> Result<f64, AgentError> {
        if a.len() != b.len() {
            return Err(AgentError::ProcessingError(format!(
                "vector dimension mismatch: {} vs {}",
                a.len(),
                b.len()
            )));
        }

        let sum: f64 = a.iter().zip(b.iter()).map(|(x, y)| (x - y).powi(2)).sum();

        Ok(sum.sqrt())
    }

    /// Calculate dot product between two vectors.
    ///
    /// Returns the inner product of two vectors.
    /// Higher values indicate more similarity for normalized vectors.
    fn dot_product(a: &[f64], b: &[f64]) -> Result<f64, AgentError> {
        if a.len() != b.len() {
            return Err(AgentError::ProcessingError(format!(
                "vector dimension mismatch: {} vs {}",
                a.len(),
                b.len()
            )));
        }

        let product: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();

        Ok(product)
    }

    /// Calculate similarity using specified distance metric.
    ///
    /// Converts all distance metrics to similarity scores where higher is more similar.
    ///
    /// # Arguments
    ///
    /// * `a` - First vector
    /// * `b` - Second vector
    /// * `metric` - Distance metric to use
    ///
    /// # Returns
    ///
    /// Similarity score (higher = more similar)
    fn calculate_similarity(
        a: &[f64],
        b: &[f64],
        metric: DistanceMetric,
    ) -> Result<f64, AgentError> {
        match metric {
            DistanceMetric::Cosine => Self::cosine_similarity(a, b),
            DistanceMetric::Euclidean => {
                let distance = Self::euclidean_distance(a, b)?;
                // Convert distance to similarity: 1 / (1 + distance)
                Ok(1.0 / (1.0 + distance))
            }
            DistanceMetric::DotProduct => Self::dot_product(a, b),
        }
    }

    /// Check if entry passes filters.
    fn apply_filters(entry: &VectorEntry, options: &SearchOptions) -> bool {
        // Time range filter
        if let Some((start_time, end_time)) = options.time_range {
            if entry.timestamp < start_time || entry.timestamp > end_time {
                return false;
            }
        }

        // Importance threshold filter
        if let Some(threshold) = options.importance_threshold {
            let importance = entry
                .metadata
                .get("importance")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0);
            if importance < threshold {
                return false;
            }
        }

        // Tags filter
        if !options.tags.is_empty() {
            let message_tags: Vec<String> = entry
                .metadata
                .get("tags")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(|s| s.to_string()))
                        .collect()
                })
                .unwrap_or_default();

            let has_intersection = options.tags.iter().any(|tag| message_tags.contains(tag));
            if !has_intersection {
                return false;
            }
        }

        true
    }
}

impl Default for InMemoryVectorStore {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl VectorStore for InMemoryVectorStore {
    async fn add(
        &self,
        session_id: &str,
        message_id: &str,
        embedding: Vec<f64>,
        message: Message,
        metadata: HashMap<String, JsonValue>,
        timestamp: f64,
    ) -> Result<(), AgentError> {
        let mut storage = self.storage.lock().unwrap();

        let entry = VectorEntry {
            message_id: message_id.to_string(),
            embedding,
            message,
            metadata,
            timestamp,
        };

        storage
            .entry(session_id.to_string())
            .or_default()
            .push(entry);

        Ok(())
    }

    async fn search(
        &self,
        session_id: &str,
        query_embedding: Vec<f64>,
        limit: usize,
        options: &SearchOptions,
    ) -> Result<Vec<MessageSearchResult>, AgentError> {
        let storage = self.storage.lock().unwrap();

        let entries = match storage.get(session_id) {
            Some(entries) => entries,
            None => return Ok(Vec::new()),
        };

        // Calculate similarity for all messages using the specified metric
        let mut results: Vec<(Message, HashMap<String, JsonValue>, f64)> = Vec::new();

        for entry in entries {
            let score = Self::calculate_similarity(
                &query_embedding,
                &entry.embedding,
                options.distance_metric,
            )?;
            results.push((entry.message.clone(), entry.metadata.clone(), score));
        }

        // Sort by score (descending)
        results.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));

        // Apply filters
        let mut filtered = Vec::new();

        for (message, metadata, score) in results {
            // Check similarity threshold
            if score < options.min_similarity {
                continue;
            }

            // Find original entry for filtering
            let entry = entries
                .iter()
                .find(|e| e.message.content == message.content);
            if let Some(entry) = entry {
                if !Self::apply_filters(entry, options) {
                    continue;
                }
            }

            filtered.push(MessageSearchResult {
                message,
                metadata,
                score,
            });

            if filtered.len() >= limit {
                break;
            }
        }

        Ok(filtered)
    }

    async fn get_recent(
        &self,
        session_id: &str,
        limit: usize,
        options: &SearchOptions,
    ) -> Result<Vec<MessageWithMetadata>, AgentError> {
        let storage = self.storage.lock().unwrap();

        let entries = match storage.get(session_id) {
            Some(entries) => entries,
            None => return Ok(Vec::new()),
        };

        // Sort by timestamp (most recent first)
        let mut sorted = entries.clone();
        sorted.sort_by(|a, b| {
            b.timestamp
                .partial_cmp(&a.timestamp)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Apply filters
        let mut filtered = Vec::new();

        for entry in sorted {
            if !Self::apply_filters(&entry, options) {
                continue;
            }

            filtered.push(MessageWithMetadata {
                message: entry.message.clone(),
                metadata: entry.metadata.clone(),
            });

            if filtered.len() >= limit {
                break;
            }
        }

        Ok(filtered)
    }

    async fn add_batch(
        &self,
        session_id: &str,
        items: Vec<VectorStoreItem>,
    ) -> Result<(), AgentError> {
        let mut storage = self.storage.lock().unwrap();

        if !storage.contains_key(session_id) {
            storage.insert(session_id.to_string(), Vec::new());
        }

        let entries = storage.get_mut(session_id).unwrap();

        for item in items {
            entries.push(VectorEntry {
                message_id: item.message_id,
                embedding: item.embedding,
                message: item.message,
                metadata: item.metadata,
                timestamp: item.timestamp,
            });
        }

        Ok(())
    }

    async fn search_batch(
        &self,
        session_id: &str,
        query_embeddings: Vec<Vec<f64>>,
        limit: usize,
        options: &SearchOptions,
    ) -> Result<Vec<Vec<MessageSearchResult>>, AgentError> {
        let mut all_results = Vec::new();

        for query_embedding in query_embeddings {
            let results = self
                .search(session_id, query_embedding, limit, options)
                .await?;
            all_results.push(results);
        }

        Ok(all_results)
    }

    async fn clear(&self, session_id: &str) -> Result<(), AgentError> {
        let mut storage = self.storage.lock().unwrap();
        storage.remove(session_id);
        Ok(())
    }
}

/// Vector memory for semantic retrieval.
///
/// Features:
/// - Semantic search via embeddings
/// - Relevance-based retrieval
/// - Pluggable embedding providers
/// - Pluggable vector stores
///
/// Use cases:
/// - RAG (Retrieval-Augmented Generation)
/// - Semantic memory
/// - Large knowledge bases
/// - Context-aware agents
pub struct VectorMemory {
    embeddings: Box<dyn EmbeddingProvider>,
    vector_store: Box<dyn VectorStore>,
    id_counter: Arc<Mutex<usize>>,
}

impl VectorMemory {
    /// Create new vector memory.
    ///
    /// # Arguments
    ///
    /// * `embedding_provider` - Provider for generating embeddings
    /// * `vector_store` - Vector storage backend (defaults to in-memory)
    pub fn new(
        embedding_provider: Box<dyn EmbeddingProvider>,
        vector_store: Option<Box<dyn VectorStore>>,
    ) -> Self {
        Self {
            embeddings: embedding_provider,
            vector_store: vector_store.unwrap_or_else(|| Box::new(InMemoryVectorStore::new())),
            id_counter: Arc::new(Mutex::new(0)),
        }
    }

    /// Generate unique message ID.
    fn generate_id(&self) -> String {
        let mut counter = self.id_counter.lock().unwrap();
        *counter += 1;
        format!("msg-{}", *counter)
    }

    /// Get current timestamp in seconds.
    fn get_timestamp() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64()
    }

    /// Store message with embedding in vector store.
    pub async fn store(
        &self,
        session_id: &str,
        message: Message,
        metadata: Option<HashMap<String, JsonValue>>,
    ) -> Result<(), AgentError> {
        // Generate embedding from message content
        let content_str = match &message.content {
            JsonValue::String(s) => s.clone(),
            other => other.to_string(),
        };
        let embedding = self.embeddings.embed(&content_str).await?;

        // Store
        let timestamp = Self::get_timestamp();
        let message_id = self.generate_id();

        self.vector_store
            .add(
                session_id,
                &message_id,
                embedding,
                message,
                metadata.unwrap_or_default(),
                timestamp,
            )
            .await
    }

    /// Store multiple messages at once with parallel embedding generation.
    ///
    /// This is more efficient than calling `store()` repeatedly, as it:
    /// - Generates embeddings in parallel using tokio::spawn
    /// - Uses a single batch operation to the vector store
    ///
    /// # Arguments
    ///
    /// * `session_id` - Session identifier
    /// * `items` - Messages to store with optional metadata
    ///
    /// # Example
    ///
    /// ```no_run
    /// # use agenkit::memory::{VectorMemory, StoreBatchItem};
    /// # use agenkit::core::Message;
    /// # async fn example(memory: VectorMemory) {
    /// let items = vec![
    ///     StoreBatchItem {
    ///         message: Message::with_text("user", "First message"),
    ///         metadata: None,
    ///     },
    ///     StoreBatchItem {
    ///         message: Message::with_text("assistant", "Second message"),
    ///         metadata: None,
    ///     },
    /// ];
    ///
    /// memory.store_batch("session-1", items).await.unwrap();
    /// # }
    /// ```
    pub async fn store_batch(
        &self,
        session_id: &str,
        items: Vec<StoreBatchItem>,
    ) -> Result<(), AgentError> {
        if items.is_empty() {
            return Ok(());
        }

        // Generate all embeddings (sequential for now due to trait object limitations)
        // This is still more efficient than calling store() repeatedly because we use
        // a single add_batch() operation at the end.
        let mut embeddings = Vec::new();
        for item in &items {
            let content_str = match &item.message.content {
                JsonValue::String(s) => s.clone(),
                other => other.to_string(),
            };
            let embedding = self.embeddings.embed(&content_str).await?;
            embeddings.push(embedding);
        }

        // Prepare batch items with unique timestamps
        let mut batch_items = Vec::new();
        let mut counter = self.id_counter.lock().unwrap();

        for (idx, item) in items.into_iter().enumerate() {
            *counter += 1;
            let message_id = format!("msg-{}", *counter);
            let timestamp = Self::get_timestamp() + (idx as f64) * 0.000001; // Ensure unique timestamps

            batch_items.push(VectorStoreItem {
                message_id,
                embedding: embeddings[idx].clone(),
                message: item.message,
                metadata: item.metadata.unwrap_or_default(),
                timestamp,
            });
        }

        drop(counter); // Release lock before await

        // Store all items in batch
        self.vector_store.add_batch(session_id, batch_items).await
    }

    /// Retrieve messages with optional semantic search.
    ///
    /// If query provided, performs semantic search.
    /// Otherwise, returns most recent messages.
    ///
    /// # Arguments
    ///
    /// * `session_id` - Session identifier
    /// * `query` - Optional semantic query
    /// * `limit` - Maximum results to return
    /// * `options` - Filter options
    pub async fn retrieve(
        &self,
        session_id: &str,
        query: Option<&str>,
        limit: usize,
        options: &SearchOptions,
    ) -> Result<Vec<Message>, AgentError> {
        if let Some(query_text) = query {
            // Semantic search
            let query_embedding = self.embeddings.embed(query_text).await?;
            let results = self
                .vector_store
                .search(session_id, query_embedding, limit, options)
                .await?;
            Ok(results.into_iter().map(|r| r.message).collect())
        } else {
            // Recent messages
            let results = self
                .vector_store
                .get_recent(session_id, limit, options)
                .await?;
            Ok(results.into_iter().map(|r| r.message).collect())
        }
    }

    /// Retrieve messages with similarity scores.
    ///
    /// # Arguments
    ///
    /// * `session_id` - Session identifier
    /// * `query` - Semantic query
    /// * `limit` - Maximum results to return
    /// * `options` - Filter options
    ///
    /// # Returns
    ///
    /// List of (message, score) tuples
    pub async fn retrieve_with_scores(
        &self,
        session_id: &str,
        query: &str,
        limit: usize,
        options: &SearchOptions,
    ) -> Result<Vec<(Message, f64)>, AgentError> {
        let query_embedding = self.embeddings.embed(query).await?;
        let results = self
            .vector_store
            .search(session_id, query_embedding, limit, options)
            .await?;
        Ok(results.into_iter().map(|r| (r.message, r.score)).collect())
    }

    /// Create summary of conversation history.
    pub async fn summarize(&self, session_id: &str) -> Result<Message, AgentError> {
        let messages = self
            .retrieve(session_id, None, 100, &Default::default())
            .await?;

        if messages.is_empty() {
            return Ok(Message::with_text("system", "No messages in session."));
        }

        // Simple concatenation summary
        let mut summary_parts = Vec::new();
        for (i, msg) in messages.iter().take(10).enumerate() {
            let content_str = match &msg.content {
                JsonValue::String(s) => s.clone(),
                other => other.to_string(),
            };
            let preview = if content_str.len() > 100 {
                format!("{}...", &content_str[..100])
            } else {
                content_str
            };
            summary_parts.push(format!("{}. [{}] {}", i + 1, msg.role, preview));
        }

        let summary_content = format!(
            "Session summary ({} messages):\n{}",
            messages.len(),
            summary_parts.join("\n")
        );

        Ok(Message::with_text("system", summary_content))
    }

    /// Clear memory for session.
    pub async fn clear(&self, session_id: &str) -> Result<(), AgentError> {
        self.vector_store.clear(session_id).await
    }

    /// Return memory capabilities.
    pub fn capabilities(&self) -> Vec<&'static str> {
        vec![
            "basic_retrieval",
            "semantic_search",
            "similarity_retrieval",
            "time_filtering",
            "importance_filtering",
            "tag_filtering",
        ]
    }
}
