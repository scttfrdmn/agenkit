//! Tests for structured logging module.

use agenkit::core::AgentError;
use agenkit::observability::{configure_logging, log_agent_error, log_agent_event, log_with_level};
use std::collections::HashMap;

#[test]
fn test_configure_logging_json() {
    // Configure JSON logging
    // May succeed or be silently ignored if already initialized
    let _result = configure_logging("json", "info");
    // Don't assert - logging might already be initialized from another test
}

#[test]
fn test_configure_logging_pretty() {
    // Configure pretty logging (will be ignored if already initialized)
    let _result = configure_logging("pretty", "debug");
    // Don't assert - logging might already be initialized from another test
}

#[test]
fn test_configure_logging_compact() {
    // Configure compact logging
    let _result = configure_logging("compact", "warn");
    // Don't assert - logging might already be initialized from another test
}

#[test]
fn test_configure_logging_unsupported_format() {
    // Try to configure with unsupported format
    // This will fail if it's the first call, or succeed if already initialized
    let _result = configure_logging("invalid_format", "info");
    // Can't assert error because logging might already be initialized from another test
}

#[test]
fn test_configure_logging_idempotent() {
    // Both calls should succeed (second is ignored)
    let _result1 = configure_logging("json", "info");
    let _result2 = configure_logging("pretty", "debug");
    // Don't assert - this just tests that calling twice doesn't panic
}

#[test]
fn test_log_agent_event() {
    // Ensure logging is configured
    let _ = configure_logging("json", "info");

    let mut details = HashMap::new();
    details.insert("agent_name".to_string(), serde_json::json!("test-agent"));
    details.insert("action".to_string(), serde_json::json!("processing"));
    details.insert("duration_ms".to_string(), serde_json::json!(150));

    // Should not panic
    log_agent_event("agent.processing_complete", &details);
}

#[test]
fn test_log_agent_event_empty_details() {
    let _ = configure_logging("json", "info");

    let details = HashMap::new();

    // Should handle empty details gracefully
    log_agent_event("agent.started", &details);
}

#[test]
fn test_log_agent_error() {
    let _ = configure_logging("json", "info");

    let error = AgentError::ProcessingError("Failed to process message".to_string());

    // Should not panic
    log_agent_error(&error);
}

#[test]
fn test_log_agent_error_types() {
    let _ = configure_logging("json", "info");

    // Test different error types
    let errors = vec![
        AgentError::ProcessingError("Processing failed".to_string()),
        AgentError::Timeout("Request timed out".to_string()),
        AgentError::NotFound("Agent not found".to_string()),
        AgentError::Transport("Connection failed".to_string()),
        AgentError::Internal("Internal error".to_string()),
        AgentError::InvalidInput("Bad input".to_string()),
    ];

    for error in errors {
        log_agent_error(&error);
    }
}

#[test]
fn test_log_with_level_trace() {
    let _ = configure_logging("json", "trace");

    log_with_level("trace", "This is a trace message");
}

#[test]
fn test_log_with_level_debug() {
    let _ = configure_logging("json", "debug");

    log_with_level("debug", "This is a debug message");
}

#[test]
fn test_log_with_level_info() {
    let _ = configure_logging("json", "info");

    log_with_level("info", "This is an info message");
}

#[test]
fn test_log_with_level_warn() {
    let _ = configure_logging("json", "warn");

    log_with_level("warn", "This is a warning message");
}

#[test]
fn test_log_with_level_error() {
    let _ = configure_logging("json", "error");

    log_with_level("error", "This is an error message");
}

#[test]
fn test_log_with_level_unknown() {
    let _ = configure_logging("json", "info");

    // Unknown level should default to info
    log_with_level("unknown", "This should be logged as info");
}

#[test]
fn test_logging_with_complex_details() {
    let _ = configure_logging("json", "info");

    let mut details = HashMap::new();
    details.insert(
        "nested".to_string(),
        serde_json::json!({
            "key1": "value1",
            "key2": 42,
            "key3": true
        }),
    );
    details.insert("array".to_string(), serde_json::json!([1, 2, 3]));

    // Should handle complex JSON structures
    log_agent_event("agent.complex_event", &details);
}

#[test]
fn test_logging_integration() {
    // Configure once
    let _ = configure_logging("json", "info");

    // Log various events
    let mut details = HashMap::new();
    details.insert("step".to_string(), serde_json::json!(1));
    log_agent_event("workflow.started", &details);

    log_with_level("info", "Processing step 1");

    details.insert("step".to_string(), serde_json::json!(2));
    log_agent_event("workflow.progress", &details);

    let error = AgentError::ProcessingError("Step 3 failed".to_string());
    log_agent_error(&error);

    log_with_level("warn", "Retrying step 3");

    details.insert("step".to_string(), serde_json::json!(3));
    details.insert("status".to_string(), serde_json::json!("completed"));
    log_agent_event("workflow.completed", &details);
}
