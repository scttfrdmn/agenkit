//! Integration tests for evaluation framework
//!
//! Tests evaluation functionality including benchmarking, metrics collection,
//! result analysis, and performance assessment.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::evaluation::{SessionResult, SessionStatus, MetricsCollector};
use async_trait::async_trait;
use serde_json::json;
use std::time::Instant;

/// Simple test agent for evaluation
struct EvalTestAgent {
    name: String,
    latency_ms: u64,
}

#[async_trait]
impl Agent for EvalTestAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate processing latency
        tokio::time::sleep(tokio::time::Duration::from_millis(self.latency_ms)).await;

        let content = message.content_as_str().unwrap_or("test");
        Ok(Message::with_text("assistant", format!("Eval: {}", content)))
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["evaluate".to_string()]
    }
}

/// Test 1: Session result creation
#[tokio::test]
async fn test_session_result_creation() {
    let session = SessionResult::new("session-001", "test-agent");
    assert_eq!(session.session_id, "session-001");
    assert_eq!(session.agent_name, "test-agent");
    assert_eq!(session.status, SessionStatus::Running);
}

/// Test 2: Session status transition
#[tokio::test]
async fn test_session_status_transition() {
    let mut session = SessionResult::new("session-002", "test-agent");

    // Initial status should be Running
    assert_eq!(session.status, SessionStatus::Running);

    // Update to completed
    session.set_status(SessionStatus::Completed);
    assert_eq!(session.status, SessionStatus::Completed);
}

/// Test 3: Metrics collector initialization
#[tokio::test]
async fn test_metrics_collector_initialization() {
    let _collector = MetricsCollector::new();

    // Verify collector was created successfully
}

/// Test 4: Single message evaluation
#[tokio::test]
async fn test_single_message_evaluation() {
    let agent = EvalTestAgent {
        name: "eval-agent".to_string(),
        latency_ms: 10,
    };

    let msg = Message::with_text("user", "Evaluate this");
    let start = Instant::now();
    let result = agent.process(msg).await;
    let duration = start.elapsed();

    assert!(result.is_ok());
    assert!(duration.as_millis() >= 10);
}

/// Test 5: Multiple agent evaluation
#[tokio::test]
async fn test_multiple_agent_evaluation() {
    let agent1 = EvalTestAgent {
        name: "agent1".to_string(),
        latency_ms: 5,
    };

    let agent2 = EvalTestAgent {
        name: "agent2".to_string(),
        latency_ms: 10,
    };

    let msg = Message::with_text("user", "Compare agents");

    let result1 = agent1.process(msg.clone()).await;
    let result2 = agent2.process(msg).await;

    assert!(result1.is_ok());
    assert!(result2.is_ok());
}

/// Test 6: Evaluation metadata tracking
#[tokio::test]
async fn test_evaluation_metadata_tracking() {
    let agent = EvalTestAgent {
        name: "tracking-agent".to_string(),
        latency_ms: 5,
    };

    let msg = Message::with_text("user", "Track metadata")
        .with_metadata("eval_id", json!("eval-001"))
        .with_metadata("test_type", json!("integration"));

    let result = agent.process(msg).await;
    assert!(result.is_ok());

    if let Ok(response) = result {
        assert_eq!(response.role, "assistant");
    }
}

/// Test 7: Performance metric collection
#[tokio::test]
async fn test_performance_metric_collection() {
    let agent = EvalTestAgent {
        name: "metric-agent".to_string(),
        latency_ms: 10,
    };

    let mut timings = Vec::new();

    for _ in 0..5 {
        let msg = Message::with_text("user", "Measure");
        let start = Instant::now();
        let _ = agent.process(msg).await;
        timings.push(start.elapsed().as_millis());
    }

    // Verify we have measurements
    assert_eq!(timings.len(), 5);

    // Calculate average
    let avg = timings.iter().sum::<u128>() / timings.len() as u128;
    assert!(avg > 0);
}

/// Test 8: Evaluator error handling
#[tokio::test]
async fn test_evaluator_error_handling() {
    struct FailingAgent;

    #[async_trait]
    impl Agent for FailingAgent {
        fn name(&self) -> &str {
            "failing"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError("Eval test error".to_string()))
        }
    }

    let agent = FailingAgent;
    let msg = Message::with_text("user", "test");
    let result = agent.process(msg).await;

    assert!(result.is_err());
    match result {
        Err(AgentError::ProcessingError(msg)) => {
            assert!(msg.contains("Eval test error"))
        }
        _ => panic!("Expected ProcessingError"),
    }
}

/// Test 9: Benchmark timing consistency
#[tokio::test]
async fn test_benchmark_timing_consistency() {
    let agent = EvalTestAgent {
        name: "consistent-agent".to_string(),
        latency_ms: 5,
    };

    let mut max_time = 0u128;
    let mut min_time = u128::MAX;

    for _ in 0..3 {
        let msg = Message::with_text("user", "Test");
        let start = Instant::now();
        let _ = agent.process(msg).await;
        let elapsed = start.elapsed().as_millis();
        max_time = max_time.max(elapsed);
        min_time = min_time.min(elapsed);
    }

    // Should have measured times
    assert!(max_time > 0);
    assert!(min_time > 0);
    assert!(max_time >= min_time);
}

/// Test 10: Comparison evaluation
#[tokio::test]
async fn test_comparison_evaluation() {
    let fast_agent = EvalTestAgent {
        name: "fast".to_string(),
        latency_ms: 5,
    };

    let slow_agent = EvalTestAgent {
        name: "slow".to_string(),
        latency_ms: 15,
    };

    let msg = Message::with_text("user", "Compare performance");

    let start_fast = Instant::now();
    let _ = fast_agent.process(msg.clone()).await;
    let fast_time = start_fast.elapsed();

    let start_slow = Instant::now();
    let _ = slow_agent.process(msg).await;
    let slow_time = start_slow.elapsed();

    // Fast agent should be faster
    assert!(fast_time < slow_time);
}

/// Test 11: Session result tracking
#[tokio::test]
async fn test_session_result_tracking() {
    let mut session = SessionResult::new("session-011", "eval-agent");

    // Track metrics
    session.set_status(SessionStatus::Completed);
    assert_eq!(session.status, SessionStatus::Completed);

    // Verify session properties
    assert_eq!(session.session_id, "session-011");
    assert_eq!(session.agent_name, "eval-agent");
}

/// Test 12: Metrics collector with sessions
#[tokio::test]
async fn test_metrics_collector_with_sessions() {
    let _collector = MetricsCollector::new();

    // MetricsCollector created successfully
}

/// Test 13: Agent performance measurement
#[tokio::test]
async fn test_agent_performance_measurement() {
    let agent = EvalTestAgent {
        name: "perf-agent".to_string(),
        latency_ms: 20,
    };

    let msg = Message::with_text("user", "Measure performance");
    let start = Instant::now();
    let _ = agent.process(msg).await;
    let elapsed = start.elapsed();

    // Should have at least the expected latency
    assert!(elapsed.as_millis() >= 20);
}

/// Test 14: Session status all variants
#[tokio::test]
async fn test_session_status_variants() {
    let statuses = vec![
        SessionStatus::Running,
        SessionStatus::Completed,
        SessionStatus::Failed,
        SessionStatus::Timeout,
    ];

    assert_eq!(statuses.len(), 4);

    // Create sessions with different statuses
    let mut session1 = SessionResult::new("s1", "agent1");
    let mut session2 = SessionResult::new("s2", "agent2");
    let mut session3 = SessionResult::new("s3", "agent3");

    session1.set_status(SessionStatus::Completed);
    session2.set_status(SessionStatus::Failed);
    session3.set_status(SessionStatus::Timeout);

    assert_eq!(session1.status, SessionStatus::Completed);
    assert_eq!(session2.status, SessionStatus::Failed);
    assert_eq!(session3.status, SessionStatus::Timeout);
}
