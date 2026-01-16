//! Quality Metrics Framework
//!
//! Provides comprehensive quality scoring for agent outputs.
//!
//! Evaluates multiple quality dimensions:
//! - Relevance: How relevant is response to query?
//! - Completeness: Does response answer all parts?
//! - Coherence: Is response logically structured?
//! - Accuracy: Is information factually correct?
//!
//! # Example
//!
//! ```
//! use agenkit::evaluation::quality_metrics::{AccuracyMetric, QualityMetrics};
//!
//! // Simple accuracy metric
//! let accuracy = AccuracyMetric::new(None, false);
//!
//! // Comprehensive quality scoring
//! let quality = QualityMetrics::new(false, None, None);
//! ```

use async_trait::async_trait;
use std::collections::{HashMap, HashSet};
use std::sync::Arc;

use super::core::Metric;
use crate::core::{Agent, AgentError, Message};

/// Custom validation function type.
pub type ValidatorFunc = Arc<dyn Fn(&str, &str) -> bool + Send + Sync>;

/// Measures task accuracy.
///
/// Compares agent output to expected output to determine correctness.
/// Supports multiple validation methods:
/// - Exact string matching
/// - Substring matching (case-insensitive)
/// - Custom validator functions
///
/// # Example
///
/// ```
/// use agenkit::evaluation::quality_metrics::AccuracyMetric;
///
/// let metric = AccuracyMetric::new(None, false);
/// // Returns 1.0 if correct, 0.0 if incorrect
/// ```
pub struct AccuracyMetric {
    validator: Option<ValidatorFunc>,
    case_sensitive: bool,
}

impl AccuracyMetric {
    /// Creates a new accuracy metric.
    ///
    /// # Arguments
    ///
    /// * `validator` - Custom validation function(expected, actual) -> bool
    /// * `case_sensitive` - Whether string matching is case-sensitive
    pub fn new(validator: Option<ValidatorFunc>, case_sensitive: bool) -> Self {
        Self {
            validator,
            case_sensitive,
        }
    }
}

#[async_trait]
impl Metric for AccuracyMetric {
    fn name(&self) -> &str {
        "accuracy"
    }

    async fn measure(
        &self,
        _agent: Arc<dyn Agent>,
        _input_message: &Message,
        output_message: &Message,
        ctx: &HashMap<String, serde_json::Value>,
    ) -> Result<f64, AgentError> {
        // Get expected output from context
        let expected = match ctx.get("expected") {
            Some(serde_json::Value::String(s)) => s.clone(),
            Some(val) => val.to_string(),
            None => return Ok(1.0), // No expected output = always correct
        };

        let actual = output_message.content_as_str().unwrap_or("");

        // Custom validator
        if let Some(validator) = &self.validator {
            return Ok(if validator(&expected, actual) {
                1.0
            } else {
                0.0
            });
        }

        // String matching
        let expected_str = if self.case_sensitive {
            expected
        } else {
            expected.to_lowercase()
        };

        let actual_str = if self.case_sensitive {
            actual.to_string()
        } else {
            actual.to_lowercase()
        };

        Ok(if actual_str.contains(&expected_str) {
            1.0
        } else {
            0.0
        })
    }

    fn aggregate(&self, measurements: &[f64]) -> HashMap<String, f64> {
        if measurements.is_empty() {
            let mut result = HashMap::new();
            result.insert("accuracy".to_string(), 0.0);
            result.insert("total".to_string(), 0.0);
            result.insert("correct".to_string(), 0.0);
            result.insert("incorrect".to_string(), 0.0);
            return result;
        }

        let total = measurements.len() as f64;
        let correct: f64 = measurements.iter().sum();

        let mut result = HashMap::new();
        result.insert("accuracy".to_string(), correct / total);
        result.insert("total".to_string(), total);
        result.insert("correct".to_string(), correct);
        result.insert("incorrect".to_string(), total - correct);
        result
    }
}

/// Provides comprehensive quality scoring.
///
/// Evaluates multiple quality dimensions:
/// - Relevance: How relevant is response to query?
/// - Completeness: Does response answer all parts?
/// - Coherence: Is response logically structured?
/// - Accuracy: Is information factually correct?
///
/// Uses rule-based scoring.
///
/// # Example
///
/// ```
/// use agenkit::evaluation::quality_metrics::QualityMetrics;
///
/// let metric = QualityMetrics::new(false, None, None);
/// // Returns quality score (0.0 to 1.0)
/// ```
pub struct QualityMetrics {
    #[allow(dead_code)]
    use_llm_judge: bool,
    #[allow(dead_code)]
    judge_model: Option<String>,
    weights: HashMap<String, f64>,
}

impl QualityMetrics {
    /// Creates a new quality metrics instance.
    ///
    /// # Arguments
    ///
    /// * `use_llm_judge` - Use LLM to judge quality (not yet implemented)
    /// * `judge_model` - Model to use for judging (e.g., "claude-sonnet-4")
    /// * `weights` - Weights for each dimension (relevance, completeness, etc.)
    pub fn new(
        use_llm_judge: bool,
        judge_model: Option<String>,
        weights: Option<HashMap<String, f64>>,
    ) -> Self {
        let weights = weights.unwrap_or_else(|| {
            let mut w = HashMap::new();
            w.insert("relevance".to_string(), 0.3);
            w.insert("completeness".to_string(), 0.3);
            w.insert("coherence".to_string(), 0.2);
            w.insert("accuracy".to_string(), 0.2);
            w
        });

        Self {
            use_llm_judge,
            judge_model,
            weights,
        }
    }

    /// Performs rule-based quality scoring.
    ///
    /// Uses heuristics to evaluate quality:
    /// - Relevance: Response mentions query terms
    /// - Completeness: Response length vs query complexity
    /// - Coherence: Proper structure, no repetition
    /// - Accuracy: Matches expected output if provided
    fn rule_based_quality(
        &self,
        input_message: &Message,
        output_message: &Message,
        ctx: &HashMap<String, serde_json::Value>,
    ) -> f64 {
        let input_text = input_message.content_as_str().unwrap_or("").to_lowercase();
        let output_text = output_message.content_as_str().unwrap_or("").to_lowercase();

        let mut scores = HashMap::new();

        // Relevance: Does response mention query terms?
        let query_terms: HashSet<_> = input_text.split_whitespace().collect();

        let output_terms: HashSet<_> = output_text.split_whitespace().collect();

        let overlap = query_terms
            .iter()
            .filter(|term| output_terms.contains(*term))
            .count();

        let relevance = if query_terms.is_empty() {
            0.0
        } else {
            (overlap as f64 / query_terms.len() as f64).min(1.0)
        };
        scores.insert("relevance", relevance);

        // Completeness: Is response substantial?
        let expected_length = (input_text.len() * 2).max(100) as f64;
        let completeness = (output_text.len() as f64 / expected_length).min(1.0);
        scores.insert("completeness", completeness);

        // Coherence: Basic checks
        let has_structure = output_text.len() > 20;
        let no_repetition = !self.has_repetition(&output_text);

        let mut coherence = 0.0;
        if has_structure {
            coherence += 0.5;
        }
        if no_repetition {
            coherence += 0.5;
        }
        scores.insert("coherence", coherence);

        // Accuracy: Compare to expected if available
        let accuracy = match ctx.get("expected") {
            Some(serde_json::Value::String(s)) => {
                let expected_str = s.to_lowercase();
                if output_text.contains(&expected_str) {
                    1.0
                } else {
                    0.0
                }
            }
            Some(expected) => {
                let expected_str = expected.to_string().to_lowercase();
                if output_text.contains(&expected_str) {
                    1.0
                } else {
                    0.0
                }
            }
            None => 0.5, // Neutral if no expected output
        };
        scores.insert("accuracy", accuracy);

        // Weighted average
        let mut total_score = 0.0;
        for (dim, score) in scores {
            if let Some(weight) = self.weights.get(dim) {
                total_score += score * weight;
            }
        }

        total_score
    }

    /// Checks for excessive repetition in text.
    fn has_repetition(&self, text: &str) -> bool {
        let words: Vec<_> = text.split_whitespace().collect();
        if words.len() < 10 {
            return false;
        }

        // Check for repeated phrases (3+ word sequences)
        let mut seen_phrases = HashSet::new();
        for i in 0..words.len().saturating_sub(2) {
            let phrase = format!("{} {} {}", words[i], words[i + 1], words[i + 2]);
            if seen_phrases.contains(&phrase) {
                return true;
            }
            seen_phrases.insert(phrase);
        }

        false
    }
}

#[async_trait]
impl Metric for QualityMetrics {
    fn name(&self) -> &str {
        "quality"
    }

    async fn measure(
        &self,
        _agent: Arc<dyn Agent>,
        input_message: &Message,
        output_message: &Message,
        ctx: &HashMap<String, serde_json::Value>,
    ) -> Result<f64, AgentError> {
        Ok(self.rule_based_quality(input_message, output_message, ctx))
    }

    fn aggregate(&self, measurements: &[f64]) -> HashMap<String, f64> {
        if measurements.is_empty() {
            return HashMap::new();
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
        result.insert("std".to_string(), std);
        result.insert("min".to_string(), min);
        result.insert("max".to_string(), max);
        result.insert("count".to_string(), count);
        result
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

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", "response"))
        }
    }

    #[tokio::test]
    async fn test_accuracy_metric_exact_match() {
        let metric = AccuracyMetric::new(None, true);
        let agent = Arc::new(MockAgent);

        let input = Message::with_text("user", "What is 2+2?");
        let output = Message::with_text("assistant", "The answer is 4");

        let mut ctx = HashMap::new();
        ctx.insert("expected".to_string(), serde_json::json!("4"));

        let score = metric.measure(agent, &input, &output, &ctx).await.unwrap();
        assert_eq!(score, 1.0);
    }

    #[tokio::test]
    async fn test_accuracy_metric_no_match() {
        let metric = AccuracyMetric::new(None, false);
        let agent = Arc::new(MockAgent);

        let input = Message::with_text("user", "What is 2+2?");
        let output = Message::with_text("assistant", "The answer is 5");

        let mut ctx = HashMap::new();
        ctx.insert("expected".to_string(), serde_json::json!("4"));

        let score = metric.measure(agent, &input, &output, &ctx).await.unwrap();
        assert_eq!(score, 0.0);
    }

    #[tokio::test]
    async fn test_accuracy_metric_case_insensitive() {
        let metric = AccuracyMetric::new(None, false);
        let agent = Arc::new(MockAgent);

        let input = Message::with_text("user", "Capital of France?");
        let output = Message::with_text("assistant", "PARIS is the capital");

        let mut ctx = HashMap::new();
        ctx.insert("expected".to_string(), serde_json::json!("paris"));

        let score = metric.measure(agent, &input, &output, &ctx).await.unwrap();
        assert_eq!(score, 1.0);
    }

    #[tokio::test]
    async fn test_accuracy_metric_aggregate() {
        let metric = AccuracyMetric::new(None, false);

        let measurements = vec![1.0, 1.0, 0.0, 1.0, 0.0];
        let result = metric.aggregate(&measurements);

        assert_eq!(result.get("accuracy").unwrap(), &0.6);
        assert_eq!(result.get("total").unwrap(), &5.0);
        assert_eq!(result.get("correct").unwrap(), &3.0);
        assert_eq!(result.get("incorrect").unwrap(), &2.0);
    }

    #[tokio::test]
    async fn test_quality_metrics_basic() {
        let metric = QualityMetrics::new(false, None, None);
        let agent = Arc::new(MockAgent);

        let input = Message::with_text("user", "What is Rust programming language?");
        let output = Message::with_text(
            "assistant",
            "Rust is a systems programming language focused on safety and performance",
        );

        let ctx = HashMap::new();
        let score = metric.measure(agent, &input, &output, &ctx).await.unwrap();

        // Should have reasonable quality score due to relevance
        assert!(score > 0.0);
        assert!(score <= 1.0);
    }

    #[tokio::test]
    async fn test_quality_metrics_with_expected() {
        let metric = QualityMetrics::new(false, None, None);
        let agent = Arc::new(MockAgent);

        let input = Message::with_text("user", "What is 2+2?");
        let output = Message::with_text("assistant", "The answer is 4. This is a basic arithmetic operation where we add two and two together.");

        let mut ctx = HashMap::new();
        ctx.insert("expected".to_string(), serde_json::json!("4"));

        let score = metric.measure(agent, &input, &output, &ctx).await.unwrap();

        // Should have high quality due to accuracy and completeness
        assert!(score > 0.5);
    }

    #[test]
    fn test_has_repetition() {
        let metric = QualityMetrics::new(false, None, None);

        // No repetition
        assert!(!metric.has_repetition("This is a normal sentence without any repetition at all"));

        // With repetition (needs 10+ words)
        assert!(
            metric.has_repetition("This is a test phrase this is a test phrase again and again")
        );

        // Short text (no repetition check)
        assert!(!metric.has_repetition("Short"));
    }
}
