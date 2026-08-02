//! Production Vector Memory Example
//!
//! Demonstrates production-ready vector memory patterns including:
//! - Mock embeddings (real embeddings would use OpenAI or similar)
//! - Distance metrics (cosine, euclidean, dot product)
//! - Batch operations for efficiency
//! - Performance optimization strategies
//! - Metadata filtering and importance scoring
//!
//! Run: cargo run --example vector_memory_production

use agenkit::core::Message;
use agenkit::memory::{
    DistanceMetric, EmbeddingProvider, SearchOptions, StoreBatchItem, VectorMemory,
};
use agenkit::AgentError;
use async_trait::async_trait;
use std::collections::HashMap;
use std::time::Instant;

/// Mock embedding provider for demonstration.
///
/// In production, replace with OpenAI, Anthropic, or similar service.
struct MockEmbeddings {
    dimension: usize,
}

impl MockEmbeddings {
    fn new(dimension: usize) -> Self {
        Self { dimension }
    }
}

#[async_trait]
impl EmbeddingProvider for MockEmbeddings {
    async fn embed(&self, text: &str) -> Result<Vec<f64>, AgentError> {
        // Simple character-based embedding for demo
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

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    println!("=== Production Vector Memory Example ===\n");

    // ====================================================================
    // Part 1: Initialize Vector Memory
    // ====================================================================
    println!("1. Initialize vector memory system\n");

    let embeddings = Box::new(MockEmbeddings::new(128));
    let memory = VectorMemory::new(embeddings, None);

    println!("   Embedding dimension: 128");
    println!("   Vector store: InMemory");
    println!("   Distance metrics: Cosine (default), Euclidean, Dot Product\n");

    let session_id = "production-session";

    // ====================================================================
    // Part 2: Batch Operations for Efficiency
    // ====================================================================
    println!("2. Batch storage for efficient bulk operations\n");

    let documents = vec![
        StoreBatchItem {
            message: Message::with_text("user", "What is the capital of France?"),
            metadata: Some({
                let mut map = HashMap::new();
                map.insert("importance".to_string(), serde_json::json!(0.5));
                map.insert(
                    "tags".to_string(),
                    serde_json::json!(["geography", "europe"]),
                );
                map
            }),
        },
        StoreBatchItem {
            message: Message::with_text("assistant", "The capital of France is Paris."),
            metadata: Some({
                let mut map = HashMap::new();
                map.insert("importance".to_string(), serde_json::json!(0.5));
                map.insert(
                    "tags".to_string(),
                    serde_json::json!(["geography", "europe"]),
                );
                map
            }),
        },
        StoreBatchItem {
            message: Message::with_text(
                "user",
                "How do I implement a binary search tree in Python?",
            ),
            metadata: Some({
                let mut map = HashMap::new();
                map.insert("importance".to_string(), serde_json::json!(0.8));
                map.insert(
                    "tags".to_string(),
                    serde_json::json!(["programming", "algorithms"]),
                );
                map
            }),
        },
        StoreBatchItem {
            message: Message::with_text(
                "assistant",
                "A binary search tree can be implemented using a Node class with left, right, \
                 and value attributes. Each node maintains the BST property: left < parent < right.",
            ),
            metadata: Some({
                let mut map = HashMap::new();
                map.insert("importance".to_string(), serde_json::json!(0.8));
                map.insert(
                    "tags".to_string(),
                    serde_json::json!(["programming", "algorithms"]),
                );
                map
            }),
        },
        StoreBatchItem {
            message: Message::with_text("user", "What are the health benefits of exercise?"),
            metadata: Some({
                let mut map = HashMap::new();
                map.insert("importance".to_string(), serde_json::json!(0.6));
                map.insert("tags".to_string(), serde_json::json!(["health", "fitness"]));
                map
            }),
        },
        StoreBatchItem {
            message: Message::with_text(
                "assistant",
                "Regular exercise improves cardiovascular health, strengthens muscles, \
                 boosts mental health, and helps maintain a healthy weight.",
            ),
            metadata: Some({
                let mut map = HashMap::new();
                map.insert("importance".to_string(), serde_json::json!(0.6));
                map.insert("tags".to_string(), serde_json::json!(["health", "fitness"]));
                map
            }),
        },
        StoreBatchItem {
            message: Message::with_text("user", "Explain quantum entanglement."),
            metadata: Some({
                let mut map = HashMap::new();
                map.insert("importance".to_string(), serde_json::json!(0.9));
                map.insert("tags".to_string(), serde_json::json!(["physics", "quantum"]));
                map
            }),
        },
        StoreBatchItem {
            message: Message::with_text(
                "assistant",
                "Quantum entanglement is a phenomenon where particles become correlated \
                 such that the quantum state of one particle cannot be described independently.",
            ),
            metadata: Some({
                let mut map = HashMap::new();
                map.insert("importance".to_string(), serde_json::json!(0.9));
                map.insert("tags".to_string(), serde_json::json!(["physics", "quantum"]));
                map
            }),
        },
    ];

    println!("   Storing {} messages in batch...", documents.len());
    let start = Instant::now();

    memory.store_batch(session_id, documents).await?;

    let elapsed = start.elapsed();
    println!("   ✓ Batch storage completed in {:?}", elapsed);
    println!(
        "   Average: {:.1}ms per message\n",
        elapsed.as_millis() as f64 / 8.0
    );

    // ====================================================================
    // Part 3: Distance Metrics Comparison
    // ====================================================================
    println!("3. Compare distance metrics for semantic search\n");

    let query = "computer science data structures";
    println!("   Query: \"{}\"\n", query);

    // Cosine similarity (default - best for text)
    println!("   a) Cosine Similarity (default):");
    let cosine_options = SearchOptions {
        distance_metric: DistanceMetric::Cosine,
        ..Default::default()
    };
    let cosine_results = memory
        .retrieve_with_scores(session_id, query, 3, &cosine_options)
        .await?;

    for (msg, score) in &cosine_results {
        let content = msg.content.as_str().unwrap();
        let preview = if content.len() > 50 {
            format!("{}...", &content[..50])
        } else {
            content.to_string()
        };
        println!("      - ({:.3}) {}", score, preview);
    }

    // Euclidean distance
    println!("\n   b) Euclidean Distance:");
    let euclidean_options = SearchOptions {
        distance_metric: DistanceMetric::Euclidean,
        ..Default::default()
    };
    let euclidean_results = memory
        .retrieve_with_scores(session_id, query, 3, &euclidean_options)
        .await?;

    for (msg, score) in &euclidean_results {
        let content = msg.content.as_str().unwrap();
        let preview = if content.len() > 50 {
            format!("{}...", &content[..50])
        } else {
            content.to_string()
        };
        println!("      - ({:.3}) {}", score, preview);
    }

    // Dot product
    println!("\n   c) Dot Product:");
    let dot_options = SearchOptions {
        distance_metric: DistanceMetric::DotProduct,
        ..Default::default()
    };
    let dot_results = memory
        .retrieve_with_scores(session_id, query, 3, &dot_options)
        .await?;

    for (msg, score) in &dot_results {
        let content = msg.content.as_str().unwrap();
        let preview = if content.len() > 50 {
            format!("{}...", &content[..50])
        } else {
            content.to_string()
        };
        println!("      - ({:.3}) {}", score, preview);
    }

    println!("\n   → Cosine similarity typically works best for text embeddings\n");

    // ====================================================================
    // Part 4: Advanced Filtering with Semantic Search
    // ====================================================================
    println!("4. Advanced filtering: semantic + importance + tags\n");

    let search_query = "scientific concepts and theories";
    println!("   Query: \"{}\"", search_query);
    println!("   Filters: importance >= 0.8, tags include \"physics\" or \"programming\"\n");

    let filtered_options = SearchOptions {
        importance_threshold: Some(0.8),
        tags: vec!["physics".to_string(), "programming".to_string()],
        distance_metric: DistanceMetric::Cosine,
        ..Default::default()
    };

    let filtered_results = memory
        .retrieve_with_scores(session_id, search_query, 5, &filtered_options)
        .await?;

    println!("   Found {} matching results:", filtered_results.len());
    for (msg, score) in &filtered_results {
        let content = msg.content.as_str().unwrap();
        let preview = if content.len() > 60 {
            format!("{}...", &content[..60])
        } else {
            content.to_string()
        };
        println!("   - (score: {:.3}) {}", score, preview);
    }

    // ====================================================================
    // Part 5: Production Best Practices
    // ====================================================================
    println!("\n5. Production best practices\n");

    println!("   ✓ Batch operations: Use store_batch() for bulk inserts");
    println!("   ✓ Distance metrics: Choose based on your use case");
    println!("     - Cosine: Text/NLP (most common)");
    println!("     - Euclidean: Spatial data, images");
    println!("     - Dot product: Pre-normalized vectors");
    println!("   ✓ Metadata: Tag messages for efficient filtering");
    println!("   ✓ Importance: Prioritize critical information");
    println!("   ✓ Time ranges: Filter by recency for temporal data");
    println!("   ✓ Persistent storage: Use external DB for production");

    // ====================================================================
    // Part 6: Performance Analysis
    // ====================================================================
    println!("\n6. Performance analysis\n");

    println!("   Messages stored: 8");
    println!("   Embedding dimension: 128");
    println!("   Batch storage time: {:?}", elapsed);
    println!(
        "   Storage efficiency: {:.1}ms per message",
        elapsed.as_millis() as f64 / 8.0
    );

    println!("\n   Performance tips:");
    println!("   • Batch operations reduce overhead and improve throughput");
    println!("   • Use appropriate distance metric for your domain");
    println!("   • Index metadata fields for faster filtering");
    println!("   • Consider dimensionality reduction for very large datasets");
    println!("   • Use persistent storage (PostgreSQL, ChromaDB) for production");

    // ====================================================================
    // Part 7: Integration Guidance
    // ====================================================================
    println!("\n7. Production integration guidance\n");

    println!("   For real embeddings, integrate with:");
    println!("   • OpenAI: text-embedding-3-small (1536d, $0.02/1M tokens)");
    println!("   • Anthropic: Claude embeddings via API");
    println!("   • Local models: sentence-transformers, BERT variants");
    println!();
    println!("   For persistent storage, integrate with:");
    println!("   • PostgreSQL with pgvector extension");
    println!("   • ChromaDB (open-source vector database)");
    println!("   • Pinecone (managed vector database)");
    println!("   • Qdrant (high-performance vector search)");

    // Cleanup
    println!("\n8. Cleanup\n");
    memory.clear(session_id).await?;
    println!("   ✓ Session cleared\n");

    println!("=== Example Complete ===\n");
    println!("Key Takeaways:");
    println!("• Use batch operations for better performance");
    println!("• Choose the right distance metric for your domain");
    println!("• Combine semantic search with metadata filtering");
    println!("• Use persistent storage for production deployments");
    println!("• Monitor performance and optimize batch sizes\n");

    Ok(())
}
