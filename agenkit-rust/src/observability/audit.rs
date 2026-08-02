//! Security and compliance audit logging.
//!
//! Provides structured audit events with pluggable adapters for file, console,
//! and structured logging backends.
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::observability::{AuditLogger, AuditEvent, AuditEventType, AuditSeverity};
//! use std::path::PathBuf;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Create audit logger
//! let logger = AuditLogger::new(PathBuf::from("audit.log"));
//!
//! // Log an event
//! let event = AuditEvent::new(
//!     AuditEventType::MessageProcessed,
//!     "my-agent".to_string(),
//!     Some("session-123".to_string()),
//! );
//! logger.log(event).await?;
//!
//! // Flush to disk
//! logger.flush().await?;
//! # Ok(())
//! # }
//! ```

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::fs::OpenOptions;
use tokio::io::AsyncWriteExt;
use tokio::sync::Mutex;
use uuid::Uuid;

/// Audit event types.
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
}

/// Audit event severity.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum AuditSeverity {
    /// Informational event
    Info,
    /// Warning event
    Warning,
    /// Error event
    Error,
    /// Critical event
    Critical,
}

/// Audit event structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEvent {
    /// Event ID
    pub event_id: String,
    /// Timestamp
    pub timestamp: chrono::DateTime<chrono::Utc>,
    /// Event type
    pub event_type: AuditEventType,
    /// Event severity
    pub severity: AuditSeverity,
    /// Agent name
    pub agent_name: String,
    /// Session ID
    pub session_id: Option<String>,
    /// Event details
    pub details: HashMap<String, serde_json::Value>,
}

impl AuditEvent {
    /// Create a new audit event with default severity (Info).
    ///
    /// # Arguments
    ///
    /// * `event_type` - Type of audit event
    /// * `agent_name` - Name of the agent
    /// * `session_id` - Optional session identifier
    ///
    /// # Example
    ///
    /// ```rust
    /// # use agenkit::observability::{AuditEvent, AuditEventType};
    /// let event = AuditEvent::new(
    ///     AuditEventType::MessageProcessed,
    ///     "my-agent".to_string(),
    ///     Some("session-123".to_string()),
    /// );
    /// ```
    pub fn new(event_type: AuditEventType, agent_name: String, session_id: Option<String>) -> Self {
        Self {
            event_id: Uuid::new_v4().to_string(),
            timestamp: chrono::Utc::now(),
            event_type,
            severity: AuditSeverity::Info,
            agent_name,
            session_id,
            details: HashMap::new(),
        }
    }

    /// Create a new audit event with specified severity.
    ///
    /// # Arguments
    ///
    /// * `event_type` - Type of audit event
    /// * `severity` - Event severity
    /// * `agent_name` - Name of the agent
    /// * `session_id` - Optional session identifier
    pub fn with_severity(
        event_type: AuditEventType,
        severity: AuditSeverity,
        agent_name: String,
        session_id: Option<String>,
    ) -> Self {
        Self {
            event_id: Uuid::new_v4().to_string(),
            timestamp: chrono::Utc::now(),
            event_type,
            severity,
            agent_name,
            session_id,
            details: HashMap::new(),
        }
    }

    /// Add a detail to the audit event.
    pub fn add_detail(mut self, key: String, value: serde_json::Value) -> Self {
        self.details.insert(key, value);
        self
    }
}

/// Audit logger with buffered writing.
///
/// This logger buffers audit events in memory and writes them to disk in batches
/// for better performance. Events are automatically flushed when the buffer reaches
/// a certain size or when explicitly requested.
///
/// # Example
///
/// ```rust,no_run
/// # use agenkit::observability::{AuditLogger, AuditEvent, AuditEventType};
/// # use std::path::PathBuf;
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let logger = AuditLogger::new(PathBuf::from("audit.log"));
///
/// let event = AuditEvent::new(
///     AuditEventType::MessageProcessed,
///     "agent".to_string(),
///     None,
/// );
/// logger.log(event).await?;
///
/// // Flush to ensure all events are written
/// logger.flush().await?;
/// # Ok(())
/// # }
/// ```
pub struct AuditLogger {
    log_path: PathBuf,
    buffer: Arc<Mutex<Vec<AuditEvent>>>,
    buffer_size: usize,
}

impl AuditLogger {
    /// Create new audit logger.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the audit log file
    ///
    /// # Example
    ///
    /// ```rust
    /// # use agenkit::observability::AuditLogger;
    /// # use std::path::PathBuf;
    /// let logger = AuditLogger::new(PathBuf::from("audit.log"));
    /// ```
    pub fn new(log_path: PathBuf) -> Self {
        Self {
            log_path,
            buffer: Arc::new(Mutex::new(Vec::new())),
            buffer_size: 100, // Auto-flush after 100 events
        }
    }

    /// Create new audit logger with custom buffer size.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the audit log file
    /// * `buffer_size` - Number of events to buffer before auto-flush
    pub fn with_buffer_size(log_path: PathBuf, buffer_size: usize) -> Self {
        Self {
            log_path,
            buffer: Arc::new(Mutex::new(Vec::new())),
            buffer_size,
        }
    }

    /// Log an audit event.
    ///
    /// Events are buffered and will be written to disk when the buffer is full
    /// or when `flush()` is called.
    ///
    /// # Arguments
    ///
    /// * `event` - The audit event to log
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::observability::{AuditLogger, AuditEvent, AuditEventType};
    /// # use std::path::PathBuf;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let logger = AuditLogger::new(PathBuf::from("audit.log"));
    /// let event = AuditEvent::new(
    ///     AuditEventType::AgentCreated,
    ///     "agent".to_string(),
    ///     None,
    /// );
    /// logger.log(event).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn log(&self, event: AuditEvent) -> Result<(), Box<dyn std::error::Error>> {
        let mut buffer = self.buffer.lock().await;
        buffer.push(event);

        // Auto-flush if buffer is full
        if buffer.len() >= self.buffer_size {
            self.flush_internal(&mut buffer).await?;
        }

        Ok(())
    }

    /// Flush buffered events to disk.
    ///
    /// Writes all buffered events to the log file and clears the buffer.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::observability::AuditLogger;
    /// # use std::path::PathBuf;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let logger = AuditLogger::new(PathBuf::from("audit.log"));
    /// // ... log some events ...
    /// logger.flush().await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn flush(&self) -> Result<(), Box<dyn std::error::Error>> {
        let mut buffer = self.buffer.lock().await;
        self.flush_internal(&mut buffer).await
    }

    /// Internal flush implementation (requires buffer lock).
    async fn flush_internal(
        &self,
        buffer: &mut Vec<AuditEvent>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        if buffer.is_empty() {
            return Ok(());
        }

        // Open file in append mode
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.log_path)
            .await?;

        // Write each event as a JSON line
        for event in buffer.iter() {
            let json = serde_json::to_string(event)?;
            file.write_all(json.as_bytes()).await?;
            file.write_all(b"\n").await?;
        }

        file.sync_all().await?;
        buffer.clear();

        Ok(())
    }

    /// Query audit events from the log file.
    ///
    /// Reads all events from the log file and optionally filters by session ID.
    ///
    /// # Arguments
    ///
    /// * `session_id` - Optional session ID to filter by
    ///
    /// # Returns
    ///
    /// Vector of audit events matching the filter
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::observability::AuditLogger;
    /// # use std::path::PathBuf;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let logger = AuditLogger::new(PathBuf::from("audit.log"));
    ///
    /// // Get all events
    /// let all_events = logger.query(None).await?;
    ///
    /// // Get events for specific session
    /// let session_events = logger.query(Some("session-123".to_string())).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn query(
        &self,
        session_id: Option<String>,
    ) -> Result<Vec<AuditEvent>, Box<dyn std::error::Error>> {
        // Flush buffer first to ensure we read all events
        self.flush().await?;

        // Read the log file
        let contents = tokio::fs::read_to_string(&self.log_path).await?;

        let mut events = Vec::new();
        for line in contents.lines() {
            if line.is_empty() {
                continue;
            }

            let event: AuditEvent = serde_json::from_str(line)?;

            // Filter by session_id if provided
            if let Some(ref sid) = session_id {
                if event.session_id.as_ref() == Some(sid) {
                    events.push(event);
                }
            } else {
                events.push(event);
            }
        }

        Ok(events)
    }

    /// Get the number of events currently in the buffer.
    pub async fn buffer_len(&self) -> usize {
        self.buffer.lock().await.len()
    }
}

impl Clone for AuditLogger {
    fn clone(&self) -> Self {
        Self {
            log_path: self.log_path.clone(),
            buffer: Arc::clone(&self.buffer),
            buffer_size: self.buffer_size,
        }
    }
}
