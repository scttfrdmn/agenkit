//! Reflection Pattern - Self-Critique and Iterative Refinement
//!
//! The Reflection pattern enables agents to review and improve their own outputs
//! through an iterative cycle of generation, critique, and refinement.
//!
//! # Key Concepts
//!
//! - **Generator**: Agent that produces initial output
//! - **Critic**: Agent that evaluates output quality and provides feedback
//! - **Iteration**: Repeated refinement based on critique
//! - **Quality Threshold**: Stop when output quality is sufficient
//! - **Improvement Threshold**: Stop when incremental improvements become minimal
//!
//! # Use Cases
//!
//! - Code generation with self-review
//! - Content creation with quality improvement
//! - Multi-draft writing and editing
//! - Error detection and correction
//! - Iterative problem solving
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{ReflectionAgent, ReflectionConfig, CritiqueFormat};
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let generator = todo!();
//! # let critic = todo!();
//! let config = ReflectionConfig {
//!     generator,
//!     critic,
//!     max_iterations: 5,
//!     quality_threshold: 0.9,
//!     improvement_threshold: 0.05,
//!     critique_format: CritiqueFormat::Structured,
//!     verbose: false,
//! };
//!
//! let agent = ReflectionAgent::new(config)?;
//! let message = Message::with_text("user", "Write a function to check if a number is prime");
//! let result = agent.process(message).await?;
//!
//! // Inspect reflection metadata
//! println!("Iterations: {:?}", result.metadata.get("reflection_iterations"));
//! println!("Final score: {:?}", result.metadata.get("final_quality_score"));
//! println!("Stop reason: {:?}", result.metadata.get("stop_reason"));
//! # Ok(())
//! # }
//! ```
//!
//! # References
//!
//! - Reflexion: Language Agents with Verbal Reinforcement Learning (https://arxiv.org/abs/2303.11366)
//! - Self-Refine: Iterative Refinement with Self-Feedback (https://arxiv.org/abs/2303.17651)

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};

#[cfg(feature = "native")]
use lazy_static::lazy_static;

#[cfg(feature = "native")]
lazy_static! {
    /// Pre-compiled regex patterns for parsing free-form critiques.
    /// These are compiled once and reused across all ReflectionAgent instances.
    static ref SCORE_PATTERN: regex::Regex = regex::Regex::new(r"(?i)score[:\s]+([0-9]*\.?[0-9]+)").unwrap();
    static ref RATING_PATTERN: regex::Regex = regex::Regex::new(r"(?i)rating[:\s]+([0-9]*\.?[0-9]+)").unwrap();
    static ref SLASH_10_PATTERN: regex::Regex = regex::Regex::new(r"([0-9]+)/10").unwrap();
    static ref SLASH_1_PATTERN: regex::Regex = regex::Regex::new(r"([0-9]*\.?[0-9]+)/1\.?0").unwrap();
}

/// Reason why reflection loop stopped.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StopReason {
    /// Quality threshold was met
    QualityThresholdMet,
    /// Improvements became minimal
    MinimalImprovement,
    /// Maximum iterations reached
    MaxIterations,
    /// Perfect score (1.0) achieved
    PerfectScore,
}

impl StopReason {
    fn as_str(&self) -> &'static str {
        match self {
            StopReason::QualityThresholdMet => "quality_threshold_met",
            StopReason::MinimalImprovement => "minimal_improvement",
            StopReason::MaxIterations => "max_iterations",
            StopReason::PerfectScore => "perfect_score",
        }
    }
}

/// Format expected from critic agent.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CritiqueFormat {
    /// JSON format: {"score": 0.8, "feedback": "..."}
    Structured,
    /// Free text with score extracted
    FreeForm,
}

/// Single iteration in the reflection loop.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflectionStep {
    /// Iteration number (1-indexed)
    pub iteration: usize,
    /// Generated output for this iteration
    pub output: String,
    /// Feedback from critic
    pub critique: String,
    /// Quality score (0.0-1.0)
    pub quality_score: f64,
    /// Improvement over previous iteration
    pub improvement: f64,
    /// When this iteration occurred
    pub timestamp: DateTime<Utc>,
}

/// Structured critique response from critic agent.
#[derive(Debug, Deserialize)]
struct CritiqueResponse {
    score: f64,
    feedback: String,
}

/// Configuration for ReflectionAgent.
pub struct ReflectionConfig {
    /// Agent that produces/refines output
    pub generator: Arc<dyn Agent>,
    /// Agent that evaluates output (returns score + feedback)
    pub critic: Arc<dyn Agent>,
    /// Maximum refinement iterations (default: 5)
    pub max_iterations: usize,
    /// Stop when score exceeds this (default: 0.9)
    pub quality_threshold: f64,
    /// Min improvement to continue (default: 0.05)
    pub improvement_threshold: f64,
    /// Expected format from critic (default: structured)
    pub critique_format: CritiqueFormat,
    /// Include full reflection history in output (default: false)
    pub verbose: bool,
}

impl Default for ReflectionConfig {
    fn default() -> Self {
        // Note: generator and critic must be provided
        // This implementation provides defaults for other fields
        unimplemented!("ReflectionConfig requires generator and critic to be specified")
    }
}

/// Agent that iteratively refines output through self-critique.
///
/// The reflection loop:
/// 1. Generator creates initial output
/// 2. Critic evaluates output, provides score and feedback
/// 3. Generator refines output based on feedback
/// 4. Repeat until quality threshold, minimal improvement, or max iterations
///
/// # Performance Characteristics
///
/// - **Latency**: N × (generator + critic), where N = number of iterations
/// - **Quality**: Generally improves with iterations
/// - **Cost**: N × (generator cost + critic cost)
/// - **Best for**: Tasks where quality improvement justifies additional cost
pub struct ReflectionAgent {
    generator: Arc<dyn Agent>,
    critic: Arc<dyn Agent>,
    max_iterations: usize,
    quality_threshold: f64,
    improvement_threshold: f64,
    critique_format: CritiqueFormat,
    verbose: bool,
}

impl ReflectionAgent {
    /// Creates a new ReflectionAgent with the given configuration.
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - `max_iterations` < 1
    /// - `quality_threshold` not in [0.0, 1.0]
    /// - `improvement_threshold` not in [0.0, 1.0]
    pub fn new(config: ReflectionConfig) -> Result<Self, AgentError> {
        // Validate configuration
        if config.max_iterations < 1 {
            return Err(AgentError::InvalidInput(format!(
                "max_iterations must be at least 1, got {}",
                config.max_iterations
            )));
        }
        if !(0.0..=1.0).contains(&config.quality_threshold) {
            return Err(AgentError::InvalidInput(format!(
                "quality_threshold must be between 0.0 and 1.0, got {}",
                config.quality_threshold
            )));
        }
        if !(0.0..=1.0).contains(&config.improvement_threshold) {
            return Err(AgentError::InvalidInput(format!(
                "improvement_threshold must be between 0.0 and 1.0, got {}",
                config.improvement_threshold
            )));
        }

        Ok(Self {
            generator: config.generator,
            critic: config.critic,
            max_iterations: config.max_iterations,
            quality_threshold: config.quality_threshold,
            improvement_threshold: config.improvement_threshold,
            critique_format: config.critique_format,
            verbose: config.verbose,
        })
    }

    /// Build prompt for critic agent.
    fn build_critique_prompt(&self, original_query: &str, current_output: &str) -> Message {
        let prompt = match self.critique_format {
            CritiqueFormat::Structured => {
                format!(
                    r#"Please evaluate the following output and provide structured feedback.

Original Request:
{}

Current Output:
{}

Provide your evaluation in this JSON format:
{{
  "score": <float between 0.0 and 1.0>,
  "feedback": "<specific feedback on what could be improved>"
}}

Focus on:
- Correctness: Does it solve the problem?
- Quality: Is it well-structured and clear?
- Completeness: Does it address all aspects?
- Potential Issues: Are there bugs or edge cases?"#,
                    original_query, current_output
                )
            }
            CritiqueFormat::FreeForm => {
                format!(
                    r#"Please evaluate the following output on a scale of 0.0 to 1.0.

Original Request:
{}

Current Output:
{}

Provide:
1. A score (0.0-1.0) indicating quality
2. Specific feedback on what could be improved

Your evaluation:"#,
                    original_query, current_output
                )
            }
        };

        Message::with_text("user", prompt)
    }

    /// Build prompt for generator to refine output.
    fn build_refinement_prompt(
        &self,
        original_query: &str,
        current_output: &str,
        critique: &str,
        iteration: usize,
    ) -> Message {
        let prompt = format!(
            r#"Please refine your previous output based on the following critique.

Original Request:
{}

Your Previous Output (Iteration {}):
{}

Critique:
{}

Please provide an improved version that addresses the critique while maintaining what was already good.

Refined Output:"#,
            original_query, iteration, current_output, critique
        );

        Message::with_text("user", prompt)
    }

    /// Parse critic's response into score and feedback.
    fn parse_critique(&self, critique_content: &str) -> Result<(f64, String), AgentError> {
        match self.critique_format {
            CritiqueFormat::Structured => self.parse_structured_critique(critique_content),
            CritiqueFormat::FreeForm => Ok(self.parse_free_form_critique(critique_content)),
        }
    }

    /// Parse JSON-formatted critique.
    fn parse_structured_critique(&self, content: &str) -> Result<(f64, String), AgentError> {
        // Handle markdown code blocks
        let content = content.trim();
        let json_content = if content.starts_with("```") {
            // Extract JSON from code block
            content
                .lines()
                .filter(|line| !line.is_empty() && !line.starts_with("```"))
                .collect::<Vec<_>>()
                .join("\n")
        } else {
            content.to_string()
        };

        match serde_json::from_str::<CritiqueResponse>(&json_content) {
            Ok(critique) => {
                // Clamp score to valid range
                let score = critique.score.clamp(0.0, 1.0);
                let feedback = if critique.feedback.is_empty() {
                    content.to_string()
                } else {
                    critique.feedback
                };
                Ok((score, feedback))
            }
            Err(_) => {
                // Fallback to free-form parsing
                Ok(self.parse_free_form_critique(content))
            }
        }
    }

    /// Parse free-form critique text.
    ///
    /// Looks for score indicators like:
    /// - "Score: 0.8"
    /// - "8/10"
    /// - "Rating: 7.5"
    #[cfg(feature = "native")]
    fn parse_free_form_critique(&self, content: &str) -> (f64, String) {
        let mut score = 0.5; // Default if no score found

        // Use pre-compiled regex patterns for performance
        let patterns = [&*SCORE_PATTERN, &*RATING_PATTERN, &*SLASH_10_PATTERN, &*SLASH_1_PATTERN];

        for pattern in &patterns {
            if let Some(captures) = pattern.captures(content) {
                if let Some(matched) = captures.get(1) {
                    if let Ok(value) = matched.as_str().parse::<f64>() {
                        // Normalize to 0.0-1.0 range
                        let normalized = if value > 1.0 {
                            value / 10.0 // Assume 0-10 scale
                        } else {
                            value
                        };
                        score = normalized.clamp(0.0, 1.0);
                        break;
                    }
                }
            }
        }

        (score, content.to_string())
    }

    /// Parse free-form critique text (WASM fallback without regex caching).
    #[cfg(not(feature = "native"))]
    fn parse_free_form_critique(&self, content: &str) -> (f64, String) {
        let mut score = 0.5; // Default if no score found

        // Try to find score patterns - compile on-demand for WASM
        let patterns = [
            regex::Regex::new(r"(?i)score[:\s]+([0-9]*\.?[0-9]+)").unwrap(),
            regex::Regex::new(r"(?i)rating[:\s]+([0-9]*\.?[0-9]+)").unwrap(),
            regex::Regex::new(r"([0-9]+)/10").unwrap(),
            regex::Regex::new(r"([0-9]*\.?[0-9]+)/1\.?0").unwrap(),
        ];

        for pattern in &patterns {
            if let Some(captures) = pattern.captures(content) {
                if let Some(matched) = captures.get(1) {
                    if let Ok(value) = matched.as_str().parse::<f64>() {
                        // Normalize to 0.0-1.0 range
                        let normalized = if value > 1.0 {
                            value / 10.0 // Assume 0-10 scale
                        } else {
                            value
                        };
                        score = normalized.clamp(0.0, 1.0);
                        break;
                    }
                }
            }
        }

        (score, content.to_string())
    }

    /// Check if reflection loop should stop.
    fn check_stop_conditions(
        &self,
        score: f64,
        improvement: f64,
        history_len: usize,
    ) -> (StopReason, bool) {
        // Perfect score
        if score >= 1.0 {
            return (StopReason::PerfectScore, true);
        }

        // Quality threshold met
        if score >= self.quality_threshold {
            return (StopReason::QualityThresholdMet, true);
        }

        // Minimal improvement (skip on first iteration)
        if history_len > 1 && improvement < self.improvement_threshold {
            return (StopReason::MinimalImprovement, true);
        }

        // Continue iterating
        (StopReason::MaxIterations, false)
    }

    /// Format final result with metadata.
    fn format_result(&self, output: Message, stop_reason: StopReason, history: &[ReflectionStep]) -> Message {
        let mut metadata = output.metadata.clone();

        // Add reflection metadata
        metadata.insert(
            "reflection_iterations".to_string(),
            serde_json::json!(history.len()),
        );
        metadata.insert(
            "stop_reason".to_string(),
            serde_json::json!(stop_reason.as_str()),
        );

        if let Some(last_step) = history.last() {
            metadata.insert(
                "final_quality_score".to_string(),
                serde_json::json!(last_step.quality_score),
            );
        }

        if let Some(first_step) = history.first() {
            metadata.insert(
                "initial_quality_score".to_string(),
                serde_json::json!(first_step.quality_score),
            );
            if let Some(last_step) = history.last() {
                metadata.insert(
                    "total_improvement".to_string(),
                    serde_json::json!(last_step.quality_score - first_step.quality_score),
                );
            }
        }

        // Include history if verbose
        if self.verbose {
            metadata.insert(
                "reflection_history".to_string(),
                serde_json::to_value(history).unwrap_or(serde_json::Value::Null),
            );
        }

        Message {
            role: output.role,
            content: output.content,
            metadata,
            timestamp: Utc::now(),
        }
    }
}

#[async_trait]
impl Agent for ReflectionAgent {
    fn name(&self) -> &str {
        "ReflectionAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut caps = std::collections::HashSet::new();

        // Add generator capabilities
        for cap in self.generator.capabilities() {
            caps.insert(cap);
        }

        // Add critic capabilities
        for cap in self.critic.capabilities() {
            caps.insert(cap);
        }

        // Add reflection-specific capabilities
        caps.insert("reflection".to_string());
        caps.insert("self-critique".to_string());

        caps.into_iter().collect()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let original_query = message.content_as_str().unwrap_or("");

        // Initial generation
        let mut output = self.generator.process(message.clone()).await?;
        let mut previous_score = 0.0;
        let mut history = Vec::new();

        // Reflection loop
        for iteration in 1..=self.max_iterations {
            let current_output = output.content_as_str().unwrap_or("");

            // Critique current output
            let critique_message = self.build_critique_prompt(original_query, current_output);
            let critique_response = self.critic.process(critique_message).await?;

            // Parse critique (score + feedback)
            let critique_content = critique_response.content_as_str().unwrap_or("");
            let (score, feedback) = self.parse_critique(critique_content)?;
            let improvement = score - previous_score;

            // Record step
            let step = ReflectionStep {
                iteration,
                output: current_output.to_string(),
                critique: feedback.clone(),
                quality_score: score,
                improvement,
                timestamp: Utc::now(),
            };
            history.push(step);

            // Check stopping conditions
            let (stop_reason, should_stop) =
                self.check_stop_conditions(score, improvement, history.len());

            if should_stop {
                return Ok(self.format_result(output, stop_reason, &history));
            }

            // Refine based on critique
            let refine_message =
                self.build_refinement_prompt(original_query, current_output, &feedback, iteration);
            output = self.generator.process(refine_message).await?;
            previous_score = score;
        }

        // Max iterations reached
        Ok(self.format_result(output, StopReason::MaxIterations, &history))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    // Mock generator agent for testing
    struct MockGenerator {
        call_count: Arc<AtomicUsize>,
    }

    #[async_trait]
    impl Agent for MockGenerator {
        fn name(&self) -> &str {
            "MockGenerator"
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["generation".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let count = self.call_count.fetch_add(1, Ordering::SeqCst);
            let content = if count == 0 {
                "Initial output v1"
            } else {
                &format!("Refined output v{}", count + 1)
            };
            Ok(Message::with_text("assistant", content))
        }
    }

    // Mock critic agent for testing
    struct MockCritic {
        scores: Vec<f64>,
        call_count: Arc<AtomicUsize>,
    }

    #[async_trait]
    impl Agent for MockCritic {
        fn name(&self) -> &str {
            "MockCritic"
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["critique".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let count = self.call_count.fetch_add(1, Ordering::SeqCst);
            let score = self.scores.get(count).copied().unwrap_or(0.5);
            let feedback = format!("Quality score: {}", score);
            let response_json = serde_json::json!({
                "score": score,
                "feedback": feedback
            });
            // Return as JSON string so content_as_str() works
            let response_str = serde_json::to_string(&response_json).unwrap();
            Ok(Message::with_text("assistant", response_str))
        }
    }

    #[tokio::test]
    async fn test_reflection_quality_threshold() {
        let generator = Arc::new(MockGenerator {
            call_count: Arc::new(AtomicUsize::new(0)),
        });
        let critic = Arc::new(MockCritic {
            scores: vec![0.5, 0.7, 0.95], // Reaches threshold on iteration 3
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let config = ReflectionConfig {
            generator,
            critic,
            max_iterations: 5,
            quality_threshold: 0.9,
            improvement_threshold: 0.05,
            critique_format: CritiqueFormat::Structured,
            verbose: true,
        };

        let agent = ReflectionAgent::new(config).unwrap();
        let message = Message::with_text("user", "Test task");
        let result = agent.process(message).await.unwrap();

        // Should stop at iteration 3 due to quality threshold
        assert_eq!(
            result
                .metadata
                .get("reflection_iterations")
                .and_then(|v| v.as_u64()),
            Some(3)
        );
        assert_eq!(
            result.metadata.get("stop_reason").and_then(|v| v.as_str()),
            Some("quality_threshold_met")
        );
        assert_eq!(
            result
                .metadata
                .get("final_quality_score")
                .and_then(|v| v.as_f64()),
            Some(0.95)
        );
    }

    #[tokio::test]
    async fn test_reflection_max_iterations() {
        let generator = Arc::new(MockGenerator {
            call_count: Arc::new(AtomicUsize::new(0)),
        });
        let critic = Arc::new(MockCritic {
            scores: vec![0.5, 0.6, 0.7], // Never reaches threshold
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let config = ReflectionConfig {
            generator,
            critic,
            max_iterations: 3,
            quality_threshold: 0.9,
            improvement_threshold: 0.05,
            critique_format: CritiqueFormat::Structured,
            verbose: false,
        };

        let agent = ReflectionAgent::new(config).unwrap();
        let message = Message::with_text("user", "Test task");
        let result = agent.process(message).await.unwrap();

        // Should stop at max iterations
        assert_eq!(
            result
                .metadata
                .get("reflection_iterations")
                .and_then(|v| v.as_u64()),
            Some(3)
        );
        assert_eq!(
            result.metadata.get("stop_reason").and_then(|v| v.as_str()),
            Some("max_iterations")
        );
    }

    #[tokio::test]
    async fn test_reflection_minimal_improvement() {
        let generator = Arc::new(MockGenerator {
            call_count: Arc::new(AtomicUsize::new(0)),
        });
        let critic = Arc::new(MockCritic {
            scores: vec![0.5, 0.6, 0.61], // Improvement < 0.05 on iteration 3
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let config = ReflectionConfig {
            generator,
            critic,
            max_iterations: 5,
            quality_threshold: 0.9,
            improvement_threshold: 0.05,
            critique_format: CritiqueFormat::Structured,
            verbose: false,
        };

        let agent = ReflectionAgent::new(config).unwrap();
        let message = Message::with_text("user", "Test task");
        let result = agent.process(message).await.unwrap();

        // Should stop due to minimal improvement
        assert_eq!(
            result
                .metadata
                .get("reflection_iterations")
                .and_then(|v| v.as_u64()),
            Some(3)
        );
        assert_eq!(
            result.metadata.get("stop_reason").and_then(|v| v.as_str()),
            Some("minimal_improvement")
        );
    }

    #[tokio::test]
    async fn test_reflection_perfect_score() {
        let generator = Arc::new(MockGenerator {
            call_count: Arc::new(AtomicUsize::new(0)),
        });
        let critic = Arc::new(MockCritic {
            scores: vec![0.5, 1.0], // Perfect score on iteration 2
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let config = ReflectionConfig {
            generator,
            critic,
            max_iterations: 5,
            quality_threshold: 0.9,
            improvement_threshold: 0.05,
            critique_format: CritiqueFormat::Structured,
            verbose: false,
        };

        let agent = ReflectionAgent::new(config).unwrap();
        let message = Message::with_text("user", "Test task");
        let result = agent.process(message).await.unwrap();

        // Should stop at perfect score
        assert_eq!(
            result
                .metadata
                .get("reflection_iterations")
                .and_then(|v| v.as_u64()),
            Some(2)
        );
        assert_eq!(
            result.metadata.get("stop_reason").and_then(|v| v.as_str()),
            Some("perfect_score")
        );
        assert_eq!(
            result
                .metadata
                .get("final_quality_score")
                .and_then(|v| v.as_f64()),
            Some(1.0)
        );
    }

    #[test]
    fn test_reflection_config_validation() {
        let generator = Arc::new(MockGenerator {
            call_count: Arc::new(AtomicUsize::new(0)),
        });
        let critic = Arc::new(MockCritic {
            scores: vec![0.5],
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        // Test invalid max_iterations
        let config = ReflectionConfig {
            generator: generator.clone(),
            critic: critic.clone(),
            max_iterations: 0,
            quality_threshold: 0.9,
            improvement_threshold: 0.05,
            critique_format: CritiqueFormat::Structured,
            verbose: false,
        };
        assert!(ReflectionAgent::new(config).is_err());

        // Test invalid quality_threshold
        let config = ReflectionConfig {
            generator: generator.clone(),
            critic: critic.clone(),
            max_iterations: 5,
            quality_threshold: 1.5,
            improvement_threshold: 0.05,
            critique_format: CritiqueFormat::Structured,
            verbose: false,
        };
        assert!(ReflectionAgent::new(config).is_err());

        // Test invalid improvement_threshold
        let config = ReflectionConfig {
            generator,
            critic,
            max_iterations: 5,
            quality_threshold: 0.9,
            improvement_threshold: -0.1,
            critique_format: CritiqueFormat::Structured,
            verbose: false,
        };
        assert!(ReflectionAgent::new(config).is_err());
    }
}
