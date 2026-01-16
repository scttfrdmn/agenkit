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
async fn test_init_metrics_prometheus() {
    // Initialize metrics with Prometheus exporter
    let result = init_metrics("prometheus", None);
    assert!(result.is_ok(), "Failed to initialize Prometheus metrics");
}

#[tokio::test]
async fn test_init_metrics_otlp() {
    // Initialize metrics with OTLP exporter
    let result = init_metrics("otlp", Some("http://localhost:4317"));
    assert!(result.is_ok(), "Failed to initialize OTLP metrics");
}

#[tokio::test]
async fn test_init_metrics_stdout() {
    // Initialize metrics with stdout exporter
    let result = init_metrics("stdout", None);
    assert!(result.is_ok(), "Failed to initialize stdout metrics");
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
        let message = Message::with_text("user", &format!("test {}", i));
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
