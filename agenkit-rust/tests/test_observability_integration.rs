//! Integration tests for observability modules.
//!
//! Tests how tracing, metrics, logging, and audit work together.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{
    configure_logging, init_metrics, init_tracing, log_agent_event, AuditEvent, AuditEventType,
    AuditLogger, MetricsMiddleware, TracingMiddleware,
};
use async_trait::async_trait;
use std::collections::HashMap;
use tempfile::TempDir;

/// Simple test agent
struct TestAgent {
    name: String,
    response: String,
}

impl TestAgent {
    fn new(name: &str, response: &str) -> Self {
        Self {
            name: name.to_string(),
            response: response.to_string(),
        }
    }
}

#[async_trait]
impl Agent for TestAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", &self.response))
    }
}

#[tokio::test]
async fn test_tracing_and_metrics_together() {
    // Initialize both tracing and metrics
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();

    // Create agent with both middlewares
    let agent = TestAgent::new("test-agent", "Hello");
    let traced_agent = TracingMiddleware::new(agent, None);
    let observed_agent = MetricsMiddleware::new(traced_agent);

    // Process message - both tracing and metrics should be recorded
    let message = Message::with_text("user", "test");
    let result = observed_agent.process(message).await;

    assert!(result.is_ok());
    // Tracing span created and metrics recorded
}

#[tokio::test]
async fn test_tracing_metrics_and_logging_together() {
    // Initialize all three
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();
    let _ = configure_logging("json", "info");

    // Create fully instrumented agent
    let agent = TestAgent::new("instrumented-agent", "Response");
    let traced = TracingMiddleware::new(agent, None);
    let observed = MetricsMiddleware::new(traced);

    // Log an event
    let mut details = HashMap::new();
    details.insert("agent".to_string(), serde_json::json!("instrumented-agent"));
    log_agent_event("agent.started", &details);

    // Process message
    let message = Message::with_text("user", "test");
    let result = observed.process(message).await;

    assert!(result.is_ok());
}

#[tokio::test]
async fn test_all_observability_modules() {
    // Initialize everything
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();
    let _ = configure_logging("json", "info");

    let temp_dir = TempDir::new().unwrap();
    let audit_logger = AuditLogger::new(temp_dir.path().join("audit.log"));

    // Create agent with tracing and metrics
    let agent = TestAgent::new("full-agent", "Response");
    let traced = TracingMiddleware::new(agent, None);
    let observed = MetricsMiddleware::new(traced);

    // Log audit event
    let audit_event = AuditEvent::new(
        AuditEventType::AgentCreated,
        "full-agent".to_string(),
        Some("session-123".to_string()),
    );
    audit_logger.log(audit_event).await.unwrap();

    // Log structured event
    let mut details = HashMap::new();
    details.insert("status".to_string(), serde_json::json!("active"));
    log_agent_event("agent.processing", &details);

    // Process message
    let message = Message::with_text("user", "test");
    let result = observed.process(message).await;
    assert!(result.is_ok());

    // Log another audit event
    let audit_event = AuditEvent::new(
        AuditEventType::MessageProcessed,
        "full-agent".to_string(),
        Some("session-123".to_string()),
    );
    audit_logger.log(audit_event).await.unwrap();
    audit_logger.flush().await.unwrap();

    // Verify audit events were logged
    let events = audit_logger
        .query(Some("session-123".to_string()))
        .await
        .unwrap();
    assert_eq!(events.len(), 2);
}

#[tokio::test]
async fn test_middleware_composition_order() {
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();

    let agent = TestAgent::new("agent", "response");

    // Order 1: Metrics -> Tracing
    let traced = TracingMiddleware::new(agent.clone(), None);
    let observed1 = MetricsMiddleware::new(traced);

    let message1 = Message::with_text("user", "test1");
    let result1 = observed1.process(message1).await;
    assert!(result1.is_ok());

    // Order 2: Tracing -> Metrics (different order)
    let agent2 = TestAgent::new("agent2", "response2");
    let observed2 = MetricsMiddleware::new(agent2);
    let traced2 = TracingMiddleware::new(observed2, None);

    let message2 = Message::with_text("user", "test2");
    let result2 = traced2.process(message2).await;
    assert!(result2.is_ok());

    // Both orders should work
}

#[tokio::test]
async fn test_trace_context_propagation_with_metrics() {
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();

    // First agent with both tracing and metrics
    let agent1 = TestAgent::new("agent1", "response1");
    let traced1 = TracingMiddleware::new(agent1, None);
    let observed1 = MetricsMiddleware::new(traced1);

    // Process through first agent
    let message1 = Message::with_text("user", "test");
    let response1 = observed1.process(message1).await.unwrap();

    // Trace context should be in response metadata
    assert!(response1.metadata.contains_key("trace_context"));

    // Second agent with both tracing and metrics
    let agent2 = TestAgent::new("agent2", "response2");
    let traced2 = TracingMiddleware::new(agent2, None);
    let observed2 = MetricsMiddleware::new(traced2);

    // Process through second agent with trace context
    let response2 = observed2.process(response1).await.unwrap();

    // Trace context should still be present
    assert!(response2.metadata.contains_key("trace_context"));
}

#[tokio::test]
async fn test_multi_agent_workflow_with_observability() {
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();
    let _ = configure_logging("json", "info");

    let temp_dir = TempDir::new().unwrap();
    let audit_logger = AuditLogger::new(temp_dir.path().join("workflow.log"));

    // Create a pipeline of 3 agents
    let agent1 = TestAgent::new("preprocessor", "preprocessed");
    let traced1 = TracingMiddleware::new(agent1, Some("workflow.preprocess"));
    let observed1 = MetricsMiddleware::new(traced1);

    let agent2 = TestAgent::new("processor", "processed");
    let traced2 = TracingMiddleware::new(agent2, Some("workflow.process"));
    let observed2 = MetricsMiddleware::new(traced2);

    let agent3 = TestAgent::new("postprocessor", "final");
    let traced3 = TracingMiddleware::new(agent3, Some("workflow.postprocess"));
    let observed3 = MetricsMiddleware::new(traced3);

    // Process through pipeline
    let message = Message::with_text("user", "start");

    // Stage 1: Preprocess
    let audit_event = AuditEvent::new(
        AuditEventType::MessageProcessed,
        "preprocessor".to_string(),
        Some("workflow-1".to_string()),
    );
    audit_logger.log(audit_event).await.unwrap();
    let result1 = observed1.process(message).await.unwrap();

    // Stage 2: Process
    let audit_event = AuditEvent::new(
        AuditEventType::MessageProcessed,
        "processor".to_string(),
        Some("workflow-1".to_string()),
    );
    audit_logger.log(audit_event).await.unwrap();
    let result2 = observed2.process(result1).await.unwrap();

    // Stage 3: Postprocess
    let audit_event = AuditEvent::new(
        AuditEventType::MessageProcessed,
        "postprocessor".to_string(),
        Some("workflow-1".to_string()),
    );
    audit_logger.log(audit_event).await.unwrap();
    let result3 = observed3.process(result2).await.unwrap();

    // Content might be JSON string with quotes
    let content_str = result3.content.to_string();
    assert!(content_str == "final" || content_str == "\"final\"");

    // Flush and verify audit trail
    audit_logger.flush().await.unwrap();
    let events = audit_logger
        .query(Some("workflow-1".to_string()))
        .await
        .unwrap();
    assert_eq!(events.len(), 3);
}

#[tokio::test]
async fn test_error_handling_with_all_observability() {
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();
    let _ = configure_logging("json", "info");

    let temp_dir = TempDir::new().unwrap();
    let audit_logger = AuditLogger::new(temp_dir.path().join("errors.log"));

    // Agent that fails
    struct ErrorAgent;
    #[async_trait]
    impl Agent for ErrorAgent {
        fn name(&self) -> &str {
            "error-agent"
        }
        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError("Intentional error".to_string()))
        }
    }

    let agent = ErrorAgent;
    let traced = TracingMiddleware::new(agent, None);
    let observed = MetricsMiddleware::new(traced);

    // Process message - will fail
    let message = Message::with_text("user", "test");
    let result = observed.process(message).await;

    assert!(result.is_err());

    // Log the error in audit
    let audit_event = AuditEvent::new(
        AuditEventType::SecurityViolation,
        "error-agent".to_string(),
        None,
    );
    audit_logger.log(audit_event).await.unwrap();
    audit_logger.flush().await.unwrap();

    let events = audit_logger.query(None).await.unwrap();
    assert_eq!(events.len(), 1);
}

#[tokio::test]
async fn test_concurrent_agents_with_observability() {
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();

    let temp_dir = TempDir::new().unwrap();
    let audit_logger = AuditLogger::new(temp_dir.path().join("concurrent.log"));

    // Create multiple agents
    let mut handles = vec![];

    for i in 0..5 {
        let agent = TestAgent::new(&format!("agent-{}", i), &format!("response-{}", i));
        let traced = TracingMiddleware::new(agent, None);
        let observed = MetricsMiddleware::new(traced);

        let logger_clone = audit_logger.clone();

        let handle = tokio::spawn(async move {
            // Log audit event
            let audit_event = AuditEvent::new(
                AuditEventType::MessageProcessed,
                format!("agent-{}", i),
                Some("concurrent-test".to_string()),
            );
            logger_clone.log(audit_event).await.unwrap();

            // Process message
            let message = Message::with_text("user", format!("test-{}", i));
            observed.process(message).await.unwrap()
        });

        handles.push(handle);
    }

    // Wait for all to complete
    for handle in handles {
        let result = handle.await.unwrap();
        let content = result.content.to_string();
        // Content might be JSON string with quotes
        assert!(content.contains("response-"));
    }

    // Verify all audit events
    audit_logger.flush().await.unwrap();
    let events = audit_logger
        .query(Some("concurrent-test".to_string()))
        .await
        .unwrap();
    assert_eq!(events.len(), 5);
}

#[tokio::test]
async fn test_session_tracking_across_modules() {
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();

    let temp_dir = TempDir::new().unwrap();
    let audit_logger = AuditLogger::new(temp_dir.path().join("sessions.log"));

    let session_id = "session-xyz-789";

    // Simulate multiple operations in same session
    for i in 0..3 {
        let agent = TestAgent::new("session-agent", "response");
        let traced = TracingMiddleware::new(agent, None);
        let observed = MetricsMiddleware::new(traced);

        // Add session_id to message metadata
        let message = Message::with_text("user", format!("message-{}", i))
            .with_metadata("session_id", serde_json::json!(session_id));

        observed.process(message).await.unwrap();

        // Log audit event with session
        let audit_event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            "session-agent".to_string(),
            Some(session_id.to_string()),
        );
        audit_logger.log(audit_event).await.unwrap();
    }

    audit_logger.flush().await.unwrap();

    // Query by session - should get all 3 events
    let events = audit_logger
        .query(Some(session_id.to_string()))
        .await
        .unwrap();
    assert_eq!(events.len(), 3);
}

#[tokio::test]
async fn test_observability_with_metadata_enrichment() {
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();

    let agent = TestAgent::new("enriched-agent", "response");
    let traced = TracingMiddleware::new(agent, None);
    let observed = MetricsMiddleware::new(traced);

    // Message with rich metadata
    let message = Message::with_text("user", "test")
        .with_metadata("user_id", serde_json::json!("user-123"))
        .with_metadata("ip_address", serde_json::json!("192.168.1.1"))
        .with_metadata("timestamp", serde_json::json!(1234567890));

    let result = observed.process(message).await.unwrap();

    // Metadata should be preserved
    assert!(result.metadata.contains_key("trace_context"));
}

#[tokio::test]
async fn test_performance_with_full_observability() {
    init_tracing("console", None).unwrap();
    init_metrics("stdout", None).unwrap();

    let agent = TestAgent::new("perf-agent", "fast");
    let traced = TracingMiddleware::new(agent, None);
    let observed = MetricsMiddleware::new(traced);

    // Process many messages quickly
    let start = std::time::Instant::now();

    for i in 0..100 {
        let message = Message::with_text("user", format!("msg-{}", i));
        observed.process(message).await.unwrap();
    }

    let duration = start.elapsed();

    // Should complete reasonably fast even with full observability
    assert!(duration.as_secs() < 5, "Took too long: {:?}", duration);
}

// Add Clone trait to TestAgent for concurrent tests
impl Clone for TestAgent {
    fn clone(&self) -> Self {
        Self {
            name: self.name.clone(),
            response: self.response.clone(),
        }
    }
}
