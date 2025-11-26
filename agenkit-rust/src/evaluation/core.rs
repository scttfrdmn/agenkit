//! Core Evaluation Framework
//!
//! Provides comprehensive evaluation capabilities for autonomous agents.
//!
//! Designed for measuring agent quality and performance, with special focus on
//! extreme-scale context evaluation (1M-25M+ tokens) for systems like endless.
//!
//! # Example
//!
//! ```no_run
//! use agenkit::evaluation::{Evaluator, EvaluationResult};
//! use agenkit::core::Agent;
//! use std::sync::Arc;
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let agent: Arc<dyn Agent> = todo!();
//! let evaluator = Evaluator::new(agent, vec![], None);
//!
//! let mut test_case = HashMap::new();
//! test_case.insert("input".to_string(), serde_json::json!("What is 2+2?"));
//! test_case.insert("expected".to_string(), serde_json::json!("4"));
//!
//! let result = evaluator.evaluate(vec![test_case], None).await?;
//! println!("Accuracy: {:.2}", result.success_rate());
//! # Ok(())
//! # }
//! ```

use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use chrono::{DateTime, Utc};
use uuid::Uuid;
use serde::{Serialize, Deserialize};
use async_trait::async_trait;

use crate::core::{Agent, Message, AgentError};

/// Metric trait for evaluation metrics.
///
/// Metrics measure specific aspects of agent performance:
/// - Accuracy
/// - Latency
/// - Context usage
/// - Quality scores
#[async_trait]
pub trait Metric: Send + Sync {
    /// Returns the metric name.
    fn name(&self) -> &str;

    /// Measures metric for a single agent interaction.
    ///
    /// # Arguments
    ///
    /// * `agent` - The agent being evaluated
    /// * `input_message` - Input to the agent
    /// * `output_message` - Agent's response
    /// * `ctx` - Additional context (session history, etc.)
    ///
    /// # Returns
    ///
    /// Metric value (typically 0.0 to 1.0)
    async fn measure(
        &self,
        agent: Arc<dyn Agent>,
        input_message: &Message,
        output_message: &Message,
        ctx: &HashMap<String, serde_json::Value>,
    ) -> Result<f64, AgentError>;

    /// Aggregates multiple measurements.
    ///
    /// # Arguments
    ///
    /// * `measurements` - List of individual measurements
    ///
    /// # Returns
    ///
    /// Aggregated statistics (mean, std, min, max, etc.)
    fn aggregate(&self, measurements: &[f64]) -> HashMap<String, f64>;
}

/// Result from an evaluation run.
///
/// Includes metrics, metadata, and analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationResult {
    /// Evaluation identifier
    pub evaluation_id: String,
    /// Agent name
    pub agent_name: String,
    /// Timestamp
    pub timestamp: DateTime<Utc>,

    /// Raw metrics per test
    pub metrics: HashMap<String, Vec<f64>>,
    /// Aggregated metrics (mean, std, etc.)
    pub aggregated_metrics: HashMap<String, HashMap<String, f64>>,

    /// Context information
    pub context_length: Option<usize>,
    pub compressed_length: Option<usize>,
    pub compression_ratio: Option<f64>,

    /// Quality scores
    pub accuracy: Option<f64>,
    pub quality_score: Option<f64>,

    /// Performance metrics
    pub avg_latency_ms: Option<f64>,
    pub p95_latency_ms: Option<f64>,

    /// Test details
    pub total_tests: usize,
    pub passed_tests: usize,
    pub failed_tests: usize,

    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

impl EvaluationResult {
    /// Calculates test success rate.
    pub fn success_rate(&self) -> f64 {
        if self.total_tests == 0 {
            return 0.0;
        }
        self.passed_tests as f64 / self.total_tests as f64
    }

    /// Converts result to dictionary.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut result = HashMap::new();

        result.insert("evaluation_id".to_string(), serde_json::json!(self.evaluation_id));
        result.insert("agent_name".to_string(), serde_json::json!(self.agent_name));
        result.insert("timestamp".to_string(), serde_json::json!(self.timestamp.to_rfc3339()));
        result.insert("metrics".to_string(), serde_json::json!(self.metrics));
        result.insert("aggregated_metrics".to_string(), serde_json::json!(self.aggregated_metrics));
        result.insert("total_tests".to_string(), serde_json::json!(self.total_tests));
        result.insert("passed_tests".to_string(), serde_json::json!(self.passed_tests));
        result.insert("failed_tests".to_string(), serde_json::json!(self.failed_tests));
        result.insert("success_rate".to_string(), serde_json::json!(self.success_rate()));
        result.insert("metadata".to_string(), serde_json::json!(self.metadata));

        if let Some(val) = self.context_length {
            result.insert("context_length".to_string(), serde_json::json!(val));
        }
        if let Some(val) = self.compressed_length {
            result.insert("compressed_length".to_string(), serde_json::json!(val));
        }
        if let Some(val) = self.compression_ratio {
            result.insert("compression_ratio".to_string(), serde_json::json!(val));
        }
        if let Some(val) = self.accuracy {
            result.insert("accuracy".to_string(), serde_json::json!(val));
        }
        if let Some(val) = self.quality_score {
            result.insert("quality_score".to_string(), serde_json::json!(val));
        }
        if let Some(val) = self.avg_latency_ms {
            result.insert("avg_latency_ms".to_string(), serde_json::json!(val));
        }
        if let Some(val) = self.p95_latency_ms {
            result.insert("p95_latency_ms".to_string(), serde_json::json!(val));
        }

        result
    }
}

/// Core evaluation orchestrator.
///
/// Runs benchmarks, collects metrics, and aggregates results.
///
/// # Example
///
/// ```no_run
/// use agenkit::evaluation::Evaluator;
/// use agenkit::core::Agent;
/// use std::sync::Arc;
/// use std::collections::HashMap;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent: Arc<dyn Agent> = todo!();
/// let evaluator = Evaluator::new(agent, vec![], None);
///
/// let mut test_case = HashMap::new();
/// test_case.insert("input".to_string(), serde_json::json!("test"));
/// test_case.insert("expected".to_string(), serde_json::json!("result"));
///
/// let result = evaluator.evaluate(vec![test_case], None).await?;
/// # Ok(())
/// # }
/// ```
pub struct Evaluator {
    agent: Arc<dyn Agent>,
    metrics: Vec<Arc<dyn Metric>>,
    session_id: String,
}

impl Evaluator {
    /// Creates a new evaluator.
    ///
    /// # Arguments
    ///
    /// * `agent` - Agent to evaluate
    /// * `metrics` - List of metrics to collect (defaults to empty)
    /// * `session_id` - Optional session ID for context tracking
    ///
    /// # Example
    ///
    /// ```no_run
    /// use agenkit::evaluation::Evaluator;
    /// use agenkit::core::Agent;
    /// use std::sync::Arc;
    ///
    /// # let agent: Arc<dyn Agent> = todo!();
    /// let evaluator = Evaluator::new(agent, vec![], Some("eval-123".to_string()));
    /// ```
    pub fn new(
        agent: Arc<dyn Agent>,
        metrics: Vec<Arc<dyn Metric>>,
        session_id: Option<String>,
    ) -> Self {
        let session_id = session_id.unwrap_or_else(|| {
            format!("eval-{}", Utc::now().timestamp())
        });

        Self {
            agent,
            metrics,
            session_id,
        }
    }

    /// Evaluates agent on test cases.
    ///
    /// # Arguments
    ///
    /// * `test_cases` - List of test cases, each with 'input' and 'expected' keys
    /// * `evaluation_id` - Optional evaluation ID
    ///
    /// # Returns
    ///
    /// EvaluationResult with metrics and analysis
    ///
    /// # Example
    ///
    /// ```no_run
    /// use agenkit::evaluation::Evaluator;
    /// use std::collections::HashMap;
    ///
    /// # async fn example(evaluator: Evaluator) -> Result<(), Box<dyn std::error::Error>> {
    /// let mut test_case = HashMap::new();
    /// test_case.insert("input".to_string(), serde_json::json!("What is 2+2?"));
    /// test_case.insert("expected".to_string(), serde_json::json!("4"));
    ///
    /// let result = evaluator.evaluate(vec![test_case], None).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn evaluate(
        &self,
        test_cases: Vec<HashMap<String, serde_json::Value>>,
        evaluation_id: Option<String>,
    ) -> Result<EvaluationResult, AgentError> {
        let evaluation_id = evaluation_id.unwrap_or_else(|| Uuid::new_v4().to_string());

        let mut result = EvaluationResult {
            evaluation_id,
            agent_name: self.agent.name().to_string(),
            timestamp: Utc::now(),
            metrics: HashMap::new(),
            aggregated_metrics: HashMap::new(),
            context_length: None,
            compressed_length: None,
            compression_ratio: None,
            accuracy: None,
            quality_score: None,
            avg_latency_ms: None,
            p95_latency_ms: None,
            total_tests: test_cases.len(),
            passed_tests: 0,
            failed_tests: 0,
            metadata: HashMap::new(),
        };

        let mut latencies = Vec::new();
        let mut errors = Vec::new();

        // Run tests and collect metrics
        for test_case in &test_cases {
            // Extract input
            let input_content = match test_case.get("input") {
                Some(serde_json::Value::String(s)) => s.clone(),
                _ => {
                    result.failed_tests += 1;
                    continue;
                }
            };

            let mut input_msg = Message::with_text("user", &input_content);
            input_msg.metadata.insert(
                "session_id".to_string(),
                serde_json::json!(self.session_id),
            );

            // Run agent with timing
            let start = Instant::now();
            let output_msg = self.agent.process(input_msg).await;
            let latency = start.elapsed();

            match output_msg {
                Ok(msg) => {
                    result.passed_tests += 1;
                    latencies.push(latency.as_millis() as f64);

                    // Collect metrics
                    let ctx = test_case.clone();
                    for metric in &self.metrics {
                        let value = metric.measure(
                            self.agent.clone(),
                            &Message::with_text("user", &input_content),
                            &msg,
                            &ctx,
                        ).await?;

                        result.metrics
                            .entry(metric.name().to_string())
                            .or_insert_with(Vec::new)
                            .push(value);
                    }
                }
                Err(err) => {
                    result.failed_tests += 1;
                    errors.push(err.to_string());
                }
            }
        }

        // Calculate latency statistics
        if !latencies.is_empty() {
            let sum: f64 = latencies.iter().sum();
            result.avg_latency_ms = Some(sum / latencies.len() as f64);

            let mut sorted_latencies = latencies.clone();
            sorted_latencies.sort_by(|a, b| a.partial_cmp(b).unwrap());
            let p95_index = (sorted_latencies.len() as f64 * 0.95) as usize;
            result.p95_latency_ms = Some(sorted_latencies[p95_index.min(sorted_latencies.len() - 1)]);
        }

        // Aggregate metrics
        for (metric_name, measurements) in &result.metrics {
            if let Some(metric) = self.metrics.iter().find(|m| m.name() == metric_name) {
                let aggregated = metric.aggregate(measurements);
                result.aggregated_metrics.insert(metric_name.clone(), aggregated);
            }
        }

        // Store errors if any
        if !errors.is_empty() {
            result.metadata.insert("errors".to_string(), serde_json::json!(errors));
        }

        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::Message;

    struct MockAgent;

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock"
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", "response"))
        }
    }

    #[tokio::test]
    async fn test_evaluator_basic() {
        let agent = Arc::new(MockAgent);
        let evaluator = Evaluator::new(agent, vec![], None);

        let mut test_case = HashMap::new();
        test_case.insert("input".to_string(), serde_json::json!("test"));
        test_case.insert("expected".to_string(), serde_json::json!("result"));

        let result = evaluator.evaluate(vec![test_case], None).await.unwrap();

        assert_eq!(result.total_tests, 1);
        assert_eq!(result.passed_tests, 1);
        assert_eq!(result.failed_tests, 0);
        assert_eq!(result.success_rate(), 1.0);
    }

    #[tokio::test]
    async fn test_evaluation_result_success_rate() {
        let result = EvaluationResult {
            evaluation_id: "test".to_string(),
            agent_name: "test".to_string(),
            timestamp: Utc::now(),
            metrics: HashMap::new(),
            aggregated_metrics: HashMap::new(),
            context_length: None,
            compressed_length: None,
            compression_ratio: None,
            accuracy: None,
            quality_score: None,
            avg_latency_ms: None,
            p95_latency_ms: None,
            total_tests: 10,
            passed_tests: 8,
            failed_tests: 2,
            metadata: HashMap::new(),
        };

        assert_eq!(result.success_rate(), 0.8);
    }

    #[tokio::test]
    async fn test_evaluation_result_to_dict() {
        let result = EvaluationResult {
            evaluation_id: "test-123".to_string(),
            agent_name: "test-agent".to_string(),
            timestamp: Utc::now(),
            metrics: HashMap::new(),
            aggregated_metrics: HashMap::new(),
            context_length: Some(1000),
            compressed_length: None,
            compression_ratio: None,
            accuracy: Some(0.95),
            quality_score: None,
            avg_latency_ms: None,
            p95_latency_ms: None,
            total_tests: 5,
            passed_tests: 5,
            failed_tests: 0,
            metadata: HashMap::new(),
        };

        let dict = result.to_dict();

        assert_eq!(dict.get("evaluation_id").unwrap(), &serde_json::json!("test-123"));
        assert_eq!(dict.get("agent_name").unwrap(), &serde_json::json!("test-agent"));
        assert_eq!(dict.get("total_tests").unwrap(), &serde_json::json!(5));
        assert_eq!(dict.get("success_rate").unwrap(), &serde_json::json!(1.0));
        assert_eq!(dict.get("context_length").unwrap(), &serde_json::json!(1000));
        assert_eq!(dict.get("accuracy").unwrap(), &serde_json::json!(0.95));
    }
}
