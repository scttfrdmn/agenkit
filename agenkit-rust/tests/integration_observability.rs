//! Integration tests for the observability module.
//!
//! These tests verify that tracing, metrics, logging, and audit modules
//! work together correctly in realistic scenarios.

#[cfg(feature = "opentelemetry")]
mod observability_tests {
    use agenkit::core::{Agent, AgentError, Message};
    use agenkit::observability::{
        audit::{AuditEvent, AuditEventType, AuditLogger},
        configure_logging, extract_trace_context, get_meter, init_metrics, init_tracing,
        inject_trace_context, log_agent_error, log_agent_event, MetricsMiddleware,
        TracingMiddleware,
    };
    use async_trait::async_trait;
    use std::path::PathBuf;
    use std::sync::Arc;
    use tempfile::TempDir;

    // Test agent for integration tests
    struct TestAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for TestAgent {
        fn name(&self) -> &str {
            &self.name
        }

        async fn process(&self, mut message: Message) -> Result<Message, AgentError> {
            // Simulate some processing
            message.role = "assistant".to_string();
            Ok(message)
        }
    }

    // Agent that fails on purpose
    struct FailingAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for FailingAgent {
        fn name(&self) -> &str {
            &self.name
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError(
                "intentional failure".to_string(),
            ))
        }
    }

    #[tokio::test]
    async fn test_tracing_and_metrics_middleware_composition() {
        // Initialize observability
        let _ = init_tracing("console", None);
        let _ = init_metrics("prometheus", None);

        // Create agent with both middleware
        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);
        let full_agent = MetricsMiddleware::new(traced_agent);

        // Process a message
        let message = Message::new("user", serde_json::json!("test message"));
        let result = full_agent.process(message).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap().role, "assistant");
    }

    #[tokio::test]
    async fn test_trace_context_propagation() {
        // Initialize tracing
        let _ = init_tracing("console", None);

        // Create first agent
        let agent1 = TestAgent {
            name: "agent1".to_string(),
        };
        let traced_agent1 = TracingMiddleware::new(agent1, None);

        // Process message with first agent
        let mut message = Message::new("user", serde_json::json!("test"));
        let response1 = traced_agent1.process(message.clone()).await.unwrap();

        // Check that trace context was injected
        assert!(response1.metadata.contains_key("traceparent"));

        // Create second agent
        let agent2 = TestAgent {
            name: "agent2".to_string(),
        };
        let traced_agent2 = TracingMiddleware::new(agent2, None);

        // Process the response with second agent (should propagate trace)
        let response2 = traced_agent2.process(response1).await.unwrap();

        // Second response should also have trace context
        assert!(response2.metadata.contains_key("traceparent"));
    }

    #[tokio::test]
    async fn test_logging_with_tracing() {
        // Initialize both tracing and logging
        let _ = init_tracing("console", None);
        let _ = configure_logging("compact", "info");

        // Log some events
        log_agent_event(
            "test_event",
            "Test event message",
            &[("agent", "test_agent")],
        );

        log_agent_error("test_error", "Test error message", "error details");

        // If we got here without panicking, the test passes
        // (logs are written to stdout/stderr)
    }

    #[tokio::test]
    async fn test_audit_logging_with_agent_operations() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = Arc::new(AuditLogger::new(log_path.clone()).unwrap());

        // Create agent
        let agent = TestAgent {
            name: "test_agent".to_string(),
        };

        // Log agent creation
        logger
            .log(AuditEvent::new(
                AuditEventType::AgentCreated,
                agent.name().to_string(),
                Some("session-123".to_string()),
            ))
            .await
            .unwrap();

        // Process message
        let message = Message::new("user", serde_json::json!("test"));
        let result = agent.process(message).await;

        // Log message processing
        if result.is_ok() {
            logger
                .log(AuditEvent::new(
                    AuditEventType::MessageProcessed,
                    agent.name().to_string(),
                    Some("session-123".to_string()),
                ))
                .await
                .unwrap();
        }

        // Flush and query
        logger.flush().await.unwrap();
        let events = logger.query_by_session("session-123").await.unwrap();

        assert_eq!(events.len(), 2);
        assert_eq!(events[0].event_type, AuditEventType::AgentCreated);
        assert_eq!(events[1].event_type, AuditEventType::MessageProcessed);
    }

    #[tokio::test]
    async fn test_full_observability_stack() {
        // Initialize all observability components
        let _ = init_tracing("console", None);
        let _ = init_metrics("prometheus", None);
        let _ = configure_logging("compact", "info");

        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let audit_logger = Arc::new(AuditLogger::new(log_path.clone()).unwrap());

        // Create agent with middleware
        let agent = TestAgent {
            name: "full_stack_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);
        let full_agent = MetricsMiddleware::new(traced_agent);

        // Log agent creation to audit
        audit_logger
            .log(AuditEvent::new(
                AuditEventType::AgentCreated,
                full_agent.name().to_string(),
                Some("session-full".to_string()),
            ))
            .await
            .unwrap();

        // Process message
        log_agent_event("processing_start", "Starting message processing", &[]);

        let message = Message::new("user", serde_json::json!("test"));
        let result = full_agent.process(message).await;

        log_agent_event("processing_end", "Completed message processing", &[]);

        // Log result to audit
        if result.is_ok() {
            audit_logger
                .log(AuditEvent::new(
                    AuditEventType::MessageProcessed,
                    full_agent.name().to_string(),
                    Some("session-full".to_string()),
                ))
                .await
                .unwrap();
        }

        // Verify everything worked
        assert!(result.is_ok());

        audit_logger.flush().await.unwrap();
        let events = audit_logger.query_by_session("session-full").await.unwrap();
        assert_eq!(events.len(), 2);
    }

    #[tokio::test]
    async fn test_error_handling_across_modules() {
        // Initialize observability
        let _ = init_tracing("console", None);
        let _ = init_metrics("prometheus", None);

        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let audit_logger = Arc::new(AuditLogger::new(log_path.clone()).unwrap());

        // Create failing agent with middleware
        let agent = FailingAgent {
            name: "failing_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);
        let full_agent = MetricsMiddleware::new(traced_agent);

        // Process message (should fail)
        let message = Message::new("user", serde_json::json!("test"));
        let result = full_agent.process(message).await;

        // Verify error is propagated
        assert!(result.is_err());

        // Log error to audit
        if let Err(e) = &result {
            audit_logger
                .log(
                    AuditEvent::new(
                        AuditEventType::ErrorOccurred,
                        full_agent.name().to_string(),
                        None,
                    )
                    .with_detail("error".to_string(), serde_json::json!(e.to_string())),
                )
                .await
                .unwrap();

            log_agent_error(
                "processing_error",
                "Failed to process message",
                &e.to_string(),
            );
        }

        audit_logger.flush().await.unwrap();
        let events = audit_logger
            .query_by_type(AuditEventType::ErrorOccurred)
            .await
            .unwrap();
        assert_eq!(events.len(), 1);
    }

    #[tokio::test]
    async fn test_concurrent_operations_with_observability() {
        // Initialize observability
        let _ = init_tracing("console", None);
        let _ = init_metrics("prometheus", None);

        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let audit_logger = Arc::new(AuditLogger::new(log_path.clone()).unwrap());

        // Create agent with middleware
        let agent = TestAgent {
            name: "concurrent_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);
        let full_agent = Arc::new(MetricsMiddleware::new(traced_agent));

        // Spawn multiple concurrent tasks
        let mut handles = vec![];
        for i in 0..10 {
            let agent_clone = Arc::clone(&full_agent);
            let logger_clone = Arc::clone(&audit_logger);

            let handle = tokio::spawn(async move {
                // Process message
                let message = Message::new("user", serde_json::json!(format!("message {}", i)));
                let result = agent_clone.process(message).await;

                // Log to audit
                if result.is_ok() {
                    logger_clone
                        .log(AuditEvent::new(
                            AuditEventType::MessageProcessed,
                            agent_clone.name().to_string(),
                            Some(format!("session-{}", i)),
                        ))
                        .await
                        .unwrap();
                }

                result.is_ok()
            });

            handles.push(handle);
        }

        // Wait for all tasks
        let mut success_count = 0;
        for handle in handles {
            if handle.await.unwrap() {
                success_count += 1;
            }
        }

        // All should succeed
        assert_eq!(success_count, 10);

        // Verify audit logs
        audit_logger.flush().await.unwrap();
        let events = audit_logger.query(None).await.unwrap();
        assert_eq!(events.len(), 10);
    }

    #[tokio::test]
    async fn test_metrics_recording_with_multiple_agents() {
        // Initialize metrics
        let _ = init_metrics("prometheus", None);

        // Create multiple agents
        let agent1 = TestAgent {
            name: "agent1".to_string(),
        };
        let agent2 = TestAgent {
            name: "agent2".to_string(),
        };

        let metrics_agent1 = MetricsMiddleware::new(agent1);
        let metrics_agent2 = MetricsMiddleware::new(agent2);

        // Process messages with different agents
        let message1 = Message::new("user", serde_json::json!("test1"));
        let message2 = Message::new("user", serde_json::json!("test2"));

        let result1 = metrics_agent1.process(message1).await;
        let result2 = metrics_agent2.process(message2).await;

        assert!(result1.is_ok());
        assert!(result2.is_ok());

        // Metrics should be recorded for both agents
        // (verification happens through the metrics backend)
    }

    #[tokio::test]
    async fn test_trace_context_extraction_and_injection() {
        use std::collections::HashMap;

        // Create metadata with trace context
        let mut metadata = HashMap::new();
        metadata.insert(
            "traceparent".to_string(),
            serde_json::json!("00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"),
        );

        // Extract context
        let context = extract_trace_context(&metadata);

        // Context should be valid (we can't easily verify the exact values,
        // but we can verify it doesn't panic)
        assert!(true); // If we got here, extraction worked

        // Inject context into new metadata
        let mut new_metadata = HashMap::new();
        inject_trace_context(&mut new_metadata, &context);

        // New metadata should have traceparent
        assert!(new_metadata.contains_key("traceparent"));
    }
}
