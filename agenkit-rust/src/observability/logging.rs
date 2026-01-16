//! Structured logging with trace correlation.
//!
//! This module provides JSON logging with automatic trace context injection
//! for correlation with distributed traces.
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::observability::logging::{configure_logging, log_agent_event, log_agent_error};
//!
//! # fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Configure JSON logging at info level
//! configure_logging("json", "info")?;
//!
//! // Log agent events
//! log_agent_event("agent_started", "MyAgent started processing", &[("version", "1.0")]);
//!
//! // Log errors
//! log_agent_error("processing_failed", "Failed to process message", "timeout error");
//! # Ok(())
//! # }
//! ```

use once_cell::sync::OnceCell;
use std::collections::HashMap;
use tracing::{error, info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

/// Global flag to track if logging has been initialized.
static LOGGING_INITIALIZED: OnceCell<bool> = OnceCell::new();

/// Configure structured logging with the specified format and level.
///
/// This function sets up the tracing subscriber with optional OpenTelemetry integration
/// for trace context correlation.
///
/// # Arguments
///
/// * `format` - Log format: "json", "pretty", or "compact"
/// * `level` - Log level: "trace", "debug", "info", "warn", or "error"
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::logging::configure_logging;
///
/// // JSON format at info level
/// configure_logging("json", "info")?;
///
/// // Pretty format at debug level
/// configure_logging("pretty", "debug")?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
///
/// # Errors
///
/// Returns an error if:
/// - Format is unknown
/// - Logging is already initialized
/// - Log level is invalid
pub fn configure_logging(format: &str, level: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Check if already initialized
    if LOGGING_INITIALIZED.get().is_some() {
        return Err("Logging already initialized".into());
    }

    let env_filter = EnvFilter::try_new(level)?;

    // Add format layer based on format type
    let init_result = match format {
        "json" => {
            let json_layer = tracing_subscriber::fmt::layer()
                .json()
                .with_current_span(true)
                .with_span_list(true);

            tracing_subscriber::registry()
                .with(env_filter)
                .with(json_layer)
                .try_init()
        }
        "pretty" => {
            let pretty_layer = tracing_subscriber::fmt::layer()
                .pretty()
                .with_thread_ids(true)
                .with_thread_names(true);

            tracing_subscriber::registry()
                .with(env_filter)
                .with(pretty_layer)
                .try_init()
        }
        "compact" => {
            let compact_layer = tracing_subscriber::fmt::layer().compact();

            tracing_subscriber::registry()
                .with(env_filter)
                .with(compact_layer)
                .try_init()
        }
        _ => {
            return Err(format!("Unknown log format: {}", format).into());
        }
    };

    // Handle the result - it's OK if already initialized
    match init_result {
        Ok(_) => {
            LOGGING_INITIALIZED
                .set(true)
                .map_err(|_| "Failed to set logging initialized flag")?;
            Ok(())
        }
        Err(e) => Err(format!("Failed to initialize logging: {}", e).into()),
    }
}

/// Log an agent event with structured context.
///
/// This function logs an informational event with the given event type, message,
/// and additional context fields.
///
/// # Arguments
///
/// * `event_type` - Type of event (e.g., "agent_started", "message_processed")
/// * `message` - Human-readable message
/// * `context` - Additional key-value pairs for context
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::logging::log_agent_event;
///
/// log_agent_event(
///     "message_processed",
///     "Successfully processed user message",
///     &[("agent_name", "ChatAgent"), ("duration_ms", "150")]
/// );
/// ```
pub fn log_agent_event(event_type: &str, message: &str, context: &[(&str, &str)]) {
    let fields: HashMap<&str, &str> = context.iter().copied().collect();
    info!(event_type = event_type, ?fields, "{}", message);
}

/// Log an agent error with structured context.
///
/// This function logs an error event with the given event type, message,
/// and error details.
///
/// # Arguments
///
/// * `event_type` - Type of error (e.g., "processing_failed", "timeout")
/// * `message` - Human-readable error message
/// * `error` - Error details or description
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::logging::log_agent_error;
///
/// log_agent_error(
///     "processing_failed",
///     "Failed to process message",
///     "Connection timeout after 30s"
/// );
/// ```
pub fn log_agent_error(event_type: &str, message: &str, error: &str) {
    error!(event_type = event_type, error = error, "{}", message);
}

/// Log an agent warning with structured context.
///
/// This function logs a warning event with the given event type and message.
///
/// # Arguments
///
/// * `event_type` - Type of warning (e.g., "rate_limit_approaching", "high_latency")
/// * `message` - Human-readable warning message
/// * `context` - Additional key-value pairs for context
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::logging::log_agent_warning;
///
/// log_agent_warning(
///     "high_latency",
///     "Agent response time exceeding threshold",
///     &[("latency_ms", "2500"), ("threshold_ms", "1000")]
/// );
/// ```
pub fn log_agent_warning(event_type: &str, message: &str, context: &[(&str, &str)]) {
    let fields: HashMap<&str, &str> = context.iter().copied().collect();
    warn!(event_type = event_type, ?fields, "{}", message);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_configure_logging_json() {
        // JSON format should work (or already be initialized)
        let result = configure_logging("json", "info");
        if result.is_err() {
            let err_msg = result.unwrap_err().to_string();
            assert!(
                err_msg.contains("already initialized") || err_msg.contains("global default"),
                "Error should be about initialization: {}",
                err_msg
            );
        }
    }

    #[test]
    fn test_configure_logging_pretty() {
        // Pretty format should work (or already be initialized)
        let result = configure_logging("pretty", "debug");
        if result.is_err() {
            let err_msg = result.unwrap_err().to_string();
            assert!(
                err_msg.contains("already initialized") || err_msg.contains("global default"),
                "Error should be about initialization: {}",
                err_msg
            );
        }
    }

    #[test]
    fn test_configure_logging_compact() {
        // Compact format should work (or already be initialized)
        let result = configure_logging("compact", "warn");
        if result.is_err() {
            let err_msg = result.unwrap_err().to_string();
            assert!(
                err_msg.contains("already initialized") || err_msg.contains("global default"),
                "Error should be about initialization: {}",
                err_msg
            );
        }
    }

    #[test]
    fn test_configure_logging_unknown_format() {
        // Unknown format should fail
        let result = configure_logging("unknown", "info");
        if result.is_err() {
            let err_msg = result.unwrap_err().to_string();
            // Could be unknown format or already initialized
            assert!(
                err_msg.contains("Unknown log format")
                    || err_msg.contains("already initialized")
                    || err_msg.contains("global default"),
                "Error should be meaningful: {}",
                err_msg
            );
        }
    }

    #[test]
    fn test_log_agent_event() {
        // Initialize if not already done
        let _ = configure_logging("json", "info");

        // Should not panic
        log_agent_event(
            "test_event",
            "Test event message",
            &[("key1", "value1"), ("key2", "value2")],
        );
    }

    #[test]
    fn test_log_agent_error() {
        // Initialize if not already done
        let _ = configure_logging("json", "info");

        // Should not panic
        log_agent_error("test_error", "Test error message", "Error details here");
    }

    #[test]
    fn test_log_agent_warning() {
        // Initialize if not already done
        let _ = configure_logging("json", "info");

        // Should not panic
        log_agent_warning(
            "test_warning",
            "Test warning message",
            &[("threshold", "100"), ("actual", "150")],
        );
    }

    #[test]
    fn test_multiple_log_calls() {
        // Initialize if not already done
        let _ = configure_logging("json", "info");

        // Multiple log calls should work
        for i in 0..5 {
            log_agent_event(
                "iteration",
                &format!("Iteration {}", i),
                &[("iteration", &i.to_string())],
            );
        }
    }
}
