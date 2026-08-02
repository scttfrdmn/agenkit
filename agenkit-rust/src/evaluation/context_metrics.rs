//! Context Metrics Framework
//!
//! Tracks context length, compression, and latency metrics for extreme-scale agents.
//!
//! Essential for systems like endless that operate at 1M-25M+ token contexts.
//!
//! # Example
//!
//! ```
//! use agenkit::evaluation::context_metrics::{ContextMetrics, LatencyMetric};
//!
//! let context = ContextMetrics::new();
//! let latency = LatencyMetric::new();
//! ```

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;

use super::core::Metric;
use crate::core::{Agent, AgentError, Message};

/// Tracks context length and growth over agent lifecycle.
///
/// Essential for extreme-scale systems that operate at 1M-25M+ tokens.
/// Measures:
/// - Raw context token count
/// - Compressed context token count (if compression used)
/// - Compression ratio
/// - Context growth rate
///
/// # Example
///
/// ```
/// use agenkit::evaluation::context_metrics::ContextMetrics;
///
/// let metric = ContextMetrics::new();
/// // Returns context length in tokens
/// ```
pub struct ContextMetrics;

impl ContextMetrics {
    /// Creates a new context metrics instance.
    pub fn new() -> Self {
        Self
    }

    /// Estimates token count from text (rough: 4 chars ≈ 1 token).
    fn estimate_tokens(&self, content: &str) -> usize {
        content.len() / 4
    }
}

impl Default for ContextMetrics {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Metric for ContextMetrics {
    fn name(&self) -> &str {
        "context_length"
    }

    async fn measure(
        &self,
        _agent: Arc<dyn Agent>,
        input_message: &Message,
        _output_message: &Message,
        ctx: &HashMap<String, serde_json::Value>,
    ) -> Result<f64, AgentError> {
        // Check metadata for context length
        if let Some(context_length) = input_message.metadata.get("context_length") {
            if let Some(length) = context_length.as_f64() {
                return Ok(length);
            }
            if let Some(length) = context_length.as_i64() {
                return Ok(length as f64);
            }
        }

        // Fallback: estimate from conversation history
        if let Some(history_val) = ctx.get("conversation_history") {
            if let Some(history) = history_val.as_array() {
                let total_tokens: usize = history
                    .iter()
                    .filter_map(|msg| msg.get("content"))
                    .filter_map(|content| content.as_str())
                    .map(|content| self.estimate_tokens(content))
                    .sum();
                return Ok(total_tokens as f64);
            }
        }

        Ok(0.0)
    }

    fn aggregate(&self, measurements: &[f64]) -> HashMap<String, f64> {
        if measurements.is_empty() {
            let mut result = HashMap::new();
            result.insert("mean".to_string(), 0.0);
            result.insert("min".to_string(), 0.0);
            result.insert("max".to_string(), 0.0);
            result.insert("final".to_string(), 0.0);
            result.insert("growth_rate".to_string(), 0.0);
            return result;
        }

        let sum: f64 = measurements.iter().sum();
        let mean = sum / measurements.len() as f64;

        let min = measurements.iter().fold(f64::INFINITY, |a, &b| a.min(b));
        let max = measurements
            .iter()
            .fold(f64::NEG_INFINITY, |a, &b| a.max(b));

        let final_value = measurements[measurements.len() - 1];

        let growth_rate = if measurements.len() > 1 {
            (measurements[measurements.len() - 1] - measurements[0]) / measurements.len() as f64
        } else {
            0.0
        };

        let mut result = HashMap::new();
        result.insert("mean".to_string(), mean);
        result.insert("min".to_string(), min);
        result.insert("max".to_string(), max);
        result.insert("final".to_string(), final_value);
        result.insert("growth_rate".to_string(), growth_rate);
        result
    }
}

/// Statistics from compression evaluation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompressionStats {
    /// Raw token count
    pub raw_tokens: usize,
    /// Compressed token count
    pub compressed_tokens: usize,
    /// Compression ratio (raw / compressed)
    pub compression_ratio: f64,
    /// Retrieval accuracy (0.0 to 1.0)
    pub retrieval_accuracy: f64,
    /// Context length tested
    pub context_length_tested: usize,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
}

impl CompressionStats {
    /// Converts stats to dictionary.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut result = HashMap::new();
        result.insert("raw_tokens".to_string(), serde_json::json!(self.raw_tokens));
        result.insert(
            "compressed_tokens".to_string(),
            serde_json::json!(self.compressed_tokens),
        );
        result.insert(
            "compression_ratio".to_string(),
            serde_json::json!(self.compression_ratio),
        );
        result.insert(
            "retrieval_accuracy".to_string(),
            serde_json::json!(self.retrieval_accuracy),
        );
        result.insert(
            "context_length_tested".to_string(),
            serde_json::json!(self.context_length_tested),
        );
        result.insert(
            "timestamp".to_string(),
            serde_json::json!(self.timestamp.to_rfc3339()),
        );
        result
    }
}

/// Measures compression quality at extreme scale.
///
/// Critical for systems that use 100x-1000x compression at 25M+ tokens.
/// Measures:
/// - Compression ratio achieved
/// - Information retention after compression
/// - Retrieval accuracy from compressed context
/// - Quality degradation as context grows
///
/// # Example
///
/// ```
/// use agenkit::evaluation::context_metrics::CompressionMetrics;
///
/// let metric = CompressionMetrics::new(None, 10);
/// // Tests at 1M, 10M, 25M tokens by default
/// ```
pub struct CompressionMetrics {
    test_lengths: Vec<usize>,
    needle_count: usize,
}

impl CompressionMetrics {
    /// Creates a new compression metrics instance.
    ///
    /// # Arguments
    ///
    /// * `test_lengths` - Context lengths to test (defaults to 1M, 10M, 25M)
    /// * `needle_count` - Number of "needle" facts to test retrieval
    pub fn new(test_lengths: Option<Vec<usize>>, needle_count: usize) -> Self {
        let test_lengths = test_lengths.unwrap_or_else(|| {
            vec![
                1_000_000,  // 1M tokens
                10_000_000, // 10M tokens
                25_000_000, // 25M tokens (endless scale)
            ]
        });

        Self {
            test_lengths,
            needle_count,
        }
    }

    /// Generates default needle facts for testing.
    fn default_needles(&self) -> Vec<String> {
        (0..self.needle_count)
            .map(|i| {
                format!(
                    "NEEDLE FACT {}: The secret code is ALPHA-{:04}-OMEGA.",
                    i, i
                )
            })
            .collect()
    }

    /// Generates test context with embedded needles.
    ///
    /// # Arguments
    ///
    /// * `target_tokens` - Target context length
    /// * `needles` - Facts to embed for retrieval testing
    ///
    /// # Returns
    ///
    /// List of messages totaling ~target_tokens
    fn generate_test_context(&self, target_tokens: usize, needles: &[String]) -> Vec<String> {
        let mut messages = Vec::new();
        let mut current_tokens = 0;

        // Insert needles at regular intervals
        let needle_interval = target_tokens / (needles.len() + 1);
        let mut next_needle_at = needle_interval;
        let mut needle_idx = 0;

        // Generate filler content
        let filler = "This is filler content for context expansion. ".repeat(20);
        let filler_tokens = filler.len() / 4;

        while current_tokens < target_tokens {
            // Insert needle if at interval
            if current_tokens >= next_needle_at && needle_idx < needles.len() {
                messages.push(needles[needle_idx].clone());
                current_tokens += needles[needle_idx].len() / 4;
                needle_idx += 1;
                next_needle_at += needle_interval;
            } else {
                // Add filler
                messages.push(filler.clone());
                current_tokens += filler_tokens;
            }
        }

        messages
    }

    /// Tests retrieval accuracy of needles from context.
    ///
    /// # Arguments
    ///
    /// * `agent` - Agent to test
    /// * `needles` - Facts that should be retrievable
    ///
    /// # Returns
    ///
    /// Accuracy (0.0 to 1.0)
    async fn test_retrieval(
        &self,
        agent: Arc<dyn Agent>,
        needles: &[String],
    ) -> Result<f64, AgentError> {
        let mut correct = 0;

        for needle in needles {
            // Ask agent to retrieve the fact
            let needle_preview = if needle.len() > 50 {
                &needle[..50]
            } else {
                needle.as_str()
            };

            let query = Message::with_text(
                "user",
                format!("Recall: What was mentioned about {}?", needle_preview),
            );

            match agent.process(query).await {
                Ok(response) => {
                    let response_text = response.content_as_str().unwrap_or("").to_lowercase();
                    let needle_text = needle.to_lowercase();
                    if response_text.contains(&needle_text) {
                        correct += 1;
                    }
                }
                Err(_) => continue,
            }
        }

        if needles.is_empty() {
            return Ok(0.0);
        }
        Ok(correct as f64 / needles.len() as f64)
    }

    /// Evaluates compression quality at multiple context lengths.
    ///
    /// Tests compression and retrieval at 1M, 10M, 25M tokens to
    /// detect quality degradation as context grows.
    ///
    /// # Arguments
    ///
    /// * `agent` - Agent with compression capability
    /// * `needle_content` - Specific facts to test retrieval (optional)
    ///
    /// # Returns
    ///
    /// Dictionary mapping context_length -> CompressionStats
    pub async fn evaluate_at_lengths(
        &self,
        agent: Arc<dyn Agent>,
        needle_content: Option<Vec<String>>,
    ) -> Result<HashMap<usize, CompressionStats>, AgentError> {
        let needles = needle_content.unwrap_or_else(|| self.default_needles());
        let mut results = HashMap::new();

        for &length in &self.test_lengths {
            // Create test messages to reach target length
            let test_messages = self.generate_test_context(length, &needles);

            // Process messages through agent
            for msg in test_messages {
                let message = Message::with_text("user", &msg);
                agent.process(message).await?;
            }

            // Test retrieval accuracy
            let accuracy = self.test_retrieval(agent.clone(), &needles).await?;

            results.insert(
                length,
                CompressionStats {
                    raw_tokens: length,
                    compressed_tokens: length / 100, // Placeholder
                    compression_ratio: 100.0,        // Placeholder
                    retrieval_accuracy: accuracy,
                    context_length_tested: length,
                    timestamp: Utc::now(),
                },
            );
        }

        Ok(results)
    }
}

#[async_trait]
impl Metric for CompressionMetrics {
    fn name(&self) -> &str {
        "compression_quality"
    }

    async fn measure(
        &self,
        _agent: Arc<dyn Agent>,
        _input_message: &Message,
        output_message: &Message,
        _ctx: &HashMap<String, serde_json::Value>,
    ) -> Result<f64, AgentError> {
        // Check metadata for compression ratio
        if let Some(compression_ratio) = output_message.metadata.get("compression_ratio") {
            if let Some(ratio) = compression_ratio.as_f64() {
                return Ok(ratio);
            }
        }

        Ok(1.0) // No compression
    }

    fn aggregate(&self, measurements: &[f64]) -> HashMap<String, f64> {
        if measurements.is_empty() {
            let mut result = HashMap::new();
            result.insert("mean".to_string(), 1.0);
            result.insert("min".to_string(), 1.0);
            result.insert("max".to_string(), 1.0);
            result.insert("std".to_string(), 0.0);
            return result;
        }

        let sum: f64 = measurements.iter().sum();
        let count = measurements.len() as f64;
        let mean = sum / count;

        let variance: f64 = measurements.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / count;
        let std = variance.sqrt();

        let min = measurements.iter().fold(f64::INFINITY, |a, &b| a.min(b));
        let max = measurements
            .iter()
            .fold(f64::NEG_INFINITY, |a, &b| a.max(b));

        let mut result = HashMap::new();
        result.insert("mean".to_string(), mean);
        result.insert("min".to_string(), min);
        result.insert("max".to_string(), max);
        result.insert("std".to_string(), std);
        result
    }
}

/// Measures agent response latency.
///
/// Tracks processing time per interaction. Critical for production
/// systems where response time matters.
///
/// # Example
///
/// ```
/// use agenkit::evaluation::context_metrics::LatencyMetric;
///
/// let metric = LatencyMetric::new();
/// // Returns latency in milliseconds
/// ```
pub struct LatencyMetric;

impl LatencyMetric {
    /// Creates a new latency metric instance.
    pub fn new() -> Self {
        Self
    }
}

impl Default for LatencyMetric {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Metric for LatencyMetric {
    fn name(&self) -> &str {
        "latency"
    }

    async fn measure(
        &self,
        _agent: Arc<dyn Agent>,
        _input_message: &Message,
        _output_message: &Message,
        ctx: &HashMap<String, serde_json::Value>,
    ) -> Result<f64, AgentError> {
        if let Some(latency_ms) = ctx.get("latency_ms") {
            if let Some(latency) = latency_ms.as_f64() {
                return Ok(latency);
            }
        }
        Ok(0.0)
    }

    fn aggregate(&self, measurements: &[f64]) -> HashMap<String, f64> {
        if measurements.is_empty() {
            let mut result = HashMap::new();
            result.insert("mean".to_string(), 0.0);
            result.insert("p50".to_string(), 0.0);
            result.insert("p95".to_string(), 0.0);
            result.insert("p99".to_string(), 0.0);
            result.insert("min".to_string(), 0.0);
            result.insert("max".to_string(), 0.0);
            return result;
        }

        let mut sorted = measurements.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let n = sorted.len();
        let sum: f64 = measurements.iter().sum();
        let mean = sum / n as f64;

        let p50_idx = (n as f64 * 0.50) as usize;
        let p95_idx = (n as f64 * 0.95) as usize;
        let p99_idx = (n as f64 * 0.99) as usize;

        let mut result = HashMap::new();
        result.insert("mean".to_string(), mean);
        result.insert("p50".to_string(), sorted[p50_idx.min(n - 1)]);
        result.insert("p95".to_string(), sorted[p95_idx.min(n - 1)]);
        result.insert("p99".to_string(), sorted[p99_idx.min(n - 1)]);
        result.insert("min".to_string(), sorted[0]);
        result.insert("max".to_string(), sorted[n - 1]);
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockAgent;

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", "response"))
        }
    }

    #[tokio::test]
    async fn test_context_metrics_basic() {
        let metric = ContextMetrics::new();
        let agent = Arc::new(MockAgent);

        let mut input = Message::with_text("user", "test");
        input
            .metadata
            .insert("context_length".to_string(), serde_json::json!(1000));

        let output = Message::with_text("assistant", "response");
        let ctx = HashMap::new();

        let length = metric.measure(agent, &input, &output, &ctx).await.unwrap();
        assert_eq!(length, 1000.0);
    }

    #[tokio::test]
    async fn test_context_metrics_aggregate() {
        let metric = ContextMetrics::new();
        let measurements = vec![100.0, 200.0, 300.0, 400.0];

        let result = metric.aggregate(&measurements);

        assert_eq!(result.get("mean").unwrap(), &250.0);
        assert_eq!(result.get("min").unwrap(), &100.0);
        assert_eq!(result.get("max").unwrap(), &400.0);
        assert_eq!(result.get("final").unwrap(), &400.0);
        assert_eq!(result.get("growth_rate").unwrap(), &75.0);
    }

    #[tokio::test]
    async fn test_compression_metrics_basic() {
        let metric = CompressionMetrics::new(None, 10);
        let agent = Arc::new(MockAgent);

        let input = Message::with_text("user", "test");
        let mut output = Message::with_text("assistant", "response");
        output
            .metadata
            .insert("compression_ratio".to_string(), serde_json::json!(100.0));

        let ctx = HashMap::new();
        let ratio = metric.measure(agent, &input, &output, &ctx).await.unwrap();
        assert_eq!(ratio, 100.0);
    }

    #[tokio::test]
    async fn test_compression_metrics_aggregate() {
        let metric = CompressionMetrics::new(None, 10);
        let measurements = vec![50.0, 100.0, 150.0];

        let result = metric.aggregate(&measurements);

        assert_eq!(result.get("mean").unwrap(), &100.0);
        assert_eq!(result.get("min").unwrap(), &50.0);
        assert_eq!(result.get("max").unwrap(), &150.0);
    }

    #[tokio::test]
    async fn test_latency_metric_basic() {
        let metric = LatencyMetric::new();
        let agent = Arc::new(MockAgent);

        let input = Message::with_text("user", "test");
        let output = Message::with_text("assistant", "response");

        let mut ctx = HashMap::new();
        ctx.insert("latency_ms".to_string(), serde_json::json!(150.5));

        let latency = metric.measure(agent, &input, &output, &ctx).await.unwrap();
        assert_eq!(latency, 150.5);
    }

    #[tokio::test]
    async fn test_latency_metric_aggregate() {
        let metric = LatencyMetric::new();
        let measurements = vec![100.0, 200.0, 300.0, 400.0, 500.0];

        let result = metric.aggregate(&measurements);

        assert_eq!(result.get("mean").unwrap(), &300.0);
        assert_eq!(result.get("p50").unwrap(), &300.0);
        assert_eq!(result.get("min").unwrap(), &100.0);
        assert_eq!(result.get("max").unwrap(), &500.0);
    }

    #[test]
    fn test_compression_stats_to_dict() {
        let stats = CompressionStats {
            raw_tokens: 1000000,
            compressed_tokens: 10000,
            compression_ratio: 100.0,
            retrieval_accuracy: 0.95,
            context_length_tested: 1000000,
            timestamp: Utc::now(),
        };

        let dict = stats.to_dict();

        assert_eq!(dict.get("raw_tokens").unwrap(), &serde_json::json!(1000000));
        assert_eq!(
            dict.get("compressed_tokens").unwrap(),
            &serde_json::json!(10000)
        );
        assert_eq!(
            dict.get("compression_ratio").unwrap(),
            &serde_json::json!(100.0)
        );
        assert_eq!(
            dict.get("retrieval_accuracy").unwrap(),
            &serde_json::json!(0.95)
        );
    }
}
