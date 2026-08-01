//! Basic Metrics Collection Example
//!
//! This example demonstrates how to use the evaluation framework to:
//!   - Create SessionResult instances to track agent sessions
//!   - Add metric measurements (quality, cost, duration)
//!   - Collect multiple session results
//!   - Compute aggregate statistics across sessions
//!
//! This is the foundation for monitoring agent performance over time,
//! tracking success rates, detecting issues, and measuring improvements.
//!
//! Run with: cargo run --example evaluation-basic-metrics

use agenkit::evaluation::{
    ErrorRecord, MetricMeasurement, MetricType, MetricsCollector, SessionResult, SessionStatus,
};
use rand::RngExt;
use std::collections::HashMap;
use std::thread;
use std::time::Duration;

/// Simulates running an agent session and collecting metrics.
fn simulate_agent_session(session_id: &str, agent_name: &str) -> SessionResult {
    let mut rng = rand::rng();
    let mut result = SessionResult::new(session_id, agent_name);

    // Simulate some processing time
    thread::sleep(Duration::from_millis(10 + rng.random_range(0..50)));

    // Add quality metrics
    let quality_score = 0.7 + rng.random::<f64>() * 0.3; // 0.7-1.0
    let mut metadata = HashMap::new();
    metadata.insert("evaluator".to_string(), serde_json::json!("rule_based"));
    metadata.insert(
        "raw_score".to_string(),
        serde_json::json!(quality_score * 10.0),
    );
    metadata.insert("max_score".to_string(), serde_json::json!(10.0));

    let mut quality_metric =
        MetricMeasurement::new("response_quality", quality_score, MetricType::QualityScore);
    quality_metric.metadata = metadata;
    result.add_metric_measurement(quality_metric);

    // Add cost metrics
    let tokens_used = 100 + rng.random_range(0..400);
    let cost_per_token = 0.00001;
    let total_cost = tokens_used as f64 * cost_per_token;
    let mut cost_metadata = HashMap::new();
    cost_metadata.insert("currency".to_string(), serde_json::json!("USD"));
    cost_metadata.insert("tokens".to_string(), serde_json::json!(tokens_used));

    let mut cost_metric = MetricMeasurement::new("total_cost", total_cost, MetricType::Cost);
    cost_metric.metadata = cost_metadata;
    result.add_metric_measurement(cost_metric);

    // Add duration metrics
    let duration_seconds = 0.5 + rng.random::<f64>() * 2.0; // 0.5-2.5 seconds
    let mut duration_metadata = HashMap::new();
    duration_metadata.insert(
        "duration_hours".to_string(),
        serde_json::json!(duration_seconds / 3600.0),
    );

    let mut duration_metric =
        MetricMeasurement::new("duration", duration_seconds, MetricType::Duration);
    duration_metric.metadata = duration_metadata;
    result.add_metric_measurement(duration_metric);

    // Add custom success rate metric
    let success = rng.random::<f64>() > 0.2; // 80% success rate
    let success_value = if success { 1.0 } else { 0.0 };

    if success {
        result.set_status(SessionStatus::Completed);
    } else {
        result.set_status(SessionStatus::Failed);
        let mut details = HashMap::new();
        details.insert("reason".to_string(), serde_json::json!("timeout"));
        result.add_error(ErrorRecord::with_details(
            "processing_error",
            "Failed to complete task",
            details,
        ));
    }

    result.add_metric_measurement(MetricMeasurement::new(
        "success",
        success_value,
        MetricType::SuccessRate,
    ));

    result
}

fn main() {
    println!("Basic Metrics Collection Example");
    println!("=================================\n");

    // Step 1: Create metrics collector
    println!("Step 1: Creating Metrics Collector");
    println!("-----------------------------------");
    let mut collector = MetricsCollector::new();
    println!("✓ Metrics collector created\n");

    // Step 2: Simulate multiple agent sessions
    println!("Step 2: Simulating Agent Sessions");
    println!("----------------------------------");
    let num_sessions = 20;
    println!("Running {} simulated agent sessions...\n", num_sessions);

    for i in 0..num_sessions {
        let session_id = format!("session-{:03}", i + 1);
        let agent_name = "example-agent";

        let result = simulate_agent_session(&session_id, agent_name);

        // Print progress
        let status = if result.status == SessionStatus::Completed {
            "✓"
        } else {
            "✗"
        };
        println!("  {} Session {}: {}", status, i + 1, result.status);

        collector.add_session(result);
    }
    println!();

    // Step 3: Compute aggregate statistics
    println!("Step 3: Computing Aggregate Statistics");
    println!("---------------------------------------");

    let total_sessions = collector.sessions.len();
    let completed_count = collector
        .sessions
        .iter()
        .filter(|s| s.status == SessionStatus::Completed)
        .count();
    let failed_count = collector
        .sessions
        .iter()
        .filter(|s| s.status == SessionStatus::Failed)
        .count();
    let success_rate = collector.overall_success_rate();
    let total_errors = collector.total_errors();

    println!("Total Sessions: {}", total_sessions);
    println!("Completed: {}", completed_count);
    println!("Failed: {}", failed_count);
    println!("Success Rate: {:.1}%", success_rate * 100.0);
    println!("Total Errors: {}", total_errors);
    println!(
        "Avg Errors/Session: {:.2}\n",
        total_errors as f64 / total_sessions as f64
    );

    // Step 4: Analyze specific metrics
    println!("Step 4: Analyzing Specific Metrics");
    println!("-----------------------------------");

    // Quality metrics
    let quality_stats = collector.aggregate_by_name("response_quality");
    if quality_stats.get("count").copied().unwrap_or(0.0) > 0.0 {
        println!("\nQuality Metrics:");
        println!(
            "  Count: {:.0}",
            quality_stats.get("count").copied().unwrap_or(0.0)
        );
        println!(
            "  Mean: {:.3}",
            quality_stats.get("mean").copied().unwrap_or(0.0)
        );
        println!(
            "  Min: {:.3}",
            quality_stats.get("min").copied().unwrap_or(0.0)
        );
        println!(
            "  Max: {:.3}",
            quality_stats.get("max").copied().unwrap_or(0.0)
        );
    }

    // Cost metrics
    let cost_stats = collector.aggregate_by_name("total_cost");
    if cost_stats.get("count").copied().unwrap_or(0.0) > 0.0 {
        println!("\nCost Metrics:");
        println!(
            "  Count: {:.0}",
            cost_stats.get("count").copied().unwrap_or(0.0)
        );
        println!(
            "  Total Cost: ${:.4}",
            cost_stats.get("sum").copied().unwrap_or(0.0)
        );
        println!(
            "  Average Cost/Session: ${:.4}",
            cost_stats.get("mean").copied().unwrap_or(0.0)
        );
        println!(
            "  Min Cost: ${:.4}",
            cost_stats.get("min").copied().unwrap_or(0.0)
        );
        println!(
            "  Max Cost: ${:.4}",
            cost_stats.get("max").copied().unwrap_or(0.0)
        );
    }

    // Duration metrics
    let duration_stats = collector.aggregate_by_name("duration");
    if duration_stats.get("count").copied().unwrap_or(0.0) > 0.0 {
        println!("\nDuration Metrics:");
        println!(
            "  Count: {:.0}",
            duration_stats.get("count").copied().unwrap_or(0.0)
        );
        println!(
            "  Total Duration: {:.2}s",
            duration_stats.get("sum").copied().unwrap_or(0.0)
        );
        println!(
            "  Average Duration: {:.2}s",
            duration_stats.get("mean").copied().unwrap_or(0.0)
        );
        println!(
            "  Min Duration: {:.2}s",
            duration_stats.get("min").copied().unwrap_or(0.0)
        );
        println!(
            "  Max Duration: {:.2}s",
            duration_stats.get("max").copied().unwrap_or(0.0)
        );
    }

    // Success rate metrics
    let success_stats = collector.aggregate_by_name("success");
    if success_stats.get("count").copied().unwrap_or(0.0) > 0.0 {
        println!("\nSuccess Rate Metrics:");
        println!(
            "  Count: {:.0}",
            success_stats.get("count").copied().unwrap_or(0.0)
        );
        println!(
            "  Success Rate: {:.1}%",
            success_stats.get("mean").copied().unwrap_or(0.0) * 100.0
        );
    }

    // Step 5: Examine individual session results
    println!("\n\nStep 5: Examining Individual Sessions");
    println!("--------------------------------------");

    println!("\nTop 3 Highest Quality Sessions:");
    println!("{}", "-".repeat(70));

    // Sort by quality
    let mut sessions_with_quality: Vec<_> = collector
        .sessions
        .iter()
        .filter_map(|result| {
            result
                .get_measurements_by_name("response_quality")
                .first()
                .map(|metric| (result, metric.value))
        })
        .collect();

    sessions_with_quality.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

    for (i, (result, quality)) in sessions_with_quality.iter().take(3).enumerate() {
        println!("{}. Session: {}", i + 1, result.session_id);
        println!("   Quality: {:.3}", quality);
        if let Some(cost_metric) = result.get_measurements_by_name("total_cost").first() {
            println!("   Cost: ${:.4}", cost_metric.value);
        }
        if let Some(duration_metric) = result.get_measurements_by_name("duration").first() {
            println!("   Duration: {:.2}s", duration_metric.value);
        }
        println!("   Status: {}\n", result.status);
    }

    // Step 6: Summary and best practices
    println!("{}", "=".repeat(70));
    println!("Summary: Basic Metrics Collection");
    println!("{}", "=".repeat(70));

    println!("\nKey Capabilities:");
    println!("1. SessionResult: Track individual agent session metrics");
    println!("2. MetricsCollector: Aggregate metrics across multiple sessions");
    println!("3. Metric Types: Quality, cost, duration, success rate, custom");
    println!("4. Statistics: Success rate, averages, min/max, error rates");

    println!("\nMetric Types Available:");
    println!("- MetricType::SuccessRate: Binary success/failure tracking");
    println!("- MetricType::QualityScore: Normalized quality scores (0.0-1.0)");
    println!("- MetricType::Cost: Token costs and API expenses");
    println!("- MetricType::Duration: Execution time tracking");
    println!("- MetricType::ErrorRate: Error frequency analysis");
    println!("- MetricType::TaskCompletion: Task completion tracking");
    println!("- MetricType::Custom: Domain-specific metrics");

    println!("\nThread Safety:");
    println!("MetricsCollector is thread-safe and can be used concurrently");
    println!("from multiple threads without additional synchronization.");

    println!("\nBest Practices:");
    println!("1. Create one SessionResult per agent invocation");
    println!("2. Add measurements as they occur (streaming metrics)");
    println!("3. Set final status (completed/failed) when session ends");
    println!("4. Use helper functions for common metric types");
    println!("5. Collect across many sessions for statistical significance");
    println!("6. Export to JSON for long-term storage and analysis");

    println!("\nReal-World Applications:");
    println!("- Monitor agent success rates over time");
    println!("- Track API costs and token usage");
    println!("- Identify slow or expensive sessions");
    println!("- Detect quality degradation");
    println!("- A/B test different agent configurations");
    println!("- Generate performance reports and dashboards");
}
