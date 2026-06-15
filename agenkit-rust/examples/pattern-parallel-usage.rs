//! Parallel Pattern Usage Example
//!
//! Concurrent execution of multiple agents with result aggregation
//!
//! Use cases:
//! - Ensemble methods
//! - Multi-perspective analysis
//! - Independent parallel tasks
//!
//! Run: cargo run --example pattern-parallel-usage

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::parallel::*;
use async_trait::async_trait;
use std::error::Error;

struct SimpleAgent {
    name: String,
}

impl SimpleAgent {
    fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

#[async_trait]
impl Agent for SimpleAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["demo".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        println!("   🤖 {} processing...", self.name);
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        let content_str = message.content_as_str().unwrap_or("");
        Ok(Message::with_text(
            "agent",
            format!("{} processed: {}", self.name, content_str),
        ))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    println!("=== Parallel Pattern Demo ===\n");

    let _agent1 = SimpleAgent::new("Agent1");
    let _agent2 = SimpleAgent::new("Agent2");
    let _agent3 = SimpleAgent::new("Agent3");

    // Create pattern (adjust based on pattern type)
    // let pattern = ParallelAgent::new(...)?;

    println!("\n✅ Parallel pattern example");
    println!("\nNote: This is a minimal template.");
    println!("See Python examples for complete implementations.");

    Ok(())
}
