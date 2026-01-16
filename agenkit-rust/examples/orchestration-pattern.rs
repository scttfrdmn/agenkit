//! Orchestration Pattern Example
//!
//! Demonstrates Sequential and Parallel orchestration patterns.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{ParallelPattern, SequentialPattern};
use async_trait::async_trait;
use std::sync::Arc;

/// Agent that validates input
struct ValidatorAgent;

#[async_trait]
impl Agent for ValidatorAgent {
    fn name(&self) -> &str {
        "Validator"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        println!("   🔍 Validator: Checking input...");
        let validated = format!("✓ Validated: {}", content);
        Ok(Message::with_text("assistant", validated))
    }
}

/// Agent that processes data
struct ProcessorAgent;

#[async_trait]
impl Agent for ProcessorAgent {
    fn name(&self) -> &str {
        "Processor"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        println!("   ⚙️  Processor: Processing data...");
        let processed = format!("⚙️  Processed: {}", content);
        Ok(Message::with_text("assistant", processed))
    }
}

/// Agent that formats output
struct FormatterAgent;

#[async_trait]
impl Agent for FormatterAgent {
    fn name(&self) -> &str {
        "Formatter"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        println!("   📝 Formatter: Formatting output...");
        let formatted = format!("📄 Formatted:\n   {}", content);
        Ok(Message::with_text("assistant", formatted))
    }
}

/// Agent that reviews from perspective A
struct ReviewerA;

#[async_trait]
impl Agent for ReviewerA {
    fn name(&self) -> &str {
        "ReviewerA"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        println!("   👤 Reviewer A: Analyzing from security perspective...");
        let review = format!(
            "🔒 Security Review:\n\
             Input: {}\n\
             Assessment: Looks secure, no vulnerabilities detected",
            content
        );
        Ok(Message::with_text("assistant", review))
    }
}

/// Agent that reviews from perspective B
struct ReviewerB;

#[async_trait]
impl Agent for ReviewerB {
    fn name(&self) -> &str {
        "ReviewerB"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        println!("   👥 Reviewer B: Analyzing from performance perspective...");
        let review = format!(
            "⚡ Performance Review:\n\
             Input: {}\n\
             Assessment: Efficient, good performance characteristics",
            content
        );
        Ok(Message::with_text("assistant", review))
    }
}

/// Agent that reviews from perspective C
struct ReviewerC;

#[async_trait]
impl Agent for ReviewerC {
    fn name(&self) -> &str {
        "ReviewerC"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        println!("   👨‍👩‍👧 Reviewer C: Analyzing from usability perspective...");
        let review = format!(
            "🎨 Usability Review:\n\
             Input: {}\n\
             Assessment: User-friendly, intuitive design",
            content
        );
        Ok(Message::with_text("assistant", review))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🎭 Orchestration Pattern Example\n");

    // Example 1: Sequential Pattern
    println!("{}", "=".repeat(60));
    println!("📋 Sequential Pattern: validator → processor → formatter");
    println!("{}", "=".repeat(60));

    let validator = Arc::new(ValidatorAgent);
    let processor = Arc::new(ProcessorAgent);
    let formatter = Arc::new(FormatterAgent);

    let pipeline = SequentialPattern::new(vec![validator, processor, formatter])?;

    println!("\n➡️  Input: User registration data");
    let message = Message::with_text("user", "User registration data");
    let result = pipeline.process(message).await?;

    println!("\n✅ Final Output:");
    println!("{}", result.content_as_str().unwrap_or(""));

    // Example 2: Parallel Pattern
    println!("\n\n{}", "=".repeat(60));
    println!("📋 Parallel Pattern: Multiple reviewers in parallel");
    println!("{}", "=".repeat(60));

    let reviewer_a = Arc::new(ReviewerA);
    let reviewer_b = Arc::new(ReviewerB);
    let reviewer_c = Arc::new(ReviewerC);

    let parallel = ParallelPattern::new(vec![reviewer_a, reviewer_b, reviewer_c])?;

    println!("\n➡️  Input: Code changes for review");
    let message = Message::with_text("user", "Code changes for review");
    let result = parallel.process(message).await?;

    println!("\n✅ Primary Result (first reviewer):");
    println!("{}", result.content_as_str().unwrap_or(""));

    println!("\n📊 All Parallel Results:");
    if let Some(parallel_results) = result.metadata.get("parallel_results") {
        if let Some(results_array) = parallel_results.as_array() {
            for (i, result) in results_array.iter().enumerate() {
                println!(
                    "\n   Result {} from {}:",
                    i + 1,
                    result
                        .get("role")
                        .and_then(|r| r.as_str())
                        .unwrap_or("unknown")
                );
                if let Some(content) = result.get("content") {
                    for line in content.as_str().unwrap_or("").lines() {
                        println!("      {}", line);
                    }
                }
            }
        }
    }

    // Example 3: Composed Patterns (Sequential of Parallel)
    println!("\n\n{}", "=".repeat(60));
    println!("📋 Composed Pattern: Sequential pipeline with parallel review");
    println!("{}", "=".repeat(60));

    // First stage: sequential validation and processing
    let stage1_validator = Arc::new(ValidatorAgent);
    let stage1_processor = Arc::new(ProcessorAgent);
    let stage1 =
        SequentialPattern::with_name(vec![stage1_validator, stage1_processor], "stage1_prep")?;

    // Second stage: parallel review
    let stage2_reviewer_a = Arc::new(ReviewerA);
    let stage2_reviewer_b = Arc::new(ReviewerB);
    let stage2_reviewer_c = Arc::new(ReviewerC);
    let stage2 = ParallelPattern::with_name(
        vec![stage2_reviewer_a, stage2_reviewer_b, stage2_reviewer_c],
        "stage2_review",
    )?;

    // Third stage: final formatting
    let stage3 = Arc::new(FormatterAgent);

    // Compose into final pipeline
    let composed_pipeline = SequentialPattern::new(vec![
        Arc::new(stage1) as Arc<dyn Agent>,
        Arc::new(stage2) as Arc<dyn Agent>,
        stage3,
    ])?;

    println!("\n➡️  Input: Feature implementation");
    let message = Message::with_text("user", "Feature implementation");
    let result = composed_pipeline.process(message).await?;

    println!("\n✅ Final Composed Output:");
    println!("{}", result.content_as_str().unwrap_or(""));

    println!("\n✨ Orchestration examples complete!");
    println!("\n💡 Key takeaways:");
    println!("   - Sequential: Simple pipelines, output → input chaining");
    println!("   - Parallel: Concurrent execution, aggregate results");
    println!("   - Composable: Patterns can contain other patterns");

    Ok(())
}
