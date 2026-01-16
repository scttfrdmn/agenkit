//! Structured logging with trace correlation.
//!
//! Provides JSON and pretty logging formats with automatic trace context injection
//! for correlating logs with distributed traces.
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::observability::{configure_logging, log_agent_event};
//! use std::collections::HashMap;
//!
//! # fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Configure JSON logging at info level
//! configure_logging("json", "info")?;
//!
//! // Log an event
//! let mut details = HashMap::new();
//! details.insert("action".to_string(), serde_json::json!("processing"));
//! log_agent_event("agent.started", &details);
//! # Ok(())
//! # }
//! ```

use crate::core::AgentError;
use once_cell::sync::OnceCell;
use std::collections::HashMap;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

/// Global flag to track if logging has been initialized.
static LOGGING_INITIALIZED: OnceCell<()> = OnceCell::new();

/// Configure structured logging with trace correlation.
///
/// Sets up a global tracing subscriber with the specified format and log level.
/// This function can only be called once - subsequent calls will be ignored.
///
/// # Supported Formats
///
/// - `"json"` - JSON structured logging (machine-readable)
/// - `"pretty"` - Human-readable pretty format (for development)
/// - `"compact"` - Compact format (default)
///
/// # Supported Levels
///
/// - `"trace"` - Most verbose
/// - `"debug"` - Debug information
/// - `"info"` - Informational messages (default)
/// - `"warn"` - Warnings
/// - `"error"` - Errors only
///
/// # Arguments
///
/// * `format` - Output format ("json", "pretty", or "compact")
/// * `level` - Log level filter
///
/// # Example
///
/// ```rust,no_run
/// # use agenkit::observability::configure_logging;
/// // JSON logging for production
/// configure_logging("json", "info")?;
///
/// // Pretty logging for development
/// configure_logging("pretty", "debug")?;
/// # Ok::<(), agenkit::core::AgentError>(())
/// ```
pub fn configure_logging(format: &str, level: &str) -> Result<(), AgentError> {
    // Only initialize once
    if LOGGING_INITIALIZED.get().is_some() {
        return Ok(());
    }

    // Parse log level
    let env_filter = EnvFilter::try_new(level).unwrap_or_else(|_| EnvFilter::new("info"));

    // Create the appropriate format layer
    let subscriber = tracing_subscriber::registry().with(env_filter);

    match format {
        "json" => {
            let json_layer = tracing_subscriber::fmt::layer()
                .json()
                .with_current_span(true)
                .with_span_list(false);
            subscriber.with(json_layer).try_init().map_err(|e| {
                AgentError::ProcessingError(format!("Failed to initialize logging: {}", e))
            })?;
        }
        "pretty" => {
            let pretty_layer = tracing_subscriber::fmt::layer()
                .pretty()
                .with_line_number(true)
                .with_thread_ids(true);
            subscriber.with(pretty_layer).try_init().map_err(|e| {
                AgentError::ProcessingError(format!("Failed to initialize logging: {}", e))
            })?;
        }
        "compact" => {
            let compact_layer = tracing_subscriber::fmt::layer().compact();
            subscriber.with(compact_layer).try_init().map_err(|e| {
                AgentError::ProcessingError(format!("Failed to initialize logging: {}", e))
            })?;
        }
        _ => {
            return Err(AgentError::ProcessingError(format!(
                "Unsupported format: {}",
                format
            )));
        }
    }

    let _ = LOGGING_INITIALIZED.set(());
    Ok(())
}

/// Log an agent event with structured details.
///
/// Creates a structured log entry with the event name and associated details.
/// The log level is INFO by default.
///
/// # Arguments
///
/// * `event` - Event name (e.g., "agent.started", "message.processed")
/// * `details` - HashMap of additional details to include in the log
///
/// # Example
///
/// ```rust
/// # use agenkit::observability::log_agent_event;
/// # use std::collections::HashMap;
/// let mut details = HashMap::new();
/// details.insert("agent_name".to_string(), serde_json::json!("my-agent"));
/// details.insert("duration_ms".to_string(), serde_json::json!(150));
/// log_agent_event("agent.processing_complete", &details);
/// ```
pub fn log_agent_event(event: &str, details: &HashMap<String, serde_json::Value>) {
    // Convert details to a string representation for structured logging
    let details_str = serde_json::to_string(details).unwrap_or_else(|_| "{}".to_string());

    tracing::info!(
        event = %event,
        details = %details_str,
        "Agent event"
    );
}

/// Log an agent error with full context.
///
/// Creates a structured error log entry with the error details.
/// The log level is ERROR.
///
/// # Arguments
///
/// * `error` - The AgentError to log
///
/// # Example
///
/// ```rust
/// # use agenkit::observability::log_agent_error;
/// # use agenkit::core::AgentError;
/// let error = AgentError::ProcessingError("Failed to process message".to_string());
/// log_agent_error(&error);
/// ```
pub fn log_agent_error(error: &AgentError) {
    let error_type = match error {
        AgentError::ProcessingError(_) => "ProcessingError",
        AgentError::Timeout(_) => "Timeout",
        AgentError::NotFound(_) => "NotFound",
        AgentError::Transport(_) => "Transport",
        AgentError::Serialization(_) => "Serialization",
        #[cfg(feature = "native")]
        AgentError::Http(_) => "Http",
        AgentError::Internal(_) => "Internal",
        AgentError::InvalidInput(_) => "InvalidInput",
    };

    tracing::error!(
        error_type = %error_type,
        error_message = %error,
        "Agent error occurred"
    );
}

/// Log a message at the specified level with trace context.
///
/// This is a utility function for custom logging needs.
///
/// # Arguments
///
/// * `level` - The log level (trace, debug, info, warn, error)
/// * `message` - The log message
///
/// # Example
///
/// ```rust
/// # use agenkit::observability::log_with_level;
/// log_with_level("debug", "Processing started");
/// log_with_level("warn", "Rate limit approaching");
/// ```
pub fn log_with_level(level: &str, message: &str) {
    match level {
        "trace" => tracing::trace!("{}", message),
        "debug" => tracing::debug!("{}", message),
        "info" => tracing::info!("{}", message),
        "warn" => tracing::warn!("{}", message),
        "error" => tracing::error!("{}", message),
        _ => tracing::info!("{}", message),
    }
}
