//! Security audit logging for tracking security events.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

/// Audit event types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditEventType {
    AccessGranted,
    AccessDenied,
    InputValidationFailed,
    OutputValidationFailed,
    PermissionGranted,
    PermissionDenied,
    PromptInjectionDetected,
    SensitiveDataDetected,
    AnomalyDetected,
    AgentStarted,
    AgentCompleted,
    AgentFailed,
}

/// Audit severity levels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum AuditSeverity {
    Info,
    Warning,
    Error,
    Critical,
}

/// Audit event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEvent {
    pub event_type: AuditEventType,
    pub severity: AuditSeverity,
    pub timestamp: DateTime<Utc>,
    pub user_id: Option<String>,
    pub agent_name: Option<String>,
    pub message: String,
    pub details: HashMap<String, serde_json::Value>,
}

impl AuditEvent {
    /// Create a new audit event.
    pub fn new(event_type: AuditEventType, severity: AuditSeverity, message: String) -> Self {
        Self {
            event_type,
            severity,
            timestamp: Utc::now(),
            user_id: None,
            agent_name: None,
            message,
            details: HashMap::new(),
        }
    }

    /// Set user ID.
    pub fn with_user(mut self, user_id: String) -> Self {
        self.user_id = Some(user_id);
        self
    }

    /// Set agent name.
    pub fn with_agent(mut self, agent_name: String) -> Self {
        self.agent_name = Some(agent_name);
        self
    }

    /// Add detail.
    pub fn with_detail(mut self, key: String, value: serde_json::Value) -> Self {
        self.details.insert(key, value);
        self
    }

    /// Convert to JSON string.
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
}

/// Security audit logger configuration.
#[derive(Debug, Clone)]
pub struct SecurityAuditLoggerConfig {
    /// Log file path
    pub log_file: PathBuf,
    /// Minimum severity to log
    pub min_severity: AuditSeverity,
    /// Enable console logging
    pub console_logging: bool,
}

impl Default for SecurityAuditLoggerConfig {
    fn default() -> Self {
        Self {
            log_file: PathBuf::from("security_audit.log"),
            min_severity: AuditSeverity::Info,
            console_logging: true,
        }
    }
}

/// Security audit logger.
pub struct SecurityAuditLogger {
    config: SecurityAuditLoggerConfig,
    file: Arc<Mutex<File>>,
}

impl SecurityAuditLogger {
    /// Create a new audit logger.
    pub fn new(config: SecurityAuditLoggerConfig) -> Result<Self, std::io::Error> {
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&config.log_file)?;

        Ok(Self {
            config,
            file: Arc::new(Mutex::new(file)),
        })
    }

    /// Log an audit event.
    pub fn log(&self, event: &AuditEvent) -> Result<(), std::io::Error> {
        // Check severity threshold
        if event.severity < self.config.min_severity {
            return Ok(());
        }

        // Format event as JSON
        let json = event
            .to_json()
            .map_err(std::io::Error::other)?;

        // Write to file
        {
            let mut file = self.file.lock().unwrap();
            writeln!(file, "{}", json)?;
            file.flush()?;
        }

        // Console logging
        if self.config.console_logging {
            println!(
                "[{:?}] [{:?}] {} - {}",
                event.severity,
                event.event_type,
                event.timestamp.format("%Y-%m-%d %H:%M:%S"),
                event.message
            );
        }

        Ok(())
    }

    /// Log access attempt.
    pub fn log_access(
        &self,
        granted: bool,
        user_id: &str,
        resource: &str,
    ) -> Result<(), std::io::Error> {
        let event = if granted {
            AuditEvent::new(
                AuditEventType::AccessGranted,
                AuditSeverity::Info,
                format!("Access granted to: {}", resource),
            )
            .with_user(user_id.to_string())
            .with_detail("resource".to_string(), serde_json::json!(resource))
        } else {
            AuditEvent::new(
                AuditEventType::AccessDenied,
                AuditSeverity::Warning,
                format!("Access denied to: {}", resource),
            )
            .with_user(user_id.to_string())
            .with_detail("resource".to_string(), serde_json::json!(resource))
        };

        self.log(&event)
    }

    /// Log permission check.
    pub fn log_permission_check(
        &self,
        granted: bool,
        user_id: &str,
        permission: &str,
    ) -> Result<(), std::io::Error> {
        let event = if granted {
            AuditEvent::new(
                AuditEventType::PermissionGranted,
                AuditSeverity::Info,
                format!("Permission granted: {}", permission),
            )
            .with_user(user_id.to_string())
            .with_detail("permission".to_string(), serde_json::json!(permission))
        } else {
            AuditEvent::new(
                AuditEventType::PermissionDenied,
                AuditSeverity::Warning,
                format!("Permission denied: {}", permission),
            )
            .with_user(user_id.to_string())
            .with_detail("permission".to_string(), serde_json::json!(permission))
        };

        self.log(&event)
    }

    /// Log validation failure.
    pub fn log_validation_failure(
        &self,
        is_input: bool,
        user_id: &str,
        reason: &str,
    ) -> Result<(), std::io::Error> {
        let event_type = if is_input {
            AuditEventType::InputValidationFailed
        } else {
            AuditEventType::OutputValidationFailed
        };

        let event = AuditEvent::new(
            event_type,
            AuditSeverity::Warning,
            format!("Validation failed: {}", reason),
        )
        .with_user(user_id.to_string())
        .with_detail("reason".to_string(), serde_json::json!(reason));

        self.log(&event)
    }

    /// Log prompt injection detection.
    pub fn log_prompt_injection(
        &self,
        user_id: &str,
        score: u32,
        details: &str,
    ) -> Result<(), std::io::Error> {
        let event = AuditEvent::new(
            AuditEventType::PromptInjectionDetected,
            AuditSeverity::Critical,
            format!("Prompt injection detected (score: {})", score),
        )
        .with_user(user_id.to_string())
        .with_detail("score".to_string(), serde_json::json!(score))
        .with_detail("details".to_string(), serde_json::json!(details));

        self.log(&event)
    }

    /// Log anomaly detection.
    pub fn log_anomaly(
        &self,
        user_id: &str,
        anomaly_type: &str,
        details: &str,
    ) -> Result<(), std::io::Error> {
        let event = AuditEvent::new(
            AuditEventType::AnomalyDetected,
            AuditSeverity::Warning,
            format!("Anomaly detected: {}", anomaly_type),
        )
        .with_user(user_id.to_string())
        .with_detail("type".to_string(), serde_json::json!(anomaly_type))
        .with_detail("details".to_string(), serde_json::json!(details));

        self.log(&event)
    }

    /// Log agent execution.
    pub fn log_agent_execution(
        &self,
        agent_name: &str,
        success: bool,
        duration_ms: u64,
    ) -> Result<(), std::io::Error> {
        let (event_type, severity) = if success {
            (AuditEventType::AgentCompleted, AuditSeverity::Info)
        } else {
            (AuditEventType::AgentFailed, AuditSeverity::Error)
        };

        let event = AuditEvent::new(
            event_type,
            severity,
            format!(
                "Agent {} in {}ms",
                if success { "completed" } else { "failed" },
                duration_ms
            ),
        )
        .with_agent(agent_name.to_string())
        .with_detail("duration_ms".to_string(), serde_json::json!(duration_ms));

        self.log(&event)
    }

    /// Log sensitive data redaction.
    pub fn log_sensitive_data_redaction(
        &self,
        user_id: &str,
        data_type: &str,
    ) -> Result<(), std::io::Error> {
        let event = AuditEvent::new(
            AuditEventType::SensitiveDataDetected,
            AuditSeverity::Warning,
            format!("Sensitive data redacted: {}", data_type),
        )
        .with_user(user_id.to_string())
        .with_detail("data_type".to_string(), serde_json::json!(data_type));

        self.log(&event)
    }
}

// Global logger instance
static GLOBAL_LOGGER: Mutex<Option<Arc<SecurityAuditLogger>>> = Mutex::new(None);

/// Configure the global audit logger.
pub fn configure_audit_logger(logger: SecurityAuditLogger) {
    let mut global = GLOBAL_LOGGER.lock().unwrap();
    *global = Some(Arc::new(logger));
}

/// Get the global audit logger.
pub fn get_audit_logger() -> Option<Arc<SecurityAuditLogger>> {
    let global = GLOBAL_LOGGER.lock().unwrap();
    global.clone()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn test_audit_event_creation() {
        let event = AuditEvent::new(
            AuditEventType::AccessGranted,
            AuditSeverity::Info,
            "Test event".to_string(),
        )
        .with_user("test_user".to_string())
        .with_detail("key".to_string(), serde_json::json!("value"));

        assert_eq!(event.event_type, AuditEventType::AccessGranted);
        assert_eq!(event.severity, AuditSeverity::Info);
        assert_eq!(event.user_id, Some("test_user".to_string()));
        assert!(event.details.contains_key("key"));
    }

    #[test]
    fn test_audit_event_json() {
        let event = AuditEvent::new(
            AuditEventType::PermissionDenied,
            AuditSeverity::Warning,
            "Test message".to_string(),
        );

        let json = event.to_json().unwrap();
        assert!(json.contains("PermissionDenied"));
        assert!(json.contains("Warning"));
        assert!(json.contains("Test message"));
    }

    #[test]
    fn test_audit_logger() -> Result<(), std::io::Error> {
        let test_log = PathBuf::from("test_audit.log");

        // Clean up any existing test log
        let _ = fs::remove_file(&test_log);

        let config = SecurityAuditLoggerConfig {
            log_file: test_log.clone(),
            min_severity: AuditSeverity::Info,
            console_logging: false,
        };

        let logger = SecurityAuditLogger::new(config)?;

        let event = AuditEvent::new(
            AuditEventType::AccessGranted,
            AuditSeverity::Info,
            "Test event".to_string(),
        );

        logger.log(&event)?;

        // Verify log file was created and contains data
        let content = fs::read_to_string(&test_log)?;
        assert!(content.contains("Test event"));

        // Clean up
        fs::remove_file(&test_log)?;

        Ok(())
    }
}
