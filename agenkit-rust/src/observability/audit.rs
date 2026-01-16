//! Audit logging for compliance and security.
//!
//! This module provides event logging with buffering, querying,
//! and persistence for compliance requirements.
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::observability::audit::{AuditLogger, AuditEvent, AuditEventType};
//! use std::path::PathBuf;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Create audit logger
//! let logger = AuditLogger::new(PathBuf::from("/tmp/audit.log"))?;
//!
//! // Log an event
//! let event = AuditEvent::new(
//!     AuditEventType::AgentCreated,
//!     "MyAgent".to_string(),
//!     Some("session-123".to_string())
//! );
//! logger.log(event).await?;
//!
//! // Flush to disk
//! logger.flush().await?;
//! # Ok(())
//! # }
//! ```

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::fs::OpenOptions;
use tokio::io::AsyncWriteExt;
use tokio::sync::Mutex;
use uuid::Uuid;

/// Types of audit events.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum AuditEventType {
    /// Agent was created
    AgentCreated,
    /// Message was processed
    MessageProcessed,
    /// Security violation occurred
    SecurityViolation,
    /// Configuration changed
    ConfigurationChanged,
    /// Error occurred
    ErrorOccurred,
    /// User action
    UserAction,
    /// System event
    SystemEvent,
}

/// Severity levels for audit events.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum Severity {
    /// Informational event
    Info,
    /// Warning event
    Warning,
    /// Error event
    Error,
    /// Critical event
    Critical,
}

/// An audit event with metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEvent {
    /// Unique event ID
    pub event_id: String,
    /// Timestamp of the event
    pub timestamp: DateTime<Utc>,
    /// Type of event
    pub event_type: AuditEventType,
    /// Name of the agent
    pub agent_name: String,
    /// Optional session ID
    pub session_id: Option<String>,
    /// Additional details
    pub details: HashMap<String, serde_json::Value>,
    /// Event severity
    pub severity: Severity,
}

impl AuditEvent {
    /// Create a new audit event.
    pub fn new(event_type: AuditEventType, agent_name: String, session_id: Option<String>) -> Self {
        Self {
            event_id: Uuid::new_v4().to_string(),
            timestamp: Utc::now(),
            event_type,
            agent_name,
            session_id,
            details: HashMap::new(),
            severity: Severity::Info,
        }
    }

    /// Add a detail field to the event.
    pub fn with_detail(mut self, key: String, value: serde_json::Value) -> Self {
        self.details.insert(key, value);
        self
    }

    /// Set the severity of the event.
    pub fn with_severity(mut self, severity: Severity) -> Self {
        self.severity = severity;
        self
    }
}

/// Audit logger with buffering and async persistence.
pub struct AuditLogger {
    log_path: PathBuf,
    buffer: Arc<Mutex<Vec<AuditEvent>>>,
    buffer_size: usize,
}

impl AuditLogger {
    /// Create a new audit logger.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the audit log file
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use agenkit::observability::audit::AuditLogger;
    /// use std::path::PathBuf;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let logger = AuditLogger::new(PathBuf::from("/tmp/audit.log"))?;
    /// # Ok(())
    /// # }
    /// ```
    pub fn new(log_path: PathBuf) -> Result<Self, std::io::Error> {
        Ok(Self {
            log_path,
            buffer: Arc::new(Mutex::new(Vec::new())),
            buffer_size: 100,
        })
    }

    /// Create a new audit logger with custom buffer size.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the audit log file
    /// * `buffer_size` - Maximum number of events to buffer before auto-flush
    pub fn with_buffer_size(log_path: PathBuf, buffer_size: usize) -> Result<Self, std::io::Error> {
        Ok(Self {
            log_path,
            buffer: Arc::new(Mutex::new(Vec::new())),
            buffer_size,
        })
    }

    /// Log an audit event.
    ///
    /// Events are buffered and flushed when the buffer is full or `flush()` is called.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use agenkit::observability::audit::{AuditLogger, AuditEvent, AuditEventType};
    /// use std::path::PathBuf;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let logger = AuditLogger::new(PathBuf::from("/tmp/audit.log"))?;
    /// let event = AuditEvent::new(
    ///     AuditEventType::MessageProcessed,
    ///     "MyAgent".to_string(),
    ///     None
    /// );
    /// logger.log(event).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn log(&self, event: AuditEvent) -> Result<(), std::io::Error> {
        let mut buffer = self.buffer.lock().await;
        buffer.push(event);

        // Auto-flush if buffer is full
        if buffer.len() >= self.buffer_size {
            self.flush_internal(&mut buffer).await?;
        }

        Ok(())
    }

    /// Flush all buffered events to disk.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use agenkit::observability::audit::AuditLogger;
    /// use std::path::PathBuf;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let logger = AuditLogger::new(PathBuf::from("/tmp/audit.log"))?;
    /// logger.flush().await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn flush(&self) -> Result<(), std::io::Error> {
        let mut buffer = self.buffer.lock().await;
        self.flush_internal(&mut buffer).await
    }

    /// Internal flush implementation (buffer must already be locked).
    async fn flush_internal(&self, buffer: &mut Vec<AuditEvent>) -> Result<(), std::io::Error> {
        if buffer.is_empty() {
            return Ok(());
        }

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.log_path)
            .await?;

        for event in buffer.iter() {
            let json = serde_json::to_string(event)
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
            file.write_all(json.as_bytes()).await?;
            file.write_all(b"\n").await?;
        }

        file.sync_all().await?;
        buffer.clear();

        Ok(())
    }

    /// Query audit events from the log file.
    ///
    /// # Arguments
    ///
    /// * `filter` - Optional filter function to select events
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use agenkit::observability::audit::{AuditLogger, AuditEventType};
    /// use std::path::PathBuf;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let logger = AuditLogger::new(PathBuf::from("/tmp/audit.log"))?;
    ///
    /// // Query events for a specific agent
    /// let events = logger.query(Some(Box::new(|event| {
    ///     event.agent_name == "MyAgent"
    /// }))).await?;
    /// # Ok(())
    /// # }
    /// ```
    #[allow(clippy::type_complexity)]
    pub async fn query(
        &self,
        filter: Option<Box<dyn Fn(&AuditEvent) -> bool + Send>>,
    ) -> Result<Vec<AuditEvent>, std::io::Error> {
        // First flush any buffered events
        self.flush().await?;

        // Read the log file
        let content = tokio::fs::read_to_string(&self.log_path).await?;

        let mut events = Vec::new();
        for line in content.lines() {
            if line.is_empty() {
                continue;
            }

            match serde_json::from_str::<AuditEvent>(line) {
                Ok(event) => {
                    if let Some(ref f) = filter {
                        if f(&event) {
                            events.push(event);
                        }
                    } else {
                        events.push(event);
                    }
                }
                Err(_) => continue,
            }
        }

        Ok(events)
    }

    /// Query events by session ID.
    pub async fn query_by_session(
        &self,
        session_id: &str,
    ) -> Result<Vec<AuditEvent>, std::io::Error> {
        let session_id = session_id.to_string();
        self.query(Some(Box::new(move |event| {
            event.session_id.as_ref() == Some(&session_id)
        })))
        .await
    }

    /// Query events by agent name.
    pub async fn query_by_agent(
        &self,
        agent_name: &str,
    ) -> Result<Vec<AuditEvent>, std::io::Error> {
        let agent_name = agent_name.to_string();
        self.query(Some(Box::new(move |event| event.agent_name == agent_name)))
            .await
    }

    /// Query events by event type.
    pub async fn query_by_type(
        &self,
        event_type: AuditEventType,
    ) -> Result<Vec<AuditEvent>, std::io::Error> {
        self.query(Some(Box::new(move |event| event.event_type == event_type)))
            .await
    }

    /// Get the number of buffered events.
    pub async fn buffer_len(&self) -> usize {
        self.buffer.lock().await.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_audit_event_creation() {
        let event = AuditEvent::new(
            AuditEventType::AgentCreated,
            "test_agent".to_string(),
            Some("session-123".to_string()),
        );

        assert_eq!(event.event_type, AuditEventType::AgentCreated);
        assert_eq!(event.agent_name, "test_agent");
        assert_eq!(event.session_id, Some("session-123".to_string()));
        assert_eq!(event.severity, Severity::Info);
        assert!(!event.event_id.is_empty());
    }

    #[test]
    fn test_audit_event_with_details() {
        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            "test_agent".to_string(),
            None,
        )
        .with_detail("duration_ms".to_string(), serde_json::json!(150))
        .with_detail("tokens".to_string(), serde_json::json!(50));

        assert_eq!(event.details.len(), 2);
        assert_eq!(
            event.details.get("duration_ms"),
            Some(&serde_json::json!(150))
        );
    }

    #[test]
    fn test_audit_event_with_severity() {
        let event = AuditEvent::new(
            AuditEventType::SecurityViolation,
            "test_agent".to_string(),
            None,
        )
        .with_severity(Severity::Critical);

        assert_eq!(event.severity, Severity::Critical);
    }

    #[tokio::test]
    async fn test_audit_logger_creation() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");

        let logger = AuditLogger::new(log_path);
        assert!(logger.is_ok());
    }

    #[tokio::test]
    async fn test_audit_logger_log_single_event() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = AuditLogger::new(log_path.clone()).unwrap();

        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            "test_agent".to_string(),
            None,
        );

        let result = logger.log(event).await;
        assert!(result.is_ok());

        // Buffer should contain 1 event
        assert_eq!(logger.buffer_len().await, 1);
    }

    #[tokio::test]
    async fn test_audit_logger_flush() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = AuditLogger::new(log_path.clone()).unwrap();

        let event = AuditEvent::new(
            AuditEventType::MessageProcessed,
            "test_agent".to_string(),
            None,
        );

        logger.log(event).await.unwrap();
        logger.flush().await.unwrap();

        // Buffer should be empty after flush
        assert_eq!(logger.buffer_len().await, 0);

        // File should exist and contain data
        let content = tokio::fs::read_to_string(log_path).await.unwrap();
        assert!(!content.is_empty());
    }

    #[tokio::test]
    async fn test_audit_logger_auto_flush() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = AuditLogger::with_buffer_size(log_path.clone(), 5).unwrap();

        // Log 5 events to trigger auto-flush
        for i in 0..5 {
            let event = AuditEvent::new(
                AuditEventType::MessageProcessed,
                format!("agent_{}", i),
                None,
            );
            logger.log(event).await.unwrap();
        }

        // Buffer should be empty after auto-flush
        assert_eq!(logger.buffer_len().await, 0);
    }

    #[tokio::test]
    async fn test_audit_logger_query_all() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = AuditLogger::new(log_path.clone()).unwrap();

        // Log multiple events
        for i in 0..3 {
            let event = AuditEvent::new(
                AuditEventType::MessageProcessed,
                format!("agent_{}", i),
                None,
            );
            logger.log(event).await.unwrap();
        }

        logger.flush().await.unwrap();

        // Query all events
        let events = logger.query(None).await.unwrap();
        assert_eq!(events.len(), 3);
    }

    #[tokio::test]
    async fn test_audit_logger_query_by_session() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = AuditLogger::new(log_path.clone()).unwrap();

        // Log events with different sessions
        logger
            .log(AuditEvent::new(
                AuditEventType::MessageProcessed,
                "agent1".to_string(),
                Some("session-1".to_string()),
            ))
            .await
            .unwrap();

        logger
            .log(AuditEvent::new(
                AuditEventType::MessageProcessed,
                "agent2".to_string(),
                Some("session-2".to_string()),
            ))
            .await
            .unwrap();

        logger
            .log(AuditEvent::new(
                AuditEventType::MessageProcessed,
                "agent3".to_string(),
                Some("session-1".to_string()),
            ))
            .await
            .unwrap();

        logger.flush().await.unwrap();

        // Query by session ID
        let events = logger.query_by_session("session-1").await.unwrap();
        assert_eq!(events.len(), 2);
    }

    #[tokio::test]
    async fn test_audit_logger_query_by_agent() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = AuditLogger::new(log_path.clone()).unwrap();

        // Log events from different agents
        logger
            .log(AuditEvent::new(
                AuditEventType::MessageProcessed,
                "agent1".to_string(),
                None,
            ))
            .await
            .unwrap();

        logger
            .log(AuditEvent::new(
                AuditEventType::MessageProcessed,
                "agent2".to_string(),
                None,
            ))
            .await
            .unwrap();

        logger
            .log(AuditEvent::new(
                AuditEventType::MessageProcessed,
                "agent1".to_string(),
                None,
            ))
            .await
            .unwrap();

        logger.flush().await.unwrap();

        // Query by agent name
        let events = logger.query_by_agent("agent1").await.unwrap();
        assert_eq!(events.len(), 2);
    }

    #[tokio::test]
    async fn test_audit_logger_query_by_type() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = AuditLogger::new(log_path.clone()).unwrap();

        // Log events of different types
        logger
            .log(AuditEvent::new(
                AuditEventType::AgentCreated,
                "agent1".to_string(),
                None,
            ))
            .await
            .unwrap();

        logger
            .log(AuditEvent::new(
                AuditEventType::MessageProcessed,
                "agent1".to_string(),
                None,
            ))
            .await
            .unwrap();

        logger
            .log(AuditEvent::new(
                AuditEventType::AgentCreated,
                "agent2".to_string(),
                None,
            ))
            .await
            .unwrap();

        logger.flush().await.unwrap();

        // Query by event type
        let events = logger
            .query_by_type(AuditEventType::AgentCreated)
            .await
            .unwrap();
        assert_eq!(events.len(), 2);
    }

    #[tokio::test]
    async fn test_concurrent_logging() {
        let temp_dir = TempDir::new().unwrap();
        let log_path = temp_dir.path().join("audit.log");
        let logger = Arc::new(AuditLogger::new(log_path.clone()).unwrap());

        // Spawn multiple tasks logging concurrently
        let mut handles = vec![];
        for i in 0..10 {
            let logger_clone = Arc::clone(&logger);
            let handle = tokio::spawn(async move {
                let event = AuditEvent::new(
                    AuditEventType::MessageProcessed,
                    format!("agent_{}", i),
                    None,
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

        // All events should be logged
        let events = logger.query(None).await.unwrap();
        assert_eq!(events.len(), 10);
    }
}
