//! Basic Vector Memory Example
//!
//! Demonstrates vector memory with a simple mock embedding provider.
//! Perfect for learning and testing without external dependencies.
//!
//! Run: cargo run --example vector_memory_basic

use agenkit::core::{AgentError, Message};
use agenkit::memory::{EmbeddingProvider, SearchOptions, VectorMemory};
use async_trait::async_trait;
use serde_json::json;
use std::collections::HashMap;

/// Simple embedding provider for demonstration.
/// Uses character frequencies to create embeddings.
struct SimpleEmbeddingProvider {
    dimension: usize,
}

impl SimpleEmbeddingProvider {
    fn new(dimension: usize) -> Self {
        Self { dimension }
    }
}

#[async_trait]
impl EmbeddingProvider for SimpleEmbeddingProvider {
    async fn embed(&self, text: &str) -> Result<Vec<f64>, AgentError> {
        // Create embedding based on character frequencies
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
    println!("=== Basic Vector Memory Example ===\n");

    // Initialize vector memory with simple embeddings
    println!("1. Initialize vector memory with simple embeddings\n");
    let embeddings = Box::new(SimpleEmbeddingProvider::new(10));
    let memory = VectorMemory::new(embeddings, None);

    println!("   Embedding dimension: {}", memory.capabilities().len());
    println!("   Capabilities: {:?}\n", memory.capabilities());

    // Store some messages
    println!("2. Store conversation messages\n");

    let session_id = "demo-session";

    let messages = vec![
        Message::with_text("user", "Hello! How are you today?"),
        Message::with_text("assistant", "Hello! I am doing well, thank you for asking."),
        Message::with_text("user", "What is machine learning?"),
        Message::with_text(
            "assistant",
            "Machine learning is a subset of AI that enables systems to learn from data.",
        ),
        Message::with_text("user", "Tell me about neural networks."),
        Message::with_text(
            "assistant",
            "Neural networks are computing systems inspired by biological neural networks.",
        ),
    ];

    for msg in messages {
        memory.store(session_id, msg.clone(), None).await?;
        let content = msg.content.as_str().unwrap_or("");
        println!("   ✓ {}: {}...", msg.role, &content[..content.len().min(50)]);
    }

    // Basic retrieval (most recent)
    println!("\n3. Basic retrieval (most recent)\n");

    let recent_messages = memory
        .retrieve(session_id, None, 3, &Default::default())
        .await?;

    println!("   Retrieved {} most recent messages:", recent_messages.len());
    for msg in &recent_messages {
        let content = msg.content.as_str().unwrap_or("");
        println!("   - [{}] {}", msg.role, &content[..content.len().min(60)]);
    }

    // Semantic search
    println!("\n4. Semantic search\n");

    let query = "artificial intelligence and learning";
    println!("   Query: \"{}\"\n", query);

    let search_results = memory
        .retrieve(session_id, Some(query), 2, &Default::default())
        .await?;

    println!("   Top results:");
    for msg in &search_results {
        let content = msg.content.as_str().unwrap_or("");
        println!("   - [{}] {}", msg.role, &content[..content.len().min(60)]);
    }

    // Retrieve with similarity scores
    println!("\n5. Retrieve with similarity scores\n");

    let scored_results = memory
        .retrieve_with_scores(session_id, "neural networks", 3, &Default::default())
        .await?;

    println!("   Results with scores:");
    for (msg, score) in &scored_results {
        let content = msg.content.as_str().unwrap_or("");
        println!(
            "   - [{}] (score: {:.3}) {}",
            msg.role,
            score,
            &content[..content.len().min(50)]
        );
    }

    // Store messages with metadata
    println!("\n6. Store messages with metadata\n");

    let mut important_metadata = HashMap::new();
    important_metadata.insert("importance".to_string(), json!(0.9));
    important_metadata.insert("tags".to_string(), json!(["production", "critical"]));

    memory
        .store(
            session_id,
            Message::with_text("user", "Important question about production deployment"),
            Some(important_metadata),
        )
        .await?;

    let mut casual_metadata = HashMap::new();
    casual_metadata.insert("importance".to_string(), json!(0.1));
    casual_metadata.insert("tags".to_string(), json!(["casual"]));

    memory
        .store(
            session_id,
            Message::with_text("user", "Random casual comment"),
            Some(casual_metadata),
        )
        .await?;

    println!("   ✓ Stored 2 messages with metadata\n");

    // Filter by importance
    println!("7. Filter by importance\n");

    let options = SearchOptions {
        importance_threshold: Some(0.7),
        ..Default::default()
    };

    let important_messages = memory.retrieve(session_id, None, 10, &options).await?;

    println!(
        "   Found {} high-importance messages:",
        important_messages.len()
    );
    for msg in &important_messages {
        let content = msg.content.as_str().unwrap_or("");
        println!("   - {}", &content[..content.len().min(60)]);
    }

    // Filter by tags
    println!("\n8. Filter by tags\n");

    let options = SearchOptions {
        tags: vec!["production".to_string()],
        ..Default::default()
    };

    let tagged_messages = memory.retrieve(session_id, None, 10, &options).await?;

    println!(
        "   Found {} messages tagged \"production\":",
        tagged_messages.len()
    );
    for msg in &tagged_messages {
        let content = msg.content.as_str().unwrap_or("");
        println!("   - {}", &content[..content.len().min(60)]);
    }

    // Generate session summary
    println!("\n9. Generate session summary\n");

    let summary = memory.summarize(session_id).await?;
    let summary_content = summary.content.as_str().unwrap_or("");
    println!("   {}\n", summary_content);

    // Clear session
    println!("10. Clear session\n");
    memory.clear(session_id).await?;
    println!("   ✓ Session cleared\n");

    let empty_check = memory
        .retrieve(session_id, None, 10, &Default::default())
        .await?;
    println!("   Messages remaining: {}\n", empty_check.len());

    println!("=== Example Complete ===\n");

    Ok(())
}
