//! Statistical A/B Testing Example
//!
//! This example demonstrates rigorous statistical A/B testing for comparing
//! two agent versions. It shows:
//!   - T-test for parametric testing
//!   - Mann-Whitney for non-parametric testing
//!   - Bootstrap resampling for confidence intervals
//!   - Effect size calculation (Cohen's d)
//!   - Sample size planning
//!   - Winner determination with statistical significance
//!
//! Run with: cargo run --example evaluation-ab-testing-statistical

use agenkit::core::{Agent, AgentError, Message};
use agenkit::evaluation::ab_testing::{ABTest, SignificanceLevel, StatisticalTestType, TestCase};
use async_trait::async_trait;
use rand::Rng;
use std::sync::Arc;

/// Control agent (baseline version)
/// Returns simple, factual responses
struct ControlAgent {
    accuracy: f64, // Base accuracy rate
}

impl ControlAgent {
    fn new(accuracy: f64) -> Self {
        Self { accuracy }
    }
}

#[async_trait]
impl Agent for ControlAgent {
    fn name(&self) -> &str {
        "control-agent-v1"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate accuracy with randomness
        let mut rng = rand::thread_rng();
        let score: f64 = rng.gen_range(0.0..1.0);

        let content = message.content_as_str().unwrap_or("");

        if score < self.accuracy {
            // Correct response
            Ok(Message::with_text(
                "assistant",
                format!("Correct answer for: {}", content),
            ))
        } else {
            // Incorrect response
            Ok(Message::with_text("assistant", "Incorrect answer"))
        }
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["qa".to_string()]
    }
}

/// Treatment agent (improved version)
/// Returns enhanced responses with better accuracy
struct TreatmentAgent {
    accuracy: f64, // Improved accuracy rate
}

impl TreatmentAgent {
    fn new(accuracy: f64) -> Self {
        Self { accuracy }
    }
}

#[async_trait]
impl Agent for TreatmentAgent {
    fn name(&self) -> &str {
        "treatment-agent-v2"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate improved accuracy
        let mut rng = rand::thread_rng();
        let score: f64 = rng.gen_range(0.0..1.0);

        let content = message.content_as_str().unwrap_or("");

        if score < self.accuracy {
            // Correct response with more detail
            Ok(Message::with_text(
                "assistant",
                format!("Detailed correct answer for: {}", content),
            ))
        } else {
            // Incorrect response
            Ok(Message::with_text("assistant", "Incorrect answer"))
        }
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["qa".to_string(), "detailed".to_string()]
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n{}", "=".repeat(70));
    println!("Statistical A/B Testing Example");
    println!("{}", "=".repeat(70));

    // ========================================================================
    // Step 1: Sample Size Calculation
    // ========================================================================
    println!("\nStep 1: Sample Size Planning");
    println!("{}", "-".repeat(70));

    let baseline_accuracy = 0.70; // Control agent: 70% accuracy
    let min_detectable_effect = 0.10; // Want to detect 10% improvement
    let alpha = 0.05; // 95% confidence
    let power = 0.80; // 80% power
    let std_dev = 0.15; // Estimated standard deviation

    let required_samples = ABTest::calculate_sample_size(
        baseline_accuracy,
        min_detectable_effect,
        alpha,
        power,
        std_dev,
    );

    println!("📊 Sample Size Calculation:");
    println!("   Baseline Accuracy: {:.1}%", baseline_accuracy * 100.0);
    println!(
        "   Minimum Detectable Effect: {:.1}%",
        min_detectable_effect * 100.0
    );
    println!("   Confidence Level: {:.0}%", (1.0 - alpha) * 100.0);
    println!("   Statistical Power: {:.0}%", power * 100.0);
    println!(
        "   ⚡ Required Sample Size: {} test cases per variant",
        required_samples
    );

    // ========================================================================
    // Step 2: Create Agents
    // ========================================================================
    println!("\nStep 2: Agent Setup");
    println!("{}", "-".repeat(70));

    let control: Arc<dyn Agent> = Arc::new(ControlAgent::new(0.70)); // 70% accuracy
    let treatment: Arc<dyn Agent> = Arc::new(TreatmentAgent::new(0.85)); // 85% accuracy

    println!("🔷 Control Agent: {} (70% accuracy)", control.name());
    println!("🔶 Treatment Agent: {} (85% accuracy)", treatment.name());

    // ========================================================================
    // Step 3: Generate Test Cases
    // ========================================================================
    println!("\nStep 3: Test Case Generation");
    println!("{}", "-".repeat(70));

    let test_cases: Vec<TestCase> = (0..required_samples.min(50))
        .map(|i| {
            TestCase::new(
                format!(
                    "Question {}: What is the capital of country {}?",
                    i + 1,
                    i + 1
                ),
                format!("Capital {}", i + 1),
            )
        })
        .collect();

    println!("📝 Generated {} test cases", test_cases.len());

    // ========================================================================
    // Step 4: T-Test (Parametric)
    // ========================================================================
    println!("\nStep 4: Student's T-Test (Parametric)");
    println!("{}", "-".repeat(70));

    let t_test = ABTest::new(StatisticalTestType::TTest, SignificanceLevel::P005);
    println!("🧪 Running t-test with 95% confidence...\n");

    let result = t_test
        .run(control.clone(), treatment.clone(), &test_cases, "accuracy")
        .await?;

    println!("{}", result.summary());
    println!("\n📈 Analysis:");
    println!(
        "   Is Significant: {}",
        if result.is_significant {
            "✓ Yes"
        } else {
            "✗ No"
        }
    );
    println!("   Winner: {}", result.winner);
    println!("   P-value: {:.6} (threshold: 0.05)", result.p_value);
    println!("   Effect Size (Cohen's d): {:.3}", result.effect_size);
    println!(
        "   Confidence Interval: [{:.4}, {:.4}]",
        result.confidence_interval.0, result.confidence_interval.1
    );

    // Interpret effect size
    let effect_interpretation = if result.effect_size.abs() < 0.2 {
        "Small"
    } else if result.effect_size.abs() < 0.5 {
        "Medium"
    } else if result.effect_size.abs() < 0.8 {
        "Large"
    } else {
        "Very Large"
    };
    println!(
        "   Effect Size Interpretation: {} effect",
        effect_interpretation
    );

    // ========================================================================
    // Step 5: Mann-Whitney U Test (Non-Parametric)
    // ========================================================================
    println!("\nStep 5: Mann-Whitney U Test (Non-Parametric)");
    println!("{}", "-".repeat(70));

    let mann_whitney = ABTest::new(StatisticalTestType::MannWhitney, SignificanceLevel::P005);
    println!("🧪 Running Mann-Whitney U test (robust to outliers)...\n");

    let result_mw = mann_whitney
        .run(control.clone(), treatment.clone(), &test_cases, "accuracy")
        .await?;

    println!("📊 Mann-Whitney Results:");
    println!("   P-value: {:.6}", result_mw.p_value);
    println!(
        "   Is Significant: {}",
        if result_mw.is_significant {
            "✓ Yes"
        } else {
            "✗ No"
        }
    );
    println!("   Winner: {}", result_mw.winner);
    println!("\n   Note: Mann-Whitney is more robust when data isn't normally distributed");

    // ========================================================================
    // Step 6: Bootstrap Test (Resampling)
    // ========================================================================
    println!("\nStep 6: Bootstrap Test (Resampling-Based)");
    println!("{}", "-".repeat(70));

    let bootstrap = ABTest::new(StatisticalTestType::Bootstrap, SignificanceLevel::P005);
    println!("🧪 Running bootstrap test with 10,000 resamples...\n");

    let result_boot = bootstrap
        .run(control.clone(), treatment.clone(), &test_cases, "accuracy")
        .await?;

    println!("📊 Bootstrap Results:");
    println!("   P-value: {:.6}", result_boot.p_value);
    println!(
        "   Is Significant: {}",
        if result_boot.is_significant {
            "✓ Yes"
        } else {
            "✗ No"
        }
    );
    println!("   Winner: {}", result_boot.winner);
    println!(
        "   95% CI: [{:.4}, {:.4}]",
        result_boot.confidence_interval.0, result_boot.confidence_interval.1
    );
    println!("\n   Note: Bootstrap makes minimal assumptions about data distribution");

    // ========================================================================
    // Step 7: Chi-Square Test (Categorical)
    // ========================================================================
    println!("\nStep 7: Chi-Square Test (For Binary Outcomes)");
    println!("{}", "-".repeat(70));

    let chi_square = ABTest::new(StatisticalTestType::ChiSquare, SignificanceLevel::P005);
    println!("🧪 Running chi-square test for categorical outcomes...\n");

    let result_chi = chi_square
        .run(control.clone(), treatment.clone(), &test_cases, "accuracy")
        .await?;

    println!("📊 Chi-Square Results:");
    println!("   P-value: {:.6}", result_chi.p_value);
    println!(
        "   Is Significant: {}",
        if result_chi.is_significant {
            "✓ Yes"
        } else {
            "✗ No"
        }
    );
    println!("   Winner: {}", result_chi.winner);
    println!("\n   Note: Chi-square is best for success/failure outcomes");

    // ========================================================================
    // Step 8: Different Significance Levels
    // ========================================================================
    println!("\nStep 8: Testing Different Significance Levels");
    println!("{}", "-".repeat(70));

    let significance_levels = vec![
        (SignificanceLevel::P0001, "99.9% confidence (p < 0.001)"),
        (SignificanceLevel::P001, "99% confidence (p < 0.01)"),
        (SignificanceLevel::P005, "95% confidence (p < 0.05)"),
        (SignificanceLevel::P010, "90% confidence (p < 0.10)"),
    ];

    println!("🎚️  Testing at multiple confidence levels:\n");

    for (level, description) in significance_levels {
        let test = ABTest::new(StatisticalTestType::TTest, level);
        let result = test
            .run(control.clone(), treatment.clone(), &test_cases, "accuracy")
            .await?;

        let symbol = if result.is_significant { "✓" } else { "✗" };
        println!(
            "   {} {} - Significant: {}",
            symbol,
            description,
            if result.is_significant { "Yes" } else { "No" }
        );
    }

    // ========================================================================
    // Step 9: Deployment Recommendation
    // ========================================================================
    println!("\nStep 9: Deployment Decision");
    println!("{}", "=".repeat(70));

    if result.is_significant && result.winner == "treatment" {
        println!("\n✅ RECOMMENDATION: Deploy Treatment Agent");
        println!("\n   Rationale:");
        println!(
            "   • Statistically significant improvement (p = {:.6})",
            result.p_value
        );
        println!(
            "   • {} effect size (Cohen's d = {:.3})",
            effect_interpretation, result.effect_size
        );
        println!(
            "   • Treatment accuracy: {:.1}%",
            result.treatment.mean * 100.0
        );
        println!("   • Control accuracy: {:.1}%", result.control.mean * 100.0);
        println!(
            "   • Improvement: {:.1}%",
            (result.treatment.mean - result.control.mean) * 100.0
        );

        println!("\n   Deployment Strategy:");
        println!("   1. Canary deployment (5% of traffic)");
        println!("   2. Monitor for 24-48 hours");
        println!("   3. Gradual rollout: 25% → 50% → 100%");
        println!("   4. Keep control version for rollback");
    } else if result.is_significant && result.winner == "control" {
        println!("\n⚠️  RECOMMENDATION: Keep Control Agent");
        println!("\n   Rationale:");
        println!("   • Treatment performed significantly worse");
        println!("   • Control is statistically superior");
        println!("   • Further development needed for treatment");
    } else {
        println!("\n⏸️  RECOMMENDATION: Inconclusive - More Testing Needed");
        println!("\n   Rationale:");
        println!("   • No statistically significant difference found");
        println!("   • P-value: {:.4} (not < 0.05)", result.p_value);
        println!("   • Options:");
        println!(
            "     1. Increase sample size (current: {})",
            test_cases.len()
        );
        println!("     2. Test with different use cases");
        println!("     3. Analyze specific failure patterns");
        println!("     4. Consider practical significance vs. statistical");
    }

    // ========================================================================
    // Summary
    // ========================================================================
    println!("\n{}", "=".repeat(70));
    println!("Summary: Statistical A/B Testing");
    println!("{}", "=".repeat(70));

    println!("\n📚 Key Concepts:");
    println!("\n1. Sample Size Planning:");
    println!("   • Calculate required samples before testing");
    println!("   • Balance statistical power with cost");
    println!("   • Larger samples = more confidence");

    println!("\n2. Statistical Tests:");
    println!("   • T-Test: Parametric, assumes normal distribution");
    println!("   • Mann-Whitney: Non-parametric, robust to outliers");
    println!("   • Bootstrap: Resampling-based, minimal assumptions");
    println!("   • Chi-Square: For categorical outcomes (success/failure)");

    println!("\n3. Effect Size:");
    println!("   • Cohen's d measures practical significance");
    println!("   • 0.2 = small, 0.5 = medium, 0.8 = large");
    println!("   • Large effect + statistical significance = strong result");

    println!("\n4. Significance Levels:");
    println!("   • p < 0.001: Very high confidence (99.9%)");
    println!("   • p < 0.01: High confidence (99%)");
    println!("   • p < 0.05: Standard confidence (95%)");
    println!("   • p < 0.10: Lower confidence (90%)");

    println!("\n5. Confidence Intervals:");
    println!("   • Range of plausible values for true difference");
    println!("   • If CI excludes 0, difference is significant");
    println!("   • Wider CI = more uncertainty");

    println!("\n🎯 Best Practices:");
    println!("   • Plan sample size before testing");
    println!("   • Use multiple statistical tests for robustness");
    println!("   • Consider both statistical and practical significance");
    println!("   • Account for multiple comparisons if testing many variants");
    println!("   • Monitor real-world metrics post-deployment");
    println!("   • Document assumptions and limitations");

    println!("\n✅ Test Complete!");
    println!("{}", "=".repeat(70));

    Ok(())
}
