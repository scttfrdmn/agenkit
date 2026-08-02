//! Redis Memory Example - Rust
//!
//! Demonstrates Redis-backed persistent memory for production deployments.
//!
//! Prerequisites:
//!   docker run -d -p 6379:6379 redis:7-alpine
//!
//! Features:
//! - Persistent storage (survives restarts)
//! - TTL support (automatic expiry)
//! - Multi-instance agents (shared memory)
//! - Filtering (time, importance, tags)
//! - Utilities (session management, stats)

use agenkit::memory::RedisMemory;
use anyhow::Result;
use std::collections::HashMap;

async fn basic_usage() -> Result<()> {
    println!("{}", "=".repeat(60));
    println!("Basic Redis Memory Usage");
    println!("{}", "=".repeat(60));

    // Create Redis memory with 24-hour TTL
    let memory = RedisMemory::new(
        "redis://localhost:6379",
        86400, // 24 hours
        "agenkit:demo",
    )
    .await?;

    let session_id = "demo-session-1";

    // Store messages with metadata
    println!("\n📝 Storing messages...");
    let mut metadata = HashMap::new();
    metadata.insert("importance".to_string(), serde_json::json!(0.8));
    metadata.insert(
        "tags".to_string(),
        serde_json::json!(["question", "technical"]),
    );

    memory
        .store(session_id, "user", "What is Redis?", Some(metadata.clone()))
        .await?;

    memory
        .store(
            session_id,
            "assistant",
            "Redis is an in-memory data structure store used as a database, cache, and message broker.",
            Some({
                let mut m = HashMap::new();
                m.insert("importance".to_string(), serde_json::json!(0.9));
                m.insert("tags".to_string(), serde_json::json!(["answer", "technical"]));
                m
            }),
        )
        .await?;

    memory
        .store(
            session_id,
            "user",
            "Thanks!",
            Some({
                let mut m = HashMap::new();
                m.insert("importance".to_string(), serde_json::json!(0.5));
                m.insert("tags".to_string(), serde_json::json!(["gratitude"]));
                m
            }),
        )
        .await?;

    // Retrieve recent messages
    println!("\n📤 Retrieving recent messages...");
    let messages = memory.retrieve(session_id, 3, None, None, None).await?;

    for msg in &messages {
        println!("[{}] {}", msg.role, msg.content);
    }

    // Get session count
    let count = memory.get_session_count(session_id).await?;
    println!("\n📊 Session has {} messages", count);

    Ok(())
}

async fn filtering_example() -> Result<()> {
    println!("\n{}", "=".repeat(60));
    println!("Filtering Example");
    println!("{}", "=".repeat(60));

    let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:filter").await?;

    let session_id = "filter-demo";

    // Store messages with different importance and tags
    println!("\n📝 Storing messages with metadata...");

    let messages = vec![
        ("Hello", 0.3, vec!["greeting"]),
        ("Can you help with Redis?", 0.8, vec!["question", "redis"]),
        ("How do I scale it?", 0.9, vec!["question", "scaling"]),
        ("Thanks!", 0.2, vec!["gratitude"]),
    ];

    for (content, importance, tags) in messages {
        let mut metadata = HashMap::new();
        metadata.insert("importance".to_string(), serde_json::json!(importance));
        metadata.insert("tags".to_string(), serde_json::json!(tags));

        memory
            .store(session_id, "user", content, Some(metadata))
            .await?;
    }

    // Filter by importance
    println!("\n🔍 High-importance messages (>0.5):");
    let important = memory
        .retrieve(session_id, 10, None, Some(0.5), None)
        .await?;
    for msg in &important {
        println!("  {}", msg.content);
    }

    // Filter by tags
    println!("\n🔍 Question messages:");
    let questions = memory
        .retrieve(
            session_id,
            10,
            None,
            None,
            Some(vec!["question".to_string()]),
        )
        .await?;
    for msg in &questions {
        println!("  {}", msg.content);
    }

    // Combined filtering
    println!("\n🔍 Important questions:");
    let important_questions = memory
        .retrieve(
            session_id,
            10,
            None,
            Some(0.8),
            Some(vec!["question".to_string()]),
        )
        .await?;
    for msg in &important_questions {
        println!("  {}", msg.content);
    }

    Ok(())
}

async fn multi_session_example() -> Result<()> {
    println!("\n{}", "=".repeat(60));
    println!("Multi-Session Example");
    println!("{}", "=".repeat(60));

    let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:multi").await?;

    // Simulate multiple user sessions
    println!("\n👥 Creating multiple sessions...");
    memory
        .store("user-alice", "user", "Hello from Alice", None)
        .await?;
    memory
        .store("user-bob", "user", "Hello from Bob", None)
        .await?;
    memory
        .store("user-charlie", "user", "Hello from Charlie", None)
        .await?;

    // List all sessions
    println!("\n📋 All sessions:");
    let sessions = memory.get_all_sessions().await?;
    for session in &sessions {
        let count = memory.get_session_count(session).await?;
        println!("  {}: {} messages", session, count);
    }

    // Get usage statistics
    println!("\n📊 Memory usage:");
    let (total_sessions, total_messages, ttl) = memory.get_memory_usage().await?;
    println!("  Total sessions: {}", total_sessions);
    println!("  Total messages: {}", total_messages);
    println!("  TTL: {} seconds ({} hours)", ttl, ttl / 3600);

    Ok(())
}

async fn summarization_example() -> Result<()> {
    println!("\n{}", "=".repeat(60));
    println!("Summarization Example");
    println!("{}", "=".repeat(60));

    let memory = RedisMemory::new("redis://localhost:6379", 86400, "agenkit:summary").await?;

    let session_id = "conversation";

    // Simulate a long conversation
    println!("\n💬 Simulating conversation...");
    let conversation = vec![
        ("user", "What is Redis?"),
        ("assistant", "Redis is an in-memory database..."),
        ("user", "How fast is it?"),
        ("assistant", "Redis can handle millions of ops/sec..."),
        ("user", "Is it persistent?"),
        ("assistant", "Yes, Redis supports persistence..."),
    ];

    for (role, content) in conversation {
        memory.store(session_id, role, content, None).await?;
    }

    // Get summary
    println!("\n📝 Conversation summary:");
    let summary = memory.summarize(session_id).await?;
    println!("{}", summary.content);

    Ok(())
}

async fn production_example() -> Result<()> {
    println!("\n{}", "=".repeat(60));
    println!("Production Deployment Example");
    println!("{}", "=".repeat(60));

    // Production configuration
    let redis_url =
        std::env::var("REDIS_URL").unwrap_or_else(|_| "redis://localhost:6379".to_string());
    let memory = RedisMemory::new(&redis_url, 7 * 24 * 3600, "prod:agenkit:memory").await?;

    println!("\n✅ Production features:");
    println!("  • Persistent storage (survives restarts)");
    println!("  • 7-day TTL (automatic cleanup)");
    println!("  • Multi-instance support (shared memory)");
    println!("  • Filtering (time, importance, tags)");
    println!("  • Session management utilities");

    let capabilities = memory.capabilities();
    println!("\n🎯 Capabilities:");
    for capability in capabilities {
        println!("  • {}", capability);
    }

    println!("\n💡 Use cases:");
    println!("  • Long-running agents (persist across restarts)");
    println!("  • Multi-instance deployments (shared state)");
    println!("  • Session recovery (restore after failure)");
    println!("  • Conversation history (queryable archive)");

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Run all examples
    if let Err(e) = basic_usage().await {
        if e.to_string().contains("Connection refused") {
            eprintln!("\n❌ Error: Redis connection refused");
            eprintln!("Please start Redis: docker run -d -p 6379:6379 redis:7-alpine");
            std::process::exit(1);
        }
        return Err(e);
    }

    filtering_example().await?;
    multi_session_example().await?;
    summarization_example().await?;
    production_example().await?;

    println!("\n{}", "=".repeat(60));
    println!("✅ All examples completed!");
    println!("{}", "=".repeat(60));

    Ok(())
}
