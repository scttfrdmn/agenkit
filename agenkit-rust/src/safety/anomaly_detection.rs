//! Anomaly detection for monitoring suspicious agent behavior.

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::collections::{HashMap, VecDeque};
use std::hash::{Hash, Hasher};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;

/// Security event types.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SecurityEvent {
    HighRequestRate,
    BurstDetected,
    RepeatedFailures,
    PermissionDeniedSpike,
    ValidationFailures,
    UnusualInputSize,
    UnusualOutputSize,
    UnusualProcessingTime,
    SuspiciousContentPattern,
    RepetitiveContent,
}

/// Anomaly detector configuration.
#[derive(Debug, Clone)]
pub struct AnomalyDetectorConfig {
    /// Maximum requests per minute
    pub max_requests_per_minute: usize,
    /// Maximum burst size (requests per second)
    pub max_burst_size: usize,
    /// Z-score threshold for size anomalies
    pub size_threshold: f64,
    /// Maximum processing time (seconds)
    pub max_processing_time: u64,
    /// Failure rate threshold (0.0-1.0)
    pub failure_rate_threshold: f64,
}

impl Default for AnomalyDetectorConfig {
    fn default() -> Self {
        Self {
            max_requests_per_minute: 60,
            max_burst_size: 10,
            size_threshold: 3.0, // 3 sigma
            max_processing_time: 30,
            failure_rate_threshold: 0.5, // 50%
        }
    }
}

/// User activity tracker.
#[derive(Debug)]
struct UserActivity {
    request_timestamps: VecDeque<Instant>,
    failure_count: usize,
    success_count: usize,
    input_sizes: VecDeque<usize>,
    output_sizes: VecDeque<usize>,
    processing_times: VecDeque<Duration>,
    recent_content_hashes: VecDeque<u64>,
}

impl UserActivity {
    fn new() -> Self {
        Self {
            request_timestamps: VecDeque::new(),
            failure_count: 0,
            success_count: 0,
            input_sizes: VecDeque::new(),
            output_sizes: VecDeque::new(),
            processing_times: VecDeque::new(),
            recent_content_hashes: VecDeque::new(),
        }
    }
}

/// Anomaly detector for monitoring agent behavior.
pub struct AnomalyDetector {
    config: AnomalyDetectorConfig,
    user_activity: Arc<Mutex<HashMap<String, UserActivity>>>,
}

impl AnomalyDetector {
    /// Create a new anomaly detector.
    pub fn new() -> Self {
        Self::with_config(AnomalyDetectorConfig::default())
    }

    /// Create with custom configuration.
    pub fn with_config(config: AnomalyDetectorConfig) -> Self {
        Self {
            config,
            user_activity: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Calculate simple hash of content.
    fn simple_hash(content: &str) -> u64 {
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        content.hash(&mut hasher);
        hasher.finish()
    }

    /// Calculate mean of values.
    fn mean(values: &VecDeque<usize>) -> f64 {
        if values.is_empty() {
            return 0.0;
        }
        values.iter().sum::<usize>() as f64 / values.len() as f64
    }

    /// Calculate standard deviation.
    fn stdev(values: &VecDeque<usize>) -> f64 {
        if values.len() < 2 {
            return 0.0;
        }
        let mean = Self::mean(values);
        let variance = values
            .iter()
            .map(|&x| {
                let diff = x as f64 - mean;
                diff * diff
            })
            .sum::<f64>()
            / (values.len() - 1) as f64;
        variance.sqrt()
    }

    /// Detect rate anomaly.
    pub async fn detect_rate_anomaly(&self, user_id: &str) -> Option<(SecurityEvent, String)> {
        let mut activities = self.user_activity.lock().await;
        let activity = activities
            .entry(user_id.to_string())
            .or_insert_with(UserActivity::new);

        let now = Instant::now();
        let one_minute_ago = now - Duration::from_secs(60);
        let one_second_ago = now - Duration::from_secs(1);

        // Clean old timestamps
        while let Some(timestamp) = activity.request_timestamps.front() {
            if *timestamp < one_minute_ago {
                activity.request_timestamps.pop_front();
            } else {
                break;
            }
        }

        // Keep only last 1000 timestamps
        if activity.request_timestamps.len() > 1000 {
            activity.request_timestamps.pop_front();
        }

        activity.request_timestamps.push_back(now);

        // Check requests per minute
        let requests_per_minute = activity.request_timestamps.len();
        if requests_per_minute > self.config.max_requests_per_minute {
            return Some((
                SecurityEvent::HighRequestRate,
                format!("High request rate: {} requests/min", requests_per_minute),
            ));
        }

        // Check burst (requests in last second)
        let recent_count = activity
            .request_timestamps
            .iter()
            .filter(|t| **t > one_second_ago)
            .count();

        if recent_count > self.config.max_burst_size {
            return Some((
                SecurityEvent::BurstDetected,
                format!("Burst detected: {} requests/sec", recent_count),
            ));
        }

        None
    }

    /// Detect failure anomaly.
    pub async fn detect_failure_anomaly(
        &self,
        user_id: &str,
        is_success: bool,
    ) -> Option<(SecurityEvent, String)> {
        let mut activities = self.user_activity.lock().await;
        let activity = activities
            .entry(user_id.to_string())
            .or_insert_with(UserActivity::new);

        if is_success {
            activity.success_count += 1;
        } else {
            activity.failure_count += 1;
        }

        let total = activity.success_count + activity.failure_count;
        if total >= 10 {
            let failure_rate = activity.failure_count as f64 / total as f64;
            if failure_rate > self.config.failure_rate_threshold {
                return Some((
                    SecurityEvent::RepeatedFailures,
                    format!("High failure rate: {:.1}%", failure_rate * 100.0),
                ));
            }
        }

        None
    }

    /// Detect size anomaly using z-score.
    pub async fn detect_size_anomaly(
        &self,
        user_id: &str,
        input_size: usize,
        output_size: usize,
    ) -> Option<(SecurityEvent, String)> {
        let mut activities = self.user_activity.lock().await;
        let activity = activities
            .entry(user_id.to_string())
            .or_insert_with(UserActivity::new);

        activity.input_sizes.push_back(input_size);
        activity.output_sizes.push_back(output_size);

        // Keep only last 100
        if activity.input_sizes.len() > 100 {
            activity.input_sizes.pop_front();
        }
        if activity.output_sizes.len() > 100 {
            activity.output_sizes.pop_front();
        }

        // Need at least 10 samples for meaningful statistics
        if activity.input_sizes.len() < 10 {
            return None;
        }

        // Check input size
        let input_mean = Self::mean(&activity.input_sizes);
        let input_stdev = Self::stdev(&activity.input_sizes);
        if input_stdev > 0.0 {
            let z_score = (input_size as f64 - input_mean).abs() / input_stdev;
            if z_score > self.config.size_threshold {
                return Some((
                    SecurityEvent::UnusualInputSize,
                    format!(
                        "Unusual input size: {} bytes (z-score: {:.2})",
                        input_size, z_score
                    ),
                ));
            }
        }

        // Check output size
        let output_mean = Self::mean(&activity.output_sizes);
        let output_stdev = Self::stdev(&activity.output_sizes);
        if output_stdev > 0.0 {
            let z_score = (output_size as f64 - output_mean).abs() / output_stdev;
            if z_score > self.config.size_threshold {
                return Some((
                    SecurityEvent::UnusualOutputSize,
                    format!(
                        "Unusual output size: {} bytes (z-score: {:.2})",
                        output_size, z_score
                    ),
                ));
            }
        }

        None
    }

    /// Detect content anomaly (repetitive content).
    pub async fn detect_content_anomaly(
        &self,
        user_id: &str,
        content: &str,
    ) -> Option<(SecurityEvent, String)> {
        let mut activities = self.user_activity.lock().await;
        let activity = activities
            .entry(user_id.to_string())
            .or_insert_with(UserActivity::new);

        let hash = Self::simple_hash(content);
        activity.recent_content_hashes.push_back(hash);

        // Keep only last 10
        if activity.recent_content_hashes.len() > 10 {
            activity.recent_content_hashes.pop_front();
        }

        // Check for repetition (same content 5 times in a row)
        if activity.recent_content_hashes.len() >= 5 {
            let last_5: Vec<_> = activity
                .recent_content_hashes
                .iter()
                .rev()
                .take(5)
                .collect();
            if last_5.iter().all(|&h| *h == hash) {
                return Some((
                    SecurityEvent::RepetitiveContent,
                    "Repetitive content detected (same message 5 times)".to_string(),
                ));
            }
        }

        None
    }

    /// Record processing time.
    pub async fn record_processing_time(
        &self,
        user_id: &str,
        duration: Duration,
    ) -> Option<(SecurityEvent, String)> {
        let mut activities = self.user_activity.lock().await;
        let activity = activities
            .entry(user_id.to_string())
            .or_insert_with(UserActivity::new);

        activity.processing_times.push_back(duration);

        // Keep only last 100
        if activity.processing_times.len() > 100 {
            activity.processing_times.pop_front();
        }

        // Check if processing time exceeds threshold
        if duration.as_secs() > self.config.max_processing_time {
            return Some((
                SecurityEvent::UnusualProcessingTime,
                format!("Unusual processing time: {}s", duration.as_secs()),
            ));
        }

        None
    }
}

impl Default for AnomalyDetector {
    fn default() -> Self {
        Self::new()
    }
}

/// Anomaly detection middleware.
pub struct AnomalyDetectionMiddleware<A: Agent> {
    inner: A,
    detector: Arc<AnomalyDetector>,
    user_id: String,
}

impl<A: Agent> AnomalyDetectionMiddleware<A> {
    /// Create a new anomaly detection middleware.
    pub fn new(agent: A, user_id: String) -> Self {
        Self {
            inner: agent,
            detector: Arc::new(AnomalyDetector::new()),
            user_id,
        }
    }

    /// Create with custom detector.
    pub fn with_detector(agent: A, user_id: String, detector: Arc<AnomalyDetector>) -> Self {
        Self {
            inner: agent,
            detector,
            user_id,
        }
    }
}

#[async_trait]
impl<A: Agent> Agent for AnomalyDetectionMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    fn capabilities(&self) -> Vec<String> {
        self.inner.capabilities()
    }

    fn introspect(&self) -> IntrospectionResult {
        let mut result = self.inner.introspect();
        result.metadata.insert(
            "middleware".to_string(),
            serde_json::json!("anomaly_detection"),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let input_content = message.content_as_str().unwrap_or("");
        let input_size = input_content.len();

        // Check rate anomaly
        if let Some((event, details)) = self.detector.detect_rate_anomaly(&self.user_id).await {
            eprintln!("Anomaly detected: {:?} - {}", event, details);
        }

        // Check content anomaly
        if let Some((event, details)) = self
            .detector
            .detect_content_anomaly(&self.user_id, input_content)
            .await
        {
            eprintln!("Anomaly detected: {:?} - {}", event, details);
        }

        // Process message
        let start = Instant::now();
        let result = self.inner.process(message).await;
        let duration = start.elapsed();

        // Record processing time
        if let Some((event, details)) = self
            .detector
            .record_processing_time(&self.user_id, duration)
            .await
        {
            eprintln!("Anomaly detected: {:?} - {}", event, details);
        }

        // Check failure anomaly
        let is_success = result.is_ok();
        if let Some((event, details)) = self
            .detector
            .detect_failure_anomaly(&self.user_id, is_success)
            .await
        {
            eprintln!("Anomaly detected: {:?} - {}", event, details);
        }

        // Check size anomaly
        if let Ok(ref response) = result {
            let output_size = response.content_as_str().unwrap_or("").len();
            if let Some((event, details)) = self
                .detector
                .detect_size_anomaly(&self.user_id, input_size, output_size)
                .await
            {
                eprintln!("Anomaly detected: {:?} - {}", event, details);
            }
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_rate_anomaly_detection() {
        let detector = AnomalyDetector::new();
        let user_id = "test_user";

        // Simulate high request rate
        for _ in 0..70 {
            let _ = detector.detect_rate_anomaly(user_id).await;
        }

        let result = detector.detect_rate_anomaly(user_id).await;
        assert!(result.is_some());

        if let Some((event, _)) = result {
            assert_eq!(event, SecurityEvent::HighRequestRate);
        }
    }

    #[tokio::test]
    async fn test_failure_anomaly_detection() {
        let detector = AnomalyDetector::new();
        let user_id = "test_user";

        // Simulate high failure rate
        for _ in 0..8 {
            let _ = detector.detect_failure_anomaly(user_id, false).await;
        }
        for _ in 0..2 {
            let _ = detector.detect_failure_anomaly(user_id, true).await;
        }

        let result = detector.detect_failure_anomaly(user_id, false).await;
        assert!(result.is_some());

        if let Some((event, _)) = result {
            assert_eq!(event, SecurityEvent::RepeatedFailures);
        }
    }

    #[tokio::test]
    async fn test_content_repetition_detection() {
        let detector = AnomalyDetector::new();
        let user_id = "test_user";
        let content = "Same message";

        // Send same content 5 times
        for _ in 0..5 {
            let _ = detector.detect_content_anomaly(user_id, content).await;
        }

        let result = detector.detect_content_anomaly(user_id, content).await;
        assert!(result.is_some());

        if let Some((event, _)) = result {
            assert_eq!(event, SecurityEvent::RepetitiveContent);
        }
    }
}
