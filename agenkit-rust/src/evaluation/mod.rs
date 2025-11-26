//! Evaluation Framework
//!
//! Comprehensive evaluation capabilities for autonomous agents.
//!
//! This module provides tools for measuring agent quality and performance:
//! - Core evaluation infrastructure
//! - Enhanced metrics tracking
//! - Session status management
//! - Error collection and analysis
//!
//! # Example
//!
//! ```no_run
//! use agenkit::evaluation::{Evaluator, SessionResult, SessionStatus};
//! use agenkit::core::Agent;
//! use std::sync::Arc;
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let agent: Arc<dyn Agent> = todo!();
//! // Create evaluator
//! let evaluator = Evaluator::new(agent, vec![], None);
//!
//! // Run evaluation
//! let mut test_case = HashMap::new();
//! test_case.insert("input".to_string(), serde_json::json!("test"));
//! test_case.insert("expected".to_string(), serde_json::json!("result"));
//!
//! let result = evaluator.evaluate(vec![test_case], None).await?;
//! println!("Success rate: {:.2}", result.success_rate());
//!
//! // Track session with enhanced metrics
//! let mut session = SessionResult::new("session-123", "my-agent");
//! session.set_status(SessionStatus::Completed);
//! # Ok(())
//! # }
//! ```

pub mod core;
pub mod metrics;
pub mod quality_metrics;
pub mod context_metrics;
pub mod recorder;

pub use core::{Metric, EvaluationResult, Evaluator};
pub use metrics::{
    SessionStatus, MetricType, MetricMeasurement, ErrorRecord,
    SessionResult, MetricsCollector,
};
pub use quality_metrics::{AccuracyMetric, QualityMetrics, ValidatorFunc};
pub use context_metrics::{
    ContextMetrics, CompressionMetrics, CompressionStats, LatencyMetric,
};
pub use recorder::{
    InteractionRecord, SessionRecording, RecordingStorage,
    FileRecordingStorage, InMemoryRecordingStorage, SessionRecorder,
};
