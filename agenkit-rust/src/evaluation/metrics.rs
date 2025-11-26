//! Enhanced Metrics Tracking
//!
//! This module extends core evaluation with enhanced metric tracking including:
//! - Session status tracking (running, completed, failed, etc.)
//! - Error collection and analysis
//! - Metric type categorization
//! - Cross-session aggregation
//!
//! # Key Use Case
//!
//! "How do you know a long-running agent succeeded?"
//!
//! # Example
//!
//! ```
//! use agenkit::evaluation::{SessionResult, MetricMeasurement, MetricType, SessionStatus};
//!
//! let mut result = SessionResult::new("session-123", "my-agent");
//! result.add_metric_measurement(MetricMeasurement::new(
//!     "accuracy",
//!     0.95,
//!     MetricType::SuccessRate,
//! ));
//! result.set_status(SessionStatus::Completed);
//! ```

use std::collections::HashMap;
use chrono::{DateTime, Utc};
use serde::{Serialize, Deserialize};

/// Status of an evaluation session.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionStatus {
    /// Session is currently running
    Running,
    /// Session completed successfully
    Completed,
    /// Session failed
    Failed,
    /// Session timed out
    Timeout,
    /// Session was cancelled
    Cancelled,
}

impl std::fmt::Display for SessionStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SessionStatus::Running => write!(f, "running"),
            SessionStatus::Completed => write!(f, "completed"),
            SessionStatus::Failed => write!(f, "failed"),
            SessionStatus::Timeout => write!(f, "timeout"),
            SessionStatus::Cancelled => write!(f, "cancelled"),
        }
    }
}

/// Categorizes different types of metrics.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MetricType {
    /// Measures success/failure rates
    SuccessRate,
    /// Measures output quality
    QualityScore,
    /// Measures token/API costs
    Cost,
    /// Measures time taken
    Duration,
    /// Measures error frequency
    ErrorRate,
    /// Measures task completion
    TaskCompletion,
    /// Custom metrics
    Custom,
}

impl std::fmt::Display for MetricType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MetricType::SuccessRate => write!(f, "success_rate"),
            MetricType::QualityScore => write!(f, "quality_score"),
            MetricType::Cost => write!(f, "cost"),
            MetricType::Duration => write!(f, "duration"),
            MetricType::ErrorRate => write!(f, "error_rate"),
            MetricType::TaskCompletion => write!(f, "task_completion"),
            MetricType::Custom => write!(f, "custom"),
        }
    }
}

/// Single metric measurement.
///
/// Note: This is distinct from the Metric trait in core.rs.
/// Metric trait defines how to measure, MetricMeasurement stores the measurement.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricMeasurement {
    /// Name of the metric
    pub name: String,
    /// Value of the measurement
    pub value: f64,
    /// Type categorizes the metric
    #[serde(rename = "type")]
    pub metric_type: MetricType,
    /// Timestamp when measurement was taken
    pub timestamp: DateTime<Utc>,
    /// Metadata for additional context
    #[serde(skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl MetricMeasurement {
    /// Creates a new metric measurement with current timestamp.
    pub fn new(name: impl Into<String>, value: f64, metric_type: MetricType) -> Self {
        Self {
            name: name.into(),
            value,
            metric_type,
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        }
    }

    /// Creates a new metric measurement with metadata.
    pub fn with_metadata(
        name: impl Into<String>,
        value: f64,
        metric_type: MetricType,
        metadata: HashMap<String, serde_json::Value>,
    ) -> Self {
        Self {
            name: name.into(),
            value,
            metric_type,
            timestamp: Utc::now(),
            metadata,
        }
    }
}

/// Error that occurred during evaluation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorRecord {
    /// Type of error
    #[serde(rename = "type")]
    pub error_type: String,
    /// Error message
    pub message: String,
    /// Additional details
    #[serde(skip_serializing_if = "HashMap::is_empty")]
    pub details: HashMap<String, serde_json::Value>,
    /// Timestamp when error occurred
    pub timestamp: DateTime<Utc>,
}

impl ErrorRecord {
    /// Creates a new error record with current timestamp.
    pub fn new(error_type: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            error_type: error_type.into(),
            message: message.into(),
            details: HashMap::new(),
            timestamp: Utc::now(),
        }
    }

    /// Creates a new error record with details.
    pub fn with_details(
        error_type: impl Into<String>,
        message: impl Into<String>,
        details: HashMap<String, serde_json::Value>,
    ) -> Self {
        Self {
            error_type: error_type.into(),
            message: message.into(),
            details,
            timestamp: Utc::now(),
        }
    }
}

/// Results from evaluating an agent session with enhanced tracking.
///
/// This extends the core EvaluationResult with session status, error tracking,
/// and richer metadata for long-running agent evaluations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionResult {
    /// SessionID uniquely identifies this session
    pub session_id: String,
    /// AgentName identifies the agent being evaluated
    pub agent_name: String,
    /// Status of the session
    pub status: SessionStatus,
    /// StartTime when session started
    pub start_time: DateTime<Utc>,
    /// EndTime when session ended (None if still running)
    pub end_time: Option<DateTime<Utc>>,
    /// Measurements collected during session
    pub measurements: Vec<MetricMeasurement>,
    /// Errors that occurred during session
    pub errors: Vec<ErrorRecord>,
    /// Metadata for additional context
    #[serde(skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl SessionResult {
    /// Creates a new session result.
    pub fn new(session_id: impl Into<String>, agent_name: impl Into<String>) -> Self {
        Self {
            session_id: session_id.into(),
            agent_name: agent_name.into(),
            status: SessionStatus::Running,
            start_time: Utc::now(),
            end_time: None,
            measurements: Vec::new(),
            errors: Vec::new(),
            metadata: HashMap::new(),
        }
    }

    /// Sets the session status.
    pub fn set_status(&mut self, status: SessionStatus) {
        self.status = status;
        if self.end_time.is_none() && status != SessionStatus::Running {
            self.end_time = Some(Utc::now());
        }
    }

    /// Adds a metric measurement.
    pub fn add_metric_measurement(&mut self, measurement: MetricMeasurement) {
        self.measurements.push(measurement);
    }

    /// Adds an error record.
    ///
    /// If the session is Running or Completed, it will be marked as Failed.
    pub fn add_error(&mut self, error: ErrorRecord) {
        self.errors.push(error);
        if self.status == SessionStatus::Running || self.status == SessionStatus::Completed {
            self.status = SessionStatus::Failed;
            if self.end_time.is_none() {
                self.end_time = Some(Utc::now());
            }
        }
    }

    /// Gets measurements by metric type.
    pub fn get_measurements_by_type(&self, metric_type: MetricType) -> Vec<&MetricMeasurement> {
        self.measurements
            .iter()
            .filter(|m| m.metric_type == metric_type)
            .collect()
    }

    /// Gets measurements by metric name.
    pub fn get_measurements_by_name(&self, name: &str) -> Vec<&MetricMeasurement> {
        self.measurements
            .iter()
            .filter(|m| m.name == name)
            .collect()
    }

    /// Calculates duration in seconds.
    pub fn duration_secs(&self) -> Option<f64> {
        self.end_time.map(|end| {
            (end - self.start_time).num_milliseconds() as f64 / 1000.0
        })
    }

    /// Checks if session succeeded.
    pub fn is_successful(&self) -> bool {
        self.status == SessionStatus::Completed && self.errors.is_empty()
    }
}

/// Collector for aggregating metrics across multiple sessions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsCollector {
    /// Sessions tracked by this collector
    pub sessions: Vec<SessionResult>,
    /// Collector metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

impl MetricsCollector {
    /// Creates a new metrics collector.
    pub fn new() -> Self {
        Self {
            sessions: Vec::new(),
            metadata: HashMap::new(),
        }
    }

    /// Adds a session result.
    pub fn add_session(&mut self, session: SessionResult) {
        self.sessions.push(session);
    }

    /// Gets all measurements of a specific type across all sessions.
    pub fn get_all_measurements_by_type(&self, metric_type: MetricType) -> Vec<&MetricMeasurement> {
        self.sessions
            .iter()
            .flat_map(|s| s.get_measurements_by_type(metric_type))
            .collect()
    }

    /// Gets all measurements of a specific name across all sessions.
    pub fn get_all_measurements_by_name(&self, name: &str) -> Vec<&MetricMeasurement> {
        self.sessions
            .iter()
            .flat_map(|s| s.get_measurements_by_name(name))
            .collect()
    }

    /// Calculates aggregated statistics for a metric type.
    pub fn aggregate_by_type(&self, metric_type: MetricType) -> HashMap<String, f64> {
        let measurements = self.get_all_measurements_by_type(metric_type);
        let values: Vec<f64> = measurements.iter().map(|m| m.value).collect();
        Self::calculate_statistics(&values)
    }

    /// Calculates aggregated statistics for a metric name.
    pub fn aggregate_by_name(&self, name: &str) -> HashMap<String, f64> {
        let measurements = self.get_all_measurements_by_name(name);
        let values: Vec<f64> = measurements.iter().map(|m| m.value).collect();
        Self::calculate_statistics(&values)
    }

    /// Calculates basic statistics for a set of values.
    fn calculate_statistics(values: &[f64]) -> HashMap<String, f64> {
        let mut stats = HashMap::new();

        if values.is_empty() {
            return stats;
        }

        let sum: f64 = values.iter().sum();
        let count = values.len() as f64;
        let mean = sum / count;

        stats.insert("mean".to_string(), mean);
        stats.insert("count".to_string(), count);
        stats.insert("sum".to_string(), sum);

        if !values.is_empty() {
            let min = values.iter().fold(f64::INFINITY, |a, &b| a.min(b));
            let max = values.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
            stats.insert("min".to_string(), min);
            stats.insert("max".to_string(), max);

            // Calculate standard deviation
            let variance = values.iter()
                .map(|v| (v - mean).powi(2))
                .sum::<f64>() / count;
            stats.insert("std".to_string(), variance.sqrt());
        }

        stats
    }

    /// Gets success rate across all sessions.
    pub fn overall_success_rate(&self) -> f64 {
        if self.sessions.is_empty() {
            return 0.0;
        }

        let successful = self.sessions.iter().filter(|s| s.is_successful()).count();
        successful as f64 / self.sessions.len() as f64
    }

    /// Gets total error count across all sessions.
    pub fn total_errors(&self) -> usize {
        self.sessions.iter().map(|s| s.errors.len()).sum()
    }
}

impl Default for MetricsCollector {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_result_basic() {
        let mut session = SessionResult::new("test-123", "agent-1");

        assert_eq!(session.session_id, "test-123");
        assert_eq!(session.agent_name, "agent-1");
        assert_eq!(session.status, SessionStatus::Running);
        assert!(session.end_time.is_none());

        session.set_status(SessionStatus::Completed);
        assert_eq!(session.status, SessionStatus::Completed);
        assert!(session.end_time.is_some());
    }

    #[test]
    fn test_session_result_measurements() {
        let mut session = SessionResult::new("test-123", "agent-1");

        session.add_metric_measurement(MetricMeasurement::new(
            "accuracy",
            0.95,
            MetricType::SuccessRate,
        ));

        session.add_metric_measurement(MetricMeasurement::new(
            "latency",
            100.0,
            MetricType::Duration,
        ));

        assert_eq!(session.measurements.len(), 2);

        let accuracy_measurements = session.get_measurements_by_name("accuracy");
        assert_eq!(accuracy_measurements.len(), 1);
        assert_eq!(accuracy_measurements[0].value, 0.95);

        let duration_measurements = session.get_measurements_by_type(MetricType::Duration);
        assert_eq!(duration_measurements.len(), 1);
        assert_eq!(duration_measurements[0].value, 100.0);
    }

    #[test]
    fn test_session_result_errors() {
        let mut session = SessionResult::new("test-123", "agent-1");
        session.set_status(SessionStatus::Completed);

        assert!(session.is_successful());

        session.add_error(ErrorRecord::new("timeout", "Request timed out"));

        assert!(!session.is_successful());
        assert_eq!(session.status, SessionStatus::Failed);
        assert_eq!(session.errors.len(), 1);
    }

    #[test]
    fn test_metrics_collector() {
        let mut collector = MetricsCollector::new();

        let mut session1 = SessionResult::new("s1", "agent-1");
        session1.add_metric_measurement(MetricMeasurement::new(
            "accuracy",
            0.9,
            MetricType::SuccessRate,
        ));
        session1.set_status(SessionStatus::Completed);

        let mut session2 = SessionResult::new("s2", "agent-1");
        session2.add_metric_measurement(MetricMeasurement::new(
            "accuracy",
            0.95,
            MetricType::SuccessRate,
        ));
        session2.set_status(SessionStatus::Completed);

        collector.add_session(session1);
        collector.add_session(session2);

        let stats = collector.aggregate_by_name("accuracy");
        assert_eq!(stats.get("count").unwrap(), &2.0);
        assert_eq!(stats.get("mean").unwrap(), &0.925);
        assert_eq!(stats.get("min").unwrap(), &0.9);
        assert_eq!(stats.get("max").unwrap(), &0.95);

        assert_eq!(collector.overall_success_rate(), 1.0);
    }

    #[test]
    fn test_metric_measurement_creation() {
        let measurement = MetricMeasurement::new("test", 0.5, MetricType::QualityScore);

        assert_eq!(measurement.name, "test");
        assert_eq!(measurement.value, 0.5);
        assert_eq!(measurement.metric_type, MetricType::QualityScore);
        assert!(measurement.metadata.is_empty());
    }

    #[test]
    fn test_error_record_creation() {
        let error = ErrorRecord::new("timeout", "Request failed");

        assert_eq!(error.error_type, "timeout");
        assert_eq!(error.message, "Request failed");
        assert!(error.details.is_empty());
    }
}
