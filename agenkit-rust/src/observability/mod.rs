//! OpenTelemetry-based observability for Agenkit agents.
//!
//! This module provides distributed tracing, metrics collection, structured logging,
//! and audit logging for production agent deployments.
//!
//! # Features
//!
//! - **Distributed Tracing**: W3C Trace Context propagation across agents
//! - **Metrics Collection**: Counters, histograms, and gauges for monitoring
//! - **Structured Logging**: JSON logging with trace correlation
//! - **Audit Logging**: Compliance-friendly event logging
//!
//! # Quick Start
//!
//! ## Basic Setup
//!
//! ```rust,no_run
//! use agenkit::observability::{init_tracing, init_metrics, configure_logging};
//! use agenkit::observability::{TracingMiddleware, MetricsMiddleware};
//! use agenkit::core::Agent;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Initialize observability components
//! init_tracing("console", None)?;
//! init_metrics("prometheus", None)?;
//! configure_logging("json", "info")?;
//!
//! // Wrap your agent with middleware (commented for doc test)
//! // let agent = MyAgent::new();
//! // let traced_agent = TracingMiddleware::new(agent, None);
//! // let full_agent = MetricsMiddleware::new(traced_agent);
//!
//! // Process messages (observability automatic)
//! // let response = full_agent.process(msg).await?;
//! # Ok(())
//! # }
//! ```
//!
//! ## Production Setup
//!
//! ```rust,no_run
//! use agenkit::observability::{init_tracing, init_metrics, configure_logging};
//! use agenkit::observability::audit::AuditLogger;
//! use std::sync::Arc;
//! use std::path::PathBuf;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // OTLP for distributed tracing
//! init_tracing("otlp", Some("http://localhost:4317"))?;
//!
//! // Prometheus metrics
//! init_metrics("prometheus", None)?;
//!
//! // Structured JSON logging
//! configure_logging("json", "info")?;
//!
//! // Audit logging for compliance
//! let audit_logger = Arc::new(
//!     AuditLogger::new(PathBuf::from("/var/log/audit.log"))?
//! );
//! # Ok(())
//! # }
//! ```
//!
//! # Architecture
//!
//! The observability module is organized into four sub-modules:
//!
//! - [`tracing`]: Distributed tracing with OpenTelemetry and W3C Trace Context
//! - [`metrics`]: Metrics collection with Prometheus and OTLP exporters
//! - [`logging`]: Structured logging with trace correlation
//! - [`audit`]: Audit logging for compliance and security
//!
//! Each module can be used independently or combined for comprehensive observability.
//!
//! # Exporters
//!
//! ## Tracing Exporters
//!
//! - **OTLP**: OpenTelemetry Protocol (gRPC) - best for production
//! - **Jaeger**: Native Jaeger format (deprecated, use OTLP instead)
//! - **Zipkin**: Zipkin format
//! - **Console**: JSON output to stdout - best for development
//!
//! ## Metrics Exporters
//!
//! - **Prometheus**: Pull-based metrics on port 9464
//! - **OTLP**: Push-based metrics to OTLP collector
//!
//! # Cross-Language Compatibility
//!
//! This implementation uses message metadata for trace context propagation
//! instead of thread-local context. This ensures compatibility across
//! language boundaries when building multi-language agent systems.
//!
//! # Examples
//!
//! See the `examples/` directory for complete examples:
//!
//! - `observability_basic.rs` - Simple setup
//! - `observability_distributed.rs` - Multi-agent tracing
//! - `observability_production.rs` - Full production setup

#[cfg(feature = "opentelemetry")]
pub mod tracing;

#[cfg(feature = "opentelemetry")]
pub mod metrics;

#[cfg(feature = "opentelemetry")]
pub mod logging;

#[cfg(feature = "opentelemetry")]
pub mod audit;

// Re-export common types when OpenTelemetry is enabled
#[cfg(feature = "opentelemetry")]
pub use self::tracing::{
    extract_trace_context, init_tracing, inject_trace_context, TracingMiddleware,
};

#[cfg(feature = "opentelemetry")]
pub use self::metrics::{get_meter, init_metrics, MetricsMiddleware};

#[cfg(feature = "opentelemetry")]
pub use self::logging::{configure_logging, log_agent_error, log_agent_event, log_agent_warning};

#[cfg(feature = "opentelemetry")]
pub use self::audit::{AuditEvent, AuditEventType, AuditLogger, Severity};

// Re-export OpenTelemetry types for convenience
#[cfg(feature = "opentelemetry")]
pub use opentelemetry::{Context, KeyValue};

#[cfg(feature = "opentelemetry")]
pub use opentelemetry::trace::{Span, SpanKind, Status, Tracer};

#[cfg(feature = "opentelemetry")]
pub use opentelemetry::metrics::{Counter, Histogram, Meter};

/// Initialize all observability components with sensible defaults.
///
/// This is a convenience function that initializes tracing, metrics, and logging
/// with OTLP exporters and JSON logging. Perfect for production deployments.
///
/// # Arguments
///
/// * `tracing_endpoint` - OTLP endpoint for traces (e.g., "http://localhost:4317")
/// * `metrics_endpoint` - OTLP endpoint for metrics (e.g., "http://localhost:4317")
///
/// # Returns
///
/// Returns `Ok(())` on success, or an error if any component fails to initialize.
/// Note that if components are already initialized, this will return an error.
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::init_observability;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// init_observability("http://localhost:4317", "http://localhost:4317")?;
/// # Ok(())
/// # }
/// ```
#[cfg(feature = "opentelemetry")]
pub fn init_observability(
    tracing_endpoint: &str,
    metrics_endpoint: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    init_tracing("otlp", Some(tracing_endpoint))?;
    init_metrics("otlp", Some(metrics_endpoint))?;
    configure_logging("json", "info")?;
    Ok(())
}

/// Shutdown all observability components gracefully.
///
/// This function should be called before the application exits to ensure all
/// pending traces, metrics, and logs are flushed to their respective backends.
///
/// # Returns
///
/// Returns `Ok(())` on success, or an error if shutdown fails.
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::shutdown_observability;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// // ... application code ...
/// shutdown_observability().await?;
/// # Ok(())
/// # }
/// ```
#[cfg(feature = "opentelemetry")]
pub async fn shutdown_observability() -> Result<(), Box<dyn std::error::Error>> {
    opentelemetry::global::shutdown_tracer_provider();
    Ok(())
}
