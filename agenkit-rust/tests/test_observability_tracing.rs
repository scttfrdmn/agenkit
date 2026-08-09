//! Tests for OpenTelemetry tracing module.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    extract_trace_context, init_tracing, init_tracing_with_config, TracingMiddleware,
};
use async_trait::async_trait;
use serde_json::json;
use std::collections::HashMap;

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
    use agenkit::observability::inject_trace_context_from;
    use opentelemetry::trace::{
        SpanContext, SpanId, TraceContextExt, TraceFlags, TraceId, TraceState,
    };
    use opentelemetry::Context;

    // Build a context carrying a known-valid span context. We construct it
    // explicitly (rather than via the process-global tracer) so the test is
    // deterministic and independent of test ordering / global tracer state.
    let span_context = SpanContext::new(
        TraceId::from_hex("4bf92f3577b34da6a3ce929d0e0e4736").unwrap(),
        SpanId::from_hex("00f067aa0ba902b7").unwrap(),
        TraceFlags::SAMPLED,
        false,
        TraceState::default(),
    );
    assert!(span_context.is_valid());
    let cx = Context::current().with_remote_span_context(span_context);

    let mut metadata = HashMap::new();
    inject_trace_context_from(&mut metadata, &cx);

    // A valid span context should produce a trace_context entry.
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

// #771: negative-verification target — passing `None` as the endpoint must
// not be an error, and must actually defer to OTEL_EXPORTER_OTLP_ENDPOINT
// rather than silently building an exporter pointed at the hardcoded
// localhost default with no regard for the environment. The OTLP exporter
// builder itself performs this resolution (this crate does not call
// `with_endpoint` at all when `endpoint` is `None`, so nothing here can
// override the SDK's own env var read — see the `builder.with_endpoint`
// guard in `init_tracing_with_config`), so a successful `Ok(())` with the
// env var set and no explicit endpoint is the observable proof that the
// fallback path executed rather than short-circuiting on an empty
// parameter as it would if `with_endpoint("")` were called unconditionally.
#[tokio::test]
async fn test_init_tracing_otlp_without_endpoint_defers_to_env_var() {
    std::env::set_var("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317");

    let result = init_tracing("otlp", None);
    assert!(
        result.is_ok(),
        "init_tracing(\"otlp\", None) should defer to OTEL_EXPORTER_OTLP_ENDPOINT, not error"
    );

    std::env::remove_var("OTEL_EXPORTER_OTLP_ENDPOINT");
}

// Explicit endpoint parameter must still win over the environment.
#[tokio::test]
async fn test_init_tracing_otlp_explicit_endpoint_overrides_env_var() {
    std::env::set_var("OTEL_EXPORTER_OTLP_ENDPOINT", "http://should-not-be-used:4317");

    let result = init_tracing("otlp", Some("http://explicit:4317"));
    assert!(
        result.is_ok(),
        "init_tracing with an explicit endpoint should still succeed"
    );

    std::env::remove_var("OTEL_EXPORTER_OTLP_ENDPOINT");
}

#[tokio::test]
async fn test_init_tracing_with_config_accepts_service_name() {
    // #768: service.name used to be hardcoded to "agenkit" with no override, so
    // every consumer's spans were indistinguishable in a shared collector.
    let result = init_tracing_with_config("console", None, Some("my-service"), 1.0);
    assert!(
        result.is_ok(),
        "should accept a caller-supplied service name"
    );
}

#[tokio::test]
async fn test_init_tracing_with_config_clamps_sample_rate() {
    // Out-of-range rates are clamped rather than rejected: a bad rate should not
    // take down tracing initialization for the whole process.
    assert!(init_tracing_with_config("console", None, None, 5.0).is_ok());
    assert!(init_tracing_with_config("console", None, None, -1.0).is_ok());
}

#[tokio::test]
async fn test_init_tracing_with_config_rejects_unknown_exporter() {
    let result = init_tracing_with_config("nope", None, Some("svc"), 1.0);
    assert!(
        result.is_err(),
        "should reject an unsupported exporter type"
    );
}

#[tokio::test]
async fn test_tracing_middleware_error_is_propagated_not_swallowed() {
    // The span's status is recorded on the error path now (it used to be dropped
    // Unset by an early `?`, making a failure look like a success in the trace).
    // Asserting on the exported span's status would need a span exporter this
    // suite does not install — that is covered at the transport level in
    // test_observability_otlp_export.rs. Here we assert the error still reaches
    // the caller unchanged, which is what the added span.end() could have broken.
    init_tracing("console", None).unwrap();

    struct FailingAgent;

    #[async_trait]
    impl Agent for FailingAgent {
        fn name(&self) -> &str {
            "failing-agent"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError("boom".to_string()))
        }
    }

    let traced = TracingMiddleware::new(FailingAgent, None);
    let err = traced
        .process(Message::with_text("user", "test"))
        .await
        .expect_err("failing agent should surface its error");
    assert!(
        err.to_string().contains("boom"),
        "error message should be preserved verbatim, got: {err}"
    );
}
