//! Production Monitoring Example
//!
//! Shows how to integrate evaluation framework into production systems
//! for continuous monitoring of agent performance.
//!
//! Run with: cargo run --example evaluation-production-monitoring

use agenkit::core::{Agent, AgentError, Message};
use agenkit::evaluation::recorder::{FileRecordingStorage, SessionRecorder};
use agenkit::evaluation::{
    EvaluationResult, MetricsCollector, RegressionDetector, SessionResult, SessionStatus,
};
use async_trait::async_trait;
use chrono::Utc;
use rand::RngExt;
use std::collections::HashMap;
use std::time::Duration;
use tokio::time::sleep;

/// ProductionAgent simulates a production agent
struct ProductionAgent;

#[async_trait]
impl Agent for ProductionAgent {
    fn name(&self) -> &str {
        "production-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate processing. Scope the (non-Send) RNG so it is dropped
        // before the await point — the Agent future must be Send.
        let jitter = {
            let mut rng = rand::rng();
            rng.random_range(0..200)
        };
        sleep(Duration::from_millis(50 + jitter)).await;

        let content = message.content_as_str().unwrap_or("");
        Ok(Message::with_text(
            "assistant",
            format!("Response to: {}", content),
        ))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Production Monitoring Example");
    println!("=============================\n");

    // Step 1: Initialize monitoring infrastructure
    println!("Step 1: Initializing Monitoring Infrastructure");
    println!("-----------------------------------------------");

    // Create metrics collector (aggregates results across sessions)
    let mut collector = MetricsCollector::new();

    // Create session recorder with file storage
    let recorder = SessionRecorder::new(Some(Box::new(FileRecordingStorage::new(
        "./production_recordings",
    ))));

    // Create regression detector with baseline
    let baseline = EvaluationResult {
        evaluation_id: "baseline".to_string(),
        agent_name: "production-agent".to_string(),
        timestamp: Utc::now(),
        metrics: HashMap::new(),
        aggregated_metrics: HashMap::new(),
        context_length: None,
        compressed_length: None,
        compression_ratio: None,
        accuracy: Some(0.95),
        quality_score: Some(0.90),
        avg_latency_ms: Some(150.0),
        p95_latency_ms: None,
        total_tests: 0,
        passed_tests: 0,
        failed_tests: 0,
        metadata: HashMap::new(),
    };

    let mut detector = RegressionDetector::new(None, Some(baseline));

    println!("✓ MetricsCollector initialized (thread-safe)");
    println!("✓ SessionRecorder configured with file storage");
    println!("✓ RegressionDetector configured with baseline\n");

    // Step 2: Wrap agent for automatic monitoring
    println!("Step 2: Wrapping Agent for Monitoring");
    println!("--------------------------------------");
    let agent = std::sync::Arc::new(ProductionAgent);
    let monitored_agent = recorder.wrap(agent.clone());

    println!("✓ Agent wrapped - all interactions will be recorded\n");

    // Step 3: Simulate production traffic
    println!("Step 3: Simulating Production Traffic");
    println!("--------------------------------------");
    println!("Processing 50 user requests...\n");

    let mut rng = rand::rng();

    for i in 0..50 {
        let session_id = format!("prod-session-{:03}", i + 1);

        // Create session result
        let mut result = SessionResult::new(&session_id, agent.name());

        // Process message
        let message = Message::with_text("user", format!("User query {}", i + 1))
            .with_metadata("session_id", serde_json::json!(session_id));

        let start = std::time::Instant::now();
        let process_result = monitored_agent.process(message).await;
        let duration = start.elapsed().as_secs_f64();

        // Record metrics
        match process_result {
            Err(e) => {
                result.set_status(SessionStatus::Failed);
                result.add_error(agenkit::evaluation::ErrorRecord::new(
                    "processing_error",
                    format!("{:?}", e),
                ));
            }
            Ok(_) => {
                result.set_status(SessionStatus::Completed);

                // Add quality metric
                let quality_score = 0.85 + rng.random::<f64>() * 0.15;
                let mut quality_metadata = HashMap::new();
                quality_metadata.insert(
                    "raw_score".to_string(),
                    serde_json::json!(quality_score * 10.0),
                );
                quality_metadata.insert("max_score".to_string(), serde_json::json!(10.0));

                let mut quality_measurement = agenkit::evaluation::MetricMeasurement::new(
                    "response_quality",
                    quality_score,
                    agenkit::evaluation::MetricType::QualityScore,
                );
                quality_measurement.metadata = quality_metadata;
                result.add_metric_measurement(quality_measurement);

                // Add duration metric
                let mut duration_metadata = HashMap::new();
                duration_metadata.insert(
                    "duration_hours".to_string(),
                    serde_json::json!(duration / 3600.0),
                );

                let mut duration_measurement = agenkit::evaluation::MetricMeasurement::new(
                    "duration",
                    duration,
                    agenkit::evaluation::MetricType::Duration,
                );
                duration_measurement.metadata = duration_metadata;
                result.add_metric_measurement(duration_measurement);

                // Add cost metric (simulate token usage)
                let tokens = 100 + rng.random_range(0..300);
                let cost = tokens as f64 * 0.00001;
                let mut cost_metadata = HashMap::new();
                cost_metadata.insert("currency".to_string(), serde_json::json!("USD"));
                cost_metadata.insert("tokens".to_string(), serde_json::json!(tokens));

                let mut cost_measurement = agenkit::evaluation::MetricMeasurement::new(
                    "total_cost",
                    cost,
                    agenkit::evaluation::MetricType::Cost,
                );
                cost_measurement.metadata = cost_metadata;
                result.add_metric_measurement(cost_measurement);
            }
        }

        collector.add_session(result);

        // Print progress every 10 requests
        if (i + 1) % 10 == 0 {
            println!("  Processed {} requests", i + 1);
        }
    }

    println!("\n✓ Processing complete\n");

    // Step 4: Real-time statistics
    println!("Step 4: Real-time Performance Statistics");
    println!("-----------------------------------------");

    let total_sessions = collector.sessions.len();
    let completed = collector
        .sessions
        .iter()
        .filter(|s| s.is_successful())
        .count();
    let failed = total_sessions - completed;
    let success_rate = collector.overall_success_rate();
    let avg_duration = {
        let durations: Vec<f64> = collector
            .sessions
            .iter()
            .filter_map(|s| s.duration_secs())
            .collect();
        if durations.is_empty() {
            0.0
        } else {
            durations.iter().sum::<f64>() / durations.len() as f64
        }
    };

    println!("Session Statistics:");
    println!("  Total Sessions: {}", total_sessions);
    println!("  Completed: {}", completed);
    println!("  Failed: {}", failed);
    println!("  Success Rate: {:.1}%", success_rate * 100.0);
    println!("  Avg Duration: {:.3}s", avg_duration);
    println!("  Total Errors: {}\n", collector.total_errors());

    // Quality metrics (aggregate_by_name returns mean/min/max/sum/std/count)
    let quality_stats = collector.aggregate_by_name("response_quality");
    println!("Quality Metrics:");
    println!(
        "  Mean: {:.3}",
        quality_stats.get("mean").copied().unwrap_or(0.0)
    );
    println!(
        "  Min: {:.3}",
        quality_stats.get("min").copied().unwrap_or(0.0)
    );
    println!(
        "  Max: {:.3}\n",
        quality_stats.get("max").copied().unwrap_or(0.0)
    );

    // Cost metrics
    let cost_stats = collector.aggregate_by_name("total_cost");
    println!("Cost Metrics:");
    println!(
        "  Total: ${:.4}",
        cost_stats.get("sum").copied().unwrap_or(0.0)
    );
    println!(
        "  Average: ${:.4}\n",
        cost_stats.get("mean").copied().unwrap_or(0.0)
    );

    // Step 5: Regression detection
    println!("Step 5: Checking for Regressions");
    println!("---------------------------------");

    let current_eval = EvaluationResult {
        evaluation_id: "current".to_string(),
        agent_name: "production-agent".to_string(),
        timestamp: Utc::now(),
        metrics: HashMap::new(),
        aggregated_metrics: HashMap::new(),
        context_length: None,
        compressed_length: None,
        compression_ratio: None,
        accuracy: Some(success_rate),
        quality_score: Some(quality_stats.get("mean").copied().unwrap_or(0.0)),
        avg_latency_ms: Some(avg_duration * 1000.0),
        p95_latency_ms: None,
        total_tests: 50,
        passed_tests: completed,
        failed_tests: failed,
        metadata: HashMap::new(),
    };

    let regressions = detector.detect(&current_eval, false);

    if regressions.is_empty() {
        println!("✓ No regressions detected - performance nominal\n");
    } else {
        println!("⚠ Regressions detected: {}\n", regressions.len());
        for reg in regressions {
            println!(
                "  {}: {:.1}% degradation ({})",
                reg.metric_name, reg.degradation_percent, reg.severity
            );
        }
        println!();
    }

    // Summary
    println!("{}", "=".repeat(70));
    println!("Summary: Production Monitoring");
    println!("{}", "=".repeat(70));

    println!("\nMonitoring Stack:");
    println!("1. MetricsCollector: Aggregate real-time statistics");
    println!("2. SessionRecorder: Record all interactions for debugging");
    println!("3. RegressionDetector: Alert on performance degradation");

    println!("\nKey Metrics Tracked:");
    println!("- Success Rate: % of successful completions");
    println!("- Quality Score: Response quality (0.0-1.0)");
    println!("- Latency: Response time (ms)");
    println!("- Cost: API/token costs ($)");
    println!("- Error Rate: Frequency and types of errors");

    println!("\nReal-World Integration:");
    println!("- Prometheus/Grafana: Export metrics for dashboards");
    println!("- Datadog/New Relic: APM integration");
    println!("- PagerDuty/Slack: Alert on regressions");
    println!("- S3/CloudWatch: Long-term storage");
    println!("- Kubernetes: Health checks and auto-scaling");

    println!("\nBest Practices:");
    println!("1. Set up alerts for critical regressions");
    println!("2. Monitor trends, not just point-in-time metrics");
    println!("3. Record failed sessions for debugging");
    println!("4. Track costs to avoid budget overruns");
    println!("5. Use percentiles (p50, p95, p99) for latency");
    println!("6. Segment metrics by user cohorts");

    println!("\nPerformance Characteristics:");
    println!("- Recording overhead: <1ms per request");
    println!("- Memory: ~1KB per session result");
    println!("- Thread-safe: Concurrent access supported");
    println!("- Storage: JSON files rotated daily");

    Ok(())
}
