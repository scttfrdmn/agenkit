//! Quality Scoring Example
//!
//! Quality scoring measures how well an agent performs across multiple dimensions:
//!   - Accuracy: Does it give correct answers?
//!   - Relevance: Are responses on-topic?
//!   - Completeness: Does it answer all parts of the question?
//!   - Coherence: Is the response well-structured?
//!
//! This example shows how to use AccuracyMetric, QualityMetrics, and other
//! evaluation metrics to comprehensively evaluate agent quality.
//!
//! Run with: cargo run --example evaluation-quality-scoring

use agenkit::core::{Agent, AgentError, Message};
use agenkit::evaluation::{AccuracyMetric, Evaluator, QualityMetrics};
use async_trait::async_trait;
use std::collections::HashMap;

/// QuizAgent simulates an agent that answers quiz questions.
struct QuizAgent;

#[async_trait]
impl Agent for QuizAgent {
    fn name(&self) -> &str {
        "quiz-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simple rule-based responses for demo
        let query = message.content_as_str().unwrap_or("").to_lowercase();

        let response = if query.contains("capital of france") {
            "The capital of France is Paris, a beautiful city known for its art, culture, and the Eiffel Tower."
        } else if query.contains("2+2") {
            "2+2 equals 4."
        } else if query.contains("largest ocean") {
            "The Pacific Ocean is the largest ocean on Earth, covering more than 63 million square miles."
        } else if query.contains("python language") {
            "Python is a high-level programming language created by Guido van Rossum. It's known for its simplicity and readability."
        } else if query.contains("photosynthesis") {
            "Photosynthesis is the process by which plants convert light energy into chemical energy, producing oxygen as a byproduct."
        } else {
            "I'm not sure about that. Could you rephrase the question?"
        };

        Ok(Message::with_text("assistant", response))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Quality Scoring Example");
    println!("=======================\n");

    // Step 1: Create agent and metrics
    println!("Step 1: Setting Up Evaluation");
    println!("------------------------------");
    let agent = std::sync::Arc::new(QuizAgent);

    let accuracy_metric = Box::new(AccuracyMetric::new(None, false));
    let quality_metric = Box::new(QualityMetrics::new(false, "", None));

    let evaluator = Evaluator::new(
        agent,
        vec![accuracy_metric, quality_metric],
        Some("quality-eval".to_string()),
    );

    println!("✓ Agent created: quiz-agent");
    println!("✓ Metrics configured: accuracy, quality\n");

    // Step 2: Define test cases
    println!("Step 2: Defining Test Cases");
    println!("----------------------------");
    let test_cases = vec![
        {
            let mut tc = HashMap::new();
            tc.insert(
                "input".to_string(),
                serde_json::json!("What is the capital of France?"),
            );
            tc.insert("expected".to_string(), serde_json::json!("Paris"));
            tc
        },
        {
            let mut tc = HashMap::new();
            tc.insert("input".to_string(), serde_json::json!("What is 2+2?"));
            tc.insert("expected".to_string(), serde_json::json!("4"));
            tc
        },
        {
            let mut tc = HashMap::new();
            tc.insert(
                "input".to_string(),
                serde_json::json!("What is the largest ocean?"),
            );
            tc.insert("expected".to_string(), serde_json::json!("Pacific"));
            tc
        },
        {
            let mut tc = HashMap::new();
            tc.insert(
                "input".to_string(),
                serde_json::json!("Tell me about the Python programming language"),
            );
            tc.insert("expected".to_string(), serde_json::json!("Python"));
            tc
        },
        {
            let mut tc = HashMap::new();
            tc.insert(
                "input".to_string(),
                serde_json::json!("Explain photosynthesis"),
            );
            tc.insert("expected".to_string(), serde_json::json!("photosynthesis"));
            tc
        },
        {
            let mut tc = HashMap::new();
            tc.insert(
                "input".to_string(),
                serde_json::json!("What is the meaning of life?"),
            );
            tc.insert("expected".to_string(), serde_json::json!("42")); // Agent will fail this
            tc
        },
    ];

    println!("Test cases defined: {}\n", test_cases.len());

    // Step 3: Run evaluation
    println!("Step 3: Running Evaluation");
    println!("---------------------------");
    let result = evaluator
        .evaluate(test_cases, Some("quality-eval-001".to_string()))
        .await?;

    println!("✓ Evaluation complete");
    println!("  Tests Run: {}", result.total_tests);
    println!("  Passed: {}", result.passed_tests);
    println!("  Failed: {}\n", result.failed_tests);

    // Step 4: Analyze accuracy results
    println!("Step 4: Accuracy Analysis");
    println!("-------------------------");
    if let Some(accuracy_stats) = result.aggregated_metrics.get("accuracy") {
        if let Some(accuracy) = accuracy_stats.get("accuracy").and_then(|v| v.as_f64()) {
            println!("Overall Accuracy: {:.1}%", accuracy * 100.0);
        }
        if let Some(correct) = accuracy_stats.get("correct").and_then(|v| v.as_f64()) {
            println!("Correct: {:.0}", correct);
        }
        if let Some(incorrect) = accuracy_stats.get("incorrect").and_then(|v| v.as_f64()) {
            println!("Incorrect: {:.0}", incorrect);
        }
        if let Some(total) = accuracy_stats.get("total").and_then(|v| v.as_f64()) {
            println!("Total: {:.0}\n", total);
        }
    }

    // Step 5: Analyze quality results
    println!("Step 5: Quality Analysis");
    println!("------------------------");
    if let Some(quality_stats) = result.aggregated_metrics.get("quality") {
        if let Some(mean) = quality_stats.get("mean").and_then(|v| v.as_f64()) {
            println!("Overall Quality Score: {:.3}", mean);
        }
        if let Some(min) = quality_stats.get("min").and_then(|v| v.as_f64()) {
            println!("Min: {:.3}", min);
        }
        if let Some(max) = quality_stats.get("max").and_then(|v| v.as_f64()) {
            println!("Max: {:.3}", max);
        }
        if let Some(std) = quality_stats.get("std").and_then(|v| v.as_f64()) {
            println!("Std Dev: {:.3}\n", std);
        }
    }

    // Summary
    println!("{}", "=".repeat(70));
    println!("Summary: Quality Scoring");
    println!("{}", "=".repeat(70));

    println!("\nQuality Dimensions:");
    println!("1. Accuracy: Factual correctness of responses");
    println!("2. Relevance: How on-topic responses are");
    println!("3. Completeness: Whether all parts are answered");
    println!("4. Coherence: Logical structure and clarity");

    println!("\nMetric Types:");
    println!("- AccuracyMetric: Binary correct/incorrect");
    println!("- QualityMetrics: Multi-dimensional quality (0.0-1.0)");
    println!("- Custom validators for domain-specific criteria");

    println!("\nBest Practices:");
    println!("1. Use multiple metrics for comprehensive evaluation");
    println!("2. Define clear expected outputs for accuracy testing");
    println!("3. Combine rule-based and LLM-based judging");
    println!("4. Track quality trends over time");
    println!("5. Set quality thresholds for production deployment");

    println!("\nReal-World Applications:");
    println!("- Pre-deployment quality gates");
    println!("- A/B testing different prompts/models");
    println!("- Monitoring production quality");
    println!("- Training data curation");
    println!("- Customer satisfaction prediction");

    Ok(())
}
