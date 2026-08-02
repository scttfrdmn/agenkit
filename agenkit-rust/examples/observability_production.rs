//! Production-ready observability setup with OTLP exporters.
//!
//! This example demonstrates:
//! - OTLP exporters for tracing and metrics
//! - JSON structured logging for production
//! - Comprehensive audit logging
//! - Error handling and monitoring
//! - Production configuration patterns
//!
//! Prerequisites:
//! 1. Run an OpenTelemetry Collector or Jaeger:
//!    ```bash
//!    docker run -d --name jaeger \
//!      -p 4317:4317 \
//!      -p 16686:16686 \
//!      jaegertracing/all-in-one:latest
//!    ```
//!
//! 2. Run this example:
//!    ```bash
//!    cargo run --example observability_production
//!    ```
//!
//! 3. View traces at http://localhost:16686

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    configure_logging, init_metrics, init_tracing, init_tracing_with_config, log_agent_error,
    log_agent_event, AuditEvent, AuditEventType, AuditLogger, AuditSeverity, MetricsMiddleware,
    TracingMiddleware,
};
use async_trait::async_trait;
use std::collections::HashMap;
use std::env;
use std::path::PathBuf;

/// Production agent with error handling
struct ProductionAgent {
    name: String,
    fail_rate: f64, // Simulate occasional failures
}

impl ProductionAgent {
    fn new(name: &str, fail_rate: f64) -> Self {
        Self {
            name: name.to_string(),
            fail_rate,
        }
    }
}

#[async_trait]
impl Agent for ProductionAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate work
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

        // Simulate occasional failures
        if rand::random::<f64>() < self.fail_rate {
            return Err(AgentError::ProcessingError(format!(
                "Simulated failure in {}",
                self.name
            )));
        }

        let response = format!("Processed by {}: {}", self.name, message.content);
        Ok(Message::with_text("assistant", &response))
    }
}

/// Production configuration from environment
struct Config {
    otlp_endpoint: String,
    metrics_endpoint: String,
    service_name: String,
    sample_rate: f64,
    log_level: String,
    audit_path: PathBuf,
}

impl Config {
    fn from_env() -> Self {
        Self {
            otlp_endpoint: env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
                .unwrap_or_else(|_| "http://localhost:4317".to_string()),
            metrics_endpoint: env::var("OTEL_EXPORTER_METRICS_ENDPOINT")
                .unwrap_or_else(|_| "http://localhost:4317".to_string()),
            // OTEL_SERVICE_NAME is the spec-named variable; the SDK reads it too,
            // but we pass it explicitly so the value is visible in the printout.
            service_name: env::var("OTEL_SERVICE_NAME")
                .unwrap_or_else(|_| "agenkit-production-example".to_string()),
            // Production deployments sample well below 1.0; 1% is a common floor.
            sample_rate: env::var("OTEL_TRACES_SAMPLER_ARG")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(1.0),
            log_level: env::var("LOG_LEVEL").unwrap_or_else(|_| "info".to_string()),
            audit_path: PathBuf::from(
                env::var("AUDIT_LOG_PATH").unwrap_or_else(|_| "/tmp/agenkit-audit.log".to_string()),
            ),
        }
    }

    fn print(&self) {
        println!("Configuration:");
        println!("  OTLP Endpoint: {}", self.otlp_endpoint);
        println!("  Metrics Endpoint: {}", self.metrics_endpoint);
        println!("  Service Name: {}", self.service_name);
        println!("  Sample Rate: {}", self.sample_rate);
        println!("  Log Level: {}", self.log_level);
        println!("  Audit Path: {:?}", self.audit_path);
        println!();
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== Agenkit Rust - Production Observability Example ===\n");

    // Load configuration from environment
    let config = Config::from_env();
    config.print();

    // Initialize observability stack
    println!("Initializing production observability...");

    // The OTLP gRPC channel is built lazily, so this succeeds even when no
    // collector is listening — an unreachable collector shows up as a failed
    // export later, not as an Err here. The Err arm therefore covers exporter
    // *construction* failure (e.g. a malformed endpoint), not connectivity.
    // Use init_tracing_with_config to set service.name: without it the SDK
    // falls back to OTEL_SERVICE_NAME, then "unknown_service:<exe>", and spans
    // from different services cannot be told apart in a shared collector.
    match init_tracing_with_config(
        "otlp",
        Some(&config.otlp_endpoint),
        Some(&config.service_name),
        config.sample_rate,
    ) {
        Ok(_) => println!("✓ Tracing initialized (OTLP)"),
        Err(e) => {
            println!("⚠ OTLP exporter could not be built ({e}), using console exporter");
            init_tracing("console", None)?;
        }
    }

    // Metrics export on a 60s interval, so shutdown_observability() at the end of
    // main is what delivers the final interval — see the flush below.
    match init_metrics("otlp", Some(&config.metrics_endpoint)) {
        Ok(_) => println!("✓ Metrics initialized (OTLP → {})", config.metrics_endpoint),
        Err(e) => {
            println!("⚠ OTLP metrics init failed ({e}), using stdout exporter");
            init_metrics("stdout", None)?;
        }
    }

    configure_logging("json", &config.log_level)?;
    println!("✓ Logging configured (JSON, {})", config.log_level);

    let audit_logger = AuditLogger::with_buffer_size(config.audit_path.clone(), 50);
    println!("✓ Audit logger initialized\n");

    // Log system startup
    let startup_event = AuditEvent::with_severity(
        AuditEventType::ConfigurationChanged,
        AuditSeverity::Info,
        "system".to_string(),
        None,
    )
    .add_detail(
        "event".to_string(),
        serde_json::json!("observability_initialized"),
    );
    audit_logger.log(startup_event).await?;

    // Create production agents
    println!("Creating production agents...");
    let agent1 = ProductionAgent::new("worker-1", 0.1); // 10% failure rate
    let traced1 = TracingMiddleware::new(agent1, Some("worker.process"));
    let observed1 = MetricsMiddleware::new(traced1);

    let agent2 = ProductionAgent::new("worker-2", 0.05); // 5% failure rate
    let traced2 = TracingMiddleware::new(agent2, Some("worker.process"));
    let observed2 = MetricsMiddleware::new(traced2);

    println!("✓ Created 2 workers with failure simulation\n");

    // Log agent creation
    for worker_name in &["worker-1", "worker-2"] {
        let event = AuditEvent::new(
            AuditEventType::AgentCreated,
            worker_name.to_string(),
            Some("prod-session-001".to_string()),
        );
        audit_logger.log(event).await?;
    }

    // Process requests with monitoring
    println!("Processing production workload...");
    let mut success_count = 0;
    let mut error_count = 0;

    for i in 0..20 {
        let message = Message::with_text("user", format!("Request {}", i + 1))
            .with_metadata("request_id", serde_json::json!(i + 1));

        // Alternate between agents
        let agent = if i % 2 == 0 { &observed1 } else { &observed2 };

        let agent_name = if i % 2 == 0 { "worker-1" } else { "worker-2" };

        // Log processing start
        let mut details = HashMap::new();
        details.insert("request_id".to_string(), serde_json::json!(i + 1));
        details.insert("agent".to_string(), serde_json::json!(agent_name));
        log_agent_event("request.start", &details);

        // Process with error handling
        match agent.process(message).await {
            Ok(_response) => {
                success_count += 1;
                print!(".");

                // Log success audit event
                let event = AuditEvent::new(
                    AuditEventType::MessageProcessed,
                    agent_name.to_string(),
                    Some("prod-session-001".to_string()),
                )
                .add_detail("status".to_string(), serde_json::json!("success"))
                .add_detail("request_id".to_string(), serde_json::json!(i + 1));
                audit_logger.log(event).await?;
            }
            Err(error) => {
                error_count += 1;
                print!("✗");

                // Log error
                log_agent_error(&error);

                // Log security event for failures (in production, you'd have smarter detection)
                let event = AuditEvent::with_severity(
                    AuditEventType::SecurityViolation,
                    AuditSeverity::Warning,
                    agent_name.to_string(),
                    Some("prod-session-001".to_string()),
                )
                .add_detail("error".to_string(), serde_json::json!(error.to_string()))
                .add_detail("request_id".to_string(), serde_json::json!(i + 1));
                audit_logger.log(event).await?;
            }
        }

        if (i + 1) % 10 == 0 {
            println!();
        }
    }

    println!("\n\nWorkload Summary:");
    println!("  Requests: 20");
    println!(
        "  Success: {} ({:.1}%)",
        success_count,
        (success_count as f64 / 20.0) * 100.0
    );
    println!(
        "  Errors: {} ({:.1}%)",
        error_count,
        (error_count as f64 / 20.0) * 100.0
    );
    println!();

    // Flush audit logs
    println!("Flushing audit logs...");
    audit_logger.flush().await?;
    println!("✓ Audit logs persisted\n");

    // Query audit events
    let all_events = audit_logger.query(None).await?;
    println!("Audit Summary:");
    println!("  Total events: {}", all_events.len());

    let session_events = audit_logger
        .query(Some("prod-session-001".to_string()))
        .await?;
    println!("  Session events: {}", session_events.len());

    let errors = session_events
        .iter()
        .filter(|e| matches!(e.event_type, AuditEventType::SecurityViolation))
        .count();
    println!("  Security events: {}", errors);

    println!("\n=== Production Example Complete ===");
    println!("\nProduction Features Demonstrated:");
    println!("  ✓ OTLP exporters for distributed tracing");
    println!("  ✓ Structured JSON logging");
    println!("  ✓ Comprehensive audit trail");
    println!("  ✓ Error tracking and monitoring");
    println!("  ✓ Metrics collection (requests, errors, latency)");
    println!("  ✓ Environment-based configuration");
    println!("\nNext Steps:");
    println!("  1. View traces in Jaeger UI: http://localhost:16686");
    println!("  2. Check audit log: {:?}", config.audit_path);
    println!("  3. Query metrics from your metrics backend");
    println!("  4. Set up alerting on error rates and latency");

    // Flush and shut down before exit. This is not optional with the OTLP
    // exporter: the span processor batches, so exiting without it drops every
    // span still in the buffer — with no error and nothing in the collector.
    println!("\nFlushing traces...");
    agenkit::observability::shutdown_observability();
    println!("✓ Traces flushed");

    Ok(())
}
