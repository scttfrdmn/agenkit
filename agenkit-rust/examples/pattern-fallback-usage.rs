//! Fallback Pattern Usage Example
//!
//! Sequential retry across multiple agents with automatic failover
//!
//! Use cases:
//! - Resilient service calls
//! - Multi-provider fallback
//! - Error recovery
//!
//! Run: cargo run --example pattern-fallback-usage

use agenkit::core::{Agent, Message};
use agenkit::patterns::fallback::*;
use async_trait::async_trait;
use std::error::Error;

struct SimpleAgent {
    name: String,
}

impl SimpleAgent {
    fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
        }
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

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error>> {
        println!("   🤖 {} processing...", self.name);
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        Ok(Message::new(
            "agent",
            format!("{} processed: {}", self.name, message.content()),
        ))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    println!("=== Fallback Pattern Demo ===\n");

    let agent1 = SimpleAgent::new("Agent1");
    let agent2 = SimpleAgent::new("Agent2");
    let agent3 = SimpleAgent::new("Agent3");

    // Create pattern (adjust based on pattern type)
    // let pattern = FallbackAgent::new(...)?;

    println!("\n✅ Fallback pattern example");
    println!("\nNote: This is a minimal template.");
    println!("See Python examples for complete implementations.");

    Ok(())
}
