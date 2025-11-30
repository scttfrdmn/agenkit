//! Regression Detection Example
//!
//! Regression detection compares current agent performance to a baseline,
//! alerting when quality degrades beyond acceptable thresholds.
//!
//! Run with: cargo run --example evaluation-regression-detection

use agenkit::evaluation::{EvaluationResult, RegressionDetector, Severity};
use chrono::Utc;

fn create_evaluation_result(id: &str, accuracy: f64, quality: f64, latency: f64) -> EvaluationResult {
    EvaluationResult {
        evaluation_id: id.to_string(),
        agent_name: "production-agent".to_string(),
        timestamp: Utc::now(),
        total_tests: 100,
        passed_tests: (accuracy * 100.0) as usize,
        failed_tests: ((1.0 - accuracy) * 100.0) as usize,
        accuracy: Some(accuracy),
        quality_score: Some(quality),
        avg_latency_ms: Some(latency),
        context_length: None,
        compression_ratio: None,
        per_test_metrics: vec![],
        aggregated_metrics: std::collections::HashMap::new(),
    }
}

fn main() {
    println!("Regression Detection Example");
    println!("============================\n");

    // Step 1: Establish baseline
    println!("Step 1: Establishing Baseline Performance");
    println!("------------------------------------------");
    let baseline = create_evaluation_result("baseline-001", 0.95, 0.92, 150.0);

    println!("Baseline Metrics:");
    println!("  Accuracy: {:.1}%", baseline.accuracy.unwrap_or(0.0) * 100.0);
    println!("  Quality: {:.3}", baseline.quality_score.unwrap_or(0.0));
    println!("  Latency: {:.0}ms\n", baseline.avg_latency_ms.unwrap_or(0.0));

    // Step 2: Create detector
    println!("Step 2: Creating Regression Detector");
    println!("-------------------------------------");
    let mut detector = RegressionDetector::new(None, Some(baseline));

    println!("✓ Detector created with default thresholds:");
    println!("  Accuracy: 10% degradation");
    println!("  Quality: 10% degradation");
    println!("  Latency: 20% increase\n");

    // Step 3: Simulate good performance (no regression)
    println!("Step 3: Testing Good Performance (No Regression)");
    println!("------------------------------------------------");
    let good_result = create_evaluation_result("eval-002", 0.94, 0.91, 155.0);
    let regressions = detector.detect(&good_result, true);

    println!("Current Performance:");
    println!("  Accuracy: {:.1}%", good_result.accuracy.unwrap_or(0.0) * 100.0);
    println!("  Quality: {:.3}", good_result.quality_score.unwrap_or(0.0));
    println!("  Latency: {:.0}ms", good_result.avg_latency_ms.unwrap_or(0.0));
    println!("\nRegressions Detected: {}", regressions.len());
    if regressions.is_empty() {
        println!("✓ Performance within acceptable range\n");
    }

    // Step 4: Simulate moderate regression
    println!("Step 4: Testing Moderate Degradation");
    println!("-------------------------------------");
    let moderate_result = create_evaluation_result("eval-003", 0.83, 0.81, 190.0);
    let regressions = detector.detect(&moderate_result, true);

    println!("Current Performance:");
    println!("  Accuracy: {:.1}%", moderate_result.accuracy.unwrap_or(0.0) * 100.0);
    println!("  Quality: {:.3}", moderate_result.quality_score.unwrap_or(0.0));
    println!("  Latency: {:.0}ms", moderate_result.avg_latency_ms.unwrap_or(0.0));
    println!("\n⚠ Regressions Detected: {}\n", regressions.len());

    for reg in &regressions {
        println!("Regression: {}", reg.metric_name);
        println!("  Baseline: {:.3}", reg.baseline_value);
        println!("  Current: {:.3}", reg.current_value);
        println!("  Degradation: {:.1}%", reg.degradation_percent);
        println!("  Severity: {}\n", reg.severity);
    }

    // Step 5: Simulate critical regression
    println!("Step 5: Testing Critical Degradation");
    println!("-------------------------------------");
    let critical_result = create_evaluation_result("eval-004", 0.45, 0.42, 350.0);
    let regressions = detector.detect(&critical_result, true);

    println!("Current Performance:");
    println!("  Accuracy: {:.1}%", critical_result.accuracy.unwrap_or(0.0) * 100.0);
    println!("  Quality: {:.3}", critical_result.quality_score.unwrap_or(0.0));
    println!("  Latency: {:.0}ms", critical_result.avg_latency_ms.unwrap_or(0.0));
    println!("\n✗ CRITICAL Regressions Detected: {}\n", regressions.len());

    for reg in &regressions {
        println!("Regression: {}", reg.metric_name);
        println!("  Baseline: {:.3}", reg.baseline_value);
        println!("  Current: {:.3}", reg.current_value);
        println!("  Degradation: {:.1}%", reg.degradation_percent);
        println!("  Severity: {}\n", reg.severity);
    }

    // Step 6: Trend analysis
    println!("Step 6: Analyzing Performance Trends");
    println!("-------------------------------------");

    // Add more historical data
    for i in 0..10 {
        let accuracy = 0.95 - (i as f64) * 0.03; // Declining trend
        let quality = 0.92 - (i as f64) * 0.025;
        let latency = 150.0 + (i as f64) * 15.0;

        let result = create_evaluation_result(&format!("eval-{:03}", i + 5), accuracy, quality, latency);
        let _ = detector.detect(&result, true);
    }

    if let Some(trend) = detector.get_trend("accuracy", 10) {
        println!("Accuracy Trend (last 10 evaluations):");
        println!("  Direction: {}", trend.get("direction").and_then(|v| v.as_str()).unwrap_or("unknown"));
        println!("  Slope: {:.6}", trend.get("slope").and_then(|v| v.as_f64()).unwrap_or(0.0));
        println!("  Current: {:.3}", trend.get("current").and_then(|v| v.as_f64()).unwrap_or(0.0));
        println!("  Mean: {:.3}", trend.get("mean").and_then(|v| v.as_f64()).unwrap_or(0.0));
        println!("  Variance: {:.6}\n", trend.get("variance").and_then(|v| v.as_f64()).unwrap_or(0.0));

        if trend.get("direction").and_then(|v| v.as_str()) == Some("degrading") {
            println!("⚠ Warning: Accuracy is trending downward");
        }
    }

    // Summary
    println!("{}", "=".repeat(70));
    println!("Summary: Regression Detection");
    println!("{}", "=".repeat(70));

    println!("\nSeverity Levels:");
    println!("- None: <10% degradation (within normal variance)");
    println!("- Minor: 10-20% degradation (monitor closely)");
    println!("- Moderate: 20-50% degradation (investigate)");
    println!("- Critical: >50% degradation (immediate action)");

    println!("\nKey Capabilities:");
    println!("1. Baseline Comparison: Compare against known-good performance");
    println!("2. Threshold Detection: Alert when metrics cross thresholds");
    println!("3. Severity Classification: Categorize degradation severity");
    println!("4. Trend Analysis: Identify gradual degradation over time");
    println!("5. Multi-Metric: Track accuracy, quality, latency simultaneously");

    println!("\nConfigurable Thresholds:");
    println!("- Accuracy: Default 10% (can adjust per use case)");
    println!("- Quality: Default 10% (subjective metrics)");
    println!("- Latency: Default 20% (performance tolerance)");
    println!("- Custom: Add thresholds for domain metrics");

    println!("\nBest Practices:");
    println!("1. Establish baseline from production data");
    println!("2. Run regression checks in CI/CD pipeline");
    println!("3. Monitor trends to catch gradual degradation");
    println!("4. Set alerts for moderate+ severity regressions");
    println!("5. Store regression history for post-mortems");

    println!("\nReal-World Applications:");
    println!("- CI/CD Quality Gates: Block deploys on regression");
    println!("- Production Monitoring: Alert on live degradation");
    println!("- A/B Testing: Verify new version doesn't regress");
    println!("- Model Updates: Validate fine-tuned models");
    println!("- Infrastructure Changes: Detect performance impact");

    println!("\nIntegration Points:");
    println!("- GitHub Actions: Fail PR on regression");
    println!("- Slack/PagerDuty: Alert on critical regressions");
    println!("- Datadog/Grafana: Visualize trends over time");
    println!("- Rollback Automation: Auto-revert on critical regression");
}
