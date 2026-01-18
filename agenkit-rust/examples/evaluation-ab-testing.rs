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
use agenkit::evaluation::recorder::SessionRecorder;
use async_trait::async_trait;
use std::collections::HashMap;

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

    let test_inputs = vec![
        "What's the weather like today?",
        "Can you help me?",
        "I need assistance with my order",
        "Tell me about your capabilities",
        "How do I reset my password?",
    ];

    println!("Agent A (Control): {}", agent_v1.name());
    println!("Agent B (Variant): {}", agent_v2.name());
    println!("Test Cases: {}\n", test_inputs.len());

    // Step 2: Record baseline session (V1)
    println!("Step 2: Recording Baseline Session (Agent V1)");
    println!("----------------------------------------------");

    let recorder_v1 = SessionRecorder::new(None);
    let wrapped_v1 = recorder_v1.wrap(agent_v1.clone());

    let session_id = "ab-test-session";
    for (i, input) in test_inputs.iter().enumerate() {
        let mut metadata = HashMap::new();
        metadata.insert("session_id".to_string(), serde_json::json!(session_id));

        let message = Message::with_text("user", input).with_metadata_map(metadata);

        let response = wrapped_v1.process(message).await?;
        println!("  {}. Input: {}", i + 1, input);
        println!("     V1: {}", response.content_as_str().unwrap_or(""));
    }

    let recording_v1 = recorder_v1.finalize_session(session_id).await?;
    println!(
        "\n✓ Baseline recorded: {} interactions\n",
        recording_v1.interactions.len()
    );

    // Step 3: Replay with both versions
    println!("Step 3: Replaying with Both Versions");
    println!("-------------------------------------");

    let results_v1 = recorder_v1
        .replay(&recording_v1, agent_v1.clone(), None)
        .await?;
    let results_v2 = recorder_v1
        .replay(&recording_v1, agent_v2.clone(), None)
        .await?;

    println!("Comparing outputs:\n");

    // Extract interactions
    let interactions_v1 = results_v1
        .get("interactions")
        .and_then(|v: &serde_json::Value| v.as_array())
        .unwrap();
    let interactions_v2 = results_v2
        .get("interactions")
        .and_then(|v: &serde_json::Value| v.as_array())
        .unwrap();

    for i in 0..interactions_v1.len() {
        let output_v1 = interactions_v1[i]
            .get("replay_output")
            .and_then(|v: &serde_json::Value| v.get("content"))
            .and_then(|v: &serde_json::Value| v.as_str())
            .unwrap_or("");
        let output_v2 = interactions_v2[i]
            .get("replay_output")
            .and_then(|v: &serde_json::Value| v.get("content"))
            .and_then(|v: &serde_json::Value| v.as_str())
            .unwrap_or("");

        let input = interactions_v1[i]
            .get("input")
            .and_then(|v: &serde_json::Value| v.get("content"))
            .and_then(|v: &serde_json::Value| v.as_str())
            .unwrap_or("");

        println!("  {}. Input: {}", i + 1, input);
        println!("     V1: {}", output_v1);
        println!("     V2: {}", output_v2);

        if output_v2.len() > output_v1.len() {
            let improvement =
                (output_v2.len() - output_v1.len()) as f64 / output_v1.len() as f64 * 100.0;
            println!("     📈 V2 is {:.0}% longer (more detailed)", improvement);
        }
        println!();
    }

    // Step 4: Compare metrics
    println!("Step 4: Comparing Metrics");
    println!("-------------------------");

    let comparison = recorder_v1.compare(&results_v1, &results_v2);

    println!("Performance Comparison:");
    println!(
        "  Latency V1: {:.0}ms",
        results_v1
            .get("total_latency_ms")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .unwrap_or(0.0)
    );
    println!(
        "  Latency V2: {:.0}ms",
        results_v2
            .get("total_latency_ms")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .unwrap_or(0.0)
    );
    println!(
        "  Difference: {:.0}ms ({:.1}%)",
        comparison
            .get("latency_diff_ms")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .unwrap_or(0.0),
        comparison
            .get("latency_diff_percent")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .unwrap_or(0.0)
    );

    let output_diffs = comparison
        .get("output_differences")
        .and_then(|v: &serde_json::Value| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    println!(
        "\n  Output Differences: {}/{}",
        output_diffs,
        test_inputs.len()
    );

    // Step 5: Statistical analysis
    println!("\nStep 5: Statistical Analysis");
    println!("----------------------------");

    // Calculate response lengths
    let mut v1_lengths = Vec::new();
    let mut v2_lengths = Vec::new();

    for i in 0..interactions_v1.len() {
        if let Some(output) = interactions_v1[i]
            .get("replay_output")
            .and_then(|v: &serde_json::Value| v.get("content"))
            .and_then(|v: &serde_json::Value| v.as_str())
        {
            v1_lengths.push(output.len());
        }
        if let Some(output) = interactions_v2[i]
            .get("replay_output")
            .and_then(|v: &serde_json::Value| v.get("content"))
            .and_then(|v: &serde_json::Value| v.as_str())
        {
            v2_lengths.push(output.len());
        }
    }

    let v1_avg_length = v1_lengths.iter().sum::<usize>() as f64 / v1_lengths.len() as f64;
    let v2_avg_length = v2_lengths.iter().sum::<usize>() as f64 / v2_lengths.len() as f64;

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

    // Step 6: Recommendation
    println!("\nStep 6: Recommendation");
    println!("----------------------");

    let latency_increase = comparison
        .get("latency_diff_percent")
        .and_then(|v: &serde_json::Value| v.as_f64())
        .unwrap_or(0.0);

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
