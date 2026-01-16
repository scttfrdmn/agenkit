//! Tests for OpenTelemetry tracing module.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{extract_trace_context, init_tracing, TracingMiddleware};
use async_trait::async_trait;
use std::collections::HashMap;
use serde_json::json;

/// Simple test agent for testing tracing middleware.
struct SimpleAgent {
    name: String,
    response: String,
}

impl SimpleAgent {
    fn new(name: &str, response: &str) -> Self {
        Self {
            name: name.to_string(),
            response: response.to_string(),
        }
    }
}

#[async_trait]
impl Agent for SimpleAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", &self.response))
    }
}

#[tokio::test]
async fn test_init_tracing_console() {
    // Initialize tracing with console exporter
    let result = init_tracing("console", None);
    assert!(result.is_ok(), "Failed to initialize console tracing");
}

#[tokio::test]
async fn test_tracing_middleware_creates_span() {
    // Initialize tracing
    init_tracing("console", None).unwrap();

    // Create traced agent
    let agent = SimpleAgent::new("test-agent", "Hello");
    let traced = TracingMiddleware::new(agent, None);

    // Process message
    let message = Message::with_text("user", "Test");
    let result = traced.process(message).await;

    assert!(result.is_ok(), "Traced agent should process successfully");
}

#[tokio::test]
async fn test_tracing_middleware_preserves_agent_interface() {
    let agent = SimpleAgent::new("my-agent", "Response");
    let traced = TracingMiddleware::new(agent, None);

    // Test name preservation
    assert_eq!(traced.name(), "my-agent");
}

#[tokio::test]
async fn test_inject_trace_context() {
    use opentelemetry::global;
    use opentelemetry::trace::{Span, Tracer};

    init_tracing("console", None).unwrap();

    // Create a span
    let tracer = global::tracer("test");
    let span = tracer.start("test-span");
    let span_context = span.span_context().clone();

    // Manually create trace context in metadata
    let mut metadata = HashMap::new();
    if span_context.is_valid() {
        let trace_id = format!("{:032x}", span_context.trace_id());
        let span_id = format!("{:016x}", span_context.span_id());
        let flags = if span_context.is_sampled() { "01" } else { "00" };
        let traceparent = format!("00-{}-{}-{}", trace_id, span_id, flags);

        let mut trace_ctx = HashMap::new();
        trace_ctx.insert("traceparent".to_string(), json!(traceparent));
        metadata.insert("trace_context".to_string(), json!(trace_ctx));
    }

    // Should have trace_context key when there's a valid span
    assert!(metadata.contains_key("trace_context"));
}

#[tokio::test]
async fn test_extract_trace_context_empty() {
    let metadata = HashMap::new();
    let _context = extract_trace_context(&metadata);

    // Should not panic with empty metadata
}

#[tokio::test]
async fn test_extract_trace_context_with_data() {
    let mut metadata = HashMap::new();
    metadata.insert(
        "trace_context".to_string(),
        json!({
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        }),
    );

    let _context = extract_trace_context(&metadata);
    // Should not panic with valid trace context
}

#[tokio::test]
async fn test_tracing_middleware_custom_span_name() {
    init_tracing("console", None).unwrap();

    let agent = SimpleAgent::new("agent", "response");
    let traced = TracingMiddleware::new(agent, Some("custom.span.name"));

    let message = Message::with_text("user", "test");
    let result = traced.process(message).await;

    assert!(result.is_ok());
}

#[tokio::test]
async fn test_tracing_middleware_propagates_context() {
    init_tracing("console", None).unwrap();

    // First agent with tracing
    let agent1 = SimpleAgent::new("agent1", "response1");
    let traced1 = TracingMiddleware::new(agent1, None);

    // Process message through first agent
    let message1 = Message::with_text("user", "test");
    let response1 = traced1.process(message1).await.unwrap();

    // Response should have trace context
    assert!(response1.metadata.contains_key("trace_context"));

    // Second agent with tracing
    let agent2 = SimpleAgent::new("agent2", "response2");
    let traced2 = TracingMiddleware::new(agent2, None);

    // Process response through second agent
    let response2 = traced2.process(response1).await.unwrap();

    // Should still have trace context
    assert!(response2.metadata.contains_key("trace_context"));
}

#[tokio::test]
async fn test_tracing_middleware_error_handling() {
    init_tracing("console", None).unwrap();

    // Agent that returns error
    struct ErrorAgent;

    #[async_trait]
    impl Agent for ErrorAgent {
        fn name(&self) -> &str {
            "error-agent"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError("Test error".to_string()))
        }
    }

    let agent = ErrorAgent;
    let traced = TracingMiddleware::new(agent, None);

    let message = Message::with_text("user", "test");
    let result = traced.process(message).await;

    // Should propagate error
    assert!(result.is_err());
}

#[tokio::test]
async fn test_tracing_middleware_with_metadata() {
    init_tracing("console", None).unwrap();

    let agent = SimpleAgent::new("agent", "response");
    let traced = TracingMiddleware::new(agent, None);

    // Message with metadata
    let message = Message::with_text("user", "test")
        .with_metadata("session_id", json!("abc123"))
        .with_metadata("user_id", json!(42))
        .with_metadata("flag", json!(true));

    let result = traced.process(message).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_unsupported_exporter_type() {
    let result = init_tracing("invalid_exporter", None);
    assert!(result.is_err(), "Should fail with unsupported exporter");
}
