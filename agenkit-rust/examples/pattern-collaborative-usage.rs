//! Collaborative Pattern Usage Example
//!
//! Peer-to-peer collaboration with iterative refinement
//!
//! Use cases:
//! - Peer review
//! - Consensus building
//! - Iterative refinement
//!
//! Run: cargo run --example pattern-collaborative-usage

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::collaborative::*;
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

        Ok(Message::with_text(
            "agent",
            format!("{} processed: {}", self.name, message.content_as_str().unwrap_or("")),
        ))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    println!("=== Collaborative Pattern Demo ===\n");

    let agent1 = SimpleAgent::new("Agent1");
    let agent2 = SimpleAgent::new("Agent2");
    let agent3 = SimpleAgent::new("Agent3");

    // Create pattern (adjust based on pattern type)
    // let pattern = CollaborativeAgent::new(...)?;

    println!("\n✅ Collaborative pattern example");
    println!("\nNote: This is a minimal template.");
    println!("See Python examples for complete implementations.");

    Ok(())
}
