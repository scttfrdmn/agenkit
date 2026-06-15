//! Basic observability example with console exporters.
//!
//! This example demonstrates:
//! - Setting up tracing with console exporter
//! - Setting up metrics with stdout exporter
//! - Configuring structured logging
//! - Using TracingMiddleware and MetricsMiddleware
//! - Basic audit logging
//!
//! Run with:
//! ```bash
//! cargo run --example observability_basic
//! ```

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    configure_logging, init_metrics, init_tracing, log_agent_event, AuditEvent, AuditEventType,
    AuditLogger, MetricsMiddleware, TracingMiddleware,
};
use async_trait::async_trait;
use std::collections::HashMap;
use tempfile::TempDir;

/// Simple echo agent for demonstration
struct EchoAgent {
    name: String,
}

impl EchoAgent {
    fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
        }
    }
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Echo back the message with a prefix
        let response = format!("Echo: {}", message.content);
        Ok(Message::with_text("assistant", &response))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== Agenkit Rust - Basic Observability Example ===\n");

    // Step 1: Initialize tracing with console exporter
    println!("1. Initializing distributed tracing...");
    init_tracing("console", None)?;
    println!("   ✓ Tracing initialized (console exporter)\n");

    // Step 2: Initialize metrics with stdout exporter
    println!("2. Initializing metrics...");
    init_metrics("stdout", None)?;
    println!("   ✓ Metrics initialized (stdout exporter)\n");

    // Step 3: Configure structured logging
    println!("3. Configuring structured logging...");
    configure_logging("pretty", "info")?;
    println!("   ✓ Logging configured (pretty format, info level)\n");

    // Step 4: Set up audit logging
    println!("4. Setting up audit logging...");
    let temp_dir = TempDir::new()?;
    let audit_path = temp_dir.path().join("audit.log");
    let audit_logger = AuditLogger::new(audit_path.clone());
    println!("   ✓ Audit logger created: {:?}\n", audit_path);

    // Step 5: Create agent with observability middleware
    println!("5. Creating instrumented agent...");
    let agent = EchoAgent::new("echo-agent");
    let traced_agent = TracingMiddleware::new(agent, None);
    let observed_agent = MetricsMiddleware::new(traced_agent);
    println!("   ✓ Agent wrapped with TracingMiddleware and MetricsMiddleware\n");

    // Step 6: Log agent creation
    let audit_event = AuditEvent::new(
        AuditEventType::AgentCreated,
        "echo-agent".to_string(),
        Some("demo-session".to_string()),
    );
    audit_logger.log(audit_event).await?;

    // Step 7: Process messages
    println!("6. Processing messages with full observability...\n");

    let messages = vec!["Hello, World!", "How are you?", "Testing observability"];

    for (i, content) in messages.iter().enumerate() {
        println!("   Message {}: \"{}\"", i + 1, content);

        // Log the event
        let mut details = HashMap::new();
        details.insert("message_id".to_string(), serde_json::json!(i + 1));
        details.insert("content".to_string(), serde_json::json!(content));
        log_agent_event("message.processing", &details);

        // Process the message (tracing span created automatically)
        let message = Message::with_text("user", *content);
        let response = observed_agent.process(message).await?;

        println!("   Response: \"{}\"", response.content_as_str().unwrap_or(""));

        // Log audit event
        let audit_event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            "echo-agent".to_string(),
            Some("demo-session".to_string()),
        );
        audit_logger.log(audit_event).await?;

        println!();
    }

    // Step 8: Flush audit logs
    println!("7. Flushing audit logs...");
    audit_logger.flush().await?;
    println!("   ✓ Audit logs written to disk\n");

    // Step 9: Query audit events
    println!("8. Querying audit events...");
    let events = audit_logger
        .query(Some("demo-session".to_string()))
        .await?;
    println!("   ✓ Found {} audit events for session 'demo-session'", events.len());

    for (i, event) in events.iter().enumerate() {
        println!(
            "     Event {}: {:?} - {} at {}",
            i + 1,
            event.event_type,
            event.agent_name,
            event.timestamp.format("%Y-%m-%d %H:%M:%S")
        );
    }

    println!("\n=== Example Complete ===");
    println!("This example demonstrated:");
    println!("  • Distributed tracing with OpenTelemetry");
    println!("  • Metrics collection (request counts, durations)");
    println!("  • Structured logging with trace correlation");
    println!("  • Audit logging with session tracking");
    println!("\nAll observability data was captured during agent execution!");

    Ok(())
}
