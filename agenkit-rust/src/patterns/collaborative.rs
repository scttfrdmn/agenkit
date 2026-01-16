//! Collaborative Pattern - Peer-to-Peer Agent Collaboration
//!
//! Implements peer-to-peer agent collaboration with iterative refinement.
//! Multiple agents work together, each contributing their perspective and
//! refining the collective output through rounds.
//!
//! # Key Concepts
//!
//! - **Peer collaboration**: No hierarchy, agents work as equals
//! - **Iterative refinement**: Multiple rounds of contribution
//! - **Consensus detection**: Early termination when agreement reached
//! - **Context sharing**: Each agent sees all previous responses
//!
//! # Use Cases
//!
//! - Code review: multiple reviewers provide feedback
//! - Document editing: iterative improvements from editors
//! - Decision making: collaborative analysis and consensus
//! - Creative writing: multiple perspectives and refinement
//! - Research: peer review and iteration
//!
//! # Performance Characteristics
//!
//! - **Time**: O(rounds * n agents) worst case
//! - **Memory**: O(rounds * n agents * message size)
//! - Early termination on consensus
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{CollaborativeAgent, CollaborativeConfig, DefaultMergeFunc};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let reviewer1: Arc<dyn Agent> = todo!();
//! # let reviewer2: Arc<dyn Agent> = todo!();
//! # let reviewer3: Arc<dyn Agent> = todo!();
//! let agents = vec![reviewer1, reviewer2, reviewer3];
//! let collaborative = CollaborativeAgent::new(CollaborativeConfig {
//!     agents,
//!     max_rounds: 3,
//!     consensus_func: None,
//!     merge_func: DefaultMergeFunc::concatenate,
//! })?;
//!
//! let result = collaborative.process(Message::with_text("user", "Review this code")).await?;
//! # Ok(())
//! # }
//! ```

use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};
use serde_json::json;

/// Function type that determines if agents have reached consensus.
///
/// The function receives all agent responses from a round and returns true
/// if consensus is achieved. Common strategies include:
/// - Content similarity threshold
/// - Voting on same answer
/// - Agreement indicators in responses
/// - Convergence metrics
pub type ConsensusFunc = fn(&[Message]) -> bool;

/// Function type that combines multiple agent responses into a single result.
///
/// The function receives all responses and produces a merged output.
/// Common strategies include:
/// - Voting/majority rule
/// - Weighted combination
/// - Concatenation with synthesis
/// - Best response selection
pub type MergeFunc = fn(&[Message]) -> Message;

/// Configuration for CollaborativeAgent.
pub struct CollaborativeConfig {
    /// Agents participating in collaboration
    pub agents: Vec<Arc<dyn Agent>>,
    /// MaxRounds limits iteration (default: 3)
    pub max_rounds: usize,
    /// ConsensusFunc detects agreement (optional)
    pub consensus_func: Option<ConsensusFunc>,
    /// MergeFunc combines responses (required)
    pub merge_func: MergeFunc,
}

/// Collaborative agent that enables peer collaboration with iterative refinement.
///
/// Agents work together in rounds, each seeing previous responses and
/// contributing refinements. The process continues until consensus is
/// reached or maximum rounds are exhausted.
///
/// The collaborative pattern is ideal when multiple perspectives improve
/// output quality through discussion and refinement.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{CollaborativeAgent, CollaborativeConfig, DefaultMergeFunc};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let editor1: Arc<dyn Agent> = todo!();
/// # let editor2: Arc<dyn Agent> = todo!();
/// let agents = vec![editor1, editor2];
/// let collaborative = CollaborativeAgent::new(CollaborativeConfig {
///     agents,
///     max_rounds: 5,
///     consensus_func: None,
///     merge_func: DefaultMergeFunc::last,
/// })?;
///
/// let input = Message::with_text("user", "Draft a document");
/// let output = collaborative.process(input).await?;
/// # Ok(())
/// # }
/// ```
pub struct CollaborativeAgent {
    agents: Vec<Arc<dyn Agent>>,
    max_rounds: usize,
    consensus_func: Option<ConsensusFunc>,
    merge_func: MergeFunc,
}

impl std::fmt::Debug for CollaborativeAgent {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CollaborativeAgent")
            .field("agents", &format!("{} agents", self.agents.len()))
            .field("max_rounds", &self.max_rounds)
            .field(
                "consensus_func",
                &if self.consensus_func.is_some() {
                    "Some(<function>)"
                } else {
                    "None"
                },
            )
            .field("merge_func", &"<function>")
            .finish()
    }
}

impl CollaborativeAgent {
    /// Create a new collaborative agent.
    ///
    /// # Arguments
    ///
    /// * `config` - Configuration with agents and collaboration settings
    ///
    /// If no consensus function is provided, collaboration continues for all rounds.
    /// The merge function is required and determines how responses are combined.
    ///
    /// # Errors
    ///
    /// Returns an error if fewer than two agents are provided.
    pub fn new(config: CollaborativeConfig) -> Result<Self, AgentError> {
        if config.agents.len() < 2 {
            return Err(AgentError::InvalidInput(
                "at least two agents are required for collaboration".to_string(),
            ));
        }

        let max_rounds = if config.max_rounds == 0 {
            3
        } else {
            config.max_rounds
        };

        Ok(Self {
            agents: config.agents,
            max_rounds,
            consensus_func: config.consensus_func,
            merge_func: config.merge_func,
        })
    }

    /// Get the agents in the collaboration.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }

    /// Get the maximum number of rounds.
    pub fn max_rounds(&self) -> usize {
        self.max_rounds
    }

    /// Build context message with full conversation history.
    fn build_context_message(
        &self,
        context: &[Message],
        round: usize,
        agent_name: &str,
    ) -> Message {
        let mut content = format!("=== Collaboration Round {} ===\n", round);
        content.push_str(&format!("Agent: {}\n\n", agent_name));

        if round == 0 {
            content.push_str("Original Request:\n");
            if let Some(msg) = context.first() {
                if let Some(text) = msg.content_as_str() {
                    content.push_str(text);
                }
            }
        } else {
            content.push_str("Original Request:\n");
            if let Some(msg) = context.first() {
                if let Some(text) = msg.content_as_str() {
                    content.push_str(text);
                }
            }
            content.push_str("\n\n--- Previous Responses ---\n\n");

            for (i, msg) in context.iter().skip(1).enumerate() {
                if let Some(text) = msg.content_as_str() {
                    content.push_str(&format!("Response {}:\n{}\n\n", i + 1, text));
                }
            }

            content.push_str("--- Your Turn ---\n");
            content.push_str(
                "Please review the above responses and provide your refined contribution.\n",
            );
        }

        Message::with_text("user", content)
    }
}

#[async_trait::async_trait]
impl Agent for CollaborativeAgent {
    fn name(&self) -> &str {
        "CollaborativeAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut cap_set = std::collections::HashSet::new();

        for agent in &self.agents {
            for cap in agent.capabilities() {
                cap_set.insert(cap);
            }
        }

        let mut capabilities: Vec<String> = cap_set.into_iter().collect();
        capabilities.push("collaborative".to_string());
        capabilities.push("iterative".to_string());
        capabilities.push("consensus".to_string());

        capabilities
    }

    /// Execute collaborative refinement through multiple rounds.
    ///
    /// The process follows these steps for each round:
    /// 1. Each agent processes the current context (original + previous responses)
    /// 2. All responses are collected
    /// 3. Consensus is checked (if function provided)
    /// 4. If consensus or max rounds, merge and return
    /// 5. Otherwise, prepare next round with all responses as context
    ///
    /// The final message includes metadata about rounds, consensus, and participation.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Merged response from final collaboration round
    ///
    /// # Errors
    ///
    /// Returns an error if any agent fails during collaboration.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut rounds_data = Vec::with_capacity(self.max_rounds);
        let mut current_context = vec![message];

        for round in 0..self.max_rounds {
            // Collect responses from all agents
            let mut responses = Vec::with_capacity(self.agents.len());

            for agent in &self.agents {
                // Build context message with conversation history
                let context_msg = self.build_context_message(&current_context, round, agent.name());

                // Get agent response
                let response = agent.process(context_msg).await.map_err(|e| {
                    AgentError::ProcessingError(format!(
                        "agent {} failed in round {}: {}",
                        agent.name(),
                        round,
                        e
                    ))
                })?;

                responses.push(response);
            }

            // Check for consensus
            let has_consensus = if let Some(consensus_func) = self.consensus_func {
                consensus_func(&responses)
            } else {
                false
            };

            // Record round
            rounds_data.push(json!({
                "round": round,
                "responses": responses.len(),
                "consensus": has_consensus,
            }));

            // Stop if consensus reached
            if has_consensus {
                let mut merged = (self.merge_func)(&responses);
                merged
                    .metadata
                    .insert("collaboration_rounds".to_string(), json!(round + 1));
                merged
                    .metadata
                    .insert("collaboration_agents".to_string(), json!(self.agents.len()));
                merged
                    .metadata
                    .insert("stop_reason".to_string(), json!("consensus"));
                merged
                    .metadata
                    .insert("rounds".to_string(), json!(rounds_data));
                return Ok(merged);
            }

            // Prepare next round context
            current_context.extend(responses);
        }

        // Max rounds reached - merge final responses
        let final_round_start = current_context.len() - self.agents.len();
        let final_responses: Vec<Message> = current_context
            .into_iter()
            .skip(final_round_start)
            .collect();

        let mut merged = (self.merge_func)(&final_responses);
        merged
            .metadata
            .insert("collaboration_rounds".to_string(), json!(self.max_rounds));
        merged
            .metadata
            .insert("collaboration_agents".to_string(), json!(self.agents.len()));
        merged
            .metadata
            .insert("stop_reason".to_string(), json!("max_rounds"));
        merged
            .metadata
            .insert("rounds".to_string(), json!(rounds_data));

        Ok(merged)
    }
}

/// Default consensus detection strategies.
pub struct DefaultConsensusFunc;

impl DefaultConsensusFunc {
    /// Requires all responses to be identical.
    pub fn exact_match(messages: &[Message]) -> bool {
        if messages.len() <= 1 {
            return true;
        }

        let first = messages[0].content_as_str().unwrap_or("");
        messages
            .iter()
            .skip(1)
            .all(|msg| msg.content_as_str().unwrap_or("") == first)
    }

    /// Requires majority of responses to match.
    pub fn majority_agreement(messages: &[Message]) -> bool {
        if messages.len() <= 1 {
            return true;
        }

        // Count identical responses
        let mut content_count = std::collections::HashMap::new();
        for msg in messages {
            if let Some(content) = msg.content_as_str() {
                *content_count.entry(content).or_insert(0) += 1;
            }
        }

        // Check if any content has majority
        let majority = (messages.len() / 2) + 1;
        content_count.values().any(|&count| count >= majority)
    }
}

/// Default merge strategies for collaborative responses.
pub struct DefaultMergeFunc;

impl DefaultMergeFunc {
    /// Combines all responses with separators.
    pub fn concatenate(messages: &[Message]) -> Message {
        if messages.is_empty() {
            return Message::with_text("assistant", "No responses to merge");
        }

        let combined = messages
            .iter()
            .filter_map(|msg| msg.content_as_str())
            .collect::<Vec<_>>()
            .join("\n\n---\n\n");

        Message::with_text("assistant", combined)
    }

    /// Returns most common response.
    pub fn vote(messages: &[Message]) -> Message {
        if messages.is_empty() {
            return Message::with_text("assistant", "No responses to merge");
        }

        // Count votes
        let mut votes = std::collections::HashMap::new();
        let mut msg_by_content = std::collections::HashMap::new();

        for msg in messages {
            if let Some(content) = msg.content_as_str() {
                *votes.entry(content.to_string()).or_insert(0) += 1;
                msg_by_content.insert(content.to_string(), msg.clone());
            }
        }

        // Find winner
        if let Some((winner, max_votes)) = votes.iter().max_by_key(|(_, count)| *count) {
            if let Some(mut result) = msg_by_content.get(winner).cloned() {
                result
                    .metadata
                    .insert("votes".to_string(), json!(max_votes));
                result
                    .metadata
                    .insert("total".to_string(), json!(messages.len()));
                return result;
            }
        }

        messages[0].clone()
    }

    /// Returns first response.
    pub fn first(messages: &[Message]) -> Message {
        if messages.is_empty() {
            return Message::with_text("assistant", "No responses to merge");
        }
        messages[0].clone()
    }

    /// Returns last response.
    pub fn last(messages: &[Message]) -> Message {
        if messages.is_empty() {
            return Message::with_text("assistant", "No responses to merge");
        }
        messages[messages.len() - 1].clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct MockAgent {
        name: String,
        responses: Vec<String>,
        call_count: std::sync::Arc<std::sync::atomic::AtomicUsize>,
    }

    #[async_trait::async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec![format!("{}_capability", self.name)]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let count = self
                .call_count
                .fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            let response_idx = count.min(self.responses.len() - 1);
            Ok(Message::with_text(
                "assistant",
                &self.responses[response_idx],
            ))
        }
    }

    #[tokio::test]
    async fn test_collaborative_basic() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            responses: vec!["R1".to_string(), "R1-refined".to_string()],
            call_count: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            responses: vec!["R2".to_string(), "R2-refined".to_string()],
            call_count: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
        });

        let collaborative = CollaborativeAgent::new(CollaborativeConfig {
            agents: vec![agent1, agent2],
            max_rounds: 2,
            consensus_func: None,
            merge_func: DefaultMergeFunc::concatenate,
        })
        .unwrap();

        let message = Message::with_text("user", "collaborate on this");
        let result = collaborative.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("R1"));
        assert!(content.contains("R2"));

        assert_eq!(result.metadata.get("collaboration_rounds"), Some(&json!(2)));
        assert_eq!(result.metadata.get("collaboration_agents"), Some(&json!(2)));
        assert_eq!(
            result.metadata.get("stop_reason"),
            Some(&json!("max_rounds"))
        );
    }

    #[tokio::test]
    async fn test_collaborative_consensus() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            responses: vec!["same".to_string()],
            call_count: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            responses: vec!["same".to_string()],
            call_count: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
        });

        let collaborative = CollaborativeAgent::new(CollaborativeConfig {
            agents: vec![agent1, agent2],
            max_rounds: 5,
            consensus_func: Some(DefaultConsensusFunc::exact_match),
            merge_func: DefaultMergeFunc::first,
        })
        .unwrap();

        let message = Message::with_text("user", "collaborate");
        let result = collaborative.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("same"));
        assert_eq!(
            result.metadata.get("stop_reason"),
            Some(&json!("consensus"))
        );
        // Should stop early due to consensus
        assert_eq!(result.metadata.get("collaboration_rounds"), Some(&json!(1)));
    }

    #[tokio::test]
    async fn test_collaborative_too_few_agents() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            responses: vec!["response".to_string()],
            call_count: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
        });

        let result = CollaborativeAgent::new(CollaborativeConfig {
            agents: vec![agent1],
            max_rounds: 3,
            consensus_func: None,
            merge_func: DefaultMergeFunc::concatenate,
        });

        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("at least two agents"));
    }

    #[tokio::test]
    async fn test_collaborative_capabilities() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            responses: vec!["R1".to_string()],
            call_count: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            responses: vec!["R2".to_string()],
            call_count: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
        });

        let collaborative = CollaborativeAgent::new(CollaborativeConfig {
            agents: vec![agent1, agent2],
            max_rounds: 2,
            consensus_func: None,
            merge_func: DefaultMergeFunc::concatenate,
        })
        .unwrap();

        let caps = collaborative.capabilities();
        assert!(caps.contains(&"collaborative".to_string()));
        assert!(caps.contains(&"iterative".to_string()));
        assert!(caps.contains(&"consensus".to_string()));
    }

    #[tokio::test]
    async fn test_merge_vote() {
        let messages = vec![
            Message::with_text("assistant", "A"),
            Message::with_text("assistant", "A"),
            Message::with_text("assistant", "B"),
        ];

        let result = DefaultMergeFunc::vote(&messages);
        assert_eq!(result.content_as_str(), Some("A"));
        assert_eq!(result.metadata.get("votes"), Some(&json!(2)));
    }

    #[tokio::test]
    async fn test_consensus_majority() {
        let messages = vec![
            Message::with_text("assistant", "A"),
            Message::with_text("assistant", "A"),
            Message::with_text("assistant", "B"),
        ];

        assert!(DefaultConsensusFunc::majority_agreement(&messages));

        let messages2 = vec![
            Message::with_text("assistant", "A"),
            Message::with_text("assistant", "B"),
            Message::with_text("assistant", "C"),
        ];

        assert!(!DefaultConsensusFunc::majority_agreement(&messages2));
    }
}
