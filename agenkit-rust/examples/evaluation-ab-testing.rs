//! A/B Testing Example
//!
//! A/B testing compares two versions of an agent on identical inputs
//! to determine which performs better. This is essential for:
//!   - Validating improvements before deployment
//!   - Comparing different LLM models
//!   - Testing prompt variations
//!   - Evaluating configuration changes
//!
//! Run with: cargo run --example evaluation-ab-testing

use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use std::time::Instant;

/// AgentV1 represents version 1 of the agent (current production)
struct AgentV1;

#[async_trait]
impl Agent for AgentV1 {
    fn name(&self) -> &str {
        "agent-v1"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simple responses
        let query = message.content_as_str().unwrap_or("").to_lowercase();

        let response = if query.contains("weather") {
            "I don't have access to weather information."
        } else if query.contains("help") {
            "I can assist you with questions."
        } else {
            "I'll help you with that."
        };

        Ok(Message::with_text("assistant", response))
    }
}

/// AgentV2 represents version 2 of the agent (new candidate)
struct AgentV2;

#[async_trait]
impl Agent for AgentV2 {
    fn name(&self) -> &str {
        "agent-v2"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Improved responses with more detail
        let query = message.content_as_str().unwrap_or("").to_lowercase();

        let response = if query.contains("weather") {
            "I don't currently have access to real-time weather information. However, I recommend checking weather.com or your local weather service for the most accurate forecast."
        } else if query.contains("help") {
            "I'd be happy to help! I can answer questions, provide information, and assist with various tasks. What would you like to know?"
        } else {
            "I'll be glad to assist you with that. Could you provide more details so I can give you the most helpful response?"
        };

        Ok(Message::with_text("assistant", response))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("A/B Testing Example");
    println!("===================\n");

    // Step 1: Setup agents and test suite
    println!("Step 1: Setting Up A/B Test");
    println!("---------------------------");

    let agent_v1 = std::sync::Arc::new(AgentV1);
    let agent_v2 = std::sync::Arc::new(AgentV2);

    let test_inputs = ["What's the weather like today?",
        "Can you help me?",
        "I need assistance with my order",
        "Tell me about your capabilities",
        "How do I reset my password?"];

    println!("Agent A (Control): {}", agent_v1.name());
    println!("Agent B (Variant): {}", agent_v2.name());
    println!("Test Cases: {}\n", test_inputs.len());

    // Step 2: Run both versions on the identical inputs
    println!("Step 2: Running Both Versions on Identical Inputs");
    println!("--------------------------------------------------");

    // Collected per-input results: (input, v1_output, v2_output, v1_latency_ms, v2_latency_ms)
    let mut rows: Vec<(String, String, String, f64, f64)> = Vec::new();

    for (i, input) in test_inputs.iter().enumerate() {
        let msg_v1 = Message::with_text("user", *input);
        let start_v1 = Instant::now();
        let out_v1 = agent_v1.process(msg_v1).await?;
        let lat_v1 = start_v1.elapsed().as_secs_f64() * 1000.0;

        let msg_v2 = Message::with_text("user", *input);
        let start_v2 = Instant::now();
        let out_v2 = agent_v2.process(msg_v2).await?;
        let lat_v2 = start_v2.elapsed().as_secs_f64() * 1000.0;

        let output_v1 = out_v1.content_as_str().unwrap_or("").to_string();
        let output_v2 = out_v2.content_as_str().unwrap_or("").to_string();

        println!("  {}. Input: {}", i + 1, input);
        println!("     V1: {}", output_v1);
        println!("     V2: {}", output_v2);
        if output_v2.len() > output_v1.len() && !output_v1.is_empty() {
            let improvement =
                (output_v2.len() - output_v1.len()) as f64 / output_v1.len() as f64 * 100.0;
            println!("     📈 V2 is {:.0}% longer (more detailed)", improvement);
        }
        println!();

        rows.push((input.to_string(), output_v1, output_v2, lat_v1, lat_v2));
    }

    // Step 3: Compare metrics
    println!("Step 3: Comparing Metrics");
    println!("-------------------------");

    let total_lat_v1: f64 = rows.iter().map(|r| r.3).sum();
    let total_lat_v2: f64 = rows.iter().map(|r| r.4).sum();
    let latency_diff_ms = total_lat_v2 - total_lat_v1;
    let latency_increase = if total_lat_v1 > 0.0 {
        latency_diff_ms / total_lat_v1 * 100.0
    } else {
        0.0
    };
    let output_diffs = rows.iter().filter(|r| r.1 != r.2).count();

    println!("Performance Comparison:");
    println!("  Latency V1: {:.0}ms", total_lat_v1);
    println!("  Latency V2: {:.0}ms", total_lat_v2);
    println!(
        "  Difference: {:.0}ms ({:.1}%)",
        latency_diff_ms, latency_increase
    );
    println!(
        "\n  Output Differences: {}/{}",
        output_diffs,
        test_inputs.len()
    );

    // Step 4: Statistical analysis
    println!("\nStep 4: Statistical Analysis");
    println!("----------------------------");

    let v1_avg_length = rows.iter().map(|r| r.1.len()).sum::<usize>() as f64 / rows.len() as f64;
    let v2_avg_length = rows.iter().map(|r| r.2.len()).sum::<usize>() as f64 / rows.len() as f64;

    println!("Response Length Analysis:");
    println!("  V1 Average: {:.0} characters", v1_avg_length);
    println!("  V2 Average: {:.0} characters", v2_avg_length);
    println!(
        "  V2 is {:.0}% {} verbose",
        ((v2_avg_length - v1_avg_length).abs() / v1_avg_length * 100.0),
        if v2_avg_length > v1_avg_length {
            "more"
        } else {
            "less"
        }
    );

    // Step 5: Recommendation
    println!("\nStep 5: Recommendation");
    println!("----------------------");

    if v2_avg_length > v1_avg_length * 1.2 && latency_increase < 20.0 {
        println!("✓ RECOMMENDATION: Deploy V2");
        println!("  - Significantly more detailed responses");
        println!("  - Latency increase is acceptable (<20%)");
        println!("  - Better user experience expected");
    } else if latency_increase > 50.0 {
        println!("✗ RECOMMENDATION: Keep V1");
        println!("  - Latency increase too high (>50%)");
        println!("  - User experience may suffer");
    } else {
        println!("⚠ RECOMMENDATION: Run extended test");
        println!("  - Differences are marginal");
        println!("  - Recommend testing with larger sample");
        println!("  - Consider user feedback surveys");
    }

    // Summary
    println!("\n{}", "=".repeat(70));
    println!("Summary: A/B Testing");
    println!("{}", "=".repeat(70));

    println!("\nA/B Testing Workflow:");
    println!("1. Record baseline session with control (V1)");
    println!("2. Replay with both control and variant (V2)");
    println!("3. Compare outputs, latency, and quality");
    println!("4. Analyze statistical significance");
    println!("5. Make data-driven deployment decision");

    println!("\nMetrics to Compare:");
    println!("- Output Quality: Relevance, completeness, accuracy");
    println!("- Response Length: Verbosity vs. conciseness");
    println!("- Latency: Processing time for responses");
    println!("- Error Rate: Frequency of failures");
    println!("- User Satisfaction: Feedback scores (if available)");

    println!("\nBest Practices:");
    println!("1. Use representative test cases from production");
    println!("2. Test with sufficient sample size (50+ interactions)");
    println!("3. Measure both quantitative and qualitative metrics");
    println!("4. Consider user segments (power users vs. beginners)");
    println!("5. Run tests multiple times for consistency");
    println!("6. Monitor real users with gradual rollout (canary)");

    println!("\nCommon Use Cases:");
    println!("- Model Comparison: GPT-4 vs. Claude vs. Llama");
    println!("- Prompt Engineering: Testing different system prompts");
    println!("- Temperature Tuning: Creative vs. factual responses");
    println!("- Feature Flags: Testing new capabilities");
    println!("- Cost Optimization: Cheaper model with similar quality");

    println!("\nStatistical Considerations:");
    println!("- Sample Size: Larger = more confidence");
    println!("- Significance Testing: Use t-tests for means");
    println!("- Effect Size: Practical vs. statistical significance");
    println!("- Confounding Variables: Control for time-of-day, etc.");

    Ok(())
}
