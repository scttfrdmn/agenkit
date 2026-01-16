//! Distributed tracing example.
//!
//! This example demonstrates trace context propagation across multiple agents:
//! - Multiple agents processing messages
//! - Trace context propagation via message metadata
//! - Parent-child span relationships
//! - Distributed tracing visualization
//!
//! Run with: cargo run --example observability_distributed --features=native

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    configure_logging, init_metrics, init_tracing, log_agent_event, MetricsMiddleware,
    TracingMiddleware,
};
use async_trait::async_trait;

/// Router agent that forwards messages to other agents
struct RouterAgent {
    name: String,
}

#[async_trait]
impl Agent for RouterAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, mut message: Message) -> Result<Message, AgentError> {
        // Router adds routing metadata
        message
            .metadata
            .insert("routed_by".to_string(), serde_json::json!(self.name));
        message.role = "routed".to_string();
        Ok(message)
    }
}

/// Processing agent that handles the actual work
struct ProcessorAgent {
    name: String,
}

#[async_trait]
impl Agent for ProcessorAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, mut message: Message) -> Result<Message, AgentError> {
        // Simulate some processing
        tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;

        message
            .metadata
            .insert("processed_by".to_string(), serde_json::json!(self.name));
        message.role = "assistant".to_string();
        Ok(message)
    }
}

/// Aggregator agent that combines results
struct AggregatorAgent {
    name: String,
}

#[async_trait]
impl Agent for AggregatorAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, mut message: Message) -> Result<Message, AgentError> {
        // Aggregate results
        message
            .metadata
            .insert("aggregated_by".to_string(), serde_json::json!(self.name));
        message.role = "final".to_string();
        Ok(message)
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== Distributed Tracing Example ===\n");

    // Initialize observability
    println!("Initializing observability...");
    init_tracing("console", None)?;
    init_metrics("prometheus", None)?;
    configure_logging("json", "info")?;
    println!("✓ Observability initialized\n");

    // Create a distributed agent pipeline
    println!("Creating distributed agent pipeline:");
    println!("  1. Router → 2. Processor → 3. Aggregator\n");

    // Create agents with observability middleware
    let router = RouterAgent {
        name: "router".to_string(),
    };
    let router = TracingMiddleware::new(router, Some("router_span".to_string()));
    let router = MetricsMiddleware::new(router);

    let processor = ProcessorAgent {
        name: "processor".to_string(),
    };
    let processor = TracingMiddleware::new(processor, Some("processor_span".to_string()));
    let processor = MetricsMiddleware::new(processor);

    let aggregator = AggregatorAgent {
        name: "aggregator".to_string(),
    };
    let aggregator = TracingMiddleware::new(aggregator, Some("aggregator_span".to_string()));
    let aggregator = MetricsMiddleware::new(aggregator);

    // Process multiple messages through the pipeline
    println!("Processing messages through the distributed pipeline...\n");

    for i in 1..=3 {
        log_agent_event(
            "pipeline_start",
            &format!("Starting pipeline for message {}", i),
            &[("message_id", &i.to_string())],
        );

        // Create initial message
        let message = Message::new("user", serde_json::json!(format!("Request {}", i)));

        // Step 1: Router
        println!("Message {} → Router", i);
        let message = router.process(message).await?;
        println!(
            "  ✓ Routed (trace context: {})",
            message.metadata.contains_key("traceparent")
        );

        // Step 2: Processor
        println!("Message {} → Processor", i);
        let message = processor.process(message).await?;
        println!(
            "  ✓ Processed (trace context: {})",
            message.metadata.contains_key("traceparent")
        );

        // Step 3: Aggregator
        println!("Message {} → Aggregator", i);
        let message = aggregator.process(message).await?;
        println!(
            "  ✓ Aggregated (trace context: {})",
            message.metadata.contains_key("traceparent")
        );

        log_agent_event(
            "pipeline_complete",
            &format!("Completed pipeline for message {}", i),
            &[("message_id", &i.to_string())],
        );

        println!("  Final role: {}\n", message.role);
    }

    println!("=== Example Complete ===");
    println!("\nDistributed tracing features demonstrated:");
    println!("- ✓ Trace context propagation across 3 agents");
    println!("- ✓ Parent-child span relationships");
    println!("- ✓ End-to-end request tracing");
    println!("- ✓ Per-agent metrics collection");
    println!("\nView traces in the console output (JSON format)");
    println!("Look for 'parentSpanId' fields to see span relationships");

    Ok(())
}
