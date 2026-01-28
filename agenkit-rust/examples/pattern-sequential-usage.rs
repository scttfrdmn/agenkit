//! Sequential Pattern Usage Example
//!
//! Pipeline-style agent composition where each agent's output feeds the next
//!
//! Use cases:
//! - Multi-stage data transformation
//! - Document processing
//! - Step-by-step refinement
//!
//! Run: cargo run --example pattern-sequential-usage

use agenkit::core::{Agent, Message};
use agenkit::patterns::sequential::*;
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

        Ok(Message::new(
            "agent",
            format!("{} processed: {}", self.name, message.content()),
        ))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    println!("=== Sequential Pattern Demo ===\n");

    let agent1 = SimpleAgent::new("Agent1");
    let agent2 = SimpleAgent::new("Agent2");
    let agent3 = SimpleAgent::new("Agent3");

    // Create pattern (adjust based on pattern type)
    // let pattern = SequentialAgent::new(...)?;

    println!("\n✅ Sequential pattern example");
    println!("\nNote: This is a minimal template.");
    println!("See Python examples for complete implementations.");

    Ok(())
}
