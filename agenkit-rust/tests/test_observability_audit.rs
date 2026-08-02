//! Tests for audit logging module.

use agenkit::observability::{AuditEvent, AuditEventType, AuditLogger, AuditSeverity};
use std::path::PathBuf;
use tempfile::TempDir;

/// Helper to create a temporary audit log file
fn create_temp_logger() -> (AuditLogger, TempDir) {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("audit.log");
    let logger = AuditLogger::new(log_path);
    (logger, temp_dir)
}

#[tokio::test]
async fn test_audit_logger_creation() {
    let (logger, _temp_dir) = create_temp_logger();
    assert_eq!(logger.buffer_len().await, 0);
}

#[tokio::test]
async fn test_audit_event_creation() {
    let event = AuditEvent::new(
        AuditEventType::MessageProcessed,
        "test-agent".to_string(),
        Some("session-123".to_string()),
    );

    assert!(!event.event_id.is_empty());
    assert_eq!(event.event_type, AuditEventType::MessageProcessed);
    assert_eq!(event.severity, AuditSeverity::Info);
    assert_eq!(event.agent_name, "test-agent");
    assert_eq!(event.session_id, Some("session-123".to_string()));
}

#[tokio::test]
async fn test_audit_event_with_severity() {
    let event = AuditEvent::with_severity(
        AuditEventType::SecurityViolation,
        AuditSeverity::Critical,
        "agent".to_string(),
        None,
    );

    assert_eq!(event.severity, AuditSeverity::Critical);
}

#[tokio::test]
async fn test_audit_event_add_detail() {
    let event = AuditEvent::new(
        AuditEventType::ConfigurationChanged,
        "agent".to_string(),
        None,
    )
    .add_detail("key1".to_string(), serde_json::json!("value1"))
    .add_detail("key2".to_string(), serde_json::json!(42));

    assert_eq!(event.details.len(), 2);
    assert_eq!(
        event.details.get("key1"),
        Some(&serde_json::json!("value1"))
    );
    assert_eq!(event.details.get("key2"), Some(&serde_json::json!(42)));
}

#[tokio::test]
async fn test_log_audit_event() {
    let (logger, _temp_dir) = create_temp_logger();

    let event = AuditEvent::new(AuditEventType::AgentCreated, "agent".to_string(), None);

    let result = logger.log(event).await;
    assert!(result.is_ok());
    assert_eq!(logger.buffer_len().await, 1);
}

#[tokio::test]
async fn test_log_multiple_events() {
    let (logger, _temp_dir) = create_temp_logger();

    for i in 0..5 {
        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            format!("agent-{}", i),
            Some(format!("session-{}", i)),
        );
        logger.log(event).await.unwrap();
    }

    assert_eq!(logger.buffer_len().await, 5);
}

#[tokio::test]
async fn test_auto_flush_on_buffer_full() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("audit.log");

    // Create logger with small buffer size
    let logger = AuditLogger::with_buffer_size(log_path.clone(), 3);

    // Log 3 events - should trigger auto-flush
    for i in 0..3 {
        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            format!("agent-{}", i),
            None,
        );
        logger.log(event).await.unwrap();
    }

    // Buffer should be empty after auto-flush
    assert_eq!(logger.buffer_len().await, 0);

    // File should exist and contain 3 events
    let contents = tokio::fs::read_to_string(&log_path).await.unwrap();
    assert_eq!(contents.lines().count(), 3);
}

#[tokio::test]
async fn test_manual_flush() {
    let (logger, temp_dir) = create_temp_logger();
    let log_path = temp_dir.path().join("audit.log");

    // Log some events
    for i in 0..2 {
        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            format!("agent-{}", i),
            None,
        );
        logger.log(event).await.unwrap();
    }

    assert_eq!(logger.buffer_len().await, 2);

    // Manual flush
    logger.flush().await.unwrap();

    // Buffer should be empty
    assert_eq!(logger.buffer_len().await, 0);

    // File should contain events
    let contents = tokio::fs::read_to_string(&log_path).await.unwrap();
    assert_eq!(contents.lines().count(), 2);
}

#[tokio::test]
async fn test_query_all_events() {
    let (logger, _temp_dir) = create_temp_logger();

    // Log and flush events
    for i in 0..3 {
        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            format!("agent-{}", i),
            Some(format!("session-{}", i)),
        );
        logger.log(event).await.unwrap();
    }
    logger.flush().await.unwrap();

    // Query all events
    let events = logger.query(None).await.unwrap();
    assert_eq!(events.len(), 3);
}

#[tokio::test]
async fn test_query_by_session_id() {
    let (logger, _temp_dir) = create_temp_logger();

    // Log events with different session IDs
    for i in 0..5 {
        let session_id = if i % 2 == 0 {
            Some("session-even".to_string())
        } else {
            Some("session-odd".to_string())
        };

        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            format!("agent-{}", i),
            session_id,
        );
        logger.log(event).await.unwrap();
    }
    logger.flush().await.unwrap();

    // Query by specific session
    let even_events = logger
        .query(Some("session-even".to_string()))
        .await
        .unwrap();
    assert_eq!(even_events.len(), 3); // 0, 2, 4

    let odd_events = logger.query(Some("session-odd".to_string())).await.unwrap();
    assert_eq!(odd_events.len(), 2); // 1, 3
}

#[tokio::test]
async fn test_query_empty_log() {
    let (logger, _temp_dir) = create_temp_logger();

    // Query before logging anything
    let events = logger.query(None).await;

    // Should handle empty file gracefully (might fail with file not found)
    match events {
        Ok(evts) => assert_eq!(evts.len(), 0),
        Err(_) => {} // File doesn't exist yet - acceptable
    }
}

#[tokio::test]
async fn test_concurrent_logging() {
    let (logger, _temp_dir) = create_temp_logger();

    // Log concurrently from multiple tasks
    let mut handles = vec![];
    for i in 0..10 {
        let logger_clone = logger.clone();
        let handle = tokio::spawn(async move {
            let event = AuditEvent::new(
                AuditEventType::MessageProcessed,
                format!("agent-{}", i),
                Some(format!("session-{}", i)),
            );
            logger_clone.log(event).await.unwrap();
        });
        handles.push(handle);
    }

    // Wait for all tasks
    for handle in handles {
        handle.await.unwrap();
    }

    logger.flush().await.unwrap();

    // All 10 events should be logged
    let events = logger.query(None).await.unwrap();
    assert_eq!(events.len(), 10);
}

#[tokio::test]
async fn test_all_event_types() {
    let (logger, _temp_dir) = create_temp_logger();

    let event_types = vec![
        AuditEventType::AgentCreated,
        AuditEventType::MessageProcessed,
        AuditEventType::SecurityViolation,
        AuditEventType::ConfigurationChanged,
    ];

    for event_type in event_types {
        let event = AuditEvent::new(event_type.clone(), "agent".to_string(), None);
        logger.log(event).await.unwrap();
    }

    logger.flush().await.unwrap();
    let events = logger.query(None).await.unwrap();
    assert_eq!(events.len(), 4);
}

#[tokio::test]
async fn test_all_severities() {
    let (logger, _temp_dir) = create_temp_logger();

    let severities = vec![
        AuditSeverity::Info,
        AuditSeverity::Warning,
        AuditSeverity::Error,
        AuditSeverity::Critical,
    ];

    for severity in severities {
        let event = AuditEvent::with_severity(
            AuditEventType::MessageProcessed,
            severity,
            "agent".to_string(),
            None,
        );
        logger.log(event).await.unwrap();
    }

    logger.flush().await.unwrap();
    let events = logger.query(None).await.unwrap();
    assert_eq!(events.len(), 4);
}

#[tokio::test]
async fn test_event_serialization() {
    let event = AuditEvent::new(
        AuditEventType::MessageProcessed,
        "agent".to_string(),
        Some("session-123".to_string()),
    )
    .add_detail("key".to_string(), serde_json::json!("value"));

    // Serialize to JSON
    let json = serde_json::to_string(&event).unwrap();
    assert!(!json.is_empty());

    // Deserialize back
    let deserialized: AuditEvent = serde_json::from_str(&json).unwrap();
    assert_eq!(deserialized.event_id, event.event_id);
    assert_eq!(deserialized.agent_name, event.agent_name);
}

#[tokio::test]
async fn test_buffer_management() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("audit.log");
    let logger = AuditLogger::with_buffer_size(log_path, 5);

    // Add 3 events
    for i in 0..3 {
        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            format!("agent-{}", i),
            None,
        );
        logger.log(event).await.unwrap();
    }
    assert_eq!(logger.buffer_len().await, 3);

    // Add 2 more - should trigger auto-flush at 5
    for i in 3..5 {
        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            format!("agent-{}", i),
            None,
        );
        logger.log(event).await.unwrap();
    }
    assert_eq!(logger.buffer_len().await, 0); // Auto-flushed
}
