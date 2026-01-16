//! Reflection Pattern Example
//!
//! Demonstrates the Reflection pattern for iterative self-critique and refinement.
//! Uses mock agents to simulate a generator and critic working together.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{CritiqueFormat, ReflectionAgent, ReflectionConfig};
use async_trait::async_trait;
use std::sync::Arc;

/// Simple generator that adds iteration markers
struct SimpleGenerator;

#[async_trait]
impl Agent for SimpleGenerator {
    fn name(&self) -> &str {
        "SimpleGenerator"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");

        // Simulate generation/refinement
        let response = if content.contains("refine") {
            // This is a refinement request
            format!(
                "Refined version: improved and enhanced {}",
                content
                    .split("Previous Output")
                    .nth(1)
                    .and_then(|s| s.split("Critique:").next())
                    .unwrap_or("output")
            )
        } else {
            // Initial generation
            format!("Generated output for: {}", content)
        };

        Ok(Message::with_text("assistant", response))
    }
}

/// Simple critic that provides improving scores
struct SimpleCritic {
    iteration: std::sync::Mutex<usize>,
}

#[async_trait]
impl Agent for SimpleCritic {
    fn name(&self) -> &str {
        "SimpleCritic"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let mut iter = self.iteration.lock().unwrap();
        *iter += 1;

        // Gradually improve scores
        let score = match *iter {
            1 => 0.5,
            2 => 0.75,
            _ => 0.95,
        };

        let critique = serde_json::json!({
            "score": score,
            "feedback": format!("Quality is improving. Score: {}", score)
        });

        Ok(Message::with_text(
            "assistant",
            serde_json::to_string(&critique).unwrap(),
        ))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🔄 Reflection Pattern Example\n");

    // Create generator and critic agents
    let generator = Arc::new(SimpleGenerator);
    let critic = Arc::new(SimpleCritic {
        iteration: std::sync::Mutex::new(0),
    });

    // Configure reflection agent
    let config = ReflectionConfig {
        generator,
        critic,
        max_iterations: 5,
        quality_threshold: 0.9,
        improvement_threshold: 0.05,
        critique_format: CritiqueFormat::Structured,
        verbose: true,
    };

    let reflection_agent = ReflectionAgent::new(config)?;

    // Process a request
    println!("📝 Initial request: Write a function to calculate fibonacci numbers");
    let message = Message::with_text("user", "Write a function to calculate fibonacci numbers");

    let result = reflection_agent.process(message).await?;

    // Display results
    println!(
        "\n✅ Final output: {}",
        result.content_as_str().unwrap_or("")
    );
    println!("\n📊 Reflection Metadata:");
    println!(
        "   Iterations: {}",
        result.metadata.get("reflection_iterations").unwrap()
    );
    println!(
        "   Final score: {}",
        result.metadata.get("final_quality_score").unwrap()
    );
    println!(
        "   Stop reason: {}",
        result.metadata.get("stop_reason").unwrap()
    );
    println!(
        "   Total improvement: {}",
        result.metadata.get("total_improvement").unwrap()
    );

    if let Some(history) = result.metadata.get("reflection_history") {
        println!("\n📈 Reflection History:");
        if let Some(steps) = history.as_array() {
            for step in steps {
                println!(
                    "   Iteration {}: Score = {}, Improvement = {}",
                    step["iteration"], step["quality_score"], step["improvement"]
                );
            }
        }
    }

    println!("\n✨ Reflection complete!");

    Ok(())
}
