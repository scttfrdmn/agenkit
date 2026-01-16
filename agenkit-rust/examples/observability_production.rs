//! Production observability example.
//!
//! This example demonstrates a production-ready observability setup:
//! - OTLP tracing (for Jaeger/Tempo)
//! - Prometheus metrics
//! - Structured JSON logging
//! - Audit logging for compliance
//! - Error handling and monitoring
//!
//! Run with: cargo run --example observability_production --features=native

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    audit::{AuditEvent, AuditEventType, AuditLogger, Severity},
    configure_logging, init_metrics, init_tracing, log_agent_error, log_agent_event,
    log_agent_warning, MetricsMiddleware, TracingMiddleware,
};
use async_trait::async_trait;
use std::path::PathBuf;
use std::sync::Arc;

/// Production agent with comprehensive error handling
struct ProductionAgent {
    name: String,
    audit_logger: Arc<AuditLogger>,
}

impl ProductionAgent {
    fn new(name: String, audit_logger: Arc<AuditLogger>) -> Self {
        Self { name, audit_logger }
    }
}

#[async_trait]
impl Agent for ProductionAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, mut message: Message) -> Result<Message, AgentError> {
        // Log message received to audit
        let _ = self
            .audit_logger
            .log(AuditEvent::new(
                AuditEventType::MessageProcessed,
                self.name.clone(),
                message
                    .metadata
                    .get("session_id")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string()),
            ))
            .await;

        // Simulate processing with potential errors
        let content = message.content.as_str().unwrap_or("");

        if content.contains("error") {
            // Simulate an error condition
            let error = AgentError::ProcessingError("Simulated error condition".to_string());

            // Log error to audit
            let _ = self
                .audit_logger
                .log(
                    AuditEvent::new(
                        AuditEventType::ErrorOccurred,
                        self.name.clone(),
                        message
                            .metadata
                            .get("session_id")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string()),
                    )
                    .with_severity(Severity::Error)
                    .with_detail("error_type".to_string(), serde_json::json!("processing")),
                )
                .await;

            return Err(error);
        }

        if content.contains("warn") {
            // Log warning condition
            log_agent_warning(
                "high_processing_time",
                "Processing time exceeded threshold",
                &[("threshold_ms", "1000"), ("actual_ms", "1500")],
            );

            let _ = self
                .audit_logger
                .log(
                    AuditEvent::new(
                        AuditEventType::SystemEvent,
                        self.name.clone(),
                        message
                            .metadata
                            .get("session_id")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string()),
                    )
                    .with_severity(Severity::Warning)
                    .with_detail("event".to_string(), serde_json::json!("high_latency")),
                )
                .await;
        }

        // Simulate processing delay
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

        // Successful processing
        message.role = "assistant".to_string();
        Ok(message)
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== Production Observability Example ===\n");

    // Step 1: Initialize all observability components
    println!("Initializing production observability stack...");

    // Use OTLP for production (fallback to console if OTLP endpoint not available)
    match init_tracing("otlp", Some("http://localhost:4317")) {
        Ok(_) => println!("✓ Tracing: OTLP exporter to http://localhost:4317"),
        Err(_) => {
            init_tracing("console", None)?;
            println!("✓ Tracing: Console exporter (OTLP endpoint not available)");
        }
    }

    // Initialize Prometheus metrics
    init_metrics("prometheus", None)?;
    println!("✓ Metrics: Prometheus (available at http://localhost:9464/metrics)");

    // Configure structured JSON logging for production
    configure_logging("json", "info")?;
    println!("✓ Logging: JSON format, info level");

    // Initialize audit logging
    let audit_log_path = PathBuf::from("/tmp/agenkit_audit.log");
    let audit_logger = Arc::new(AuditLogger::with_buffer_size(audit_log_path.clone(), 50)?);
    println!(
        "✓ Audit: Logging to {:?} (buffer size: 50)\n",
        audit_log_path
    );

    // Step 2: Create production agent with full observability
    println!("Creating production agent with full observability...");

    let agent = ProductionAgent::new("production_agent".to_string(), Arc::clone(&audit_logger));

    // Log agent creation to audit
    audit_logger
        .log(AuditEvent::new(
            AuditEventType::AgentCreated,
            agent.name().to_string(),
            None,
        ))
        .await?;

    // Wrap with observability middleware
    let traced_agent = TracingMiddleware::new(agent, Some("production_span".to_string()));
    let full_agent = MetricsMiddleware::new(traced_agent);
    println!("✓ Agent created with tracing, metrics, and audit logging\n");

    // Step 3: Simulate production workload
    println!("Simulating production workload...\n");

    let test_cases = vec![
        ("session-1", "Normal request"),
        ("session-2", "Request with warn flag"),
        ("session-3", "Request with error condition"),
        ("session-4", "Another normal request"),
    ];

    for (session_id, content) in test_cases {
        log_agent_event(
            "request_received",
            &format!("Processing request: {}", content),
            &[("session_id", session_id)],
        );

        // Create message with session context
        let mut message = Message::new("user", serde_json::json!(content));
        message
            .metadata
            .insert("session_id".to_string(), serde_json::json!(session_id));

        // Process message
        match full_agent.process(message).await {
            Ok(response) => {
                log_agent_event(
                    "request_completed",
                    "Request processed successfully",
                    &[("session_id", session_id)],
                );
                println!("✓ {} - SUCCESS", session_id);
                println!("  Content: {}", content);
                println!("  Response: {}\n", response.role);
            }
            Err(e) => {
                log_agent_error(
                    "request_failed",
                    "Request processing failed",
                    &e.to_string(),
                );
                println!("✗ {} - ERROR", session_id);
                println!("  Content: {}", content);
                println!("  Error: {}\n", e);
            }
        }
    }

    // Step 4: Flush audit logs and query
    println!("Flushing audit logs...");
    audit_logger.flush().await?;
    println!("✓ Audit logs flushed to disk\n");

    // Query audit logs for analysis
    println!("Analyzing audit logs...");
    let all_events = audit_logger.query(None).await?;
    println!("  Total events: {}", all_events.len());

    let errors = audit_logger
        .query_by_type(AuditEventType::ErrorOccurred)
        .await?;
    println!("  Errors: {}", errors.len());

    let messages = audit_logger
        .query_by_type(AuditEventType::MessageProcessed)
        .await?;
    println!("  Messages processed: {}", messages.len());

    // Query by session
    let session_1_events = audit_logger.query_by_session("session-1").await?;
    println!("  Events for session-1: {}", session_1_events.len());

    println!("\n=== Example Complete ===");
    println!("\nProduction observability features demonstrated:");
    println!("- ✓ Distributed tracing with OTLP");
    println!("- ✓ Prometheus metrics collection");
    println!("- ✓ Structured JSON logging");
    println!("- ✓ Audit logging for compliance");
    println!("- ✓ Error tracking and monitoring");
    println!("- ✓ Warning detection");
    println!("- ✓ Session-based tracking");
    println!("\nData locations:");
    println!("- Traces: http://localhost:4317 (OTLP) or console");
    println!("- Metrics: http://localhost:9464/metrics (Prometheus)");
    println!("- Logs: stdout (JSON format)");
    println!("- Audit: {:?}", audit_log_path);

    Ok(())
}
