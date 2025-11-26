//! Regression Testing Framework
//!
//! Detects performance regressions by comparing evaluation results over time.
//!
//! Monitors agent quality and alerts when performance degrades beyond
//! acceptable thresholds.
//!
//! # Example
//!
//! ```
//! use agenkit::evaluation::regression::RegressionDetector;
//!
//! let mut detector = RegressionDetector::new(None, None);
//! // detector.set_baseline(baseline_result);
//!
//! // Later, after changes
//! // let regressions = detector.detect(&current_result, true);
//! // if !regressions.is_empty() {
//! //     println!("Found {} regressions!", regressions.len());
//! // }
//! ```

use std::collections::HashMap;
use chrono::{DateTime, Utc};
use serde::{Serialize, Deserialize};

use super::core::EvaluationResult;

/// Regression severity levels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    /// No significant regression
    None,
    /// Minor degradation (<10%)
    Minor,
    /// Moderate degradation (10-20%)
    Moderate,
    /// Major degradation (20-50%)
    Major,
    /// Critical degradation (>50%)
    Critical,
}

impl std::fmt::Display for Severity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Severity::None => write!(f, "none"),
            Severity::Minor => write!(f, "minor"),
            Severity::Moderate => write!(f, "moderate"),
            Severity::Major => write!(f, "major"),
            Severity::Critical => write!(f, "critical"),
        }
    }
}

/// Detected regression in agent performance.
///
/// Contains information about what degraded and by how much.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Regression {
    /// Metric name
    pub metric_name: String,
    /// Baseline value
    pub baseline_value: f64,
    /// Current value
    pub current_value: f64,
    /// Degradation percentage
    pub degradation_percent: f64,
    /// Severity level
    pub severity: Severity,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Additional context
    #[serde(skip_serializing_if = "HashMap::is_empty")]
    pub context: HashMap<String, serde_json::Value>,
}

impl Regression {
    /// Checks if this is a real regression (not improvement).
    pub fn is_regression(&self) -> bool {
        self.degradation_percent > 0.0
    }

    /// Converts regression to dictionary.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut result = HashMap::new();
        result.insert("metric_name".to_string(), serde_json::json!(self.metric_name));
        result.insert("baseline_value".to_string(), serde_json::json!(self.baseline_value));
        result.insert("current_value".to_string(), serde_json::json!(self.current_value));
        result.insert("degradation_percent".to_string(), serde_json::json!(self.degradation_percent));
        result.insert("severity".to_string(), serde_json::json!(self.severity.to_string()));
        result.insert("timestamp".to_string(), serde_json::json!(self.timestamp.to_rfc3339()));
        result.insert("context".to_string(), serde_json::json!(self.context));
        result
    }
}

/// Detects performance regressions by comparing results.
///
/// Monitors agent quality over time and alerts when performance
/// degrades beyond acceptable thresholds.
///
/// # Example
///
/// ```
/// use agenkit::evaluation::regression::RegressionDetector;
///
/// let mut detector = RegressionDetector::new(None, None);
/// // detector.set_baseline(baseline_result);
/// // let regressions = detector.detect(&current_result, true);
/// ```
pub struct RegressionDetector {
    thresholds: HashMap<String, f64>,
    baseline: Option<EvaluationResult>,
    history: Vec<EvaluationResult>,
}

impl RegressionDetector {
    /// Creates a new regression detector.
    ///
    /// # Arguments
    ///
    /// * `thresholds` - Acceptable degradation per metric (default 10%)
    /// * `baseline` - Baseline evaluation result to compare against
    pub fn new(
        thresholds: Option<HashMap<String, f64>>,
        baseline: Option<EvaluationResult>,
    ) -> Self {
        let thresholds = thresholds.unwrap_or_else(|| {
            let mut t = HashMap::new();
            t.insert("accuracy".to_string(), 0.10);       // 10% degradation threshold
            t.insert("quality".to_string(), 0.10);        // 10% degradation threshold
            t.insert("latency".to_string(), 0.20);        // 20% slower acceptable
            t.insert("context_length".to_string(), 0.30); // 30% larger context acceptable
            t
        });

        Self {
            thresholds,
            baseline,
            history: Vec::new(),
        }
    }

    /// Sets baseline for comparison.
    pub fn set_baseline(&mut self, result: EvaluationResult) {
        self.baseline = Some(result);
    }

    /// Detects regressions in evaluation result.
    ///
    /// Compares current result to baseline and identifies metrics
    /// that have degraded beyond acceptable thresholds.
    ///
    /// # Arguments
    ///
    /// * `result` - Current evaluation result
    /// * `store_history` - Whether to store result in history
    ///
    /// # Returns
    ///
    /// List of detected regressions (empty if no regressions)
    pub fn detect(&mut self, result: &EvaluationResult, store_history: bool) -> Vec<Regression> {
        if store_history {
            self.history.push(result.clone());
        }

        let baseline = match &self.baseline {
            Some(b) => b,
            None => return Vec::new(), // No baseline = no regressions
        };

        let mut regressions = Vec::new();

        // Check accuracy
        if let (Some(baseline_acc), Some(current_acc)) = (baseline.accuracy, result.accuracy) {
            if let Some(reg) = self.check_metric("accuracy", baseline_acc, current_acc, true) {
                regressions.push(reg);
            }
        }

        // Check quality_score
        if let (Some(baseline_qual), Some(current_qual)) = (baseline.quality_score, result.quality_score) {
            if let Some(reg) = self.check_metric("quality", baseline_qual, current_qual, true) {
                regressions.push(reg);
            }
        }

        // Check latency (lower is better)
        if let (Some(baseline_lat), Some(current_lat)) = (baseline.avg_latency_ms, result.avg_latency_ms) {
            if let Some(reg) = self.check_metric("latency", baseline_lat, current_lat, false) {
                regressions.push(reg);
            }
        }

        // Check context length
        if let (Some(baseline_ctx), Some(current_ctx)) = (baseline.context_length, result.context_length) {
            if let Some(reg) = self.check_metric(
                "context_length",
                baseline_ctx as f64,
                current_ctx as f64,
                false,
            ) {
                regressions.push(reg);
            }
        }

        // Check compression ratio (higher is better)
        if let (Some(baseline_comp), Some(current_comp)) = (baseline.compression_ratio, result.compression_ratio) {
            if let Some(reg) = self.check_metric("compression_ratio", baseline_comp, current_comp, true) {
                regressions.push(reg);
            }
        }

        regressions
    }

    /// Checks single metric for regression.
    ///
    /// # Arguments
    ///
    /// * `name` - Metric name
    /// * `baseline` - Baseline value
    /// * `current` - Current value
    /// * `higher_is_better` - Whether higher values are better
    ///
    /// # Returns
    ///
    /// Regression if detected, None otherwise
    fn check_metric(
        &self,
        name: &str,
        baseline: f64,
        current: f64,
        higher_is_better: bool,
    ) -> Option<Regression> {
        let degradation = if baseline == 0.0 {
            // Avoid division by zero
            if current == 0.0 {
                return None;
            }
            if higher_is_better {
                1.0
            } else {
                -1.0
            }
        } else if higher_is_better {
            // For accuracy, quality: lower is worse
            (baseline - current) / baseline
        } else {
            // For latency, context_length: higher is worse
            (current - baseline) / baseline
        };

        // Check if exceeds threshold
        let threshold = self.thresholds.get(name).copied().unwrap_or(0.10);

        if degradation > threshold {
            let severity = self.calculate_severity(degradation);
            let mut context = HashMap::new();
            context.insert("threshold_percent".to_string(), serde_json::json!(threshold * 100.0));
            context.insert("higher_is_better".to_string(), serde_json::json!(higher_is_better));

            Some(Regression {
                metric_name: name.to_string(),
                baseline_value: baseline,
                current_value: current,
                degradation_percent: degradation * 100.0,
                severity,
                timestamp: Utc::now(),
                context,
            })
        } else {
            None
        }
    }

    /// Calculates severity based on degradation amount.
    ///
    /// # Arguments
    ///
    /// * `degradation` - Degradation as fraction (0.1 = 10%)
    ///
    /// # Returns
    ///
    /// Severity level
    fn calculate_severity(&self, degradation: f64) -> Severity {
        if degradation < 0.10 {
            Severity::None
        } else if degradation < 0.20 {
            Severity::Minor
        } else if degradation < 0.50 {
            Severity::Moderate
        } else {
            Severity::Critical
        }
    }

    /// Gets trend for metric over recent history.
    ///
    /// # Arguments
    ///
    /// * `metric_name` - Metric to analyze
    /// * `window` - Number of recent results to analyze
    ///
    /// # Returns
    ///
    /// Trend statistics (slope, direction, variance)
    pub fn get_trend(&self, metric_name: &str, window: usize) -> Option<HashMap<String, serde_json::Value>> {
        if self.history.len() < 2 {
            return None;
        }

        // Get recent results
        let start = self.history.len().saturating_sub(window);
        let recent = &self.history[start..];

        // Extract metric values
        let values: Vec<f64> = recent
            .iter()
            .filter_map(|result| match metric_name {
                "accuracy" => result.accuracy,
                "quality" => result.quality_score,
                "latency" => result.avg_latency_ms,
                "context_length" => result.context_length.map(|v| v as f64),
                _ => None,
            })
            .collect();

        if values.len() < 2 {
            return None;
        }

        // Calculate trend
        let n = values.len() as f64;
        let x: Vec<f64> = (0..values.len()).map(|i| i as f64).collect();

        let x_mean: f64 = x.iter().sum::<f64>() / n;
        let y_mean: f64 = values.iter().sum::<f64>() / n;

        // Linear regression slope
        let mut numerator = 0.0;
        let mut denominator = 0.0;
        for i in 0..values.len() {
            numerator += (x[i] - x_mean) * (values[i] - y_mean);
            denominator += (x[i] - x_mean) * (x[i] - x_mean);
        }

        let slope = if denominator != 0.0 {
            numerator / denominator
        } else {
            0.0
        };

        // Variance
        let variance: f64 = values
            .iter()
            .map(|v| (v - y_mean).powi(2))
            .sum::<f64>()
            / n;

        let direction = if slope > 0.0 {
            "improving"
        } else if slope < 0.0 {
            "degrading"
        } else {
            "stable"
        };

        let mut result = HashMap::new();
        result.insert("metric".to_string(), serde_json::json!(metric_name));
        result.insert("slope".to_string(), serde_json::json!(slope));
        result.insert("direction".to_string(), serde_json::json!(direction));
        result.insert("variance".to_string(), serde_json::json!(variance));
        result.insert("current".to_string(), serde_json::json!(values[values.len() - 1]));
        result.insert("mean".to_string(), serde_json::json!(y_mean));
        result.insert("window_size".to_string(), serde_json::json!(values.len()));

        Some(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_result(accuracy: f64, latency: f64) -> EvaluationResult {
        EvaluationResult {
            evaluation_id: "test".to_string(),
            agent_name: "test".to_string(),
            timestamp: Utc::now(),
            metrics: HashMap::new(),
            aggregated_metrics: HashMap::new(),
            context_length: None,
            compressed_length: None,
            compression_ratio: None,
            accuracy: Some(accuracy),
            quality_score: None,
            avg_latency_ms: Some(latency),
            p95_latency_ms: None,
            total_tests: 10,
            passed_tests: 10,
            failed_tests: 0,
            metadata: HashMap::new(),
        }
    }

    #[test]
    fn test_regression_creation() {
        let regression = Regression {
            metric_name: "accuracy".to_string(),
            baseline_value: 0.9,
            current_value: 0.8,
            degradation_percent: 11.11,
            severity: Severity::Minor,
            timestamp: Utc::now(),
            context: HashMap::new(),
        };

        assert_eq!(regression.metric_name, "accuracy");
        assert!(regression.is_regression());
    }

    #[test]
    fn test_severity_levels() {
        let detector = RegressionDetector::new(None, None);

        assert_eq!(detector.calculate_severity(0.05), Severity::None);
        assert_eq!(detector.calculate_severity(0.15), Severity::Minor);
        assert_eq!(detector.calculate_severity(0.30), Severity::Moderate);
        assert_eq!(detector.calculate_severity(0.60), Severity::Critical);
    }

    #[test]
    fn test_detector_no_baseline() {
        let mut detector = RegressionDetector::new(None, None);
        let result = create_test_result(0.8, 100.0);

        let regressions = detector.detect(&result, false);
        assert_eq!(regressions.len(), 0);
    }

    #[test]
    fn test_detector_no_regression() {
        let baseline = create_test_result(0.9, 100.0);
        let mut detector = RegressionDetector::new(None, Some(baseline));

        // Slightly better result
        let current = create_test_result(0.91, 95.0);
        let regressions = detector.detect(&current, false);
        assert_eq!(regressions.len(), 0);
    }

    #[test]
    fn test_detector_accuracy_regression() {
        let baseline = create_test_result(0.9, 100.0);
        let mut detector = RegressionDetector::new(None, Some(baseline));

        // 20% worse accuracy: (0.9-0.72)/0.9 = 0.20 = 20%
        let current = create_test_result(0.72, 100.0);
        let regressions = detector.detect(&current, false);

        assert_eq!(regressions.len(), 1);
        assert_eq!(regressions[0].metric_name, "accuracy");
        assert!(regressions[0].degradation_percent > 15.0);
        assert_eq!(regressions[0].severity, Severity::Moderate); // 20% is Moderate
    }

    #[test]
    fn test_detector_latency_regression() {
        let baseline = create_test_result(0.9, 100.0);
        let mut detector = RegressionDetector::new(None, Some(baseline));

        // 30% slower latency
        let current = create_test_result(0.9, 130.0);
        let regressions = detector.detect(&current, false);

        assert_eq!(regressions.len(), 1);
        assert_eq!(regressions[0].metric_name, "latency");
        assert!(regressions[0].degradation_percent > 25.0);
    }

    #[test]
    fn test_detector_custom_thresholds() {
        let baseline = create_test_result(0.9, 100.0);

        let mut thresholds = HashMap::new();
        thresholds.insert("accuracy".to_string(), 0.30); // 30% threshold

        let mut detector = RegressionDetector::new(Some(thresholds), Some(baseline));

        // 20% worse accuracy (within 30% threshold)
        let current = create_test_result(0.72, 100.0);
        let regressions = detector.detect(&current, false);

        assert_eq!(regressions.len(), 0);
    }

    #[test]
    fn test_get_trend() {
        let mut detector = RegressionDetector::new(None, None);

        // Add history with improving accuracy
        detector.history.push(create_test_result(0.70, 100.0));
        detector.history.push(create_test_result(0.75, 100.0));
        detector.history.push(create_test_result(0.80, 100.0));
        detector.history.push(create_test_result(0.85, 100.0));

        let trend = detector.get_trend("accuracy", 4).unwrap();

        assert_eq!(trend.get("metric").unwrap(), &serde_json::json!("accuracy"));
        assert_eq!(trend.get("direction").unwrap(), &serde_json::json!("improving"));
        assert!(trend.get("slope").unwrap().as_f64().unwrap() > 0.0);
    }

    #[test]
    fn test_get_trend_degrading() {
        let mut detector = RegressionDetector::new(None, None);

        // Add history with degrading accuracy (lower values = worse)
        detector.history.push(create_test_result(0.90, 100.0));
        detector.history.push(create_test_result(0.85, 100.0));
        detector.history.push(create_test_result(0.80, 100.0));
        detector.history.push(create_test_result(0.75, 100.0));

        let trend = detector.get_trend("accuracy", 4).unwrap();

        assert_eq!(trend.get("metric").unwrap(), &serde_json::json!("accuracy"));
        assert_eq!(trend.get("direction").unwrap(), &serde_json::json!("degrading"));
        assert!(trend.get("slope").unwrap().as_f64().unwrap() < 0.0);
    }
}
