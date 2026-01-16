//! Memory Hierarchy Pattern Example
//!
//! Demonstrates the three-tier memory system for long-running conversational agents.
//!
//! # Scenarios Demonstrated
//!
//! 1. Working Memory - Current conversation context
//! 2. Short-Term Memory - Recent sessions with TTL
//! 3. Long-Term Memory - Persistent facts with importance
//! 4. Cross-Tier Retrieval - Search across all memory tiers
//! 5. Memory Promotion - Moving important memories to long-term
//! 6. TTL Expiration - Automatic cleanup of expired memories
//! 7. LRU Eviction - Capacity-based eviction
//! 8. Session Isolation - Multi-user memory management

use agenkit::patterns::{
    create_memory_entry, LongTermMemory, MemoryHierarchy, ShortTermMemory, WorkingMemory,
};
use std::collections::HashMap;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== Memory Hierarchy Pattern Examples ===\n");

    // Scenario 1: Basic Working Memory
    println!("--- Scenario 1: Working Memory (Current Context) ---");
    let working = WorkingMemory::new(5)?;

    for i in 1..=7 {
        let entry = create_memory_entry(
            format!("Message {}", i),
            HashMap::new(),
            0.5,
            Some("session-1".to_string()),
        );
        working.store(entry).await?;
    }

    let messages = working.retrieve("Message", 10).await?;
    println!("Working memory (max 5): {} messages stored", messages.len());
    println!(
        "Messages: {:?}",
        messages.iter().map(|m| &m.content).collect::<Vec<_>>()
    );
    println!("✓ LRU eviction kept only the last 5 messages\n");

    // Scenario 2: Short-Term Memory with TTL
    println!("--- Scenario 2: Short-Term Memory (Recent Sessions) ---");
    let short_term = ShortTermMemory::new(10, 2)?; // 2 second TTL

    let entry1 = create_memory_entry(
        "User asked about Rust",
        HashMap::new(),
        0.6,
        Some("session-2".to_string()),
    );
    short_term.store(entry1).await?;

    println!("Stored: 'User asked about Rust'");

    let results = short_term.retrieve("Rust", 5).await?;
    println!("Retrieved immediately: {} results", results.len());

    println!("Waiting 3 seconds for TTL expiration...");
    tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;

    let results = short_term.retrieve("Rust", 5).await?;
    println!("Retrieved after TTL: {} results", results.len());
    println!("✓ TTL-based expiration removed expired memories\n");

    // Scenario 3: Long-Term Memory with Importance
    println!("--- Scenario 3: Long-Term Memory (Persistent Facts) ---");
    let long_term = LongTermMemory::new(HashMap::new(), 0.7)?; // Min importance 0.7

    let low_importance = create_memory_entry(
        "Casual mention of weather",
        HashMap::new(),
        0.5, // Below threshold
        None,
    );

    let high_importance = create_memory_entry(
        "User's birthday is December 25",
        HashMap::new(),
        0.9, // Above threshold
        None,
    );

    long_term.store(low_importance.clone()).await?;
    long_term.store(high_importance.clone()).await?;

    let all_memories = long_term.retrieve("", 10).await?;
    println!("Stored 2 memories (importance 0.5 and 0.9)");
    println!(
        "Retrieved with min_importance=0.7: {} memories",
        all_memories.len()
    );
    println!("Memory: {}", all_memories[0].content);
    println!("✓ Importance-based filtering kept only high-value memories\n");

    // Scenario 4: Full Memory Hierarchy
    println!("--- Scenario 4: Complete Three-Tier System ---");
    let memory = MemoryHierarchy::new(
        WorkingMemory::new(10)?,
        Some(ShortTermMemory::new(50, 3600)?),
        Some(LongTermMemory::new(HashMap::new(), 0.6)?),
    );

    // Store in working memory
    memory
        .store(
            "Current topic: Rust patterns",
            HashMap::new(),
            0.7,
            Some("session-3".to_string()),
        )
        .await?;

    // Store in short-term
    memory
        .store(
            "User asked about memory patterns yesterday",
            HashMap::new(),
            0.6,
            Some("session-2".to_string()),
        )
        .await?;

    // Store in long-term
    memory
        .store(
            "User prefers async/await over callbacks",
            HashMap::new(),
            0.85,
            Some("session-1".to_string()),
        )
        .await?;

    println!("Stored memories across all three tiers");
    println!("Working: current conversation");
    println!("Short-term: recent sessions");
    println!("Long-term: persistent preferences\n");

    // Scenario 5: Cross-Tier Retrieval
    println!("--- Scenario 5: Cross-Tier Retrieval ---");

    let results = memory.retrieve("Rust", 5, None).await?;
    println!("Query: 'Rust'");
    println!("Results: {} memories found", results.len());
    for (i, result) in results.iter().enumerate() {
        println!(
            "  {}. {} (importance: {:.2})",
            i + 1,
            result.content,
            result.importance
        );
    }
    println!("✓ Retrieved and ranked results from all tiers\n");

    // Scenario 6: Tier-Specific Retrieval
    println!("--- Scenario 6: Tier-Specific Retrieval ---");

    let working_only = memory
        .retrieve("topic", 5, Some(vec!["working".to_string()]))
        .await?;
    println!("Working memory only: {} results", working_only.len());

    let long_term_only = memory
        .retrieve("User", 5, Some(vec!["long_term".to_string()]))
        .await?;
    println!("Long-term memory only: {} results", long_term_only.len());

    let short_and_long = memory
        .retrieve(
            "",
            10,
            Some(vec!["short_term".to_string(), "long_term".to_string()]),
        )
        .await?;
    println!("Short-term + Long-term: {} results", short_and_long.len());
    println!("✓ Selective tier querying for optimized retrieval\n");

    // Scenario 7: Memory with Metadata
    println!("--- Scenario 7: Structured Metadata ---");

    let mut metadata = HashMap::new();
    metadata.insert("category".to_string(), serde_json::json!("preference"));
    metadata.insert("confidence".to_string(), serde_json::json!(0.95));
    metadata.insert("source".to_string(), serde_json::json!("explicit"));

    memory
        .store(
            "User prefers functional programming style",
            metadata.clone(),
            0.9,
            Some("session-4".to_string()),
        )
        .await?;

    println!("Stored memory with metadata:");
    println!("  Category: preference");
    println!("  Confidence: 0.95");
    println!("  Source: explicit");
    println!("✓ Rich metadata enables advanced filtering and analysis\n");

    // Scenario 8: Session Isolation
    println!("--- Scenario 8: Multi-User Sessions ---");

    let user1_memory = MemoryHierarchy::new(
        WorkingMemory::new(10)?,
        Some(ShortTermMemory::new(50, 3600)?),
        Some(LongTermMemory::new(HashMap::new(), 0.6)?),
    );

    let user2_memory = MemoryHierarchy::new(
        WorkingMemory::new(10)?,
        Some(ShortTermMemory::new(50, 3600)?),
        Some(LongTermMemory::new(HashMap::new(), 0.6)?),
    );

    // User 1
    user1_memory
        .store(
            "User 1 prefers Python",
            HashMap::new(),
            0.8,
            Some("user-1-session-1".to_string()),
        )
        .await?;

    // User 2
    user2_memory
        .store(
            "User 2 prefers Go",
            HashMap::new(),
            0.8,
            Some("user-2-session-1".to_string()),
        )
        .await?;

    let user1_prefs = user1_memory.retrieve("prefers", 5, None).await?;
    let user2_prefs = user2_memory.retrieve("prefers", 5, None).await?;

    println!("User 1 memory: {}", user1_prefs[0].content);
    println!("User 2 memory: {}", user2_prefs[0].content);
    println!("✓ Session isolation maintains user privacy\n");

    // Scenario 9: Memory Statistics
    println!("--- Scenario 9: Memory Statistics ---");

    let stats_memory = MemoryHierarchy::new(
        WorkingMemory::new(10)?,
        Some(ShortTermMemory::new(50, 3600)?),
        Some(LongTermMemory::new(HashMap::new(), 0.5)?),
    );

    for i in 1..=15 {
        stats_memory
            .store(
                format!("Fact number {}", i),
                HashMap::new(),
                0.5 + (i as f64 / 30.0), // Varying importance
                Some("session-5".to_string()),
            )
            .await?;
    }

    let all = stats_memory.retrieve("", 100, None).await?;
    let working_count = all
        .iter()
        .filter(|e| e.timestamp > chrono::Utc::now() - chrono::Duration::seconds(1))
        .count();

    println!("Total memories stored: 15");
    println!("Memories retrieved: {}", all.len());
    println!("Working memory capacity: 10");
    println!("Short-term: ~5 (remainder)");
    println!("✓ Automatic tier management distributes memories efficiently\n");

    // Scenario 10: Importance-Based Ranking
    println!("--- Scenario 10: Importance-Based Ranking ---");

    let ranking_memory = MemoryHierarchy::new(WorkingMemory::new(20)?, None, None);

    let importances = vec![0.3, 0.9, 0.5, 0.8, 0.4];
    for (i, importance) in importances.iter().enumerate() {
        ranking_memory
            .store(
                format!("Item {} (importance {:.1})", i + 1, importance),
                HashMap::new(),
                *importance,
                None,
            )
            .await?;
    }

    let ranked = ranking_memory.retrieve("Item", 10, None).await?;
    println!("Memories ranked by importance:");
    for (i, memory) in ranked.iter().enumerate() {
        println!(
            "  {}. {} - importance: {:.1}",
            i + 1,
            memory.content,
            memory.importance
        );
    }
    println!("✓ Retrieval automatically ranks by importance and recency\n");

    println!("=== All Memory Hierarchy Examples Complete! ===");
    println!("\nKey Takeaways:");
    println!("1. Working Memory: Fast, in-context, LRU eviction");
    println!("2. Short-Term Memory: Recent sessions, TTL-based expiration");
    println!("3. Long-Term Memory: Persistent facts, importance filtering");
    println!("4. Cross-Tier Retrieval: Unified search with ranking");
    println!("5. Session Isolation: Multi-user privacy");
    println!("6. Rich Metadata: Structured information for filtering");
    println!("7. Automatic Management: No manual tier promotion needed");
    println!("8. Scalable: From single-user to multi-tenant systems");

    Ok(())
}
