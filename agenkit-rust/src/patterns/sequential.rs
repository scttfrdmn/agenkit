//! Sequential Agent Composition Pattern
//!
//! Enables pipeline-style agent composition where each agent processes the
//! output of the previous agent. This is ideal for multi-stage processing
//! workflows.
//!
//! # Key Concepts
//!
//! - **Linear processing pipeline**: Agents execute one after another
//! - **Output chaining**: Output of agent N becomes input of agent N+1
//! - **Early termination**: Pipeline stops immediately on errors
//! - **Metadata preservation**: Preserves metadata across pipeline stages
//!
//! # Use Cases
//!
//! - Document processing: extract -> translate -> summarize
//! - Data pipeline: validate -> transform -> enrich
//! - Content generation: draft -> review -> format
//!
//! # Performance Characteristics
//!
//! - **Time**: O(sum of agent times) - sequential execution
//! - **Memory**: O(1) for message passing (no accumulation)
//! - Each agent sees only previous agent's output
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::SequentialAgent;
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let extract_agent: Arc<dyn Agent> = todo!();
//! # let translate_agent: Arc<dyn Agent> = todo!();
//! # let summarize_agent: Arc<dyn Agent> = todo!();
//! let agents = vec![extract_agent, translate_agent, summarize_agent];
//! let sequential = SequentialAgent::new(agents)?;
//!
//! let message = Message::with_text("user", "Process this document");
//! let result = sequential.process(message).await?;
//! // Document is extracted, translated, then summarized
//! # Ok(())
//! # }
//! ```

use std::collections::HashMap;
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};
use serde_json::json;

/// Sequential agent that executes a pipeline of agents in order.
///
/// Each agent receives the output of the previous agent as input.
/// The final agent's output is returned as the result.
///
/// The pipeline stops immediately if any agent returns an error.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::SequentialAgent;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let validator: Arc<dyn Agent> = todo!();
/// # let transformer: Arc<dyn Agent> = todo!();
/// # let enricher: Arc<dyn Agent> = todo!();
/// let agents = vec![validator, transformer, enricher];
/// let pipeline = SequentialAgent::new(agents)?;
///
/// let input = Message::with_text("user", "raw data");
/// let output = pipeline.process(input).await?;
/// # Ok(())
/// # }
/// ```
pub struct SequentialAgent {
    agents: Vec<Arc<dyn Agent>>,
}

impl SequentialAgent {
    /// Create a new sequential pipeline agent.
    ///
    /// # Arguments
    ///
    /// * `agents` - List of agents to execute in order (must have at least one)
    ///
    /// The agents will be executed in the order provided. Each agent's output
    /// becomes the input for the next agent.
    ///
    /// # Errors
    ///
    /// Returns an error if the agents list is empty.
    pub fn new(agents: Vec<Arc<dyn Agent>>) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "at least one agent is required".to_string(),
            ));
        }

        Ok(Self { agents })
    }

    /// Get the agents in the pipeline.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }
}

#[async_trait::async_trait]
impl Agent for SequentialAgent {
    fn name(&self) -> &str {
        "SequentialAgent"
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
        capabilities.push("sequential".to_string());
        capabilities.push("pipeline".to_string());

        capabilities
    }

    /// Process message through the agent pipeline sequentially.
    ///
    /// The message is passed through each agent in order. Each agent's output
    /// becomes the input for the next agent. If any agent returns an error,
    /// the pipeline stops and the error is returned immediately.
    ///
    /// Metadata from each agent is preserved in the final message under the
    /// "pipeline_stages" key, allowing inspection of intermediate results.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Combined response from all agents, or error if any agent fails
    ///
    /// # Errors
    ///
    /// Returns an error if any agent in the pipeline fails.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Track pipeline stages for observability
        let mut stages = Vec::with_capacity(self.agents.len());

        // Pass message through each agent
        let mut current = message;

        for (i, agent) in self.agents.iter().enumerate() {
            // Process with current agent
            match agent.process(current.clone()).await {
                Ok(result) => {
                    // Record stage metadata
                    let mut stage_info = HashMap::new();
                    stage_info.insert("agent".to_string(), json!(agent.name()));
                    stage_info.insert("stage".to_string(), json!(i));

                    if !result.metadata.is_empty() {
                        stage_info.insert("metadata".to_string(), json!(result.metadata));
                    }

                    stages.push(stage_info);

                    // Use result as input for next agent
                    current = result;
                }
                Err(err) => {
                    return Err(AgentError::ProcessingError(format!(
                        "agent {} ({}) failed: {}",
                        i,
                        agent.name(),
                        err
                    )));
                }
            }
        }

        // Add pipeline metadata to final result
        let mut final_message = current;
        final_message
            .metadata
            .insert("pipeline_stages".to_string(), json!(stages));
        final_message
            .metadata
            .insert("pipeline_length".to_string(), json!(self.agents.len()));

        Ok(final_message)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct MockAgent {
        name: String,
        prefix: String,
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

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            if self.fail {
                return Err(AgentError::ProcessingError(format!(
                    "{} failed",
                    self.name
                )));
            }

            let content = message.content_as_str().unwrap_or("");
            let new_content = format!("{}:{}", self.prefix, content);

            Ok(Message::with_text("assistant", new_content))
        }
    }

    #[tokio::test]
    async fn test_sequential_basic() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            prefix: "A".to_string(),
            fail: false,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            prefix: "B".to_string(),
            fail: false,
        });

        let agent3 = Arc::new(MockAgent {
            name: "agent3".to_string(),
            prefix: "C".to_string(),
            fail: false,
        });

        let sequential = SequentialAgent::new(vec![agent1, agent2, agent3]).unwrap();

        let message = Message::with_text("user", "input");
        let result = sequential.process(message).await.unwrap();

        // Should be C:B:A:input (each agent prepends its prefix)
        assert_eq!(result.content_as_str(), Some("C:B:A:input"));

        // Check metadata
        assert!(result.metadata.contains_key("pipeline_stages"));
        assert_eq!(result.metadata.get("pipeline_length"), Some(&json!(3)));
    }

    #[tokio::test]
    async fn test_sequential_with_failure() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            prefix: "A".to_string(),
            fail: false,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            prefix: "B".to_string(),
            fail: true,
        });

        let agent3 = Arc::new(MockAgent {
            name: "agent3".to_string(),
            prefix: "C".to_string(),
            fail: false,
        });

        let sequential = SequentialAgent::new(vec![agent1, agent2, agent3]).unwrap();

        let message = Message::with_text("user", "input");
        let result = sequential.process(message).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("agent 1"));
        assert!(err.to_string().contains("agent2"));
        assert!(err.to_string().contains("failed"));
    }

    #[tokio::test]
    async fn test_sequential_empty_agents() {
        let result = SequentialAgent::new(vec![]);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("at least one agent"));
    }

    #[tokio::test]
    async fn test_sequential_single_agent() {
        let agent = Arc::new(MockAgent {
            name: "agent1".to_string(),
            prefix: "A".to_string(),
            fail: false,
        });

        let sequential = SequentialAgent::new(vec![agent]).unwrap();

        let message = Message::with_text("user", "input");
        let result = sequential.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("A:input"));
        assert_eq!(result.metadata.get("pipeline_length"), Some(&json!(1)));
    }

    #[tokio::test]
    async fn test_sequential_capabilities() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            prefix: "A".to_string(),
            fail: false,
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            prefix: "B".to_string(),
            fail: false,
        });

        let sequential = SequentialAgent::new(vec![agent1, agent2]).unwrap();

        let caps = sequential.capabilities();
        assert!(caps.contains(&"agent1_capability".to_string()));
        assert!(caps.contains(&"agent2_capability".to_string()));
        assert!(caps.contains(&"sequential".to_string()));
        assert!(caps.contains(&"pipeline".to_string()));
    }
}
