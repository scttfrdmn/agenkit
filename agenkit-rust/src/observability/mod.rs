//! OpenTelemetry-based observability for Agenkit agents.
//!
//! Provides distributed tracing, metrics collection, structured logging, and audit logging
//! for production AI agent systems. Enables full observability across multi-agent workflows
//! with cross-language trace propagation via W3C Trace Context.
//!
//! # Modules
//!
//! - [`tracing`] - Distributed tracing with OpenTelemetry
//! - [`metrics`] - Metrics collection with Prometheus and OTLP exporters
//! - [`logging`] - Structured logging with trace correlation
//! - [`audit`] - Security and compliance audit logging
//!
//! # Quick Start
//!
//! ```rust,no_run
//! use agenkit::observability::{init_observability, TracingMiddleware, MetricsMiddleware};
//! use agenkit::core::Agent;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Initialize all observability components
//! init_observability("http://localhost:4317", "http://localhost:4318")?;
//!
//! // Wrap your agent with observability
//! # struct MyAgent;
//! # #[async_trait::async_trait]
//! # impl Agent for MyAgent {
//! #     fn name(&self) -> &str { "my-agent" }
//! #     async fn process(&self, msg: agenkit::core::Message) -> Result<agenkit::core::Message, agenkit::core::AgentError> {
//! #         Ok(msg)
//! #     }
//! # }
//! let agent = MyAgent;
//! let traced_agent = TracingMiddleware::new(agent, None);
//! let observed_agent = MetricsMiddleware::new(traced_agent);
//!
//! // Process messages with automatic tracing and metrics
//! # use agenkit::core::Message;
//! # let message = Message::with_text("user", "test");
//! let response = observed_agent.process(message).await?;
//! # Ok(())
//! # }
//! ```
//!
//! # Features
//!
//! - **Distributed Tracing** - W3C Trace Context propagation via message metadata
//! - **Metrics Collection** - Request counting, duration tracking, resource monitoring
//! - **Structured Logging** - JSON logging with trace correlation
//! - **Audit Logging** - Security events with pluggable adapters
//! - **Cross-Language** - Compatible with Python, Go, TypeScript, C++, Zig implementations
//!
//! # Architecture
//!
//! Observability is implemented using the middleware pattern:
//!
//! ```text
//! User Message
//!     ↓
//! MetricsMiddleware (records duration, counts)
//!     ↓
//! TracingMiddleware (creates spans, propagates context)
//!     ↓
//! Your Agent (business logic)
//!     ↓
//! Response (with injected trace context)
//! ```
//!
//! # Examples
//!
//! See the `examples/` directory for complete examples:
//! - `observability_basic.rs` - Simple setup with console exporters
//! - `observability_distributed.rs` - Multi-agent tracing with context propagation
//! - `observability_production.rs` - Full production setup with OTLP exporters

#![cfg(feature = "opentelemetry")]

pub mod tracing;
pub mod metrics;
pub mod logging;
pub mod audit;

// Re-export common types
pub use tracing::{
    extract_trace_context, inject_trace_context, inject_trace_context_from, init_tracing,
    TracingMiddleware,
};
pub use metrics::{init_metrics, shutdown_metrics, MetricsMiddleware};
pub use logging::{configure_logging, log_agent_error, log_agent_event, log_with_level};
pub use audit::{AuditEvent, AuditEventType, AuditLogger, AuditSeverity};

use crate::core::AgentError;

/// Initialize all observability components with OTLP exporters.
///
/// This is a convenience function that initializes tracing, metrics, and logging
/// with production-ready defaults.
///
/// # Arguments
///
/// * `tracing_endpoint` - OTLP gRPC endpoint for traces (e.g., "http://localhost:4317")
/// * `metrics_endpoint` - OTLP gRPC endpoint for metrics (e.g., "http://localhost:4318")
///
/// # Example
///
/// ```rust,no_run
/// # use agenkit::observability::init_observability;
/// # fn main() -> Result<(), Box<dyn std::error::Error>> {
/// init_observability("http://localhost:4317", "http://localhost:4318")?;
/// # Ok(())
/// # }
/// ```
pub fn init_observability(
    tracing_endpoint: &str,
    metrics_endpoint: &str,
) -> Result<(), AgentError> {
    init_tracing("otlp", Some(tracing_endpoint))?;
    init_metrics("otlp", Some(metrics_endpoint))?;
    configure_logging("json", "info")?;
    Ok(())
}
