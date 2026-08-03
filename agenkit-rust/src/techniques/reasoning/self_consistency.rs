// Self-Consistency Reasoning Technique
//
// Self-Consistency improves reliability by generating multiple independent reasoning
// paths and using voting to select the most consistent answer.
//
// Reference: "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
// Wang et al., 2022 - https://arxiv.org/abs/2203.11171

use crate::core::{
    process_with_options, supports_options, Agent, AgentError, CallOptions, Message, OptionsAgent,
};
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

    /// Sampling temperature for diversity, 0.0-2.0 (optional).
    ///
    /// Forwarded to the wrapped agent when it implements
    /// [`OptionsAgent`](crate::core::OptionsAgent). If it does not, the samples are
    /// generated at whatever temperature the agent was configured with, so the
    /// diversity this technique depends on may not materialize —
    /// [`SelfConsistencyAgent::temperature_applied`] reports which happened.
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
    ///
    /// # Panics
    ///
    /// Panics if `config.temperature` is outside 0.0-2.0 (or is NaN). Rejecting it
    /// here rather than at call time matches the adapter constructors, and a
    /// temperature the provider will reject is a configuration error, not a runtime
    /// one.
    pub fn new(agent: Arc<dyn Agent>, config: SelfConsistencyConfig) -> Self {
        // Validated through the shared CallOptions type so the bounds cannot drift
        // apart from the ones the options themselves enforce.
        if let Err(e) = (CallOptions {
            temperature: config.temperature,
            ..Default::default()
        })
        .validate()
        {
            panic!("invalid SelfConsistencyConfig: {}", e);
        }

        let answer_extractor = config
            .answer_extractor
            .unwrap_or_else(|| Arc::new(default_answer_extractor));

        Self {
            agent,
            num_samples: config.num_samples,
            voting_strategy: config.voting_strategy,
            temperature: config.temperature,
            answer_extractor,
        }
    }

    /// Report whether the configured temperature actually reaches the LLM.
    ///
    /// False when a temperature is set but the wrapped agent does not implement
    /// [`OptionsAgent`](crate::core::OptionsAgent) — the samples are then generated at
    /// whatever temperature the agent was configured with, and this technique's
    /// diversity guarantee does not hold.
    ///
    /// Exposed rather than left implicit because a silently ignored temperature is
    /// precisely the failure this fixes: the value was accepted and dropped for as
    /// long as the field existed, and a public config field is an explicit invitation
    /// to set it (#801).
    ///
    /// Returns true when no temperature is set — there is nothing to apply, so
    /// nothing was dropped.
    pub fn temperature_applied(&self) -> bool {
        if self.temperature.is_none() {
            return true;
        }
        supports_options(self.agent.as_ref())
    }

    /// Merge the caller's options with the configured temperature.
    ///
    /// The configured temperature is applied last and therefore wins over a
    /// temperature in the caller's options. That is deliberate: this technique's
    /// correctness depends on sampling diversity, so a caller reaching through it
    /// must not silently flatten the samples. Every other option passes through
    /// untouched.
    fn call_options(&self, caller: &CallOptions) -> CallOptions {
        match self.temperature {
            None => caller.clone(),
            Some(temperature) => caller.merge(&CallOptions {
                temperature: Some(temperature),
                ..Default::default()
            }),
        }
    }

    /// Generate multiple samples in parallel (native) or sequentially (WASM).
    async fn generate_samples(
        &self,
        message: &Message,
        options: &CallOptions,
    ) -> Result<(Vec<String>, Vec<String>), AgentError> {
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
                // Cloned per sample rather than shared by reference: the spawned task
                // must own everything it touches.
                let options = options.clone();

                let handle = tokio::spawn(async move {
                    let response = process_with_options(agent.as_ref(), msg, &options).await?;
                    let full_response = response.content_as_str().unwrap_or("").to_string();
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
                let response =
                    process_with_options(self.agent.as_ref(), message.clone(), options).await?;
                let full_response = response.content_as_str().unwrap_or("").to_string();
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
            original_case
                .entry(normalized)
                .or_insert_with(|| answer.clone());
        }

        // Find most common
        let (winning_answer, max_count) = counts
            .iter()
            .max_by_key(|(_, count)| *count)
            .map(|(answer, count)| (answer.clone(), *count))
            .unwrap_or((String::new(), 0));

        let winner = original_case
            .get(&winning_answer)
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
            let entry = groups
                .entry(normalized.clone())
                .or_insert((answer.clone(), 0, 0));
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
        self.process_with(message, &CallOptions::new()).await
    }

    fn as_options_agent(&self) -> Option<&dyn OptionsAgent> {
        Some(self)
    }
}

#[async_trait]
impl OptionsAgent for SelfConsistencyAgent {
    /// Process the message with Self-Consistency and per-call options.
    ///
    /// Implemented so this technique can itself be wrapped by another that varies
    /// options — the capability has to run in both directions or the chain breaks at
    /// the first link that only consumes options (#801).
    ///
    /// The caller's options are merged with the configured temperature, which wins on
    /// conflict; see [`SelfConsistencyAgent::call_options`].
    async fn process_with(
        &self,
        message: Message,
        options: &CallOptions,
    ) -> Result<Message, AgentError> {
        let sample_options = self.call_options(options);

        // Generate multiple samples
        let (full_responses, extracted_answers) =
            self.generate_samples(&message, &sample_options).await?;

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
        response
            .metadata
            .insert("technique".to_string(), json!("self_consistency"));
        response
            .metadata
            .insert("num_samples".to_string(), json!(self.num_samples));
        response.metadata.insert(
            "voting_strategy".to_string(),
            json!(format!("{:?}", self.voting_strategy).to_lowercase()),
        );
        response
            .metadata
            .insert("consistency_score".to_string(), json!(consistency_score));
        response
            .metadata
            .insert("samples".to_string(), json!(full_responses));
        response
            .metadata
            .insert("extracted_answers".to_string(), json!(extracted_answers));
        response
            .metadata
            .insert("answer_counts".to_string(), json!(answer_counts));
        response
            .metadata
            .insert("base_agent".to_string(), json!(self.agent.name()));

        // Report the temperature and whether it reached the LLM, matching the Python
        // core. temperature is null when unset — a caller must be able to tell "not
        // requested" from "requested and dropped", which temperature_applied alone
        // cannot express.
        response
            .metadata
            .insert("temperature".to_string(), json!(self.temperature));
        response.metadata.insert(
            "temperature_applied".to_string(),
            json!(self.temperature_applied()),
        );

        Ok(response)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    struct MockAgent {
        responses: Mutex<Vec<String>>,
        call_count: Mutex<usize>,
    }

    impl MockAgent {
        fn new(responses: Vec<&str>) -> Arc<Self> {
            Arc::new(Self {
                responses: Mutex::new(responses.into_iter().map(|s| s.to_string()).collect()),
                call_count: Mutex::new(0),
            })
        }
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock"
        }

        fn capabilities(&self) -> Vec<String> {
            vec![]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let mut count = self.call_count.lock().unwrap();
            let responses = self.responses.lock().unwrap();
            let response = responses[*count % responses.len()].clone();
            *count += 1;
            Ok(Message::with_text("assistant", response))
        }
    }

    #[test]
    fn test_default_config() {
        let config = SelfConsistencyConfig::default();
        assert_eq!(config.num_samples, 5);
        assert!(matches!(config.voting_strategy, VotingStrategy::Majority));
        assert!(config.temperature.is_none());
    }

    #[test]
    fn test_agent_name_and_capabilities() {
        let agent = SelfConsistencyAgent::new(
            MockAgent::new(vec!["ans"]),
            SelfConsistencyConfig::default(),
        );
        assert_eq!(agent.name(), "self_consistency");
        let caps = agent.capabilities();
        assert!(caps.contains(&"self_consistency".to_string()));
        assert!(caps.contains(&"majority_voting".to_string()));
    }

    #[test]
    fn test_default_answer_extractor_with_answer_label() {
        let text = "The answer is: 42";
        let result = default_answer_extractor(text);
        assert!(result.contains("42"));
    }

    #[test]
    fn test_default_answer_extractor_last_sentence() {
        let text = "Some reasoning here. The final answer is 7.";
        let result = default_answer_extractor(text);
        assert!(!result.is_empty());
    }

    #[test]
    fn test_vote_majority_picks_most_common() {
        let agent =
            SelfConsistencyAgent::new(MockAgent::new(vec!["a"]), SelfConsistencyConfig::default());
        let answers = vec![
            "42".to_string(),
            "7".to_string(),
            "42".to_string(),
            "42".to_string(),
        ];
        let (winner, score) = agent.vote_majority(&answers);
        assert_eq!(winner.to_lowercase(), "42");
        assert!(score > 0.5);
    }

    #[test]
    fn test_vote_first_returns_first() {
        let agent =
            SelfConsistencyAgent::new(MockAgent::new(vec!["a"]), SelfConsistencyConfig::default());
        let answers = vec!["first".to_string(), "second".to_string()];
        let (winner, score) = agent.vote_first(&answers);
        assert_eq!(winner, "first");
        assert_eq!(score, 1.0);
    }

    #[test]
    fn test_vote_first_empty() {
        let agent =
            SelfConsistencyAgent::new(MockAgent::new(vec!["a"]), SelfConsistencyConfig::default());
        let (winner, _) = agent.vote_first(&[]);
        assert!(winner.is_empty());
    }

    #[test]
    fn test_count_answers_case_insensitive() {
        let agent =
            SelfConsistencyAgent::new(MockAgent::new(vec!["a"]), SelfConsistencyConfig::default());
        let answers = vec![
            "Paris".to_string(),
            "paris".to_string(),
            "PARIS".to_string(),
        ];
        let counts = agent.count_answers(&answers);
        assert_eq!(counts.get("paris"), Some(&3));
    }

    #[tokio::test]
    async fn test_process_majority_voting() {
        let config = SelfConsistencyConfig {
            num_samples: 3,
            voting_strategy: VotingStrategy::Majority,
            ..Default::default()
        };
        let agent = SelfConsistencyAgent::new(
            MockAgent::new(vec![
                "The answer is 42",
                "The answer is 42",
                "The answer is 7",
            ]),
            config,
        );
        let msg = Message::with_text("user", "What is 6*7?");
        let result = agent.process(msg).await.unwrap();
        assert_eq!(result.metadata["technique"], "self_consistency");
        assert_eq!(result.metadata["num_samples"], 3);
        assert!(result.metadata.contains_key("consistency_score"));
    }

    #[tokio::test]
    async fn test_process_first_strategy() {
        let config = SelfConsistencyConfig {
            num_samples: 3,
            voting_strategy: VotingStrategy::First,
            ..Default::default()
        };
        let agent = SelfConsistencyAgent::new(MockAgent::new(vec!["First response"]), config);
        let msg = Message::with_text("user", "test");
        let result = agent.process(msg).await.unwrap();
        assert_eq!(result.metadata["voting_strategy"], "first");
    }

    #[tokio::test]
    async fn test_process_metadata_completeness() {
        let agent = SelfConsistencyAgent::new(
            MockAgent::new(vec!["response"]),
            SelfConsistencyConfig {
                num_samples: 2,
                ..Default::default()
            },
        );
        let msg = Message::with_text("user", "test");
        let result = agent.process(msg).await.unwrap();
        assert!(result.metadata.contains_key("samples"));
        assert!(result.metadata.contains_key("extracted_answers"));
        assert!(result.metadata.contains_key("answer_counts"));
        assert!(result.metadata.contains_key("base_agent"));
    }
}
