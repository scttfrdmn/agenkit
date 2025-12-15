// Self-Consistency Reasoning Technique
//
// Self-Consistency improves reliability by generating multiple independent reasoning
// paths and using voting to select the most consistent answer.
//
// Reference: "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
// Wang et al., 2022 - https://arxiv.org/abs/2203.11171

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use regex::Regex;
use serde_json::json;
use std::collections::HashMap;
use std::sync::Arc;

/// Voting strategy for answer aggregation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VotingStrategy {
    /// Most common answer wins
    Majority,
    /// Weight answers by response length
    Weighted,
    /// Use first answer (no voting, for debugging)
    First,
}

/// Answer extractor function type.
pub type AnswerExtractor = Arc<dyn Fn(&str) -> String + Send + Sync>;

/// Configuration for Self-Consistency.
pub struct SelfConsistencyConfig {
    /// Number of independent samples to generate (default: 5)
    pub num_samples: usize,

    /// Voting strategy for answer aggregation (default: Majority)
    pub voting_strategy: VotingStrategy,

    /// Sampling temperature for diversity (optional, not used yet)
    pub temperature: Option<f64>,

    /// Custom answer extraction function (optional)
    pub answer_extractor: Option<AnswerExtractor>,
}

impl Default for SelfConsistencyConfig {
    fn default() -> Self {
        Self {
            num_samples: 5,
            voting_strategy: VotingStrategy::Majority,
            temperature: None,
            answer_extractor: None,
        }
    }
}

/// Default answer extractor that looks for common answer patterns.
///
/// Patterns recognized:
/// - "Therefore, X" / "Thus, X" / "So, X"
/// - "The answer is X"
/// - "= X" (for math)
/// - "Conclusion: X" / "Result: X"
/// - Last non-empty line (fallback)
pub fn default_answer_extractor(text: &str) -> String {
    // Try explicit answer markers
    let patterns = vec![
        Regex::new(r"(?i)(?:therefore|thus|so),?\s+(?:the answer is\s+)?(.+?)(?:\.|$)").unwrap(),
        Regex::new(r"(?i)(?:the answer is|answer:)\s+(.+?)(?:\.|$)").unwrap(),
        Regex::new(r"=\s*(.+?)(?:\n|$)").unwrap(),
        Regex::new(r"(?i)(?:conclusion|result):\s*(.+?)(?:\.|$)").unwrap(),
    ];

    for pattern in patterns {
        if let Some(captures) = pattern.captures(text) {
            if let Some(answer) = captures.get(1) {
                return answer.as_str().trim().to_string();
            }
        }
    }

    // Fallback: use last non-empty line
    for line in text.lines().rev() {
        let trimmed = line.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }

    text.trim().to_string()
}

/// Self-Consistency agent that wraps a base agent.
pub struct SelfConsistencyAgent {
    agent: Arc<dyn Agent>,
    num_samples: usize,
    voting_strategy: VotingStrategy,
    temperature: Option<f64>,
    answer_extractor: AnswerExtractor,
}

impl SelfConsistencyAgent {
    /// Create a new Self-Consistency agent.
    pub fn new(agent: Arc<dyn Agent>, config: SelfConsistencyConfig) -> Self {
        let answer_extractor = config.answer_extractor.unwrap_or_else(|| {
            Arc::new(default_answer_extractor)
        });

        Self {
            agent,
            num_samples: config.num_samples,
            voting_strategy: config.voting_strategy,
            temperature: config.temperature,
            answer_extractor,
        }
    }

    /// Generate multiple samples in parallel (native) or sequentially (WASM).
    async fn generate_samples(&self, message: &Message) -> Result<(Vec<String>, Vec<String>), AgentError> {
        let mut full_responses = Vec::new();
        let mut extracted_answers = Vec::new();

        #[cfg(feature = "native")]
        {
            // Generate samples in parallel using tokio
            let mut handles = Vec::new();

            for _ in 0..self.num_samples {
                let agent = Arc::clone(&self.agent);
                let msg = message.clone();
                let extractor = Arc::clone(&self.answer_extractor);

                let handle = tokio::spawn(async move {
                    let response = agent.process(msg).await?;
                    let full_response = response.content_as_str()
                        .unwrap_or("")
                        .to_string();
                    let extracted_answer = extractor(&full_response);
                    Ok::<(String, String), AgentError>((full_response, extracted_answer))
                });

                handles.push(handle);
            }

            // Collect results
            for handle in handles {
                match handle.await {
                    Ok(Ok((full, extracted))) => {
                        full_responses.push(full);
                        extracted_answers.push(extracted);
                    }
                    Ok(Err(e)) => return Err(e),
                    Err(e) => return Err(AgentError::Internal(format!("Sampling failed: {}", e))),
                }
            }
        }

        #[cfg(feature = "wasm")]
        {
            // Generate samples sequentially in WASM (spawn_local is fire-and-forget)
            for _ in 0..self.num_samples {
                let response = self.agent.process(message.clone()).await?;
                let full_response = response.content_as_str()
                    .unwrap_or("")
                    .to_string();
                let extracted_answer = (self.answer_extractor)(&full_response);

                full_responses.push(full_response);
                extracted_answers.push(extracted_answer);
            }
        }

        Ok((full_responses, extracted_answers))
    }

    /// Vote using majority (most common answer wins).
    fn vote_majority(&self, answers: &[String]) -> (String, f64) {
        if answers.is_empty() {
            return (String::new(), 0.0);
        }

        // Count answer occurrences (case-insensitive)
        let mut counts: HashMap<String, usize> = HashMap::new();
        let mut original_case: HashMap<String, String> = HashMap::new();

        for answer in answers {
            let normalized = answer.to_lowercase().trim().to_string();
            *counts.entry(normalized.clone()).or_insert(0) += 1;
            original_case.entry(normalized).or_insert_with(|| answer.clone());
        }

        // Find most common
        let (winning_answer, max_count) = counts
            .iter()
            .max_by_key(|(_, count)| *count)
            .map(|(answer, count)| (answer.clone(), *count))
            .unwrap_or((String::new(), 0));

        let winner = original_case.get(&winning_answer)
            .cloned()
            .unwrap_or(winning_answer);
        let consistency_score = max_count as f64 / answers.len() as f64;

        (winner, consistency_score)
    }

    /// Vote using weighted strategy (longer responses get more weight).
    fn vote_weighted(&self, answers: &[String], responses: &[String]) -> (String, f64) {
        if answers.is_empty() {
            return (String::new(), 0.0);
        }

        // Group answers by normalized form
        let mut groups: HashMap<String, (String, usize, usize)> = HashMap::new();

        for (i, answer) in answers.iter().enumerate() {
            let normalized = answer.to_lowercase().trim().to_string();
            let entry = groups.entry(normalized.clone()).or_insert((
                answer.clone(),
                0,
                0,
            ));
            entry.1 += responses[i].len();
            entry.2 += 1;
        }

        // Find highest weighted answer
        let total_weight: usize = groups.values().map(|(_, weight, _)| weight).sum();
        let (winning_answer, max_weight) = groups
            .values()
            .max_by_key(|(_, weight, _)| weight)
            .map(|(answer, weight, _)| (answer.clone(), *weight))
            .unwrap_or((String::new(), 0));

        let consistency_score = if total_weight > 0 {
            max_weight as f64 / total_weight as f64
        } else {
            0.0
        };

        (winning_answer, consistency_score)
    }

    /// Use first answer (no voting).
    fn vote_first(&self, answers: &[String]) -> (String, f64) {
        if answers.is_empty() {
            (String::new(), 0.0)
        } else {
            (answers[0].clone(), 1.0)
        }
    }

    /// Count answer occurrences (case-insensitive).
    fn count_answers(&self, answers: &[String]) -> HashMap<String, usize> {
        let mut counts = HashMap::new();

        for answer in answers {
            let normalized = answer.to_lowercase().trim().to_string();
            *counts.entry(normalized).or_insert(0) += 1;
        }

        counts
    }
}

#[async_trait]
impl Agent for SelfConsistencyAgent {
    fn name(&self) -> &str {
        "self_consistency"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "reasoning".to_string(),
            "self_consistency".to_string(),
            "majority_voting".to_string(),
            "reliability".to_string(),
            "consensus".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Generate multiple samples
        let (full_responses, extracted_answers) = self.generate_samples(&message).await?;

        // Vote for consensus answer
        let (consensus_answer, consistency_score) = match self.voting_strategy {
            VotingStrategy::Majority => self.vote_majority(&extracted_answers),
            VotingStrategy::Weighted => self.vote_weighted(&extracted_answers, &full_responses),
            VotingStrategy::First => self.vote_first(&extracted_answers),
        };

        // Count answer occurrences
        let answer_counts = self.count_answers(&extracted_answers);

        // Build response with metadata
        let mut response = Message::with_text("assistant", consensus_answer);
        response.metadata.insert("technique".to_string(), json!("self_consistency"));
        response.metadata.insert("num_samples".to_string(), json!(self.num_samples));
        response.metadata.insert("voting_strategy".to_string(), json!(format!("{:?}", self.voting_strategy).to_lowercase()));
        response.metadata.insert("consistency_score".to_string(), json!(consistency_score));
        response.metadata.insert("samples".to_string(), json!(full_responses));
        response.metadata.insert("extracted_answers".to_string(), json!(extracted_answers));
        response.metadata.insert("answer_counts".to_string(), json!(answer_counts));
        response.metadata.insert("base_agent".to_string(), json!(self.agent.name()));

        Ok(response)
    }
}
