//! Tests for vector memory implementation.
//!
//! Tests cover:
//! - EmbeddingProvider trait
//! - InMemoryVectorStore with multiple distance metrics (cosine, euclidean, dot product)
//! - VectorMemory with semantic search
//! - Filtering (time, importance, tags, similarity)
//! - Session isolation
//! - Retrieve with scores
//! - Distance metrics (euclidean, dot product, metric selection)
//! - Batch operations (add_batch, search_batch, store_batch)
//!
//! Total: 26 tests (17 original + 4 distance metrics + 5 batch operations)

use agenkit::core::{AgentError, Message};
use agenkit::memory::{
    DistanceMetric, EmbeddingProvider, InMemoryVectorStore, SearchOptions, VectorMemory,
    VectorStore,
};
use async_trait::async_trait;
use serde_json::json;
use std::collections::HashMap;

/// Mock embedding provider for testing.
///
/// Generates deterministic embeddings based on character frequencies
/// for predictable test behavior.
struct MockEmbeddingProvider {
    dimension: usize,
}

impl MockEmbeddingProvider {
    fn new(dimension: usize) -> Self {
        Self { dimension }
    }
}

#[async_trait]
impl EmbeddingProvider for MockEmbeddingProvider {
    async fn embed(&self, text: &str) -> Result<Vec<f64>, AgentError> {
        // Simple character-based embedding for testing
        let mut embedding = vec![0.0; self.dimension];

        for (i, ch) in text.chars().enumerate() {
            embedding[i % self.dimension] += (ch as u32) as f64;
        }

        // Normalize to unit vector
        let magnitude: f64 = embedding.iter().map(|x| x * x).sum::<f64>().sqrt();
        if magnitude > 0.0 {
            for val in &mut embedding {
                *val /= magnitude;
            }
        }

        Ok(embedding)
    }

    fn dimension(&self) -> usize {
        self.dimension
    }
}

#[tokio::test]
async fn test_store_and_retrieve() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let message = Message::with_text("user", "Hello world");
    memory
        .store("session-1", message.clone(), None)
        .await
        .unwrap();

    let messages = memory
        .retrieve("session-1", None, 10, &Default::default())
        .await
        .unwrap();

    assert_eq!(messages.len(), 1);
    assert_eq!(messages[0].content, "Hello world");
    assert_eq!(messages[0].role, "user");
}

#[tokio::test]
async fn test_multiple_messages() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let messages_to_store = vec![
        Message::with_text("user", "First message"),
        Message::with_text("assistant", "Second message"),
        Message::with_text("user", "Third message"),
    ];

    for msg in messages_to_store {
        memory.store("session-1", msg, None).await.unwrap();
    }

    let retrieved = memory
        .retrieve("session-1", None, 10, &Default::default())
        .await
        .unwrap();

    assert_eq!(retrieved.len(), 3);
}

#[tokio::test]
async fn test_session_isolation() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    memory
        .store("session-1", Message::with_text("user", "Session 1"), None)
        .await
        .unwrap();
    memory
        .store("session-2", Message::with_text("user", "Session 2"), None)
        .await
        .unwrap();

    let session1 = memory
        .retrieve("session-1", None, 10, &Default::default())
        .await
        .unwrap();
    let session2 = memory
        .retrieve("session-2", None, 10, &Default::default())
        .await
        .unwrap();

    assert_eq!(session1.len(), 1);
    assert_eq!(session2.len(), 1);
    assert_eq!(session1[0].content, "Session 1");
    assert_eq!(session2[0].content, "Session 2");
}

#[tokio::test]
async fn test_clear_session() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    memory
        .store("session-1", Message::with_text("user", "Message"), None)
        .await
        .unwrap();
    memory.clear("session-1").await.unwrap();

    let messages = memory
        .retrieve("session-1", None, 10, &Default::default())
        .await
        .unwrap();

    assert_eq!(messages.len(), 0);
}

#[tokio::test]
async fn test_semantic_search() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    // Store test messages
    memory
        .store(
            "session-1",
            Message::with_text("user", "The quick brown fox"),
            None,
        )
        .await
        .unwrap();
    memory
        .store(
            "session-1",
            Message::with_text("assistant", "Tell me about pricing plans"),
            None,
        )
        .await
        .unwrap();
    memory
        .store(
            "session-1",
            Message::with_text("user", "What are the costs?"),
            None,
        )
        .await
        .unwrap();
    memory
        .store(
            "session-1",
            Message::with_text("assistant", "The fox jumps over the fence"),
            None,
        )
        .await
        .unwrap();

    let messages = memory
        .retrieve(
            "session-1",
            Some("pricing information"),
            2,
            &Default::default(),
        )
        .await
        .unwrap();

    assert_eq!(messages.len(), 2);
    // Should find pricing-related messages first (deterministic based on char similarity)
    assert!(messages[0].content.as_str().unwrap().contains("pricing"));
}

#[tokio::test]
async fn test_retrieve_with_scores() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    memory
        .store(
            "session-1",
            Message::with_text("user", "pricing costs"),
            None,
        )
        .await
        .unwrap();
    memory
        .store("session-1", Message::with_text("user", "hello world"), None)
        .await
        .unwrap();

    let results = memory
        .retrieve_with_scores("session-1", "pricing costs", 2, &Default::default())
        .await
        .unwrap();

    assert_eq!(results.len(), 2);
    assert!(!results[0].1.is_nan(), "Score should not be NaN");
    // Allow small floating point tolerance (epsilon)
    assert!(
        results[0].1 >= -1.001 && results[0].1 <= 1.001,
        "Score should be in range [-1.0, 1.0], got {}",
        results[0].1
    );
    assert!(results[0].1 >= results[1].1); // Sorted by score
}

#[tokio::test]
async fn test_filter_by_importance() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let mut low_importance = HashMap::new();
    low_importance.insert("importance".to_string(), json!(0.3));

    let mut high_importance = HashMap::new();
    high_importance.insert("importance".to_string(), json!(0.9));

    memory
        .store(
            "session-1",
            Message::with_text("user", "Low importance"),
            Some(low_importance),
        )
        .await
        .unwrap();
    memory
        .store(
            "session-1",
            Message::with_text("user", "High importance"),
            Some(high_importance),
        )
        .await
        .unwrap();

    let options = SearchOptions {
        importance_threshold: Some(0.5),
        ..Default::default()
    };

    let messages = memory
        .retrieve("session-1", None, 10, &options)
        .await
        .unwrap();

    assert_eq!(messages.len(), 1);
    assert!(messages[0]
        .content
        .as_str()
        .unwrap()
        .contains("High importance"));
}

#[tokio::test]
async fn test_filter_by_tags() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let mut tagged_metadata = HashMap::new();
    tagged_metadata.insert("tags".to_string(), json!(["urgent", "bug"]));

    let mut other_metadata = HashMap::new();
    other_metadata.insert("tags".to_string(), json!(["feature"]));

    memory
        .store(
            "session-1",
            Message::with_text("user", "Tagged message"),
            Some(tagged_metadata),
        )
        .await
        .unwrap();
    memory
        .store(
            "session-1",
            Message::with_text("user", "Another tag"),
            Some(other_metadata),
        )
        .await
        .unwrap();

    let options = SearchOptions {
        tags: vec!["urgent".to_string()],
        ..Default::default()
    };

    let messages = memory
        .retrieve("session-1", None, 10, &options)
        .await
        .unwrap();

    assert_eq!(messages.len(), 1);
    assert!(messages[0]
        .content
        .as_str()
        .unwrap()
        .contains("Tagged message"));
}

#[tokio::test]
async fn test_filter_by_time_range() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    use std::time::{SystemTime, UNIX_EPOCH};
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64();
    let one_hour_ago = now - 3600.0;
    let one_hour_later = now + 3600.0;

    memory
        .store(
            "session-1",
            Message::with_text("user", "Recent message"),
            None,
        )
        .await
        .unwrap();

    let options = SearchOptions {
        time_range: Some((one_hour_ago, one_hour_later)),
        ..Default::default()
    };

    let messages = memory
        .retrieve("session-1", None, 10, &options)
        .await
        .unwrap();

    assert!(!messages.is_empty());
    assert!(messages[0]
        .content
        .as_str()
        .unwrap()
        .contains("Recent message"));
}

#[tokio::test]
async fn test_combined_filters() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let mut metadata = HashMap::new();
    metadata.insert("importance".to_string(), json!(0.8));
    metadata.insert("tags".to_string(), json!(["critical"]));

    memory
        .store(
            "session-1",
            Message::with_text("user", "Important and tagged"),
            Some(metadata),
        )
        .await
        .unwrap();

    let options = SearchOptions {
        importance_threshold: Some(0.7),
        tags: vec!["critical".to_string()],
        ..Default::default()
    };

    let messages = memory
        .retrieve("session-1", None, 10, &options)
        .await
        .unwrap();

    assert_eq!(messages.len(), 1);
    assert_eq!(messages[0].content, "Important and tagged");
}

#[tokio::test]
async fn test_cosine_similarity_calculation() {
    let _embeddings = Box::new(MockEmbeddingProvider::new(3));
    let store = InMemoryVectorStore::new();

    let embedding1 = vec![1.0, 0.0, 0.0];
    let embedding2 = vec![0.0, 1.0, 0.0];
    let embedding3 = vec![1.0, 0.0, 0.0]; // Same as embedding1

    store
        .add(
            "session-1",
            "msg-1",
            embedding1.clone(),
            Message::with_text("user", "Message 1"),
            HashMap::new(),
            1.0,
        )
        .await
        .unwrap();

    store
        .add(
            "session-1",
            "msg-2",
            embedding2.clone(),
            Message::with_text("user", "Message 2"),
            HashMap::new(),
            2.0,
        )
        .await
        .unwrap();

    store
        .add(
            "session-1",
            "msg-3",
            embedding3.clone(),
            Message::with_text("user", "Message 3"),
            HashMap::new(),
            3.0,
        )
        .await
        .unwrap();

    let results = store
        .search("session-1", embedding1, 3, &Default::default())
        .await
        .unwrap();

    assert_eq!(results.len(), 3);
    // embedding1 and embedding3 are identical, should have score ~1.0
    assert!((results[0].score - 1.0).abs() < 0.01);
    // embedding1 and embedding2 are orthogonal, should have score ~0.0
    assert!((results[2].score - 0.0).abs() < 0.01);
}

#[tokio::test]
async fn test_zero_magnitude_vectors() {
    let _embeddings = Box::new(MockEmbeddingProvider::new(3));
    let store = InMemoryVectorStore::new();

    let zero_vector = vec![0.0, 0.0, 0.0];
    let normal_vector = vec![1.0, 1.0, 1.0];

    store
        .add(
            "session-1",
            "msg-1",
            zero_vector,
            Message::with_text("user", "Zero vector"),
            HashMap::new(),
            1.0,
        )
        .await
        .unwrap();

    let results = store
        .search("session-1", normal_vector, 1, &Default::default())
        .await
        .unwrap();

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].score, 0.0); // Zero magnitude should give 0 similarity
}

#[tokio::test]
async fn test_min_similarity_threshold() {
    let _embeddings = Box::new(MockEmbeddingProvider::new(3));
    let store = InMemoryVectorStore::new();

    let embedding1 = vec![1.0, 0.0, 0.0];
    let embedding2 = vec![0.0, 1.0, 0.0]; // Orthogonal to embedding1

    store
        .add(
            "session-1",
            "msg-1",
            embedding1.clone(),
            Message::with_text("user", "Message 1"),
            HashMap::new(),
            1.0,
        )
        .await
        .unwrap();

    store
        .add(
            "session-1",
            "msg-2",
            embedding2,
            Message::with_text("user", "Message 2"),
            HashMap::new(),
            2.0,
        )
        .await
        .unwrap();

    let options = SearchOptions {
        min_similarity: 0.5,
        ..Default::default()
    };

    let results = store
        .search("session-1", embedding1, 10, &options)
        .await
        .unwrap();

    // Should only get embedding1 (similarity ~1.0), not embedding2 (similarity ~0.0)
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].message.content, "Message 1");
}

#[tokio::test]
async fn test_capabilities() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let capabilities = memory.capabilities();

    assert!(capabilities.contains(&"basic_retrieval"));
    assert!(capabilities.contains(&"semantic_search"));
    assert!(capabilities.contains(&"similarity_retrieval"));
    assert!(capabilities.contains(&"time_filtering"));
    assert!(capabilities.contains(&"importance_filtering"));
    assert!(capabilities.contains(&"tag_filtering"));
}

#[tokio::test]
async fn test_summarization() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    for i in 1..=5 {
        memory
            .store(
                "session-1",
                Message::with_text("user", format!("Message {}: This is some content", i)),
                None,
            )
            .await
            .unwrap();
    }

    let summary = memory.summarize("session-1").await.unwrap();

    assert_eq!(summary.role, "system");
    assert!(summary
        .content
        .as_str()
        .unwrap()
        .contains("Session summary"));
    assert!(summary.content.as_str().unwrap().contains("5 messages"));
}

#[tokio::test]
async fn test_empty_session_summary() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let summary = memory.summarize("empty-session").await.unwrap();

    assert_eq!(summary.role, "system");
    assert_eq!(summary.content, "No messages in session.");
}

#[tokio::test]
async fn test_limit_parameter() {
    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    for i in 1..=20 {
        memory
            .store(
                "session-1",
                Message::with_text("user", format!("Message {}", i)),
                None,
            )
            .await
            .unwrap();
    }

    let messages = memory
        .retrieve("session-1", None, 5, &Default::default())
        .await
        .unwrap();

    assert_eq!(messages.len(), 5);
}

#[tokio::test]
async fn test_euclidean_distance() {
    let store = InMemoryVectorStore::new();

    // Use simple vectors for easy calculation
    // Euclidean distance between [1,0,0] and [0,1,0] is sqrt(2) ≈ 1.414
    // Similarity = 1 / (1 + 1.414) ≈ 0.414
    let embedding1 = vec![1.0, 0.0, 0.0];
    let embedding2 = vec![0.0, 1.0, 0.0];

    store
        .add(
            "session-1",
            "msg-1",
            embedding1.clone(),
            Message::with_text("user", "Message 1"),
            HashMap::new(),
            1.0,
        )
        .await
        .unwrap();

    store
        .add(
            "session-1",
            "msg-2",
            embedding2.clone(),
            Message::with_text("user", "Message 2"),
            HashMap::new(),
            2.0,
        )
        .await
        .unwrap();

    let options = SearchOptions {
        distance_metric: DistanceMetric::Euclidean,
        ..Default::default()
    };

    let results = store
        .search("session-1", embedding1, 2, &options)
        .await
        .unwrap();

    assert_eq!(results.len(), 2);
    // First result should be identical vector (distance 0, similarity 1.0)
    assert!((results[0].score - 1.0).abs() < 0.01);
    // Second result should be orthogonal (distance sqrt(2), similarity ~0.414)
    assert!(results[1].score > 0.3 && results[1].score < 0.5);
}

#[tokio::test]
async fn test_dot_product() {
    let store = InMemoryVectorStore::new();

    // Dot product examples:
    // [1,0,0] · [1,0,0] = 1
    // [1,0,0] · [0,1,0] = 0
    // [1,1,0] · [1,1,0] = 2
    let embedding1 = vec![1.0, 0.0, 0.0];
    let embedding2 = vec![0.0, 1.0, 0.0];
    let embedding3 = vec![1.0, 1.0, 0.0];

    store
        .add(
            "session-1",
            "msg-1",
            embedding1.clone(),
            Message::with_text("user", "Message 1"),
            HashMap::new(),
            1.0,
        )
        .await
        .unwrap();

    store
        .add(
            "session-1",
            "msg-2",
            embedding2.clone(),
            Message::with_text("user", "Message 2"),
            HashMap::new(),
            2.0,
        )
        .await
        .unwrap();

    store
        .add(
            "session-1",
            "msg-3",
            embedding3.clone(),
            Message::with_text("user", "Message 3"),
            HashMap::new(),
            3.0,
        )
        .await
        .unwrap();

    let options = SearchOptions {
        distance_metric: DistanceMetric::DotProduct,
        ..Default::default()
    };

    let results = store
        .search("session-1", embedding1, 3, &options)
        .await
        .unwrap();

    assert_eq!(results.len(), 3);
    // embedding1 · embedding1 = 1.0
    assert!((results[0].score - 1.0).abs() < 0.01);
    // embedding1 · embedding2 = 0.0
    assert!((results[2].score - 0.0).abs() < 0.01);
}

#[tokio::test]
async fn test_distance_metric_selection() {
    let embeddings = Box::new(MockEmbeddingProvider::new(3));
    let memory = VectorMemory::new(embeddings, None);

    // Store a message
    memory
        .store(
            "session-1",
            Message::with_text("user", "test message"),
            None,
        )
        .await
        .unwrap();

    // Test cosine metric (default)
    let cosine_options = SearchOptions {
        distance_metric: DistanceMetric::Cosine,
        ..Default::default()
    };
    let cosine_results = memory
        .retrieve_with_scores("session-1", "test message", 1, &cosine_options)
        .await
        .unwrap();
    assert_eq!(cosine_results.len(), 1);

    // Test euclidean metric
    let euclidean_options = SearchOptions {
        distance_metric: DistanceMetric::Euclidean,
        ..Default::default()
    };
    let euclidean_results = memory
        .retrieve_with_scores("session-1", "test message", 1, &euclidean_options)
        .await
        .unwrap();
    assert_eq!(euclidean_results.len(), 1);

    // Test dot product metric
    let dot_options = SearchOptions {
        distance_metric: DistanceMetric::DotProduct,
        ..Default::default()
    };
    let dot_results = memory
        .retrieve_with_scores("session-1", "test message", 1, &dot_options)
        .await
        .unwrap();
    assert_eq!(dot_results.len(), 1);

    // All metrics should return results (though scores may differ)
    // Use epsilon for floating-point comparisons
    let epsilon = 1e-10;

    assert!(
        !cosine_results[0].1.is_nan(),
        "Cosine score should not be NaN, got {}",
        cosine_results[0].1
    );
    assert!(
        cosine_results[0].1 >= -1.0 - epsilon && cosine_results[0].1 <= 1.0 + epsilon,
        "Cosine score should be in range [-1.0, 1.0] (with epsilon), got {}",
        cosine_results[0].1
    );

    assert!(
        !euclidean_results[0].1.is_nan(),
        "Euclidean score should not be NaN"
    );
    assert!(
        euclidean_results[0].1 >= -epsilon,
        "Euclidean similarity should be non-negative, got {}",
        euclidean_results[0].1
    );

    assert!(
        !dot_results[0].1.is_nan(),
        "Dot product score should not be NaN"
    );
    assert!(
        dot_results[0].1 >= -1.0 - epsilon,
        "Dot product should be >= -1.0 for normalized vectors, got {}",
        dot_results[0].1
    );
}

#[tokio::test]
async fn test_default_cosine_metric() {
    let embeddings = Box::new(MockEmbeddingProvider::new(3));
    let memory = VectorMemory::new(embeddings, None);

    // Store test messages
    memory
        .store(
            "session-1",
            Message::with_text("user", "test message"),
            None,
        )
        .await
        .unwrap();

    // Default SearchOptions should use Cosine metric
    let default_options = SearchOptions::default();
    assert_eq!(default_options.distance_metric, DistanceMetric::Cosine);

    // Retrieve with default options
    let results = memory
        .retrieve_with_scores("session-1", "test message", 1, &default_options)
        .await
        .unwrap();

    assert_eq!(results.len(), 1);
    // Cosine similarity for very similar text should be high
    assert!(results[0].1 > 0.5);
}

#[tokio::test]
async fn test_add_batch() {
    use agenkit::memory::VectorStoreItem;

    let store = InMemoryVectorStore::new();

    let items = vec![
        VectorStoreItem {
            message_id: "msg-1".to_string(),
            embedding: vec![1.0, 0.0, 0.0],
            message: Message::with_text("user", "First message"),
            metadata: HashMap::new(),
            timestamp: 1.0,
        },
        VectorStoreItem {
            message_id: "msg-2".to_string(),
            embedding: vec![0.0, 1.0, 0.0],
            message: Message::with_text("assistant", "Second message"),
            metadata: HashMap::new(),
            timestamp: 2.0,
        },
        VectorStoreItem {
            message_id: "msg-3".to_string(),
            embedding: vec![1.0, 1.0, 0.0],
            message: Message::with_text("user", "Third message"),
            metadata: HashMap::new(),
            timestamp: 3.0,
        },
    ];

    store.add_batch("session-1", items).await.unwrap();

    // Verify all items were added
    let results = store
        .search("session-1", vec![1.0, 0.0, 0.0], 10, &Default::default())
        .await
        .unwrap();

    assert_eq!(results.len(), 3);
}

#[tokio::test]
async fn test_search_batch() {
    let store = InMemoryVectorStore::new();

    // Add test messages
    store
        .add(
            "session-1",
            "msg-1",
            vec![1.0, 0.0, 0.0],
            Message::with_text("user", "Message about programming"),
            HashMap::new(),
            1.0,
        )
        .await
        .unwrap();

    store
        .add(
            "session-1",
            "msg-2",
            vec![0.0, 1.0, 0.0],
            Message::with_text("user", "Message about cooking"),
            HashMap::new(),
            2.0,
        )
        .await
        .unwrap();

    store
        .add(
            "session-1",
            "msg-3",
            vec![0.0, 0.0, 1.0],
            Message::with_text("user", "Message about travel"),
            HashMap::new(),
            3.0,
        )
        .await
        .unwrap();

    // Search with multiple queries
    let query_embeddings = vec![
        vec![1.0, 0.0, 0.0], // Similar to msg-1
        vec![0.0, 1.0, 0.0], // Similar to msg-2
    ];

    let batch_results = store
        .search_batch("session-1", query_embeddings, 1, &Default::default())
        .await
        .unwrap();

    assert_eq!(batch_results.len(), 2);
    assert_eq!(batch_results[0].len(), 1);
    assert_eq!(batch_results[1].len(), 1);

    // First query should find programming message
    assert!(batch_results[0][0]
        .message
        .content
        .as_str()
        .unwrap()
        .contains("programming"));
    // Second query should find cooking message
    assert!(batch_results[1][0]
        .message
        .content
        .as_str()
        .unwrap()
        .contains("cooking"));
}

#[tokio::test]
async fn test_store_batch() {
    use agenkit::memory::StoreBatchItem;

    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let items = vec![
        StoreBatchItem {
            message: Message::with_text("user", "First batch message"),
            metadata: None,
        },
        StoreBatchItem {
            message: Message::with_text("assistant", "Second batch message"),
            metadata: None,
        },
        StoreBatchItem {
            message: Message::with_text("user", "Third batch message"),
            metadata: None,
        },
    ];

    memory.store_batch("session-1", items).await.unwrap();

    // Verify all messages were stored
    let messages = memory
        .retrieve("session-1", None, 10, &Default::default())
        .await
        .unwrap();

    assert_eq!(messages.len(), 3);
    assert!(messages[0]
        .content
        .as_str()
        .unwrap()
        .contains("batch message"));
}

#[tokio::test]
async fn test_empty_batch() {
    use agenkit::memory::StoreBatchItem;

    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    // Store empty batch - should not error
    let items: Vec<StoreBatchItem> = vec![];
    memory.store_batch("session-1", items).await.unwrap();

    // Verify no messages stored
    let messages = memory
        .retrieve("session-1", None, 10, &Default::default())
        .await
        .unwrap();

    assert_eq!(messages.len(), 0);
}

#[tokio::test]
async fn test_batch_metadata_preservation() {
    use agenkit::memory::StoreBatchItem;

    let embeddings = Box::new(MockEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    let mut metadata1 = HashMap::new();
    metadata1.insert("importance".to_string(), json!(0.8));
    metadata1.insert("tags".to_string(), json!(["urgent", "bug"]));

    let mut metadata2 = HashMap::new();
    metadata2.insert("importance".to_string(), json!(0.5));
    metadata2.insert("tags".to_string(), json!(["feature"]));

    let items = vec![
        StoreBatchItem {
            message: Message::with_text("user", "High priority message"),
            metadata: Some(metadata1),
        },
        StoreBatchItem {
            message: Message::with_text("user", "Normal priority message"),
            metadata: Some(metadata2),
        },
    ];

    memory.store_batch("session-1", items).await.unwrap();

    // Filter by importance threshold
    let options = SearchOptions {
        importance_threshold: Some(0.7),
        ..Default::default()
    };

    let messages = memory
        .retrieve("session-1", None, 10, &options)
        .await
        .unwrap();

    // Should only get high priority message
    assert_eq!(messages.len(), 1);
    assert!(messages[0]
        .content
        .as_str()
        .unwrap()
        .contains("High priority"));
}
