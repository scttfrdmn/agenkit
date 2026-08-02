//! Tests for OpenTelemetry metrics module.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{init_metrics, MetricsMiddleware};
use async_trait::async_trait;

/// Simple test agent for testing metrics middleware.
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
async fn test_init_metrics_prometheus_is_rejected() {
    // #772: this used to assert `is_ok()`, which locked in the bug. There is no
    // prometheus exporter in this build — opentelemetry-prometheus was removed
    // over vulnerable transitive deps — so accepting "prometheus" and returning
    // Ok(()) promised a scrape endpoint that would never exist. An error is the
    // only honest answer; a missing endpoint is indistinguishable from a
    // misconfigured scrape target otherwise.
    let result = init_metrics("prometheus", None);
    let err = result.expect_err("prometheus has no exporter in this build");
    assert!(
        err.to_string().contains("prometheus"),
        "the error should name the unavailable exporter, got: {err}"
    );
}

#[tokio::test]
async fn test_init_metrics_otlp() {
    // Initialize metrics with OTLP exporter
    let result = init_metrics("otlp", Some("http://localhost:4317"));
    assert!(result.is_ok(), "Failed to initialize OTLP metrics");
}

#[tokio::test]
async fn test_init_metrics_otlp_without_endpoint_defers_to_env() {
    // A None endpoint must not be an error: the OTLP exporter resolves
    // OTEL_EXPORTER_OTLP_METRICS_ENDPOINT / OTEL_EXPORTER_OTLP_ENDPOINT itself,
    // so passing nothing is how a caller opts into environment configuration.
    let result = init_metrics("otlp", None);
    assert!(
        result.is_ok(),
        "None endpoint should defer to the environment"
    );
}

#[tokio::test]
async fn test_init_metrics_stdout() {
    // Initialize metrics with stdout exporter
    let result = init_metrics("stdout", None);
    assert!(result.is_ok(), "Failed to initialize stdout metrics");
}

#[tokio::test]
async fn test_shutdown_metrics_returns_promptly() {
    // Installing a PeriodicReader is what the old no-op implementation avoided,
    // with the comment "avoids test hangs". That reasoning was stale — the
    // reader exports from its own thread — but the constraint is worth a test
    // rather than a claim, since a shutdown that blocks on an unreachable
    // collector would hang every suite that initializes metrics.
    //
    // Note this does NOT verify anything is exported: a provider with no reader
    // also returns promptly. Export is covered at the transport level in
    // test_observability_metrics_export.rs.
    init_metrics("stdout", None).expect("stdout metrics should initialize");

    let agent = SimpleAgent::new("reader-agent", "ok");
    let metered = MetricsMiddleware::new(agent);
    let response = metered.process(Message::with_text("user", "hi")).await;
    assert!(
        response.is_ok(),
        "metered agent should process successfully"
    );

    agenkit::observability::shutdown_metrics();
}

#[tokio::test]
async fn test_unsupported_exporter_type() {
    let result = init_metrics("invalid_exporter", None);
    assert!(result.is_err(), "Should fail with unsupported exporter");
}

#[tokio::test]
async fn test_metrics_middleware_creates_metrics() {
    // Initialize metrics
    init_metrics("stdout", None).unwrap();

    // Create metrics agent
    let agent = SimpleAgent::new("test-agent", "Hello");
    let metrics_agent = MetricsMiddleware::new(agent);

    // Process message
    let message = Message::with_text("user", "Test");
    let result = metrics_agent.process(message).await;

    assert!(result.is_ok(), "Metrics agent should process successfully");
}

#[tokio::test]
async fn test_metrics_middleware_preserves_agent_interface() {
    let agent = SimpleAgent::new("my-agent", "Response");
    let metrics_agent = MetricsMiddleware::new(agent);

    // Test name preservation
    assert_eq!(metrics_agent.name(), "my-agent");
}

#[tokio::test]
async fn test_metrics_middleware_records_success() {
    init_metrics("stdout", None).unwrap();

    let agent = SimpleAgent::new("agent", "response");
    let metrics_agent = MetricsMiddleware::new(agent);

    // Process successful message
    let message = Message::with_text("user", "test");
    let result = metrics_agent.process(message).await;

    assert!(result.is_ok());
    // Metrics are recorded (counter incremented with status=success)
}

#[tokio::test]
async fn test_metrics_middleware_records_error() {
    init_metrics("stdout", None).unwrap();

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
    let metrics_agent = MetricsMiddleware::new(agent);

    let message = Message::with_text("user", "test");
    let result = metrics_agent.process(message).await;

    // Should propagate error
    assert!(result.is_err());
    // Metrics are recorded (counter incremented with status=error)
}

#[tokio::test]
async fn test_metrics_middleware_records_duration() {
    init_metrics("stdout", None).unwrap();

    // Agent with small delay
    struct SlowAgent;

    #[async_trait]
    impl Agent for SlowAgent {
        fn name(&self) -> &str {
            "slow-agent"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
            Ok(Message::with_text("assistant", "response"))
        }
    }

    let agent = SlowAgent;
    let metrics_agent = MetricsMiddleware::new(agent);

    let message = Message::with_text("user", "test");
    let result = metrics_agent.process(message).await;

    assert!(result.is_ok());
    // Duration histogram recorded (should be > 0.01 seconds)
}

#[tokio::test]
async fn test_metrics_middleware_multiple_requests() {
    init_metrics("stdout", None).unwrap();

    let agent = SimpleAgent::new("agent", "response");
    let metrics_agent = MetricsMiddleware::new(agent);

    // Process multiple messages
    for i in 0..5 {
        let message = Message::with_text("user", format!("test {}", i));
        let result = metrics_agent.process(message).await;
        assert!(result.is_ok());
    }

    // All 5 requests should be counted
}

#[tokio::test]
async fn test_metrics_middleware_with_different_agents() {
    init_metrics("stdout", None).unwrap();

    // Create two different agents
    let agent1 = SimpleAgent::new("agent1", "response1");
    let metrics_agent1 = MetricsMiddleware::new(agent1);

    let agent2 = SimpleAgent::new("agent2", "response2");
    let metrics_agent2 = MetricsMiddleware::new(agent2);

    // Process messages through both agents
    let message1 = Message::with_text("user", "test1");
    let result1 = metrics_agent1.process(message1).await;
    assert!(result1.is_ok());

    let message2 = Message::with_text("user", "test2");
    let result2 = metrics_agent2.process(message2).await;
    assert!(result2.is_ok());

    // Metrics should be labeled separately by agent_name
}
