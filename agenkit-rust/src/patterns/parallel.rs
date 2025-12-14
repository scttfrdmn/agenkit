//! Parallel Agent Execution Pattern
//!
//! Enables concurrent execution of multiple agents with result aggregation.
//! This is ideal for ensemble methods, multi-perspective analysis, or
//! parallelizing independent tasks.
//!
//! # Key Concepts
//!
//! - **Concurrent execution**: All agents execute simultaneously
//! - **Custom aggregation**: Flexible result combination strategies
//! - **Same input**: All agents receive the same input message
//! - **Result collection**: Results aggregated after all complete
//!
//! # Use Cases
//!
//! - Multi-model ensemble for improved accuracy
//! - Parallel document analysis (sentiment, entities, topics)
//! - A/B testing different agent implementations
//! - Redundant processing for reliability
//!
//! # Performance Characteristics
//!
//! - **Time**: O(max agent time) - parallel execution
//! - **Memory**: O(n * message size) for concurrent processing
//! - Thread-safe with proper synchronization
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{ParallelAgent, DefaultAggregators};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let model1: Arc<dyn Agent> = todo!();
//! # let model2: Arc<dyn Agent> = todo!();
//! # let model3: Arc<dyn Agent> = todo!();
//! let agents = vec![model1, model2, model3];
//! let parallel = ParallelAgent::new(agents, DefaultAggregators::majority_vote)?;
//!
//! let message = Message::with_text("user", "Analyze this text");
//! let result = parallel.process(message).await?;
//! // All models run concurrently, majority vote wins
//! # Ok(())
//! # }
//! ```

use std::sync::Arc;
use futures::future::join_all;

use crate::core::{Agent, AgentError, Message};
use serde_json::json;

/// Function type that combines multiple agent responses into one.
///
/// The function receives all agent responses and should return a single
/// aggregated response. Common aggregation strategies include:
/// - Voting: Select most common response
/// - Averaging: Combine numeric results
/// - Concatenation: Merge all responses
/// - First-success: Return first successful result
/// - Consensus: Require agreement threshold
pub type AggregatorFunc = fn(&[Message]) -> Message;

/// Parallel agent that executes multiple agents concurrently.
///
/// All agents receive the same input message and execute concurrently.
/// Results are collected and passed to the aggregator function which
/// produces the final output.
///
/// If any agent fails, the error is collected but other agents continue.
/// The aggregator receives all successful results.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{ParallelAgent, DefaultAggregators};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let sentiment_agent: Arc<dyn Agent> = todo!();
/// # let entity_agent: Arc<dyn Agent> = todo!();
/// # let topic_agent: Arc<dyn Agent> = todo!();
/// let agents = vec![sentiment_agent, entity_agent, topic_agent];
/// let parallel = ParallelAgent::new(agents, DefaultAggregators::concatenate)?;
///
/// let input = Message::with_text("user", "Analyze this document");
/// let output = parallel.process(input).await?;
/// // All analyses run in parallel and are concatenated
/// # Ok(())
/// # }
/// ```
pub struct ParallelAgent {
    agents: Vec<Arc<dyn Agent>>,
    aggregator: AggregatorFunc,
}

impl std::fmt::Debug for ParallelAgent {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ParallelAgent")
            .field("agents", &format!("{} agents", self.agents.len()))
            .field("aggregator", &"<function>")
            .finish()
    }
}

impl ParallelAgent {
    /// Create a new parallel execution agent.
    ///
    /// # Arguments
    ///
    /// * `agents` - List of agents to execute concurrently (must have at least one)
    /// * `aggregator` - Function to combine agent results into final output
    ///
    /// The aggregator function is called with all successful agent responses
    /// and must return a single aggregated message.
    ///
    /// # Errors
    ///
    /// Returns an error if the agents list is empty.
    pub fn new(agents: Vec<Arc<dyn Agent>>, aggregator: AggregatorFunc) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "at least one agent is required".to_string(),
            ));
        }

        Ok(Self { agents, aggregator })
    }

    /// Get the agents in the parallel group.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }
}

#[async_trait::async_trait]
impl Agent for ParallelAgent {
    fn name(&self) -> &str {
        "ParallelAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        // Collect unique capabilities from all agents
        let mut cap_set = std::collections::HashSet::new();

        for agent in &self.agents {
            for cap in agent.capabilities() {
                cap_set.insert(cap);
            }
        }

        let mut capabilities: Vec<String> = cap_set.into_iter().collect();
        capabilities.push("parallel".to_string());
        capabilities.push("ensemble".to_string());

        capabilities
    }

    /// Execute all agents concurrently and aggregate results.
    ///
    /// All agents receive the same input message and execute in parallel.
    /// Results are collected as they complete. Once all agents finish
    /// (or fail), successful results are passed to the aggregator function.
    ///
    /// If all agents fail, an error is returned. If some agents succeed, their
    /// results are aggregated and any errors are recorded in metadata.
    ///
    /// The final message includes metadata about:
    /// - Total agents executed
    /// - Successful agent results
    /// - Any errors that occurred
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Aggregated response from successful agents
    ///
    /// # Errors
    ///
    /// Returns an error if all agents fail.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Launch all agents concurrently using futures::join_all
        let futures: Vec<_> = self.agents
            .iter()
            .map(|agent| {
                let agent_clone = Arc::clone(agent);
                let message_clone = message.clone();

                async move {
                    let agent_name = agent_clone.name().to_string();
                    let result = agent_clone.process(message_clone).await;
                    Ok((agent_name, result))
                }
            })
            .collect();

        // Collect all results concurrently
        let results: Vec<Result<(String, Result<Message, AgentError>), std::convert::Infallible>> =
            join_all(futures).await;

        let mut successes = Vec::new();
        let mut errors = Vec::new();

        for task_result in results {
            match task_result {
                Ok((agent_name, Ok(msg))) => {
                    successes.push(msg);
                }
                Ok((agent_name, Err(err))) => {
                    errors.push(json!({
                        "agent": agent_name,
                        "error": err.to_string(),
                    }));
                }
                Err(_) => {
                    // Infallible type - this branch is unreachable
                    unreachable!("join_all never returns Err with Infallible");
                }
            }
        }

        // Check if all agents failed
        if successes.is_empty() {
            return Err(AgentError::ProcessingError(format!(
                "all agents failed: {:?}",
                errors
            )));
        }

        // Aggregate successful results
        let mut aggregated = (self.aggregator)(&successes);

        // Add parallel execution metadata
        aggregated
            .metadata
            .insert("parallel_agents".to_string(), json!(self.agents.len()));
        aggregated
            .metadata
            .insert("successful_agents".to_string(), json!(successes.len()));

        if !errors.is_empty() {
            aggregated
                .metadata
                .insert("errors".to_string(), json!(errors));
        }

        Ok(aggregated)
    }
}

/// Default aggregation strategies for parallel agent results.
pub struct DefaultAggregators;

impl DefaultAggregators {
    /// Returns the first successful result.
    pub fn first(messages: &[Message]) -> Message {
        if messages.is_empty() {
            return Message::with_text("assistant", "No results to aggregate");
        }
        messages[0].clone()
    }

    /// Combines all results with separator.
    pub fn concatenate(messages: &[Message]) -> Message {
        if messages.is_empty() {
            return Message::with_text("assistant", "No results to aggregate");
        }

        let combined = messages
            .iter()
            .filter_map(|msg| msg.content_as_str())
            .collect::<Vec<_>>()
            .join("\n\n---\n\n");

        Message::with_text("assistant", combined)
    }

    /// Returns the most common response.
    pub fn majority_vote(messages: &[Message]) -> Message {
        if messages.is_empty() {
            return Message::with_text("assistant", "No results to aggregate");
        }

        // Count occurrences of each response
        let mut votes = std::collections::HashMap::new();
        let mut msg_by_content = std::collections::HashMap::new();

        for msg in messages {
            if let Some(content) = msg.content_as_str() {
                *votes.entry(content.to_string()).or_insert(0) += 1;
                msg_by_content.insert(content.to_string(), msg.clone());
            }
        }

        // Find most common response
        let winner = votes
            .iter()
            .max_by_key(|(_, count)| *count)
            .map(|(content, count)| (content.clone(), *count));

        if let Some((content, max_votes)) = winner {
            if let Some(mut result) = msg_by_content.get(&content).cloned() {
                result
                    .metadata
                    .insert("votes".to_string(), json!(max_votes));
                result
                    .metadata
                    .insert("total_agents".to_string(), json!(messages.len()));
                return result;
            }
        }

        // Fallback
        messages[0].clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct MockAgent {
        name: String,
        response: String,
        fail: bool,
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
            if self.fail {
                return Err(AgentError::ProcessingError(format!(
                    "{} failed",
                    self.name
                )));
            }

            Ok(Message::with_text("assistant", &self.response))
        }
    }

    #[tokio::test]
    async fn test_parallel_basic() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "Response 1".to_string(),
            fail: false,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "Response 2".to_string(),
            fail: false,
        });

        let agent3 = Arc::new(MockAgent {
            name: "agent3".to_string(),
            response: "Response 3".to_string(),
            fail: false,
        });

        let parallel =
            ParallelAgent::new(vec![agent1, agent2, agent3], DefaultAggregators::concatenate)
                .unwrap();

        let message = Message::with_text("user", "input");
        let result = parallel.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("Response 1"));
        assert!(content.contains("Response 2"));
        assert!(content.contains("Response 3"));

        assert_eq!(result.metadata.get("parallel_agents"), Some(&json!(3)));
        assert_eq!(result.metadata.get("successful_agents"), Some(&json!(3)));
    }

    #[tokio::test]
    async fn test_parallel_with_failures() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "Response 1".to_string(),
            fail: false,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "".to_string(),
            fail: true,
        });

        let agent3 = Arc::new(MockAgent {
            name: "agent3".to_string(),
            response: "Response 3".to_string(),
            fail: false,
        });

        let parallel =
            ParallelAgent::new(vec![agent1, agent2, agent3], DefaultAggregators::concatenate)
                .unwrap();

        let message = Message::with_text("user", "input");
        let result = parallel.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("Response 1"));
        assert!(content.contains("Response 3"));

        assert_eq!(result.metadata.get("successful_agents"), Some(&json!(2)));
        assert!(result.metadata.contains_key("errors"));
    }

    #[tokio::test]
    async fn test_parallel_all_fail() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "".to_string(),
            fail: true,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "".to_string(),
            fail: true,
        });

        let parallel =
            ParallelAgent::new(vec![agent1, agent2], DefaultAggregators::concatenate).unwrap();

        let message = Message::with_text("user", "input");
        let result = parallel.process(message).await;

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("all agents failed"));
    }

    #[tokio::test]
    async fn test_parallel_majority_vote() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "A".to_string(),
            fail: false,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "A".to_string(),
            fail: false,
        });

        let agent3 = Arc::new(MockAgent {
            name: "agent3".to_string(),
            response: "B".to_string(),
            fail: false,
        });

        let parallel =
            ParallelAgent::new(vec![agent1, agent2, agent3], DefaultAggregators::majority_vote)
                .unwrap();

        let message = Message::with_text("user", "input");
        let result = parallel.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("A"));
        assert_eq!(result.metadata.get("votes"), Some(&json!(2)));
    }

    #[tokio::test]
    async fn test_parallel_first() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "First".to_string(),
            fail: false,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "Second".to_string(),
            fail: false,
        });

        let parallel = ParallelAgent::new(vec![agent1, agent2], DefaultAggregators::first).unwrap();

        let message = Message::with_text("user", "input");
        let result = parallel.process(message).await.unwrap();

        // Should get one of the responses (order not guaranteed in parallel execution)
        let content = result.content_as_str().unwrap();
        assert!(content == "First" || content == "Second");
    }

    #[tokio::test]
    async fn test_parallel_empty_agents() {
        let result = ParallelAgent::new(vec![], DefaultAggregators::concatenate);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("at least one agent"));
    }

    #[tokio::test]
    async fn test_parallel_capabilities() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "R1".to_string(),
            fail: false,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "R2".to_string(),
            fail: false,
        });

        let parallel =
            ParallelAgent::new(vec![agent1, agent2], DefaultAggregators::concatenate).unwrap();

        let caps = parallel.capabilities();
        assert!(caps.contains(&"agent1_capability".to_string()));
        assert!(caps.contains(&"agent2_capability".to_string()));
        assert!(caps.contains(&"parallel".to_string()));
        assert!(caps.contains(&"ensemble".to_string()));
    }
}
