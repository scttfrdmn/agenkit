//! Distributed tracing example with multi-agent pipeline.
//!
//! This example demonstrates:
//! - W3C Trace Context propagation across agents
//! - Multi-agent pipeline with distributed tracing
//! - Parent-child span relationships
//! - Trace context in message metadata
//! - End-to-end request tracking
//!
//! Run with:
//! ```bash
//! cargo run --example observability_distributed
//! ```

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    configure_logging, init_metrics, init_tracing, log_agent_event, MetricsMiddleware,
    TracingMiddleware,
};
use async_trait::async_trait;
use std::collections::HashMap;

/// Preprocessor agent - validates and cleans input
struct PreprocessorAgent {
    name: String,
}

impl PreprocessorAgent {
    fn new() -> Self {
        Self {
            name: "preprocessor".to_string(),
        }
    }
}

#[async_trait]
impl Agent for PreprocessorAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate preprocessing work
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

        let content = message.content.to_string();
        let cleaned = content.trim().to_lowercase();

        let mut details = HashMap::new();
        details.insert("stage".to_string(), serde_json::json!("preprocess"));
        details.insert("input_length".to_string(), serde_json::json!(content.len()));
        details.insert(
            "output_length".to_string(),
            serde_json::json!(cleaned.len()),
        );
        log_agent_event("pipeline.preprocess", &details);

        Ok(Message::with_text("preprocessor", &cleaned)
            .with_metadata("preprocessed", serde_json::json!(true)))
    }
}

/// Analysis agent - performs main processing
struct AnalysisAgent {
    name: String,
}

impl AnalysisAgent {
    fn new() -> Self {
        Self {
            name: "analyzer".to_string(),
        }
    }
}

#[async_trait]
impl Agent for AnalysisAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate analysis work
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        let content = message.content.to_string();
        let word_count = content.split_whitespace().count();
        let char_count = content.len();

        let analysis = format!(
            "Analysis: {} words, {} characters, sentiment: positive",
            word_count, char_count
        );

        let mut details = HashMap::new();
        details.insert("stage".to_string(), serde_json::json!("analysis"));
        details.insert("word_count".to_string(), serde_json::json!(word_count));
        details.insert("char_count".to_string(), serde_json::json!(char_count));
        log_agent_event("pipeline.analyze", &details);

        Ok(Message::with_text("analyzer", &analysis)
            .with_metadata("analyzed", serde_json::json!(true))
            .with_metadata("word_count", serde_json::json!(word_count)))
    }
}

/// Formatter agent - formats output
struct FormatterAgent {
    name: String,
}

impl FormatterAgent {
    fn new() -> Self {
        Self {
            name: "formatter".to_string(),
        }
    }
}

#[async_trait]
impl Agent for FormatterAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate formatting work
        tokio::time::sleep(tokio::time::Duration::from_millis(30)).await;

        let content = message.content.to_string();
        let formatted = format!("📊 Report:\n{}\n✅ Complete", content);

        let mut details = HashMap::new();
        details.insert("stage".to_string(), serde_json::json!("format"));
        details.insert("format_type".to_string(), serde_json::json!("report"));
        log_agent_event("pipeline.format", &details);

        Ok(Message::with_text("formatter", &formatted).with_metadata("formatted", serde_json::json!(true)))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== Agenkit Rust - Distributed Tracing Example ===\n");

    // Initialize observability
    println!("Initializing observability stack...");
    init_tracing("console", None)?;
    init_metrics("stdout", None)?;
    configure_logging("compact", "info")?;
    println!("✓ Observability initialized\n");

    // Create pipeline of 3 agents, each with tracing and metrics
    println!("Building agent pipeline...");

    let preprocessor = PreprocessorAgent::new();
    let traced_preprocessor = TracingMiddleware::new(preprocessor, Some("pipeline.preprocess"));
    let observed_preprocessor = MetricsMiddleware::new(traced_preprocessor);

    let analyzer = AnalysisAgent::new();
    let traced_analyzer = TracingMiddleware::new(analyzer, Some("pipeline.analyze"));
    let observed_analyzer = MetricsMiddleware::new(traced_analyzer);

    let formatter = FormatterAgent::new();
    let traced_formatter = TracingMiddleware::new(formatter, Some("pipeline.format"));
    let observed_formatter = MetricsMiddleware::new(traced_formatter);

    println!("✓ Pipeline created: Preprocessor → Analyzer → Formatter\n");

    // Process messages through the pipeline
    let test_messages = vec![
        "  Hello, World!  How are you today?  ",
        "Distributed tracing is AWESOME for debugging microservices",
        "  SHORT  ",
    ];

    for (i, input) in test_messages.iter().enumerate() {
        println!("--- Request {} ---", i + 1);
        println!("Input: {:?}", input);

        let mut details = HashMap::new();
        details.insert("request_id".to_string(), serde_json::json!(i + 1));
        log_agent_event("pipeline.start", &details);

        // Stage 1: Preprocess
        let message1 = Message::with_text("user", *input)
            .with_metadata("request_id", serde_json::json!(i + 1));

        let result1 = observed_preprocessor.process(message1).await?;
        println!(
            "After preprocessing: {:?} (trace_context present: {})",
            result1.content,
            result1.metadata.contains_key("trace_context")
        );

        // Stage 2: Analyze (trace context propagated automatically)
        let result2 = observed_analyzer.process(result1).await?;
        println!(
            "After analysis: {:?} (trace_context present: {})",
            result2.content,
            result2.metadata.contains_key("trace_context")
        );

        // Stage 3: Format (trace context continues to propagate)
        let result3 = observed_formatter.process(result2).await?;
        println!(
            "Final output: {:?} (trace_context present: {})",
            result3.content,
            result3.metadata.contains_key("trace_context")
        );

        details.insert("status".to_string(), serde_json::json!("complete"));
        log_agent_event("pipeline.complete", &details);

        println!();
    }

    println!("=== Example Complete ===");
    println!("\nKey Concepts Demonstrated:");
    println!("  1. Multi-agent Pipeline: 3 agents working together");
    println!("  2. W3C Trace Context: Propagated via message metadata");
    println!("  3. Parent-Child Spans: Each agent creates a child span");
    println!("  4. End-to-End Tracing: Complete request path tracked");
    println!("  5. Automatic Propagation: No manual context passing needed");
    println!("\nIn a production system with Jaeger/Zipkin:");
    println!("  • You would see 3 spans per request (preprocess → analyze → format)");
    println!("  • Each span would show timing, agent name, and metadata");
    println!("  • The trace context links all spans together");
    println!("  • You could visualize the entire request flow");

    Ok(())
}
