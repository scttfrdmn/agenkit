//! Basic observability example.
//!
//! This example demonstrates the simplest setup for observability:
//! - Console-based tracing
//! - Prometheus metrics
//! - JSON logging
//!
//! Run with: cargo run --example observability_basic --features=native

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    configure_logging, init_metrics, init_tracing, log_agent_event, MetricsMiddleware,
    TracingMiddleware,
};
use async_trait::async_trait;

/// Simple echo agent for demonstration
struct EchoAgent {
    name: String,
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, mut message: Message) -> Result<Message, AgentError> {
        // Echo the message back
        message.role = "assistant".to_string();
        Ok(message)
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== Basic Observability Example ===\n");

    // Step 1: Initialize observability components
    println!("Initializing observability...");

    // Initialize tracing with console output
    init_tracing("console", None)?;
    println!("✓ Tracing initialized (console)");

    // Initialize metrics with Prometheus
    init_metrics("prometheus", None)?;
    println!("✓ Metrics initialized (prometheus)");

    // Configure structured logging
    configure_logging("json", "info")?;
    println!("✓ Logging configured (json, info level)\n");

    // Step 2: Create agent with observability middleware
    println!("Creating agent with observability middleware...");
    let agent = EchoAgent {
        name: "echo_agent".to_string(),
    };

    // Wrap with tracing middleware
    let traced_agent = TracingMiddleware::new(agent, None);

    // Wrap with metrics middleware
    let full_agent = MetricsMiddleware::new(traced_agent);
    println!("✓ Agent created with tracing and metrics\n");

    // Step 3: Process some messages
    println!("Processing messages...\n");

    for i in 1..=3 {
        log_agent_event(
            "message_received",
            &format!("Processing message {}", i),
            &[("message_id", &i.to_string())],
        );

        let message = Message::new("user", serde_json::json!(format!("Hello, message {}!", i)));

        match full_agent.process(message).await {
            Ok(response) => {
                log_agent_event(
                    "message_processed",
                    &format!("Successfully processed message {}", i),
                    &[("message_id", &i.to_string())],
                );
                println!("✓ Message {} processed successfully", i);
                println!("  Response role: {}", response.role);
                println!(
                    "  Response content: {}\n",
                    response.content.as_str().unwrap_or("N/A")
                );
            }
            Err(e) => {
                eprintln!("✗ Error processing message {}: {}", i, e);
            }
        }
    }

    println!("=== Example Complete ===");
    println!("\nObservability data:");
    println!("- Traces: Output to console (JSON format)");
    println!("- Metrics: Available at http://localhost:9464/metrics (if Prometheus exporter is configured)");
    println!("- Logs: Output to stdout (JSON format)");

    Ok(())
}
