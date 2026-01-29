///! Parallel agent composition pattern.
///!
///! Executes multiple agents concurrently and combines their results.

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use futures::future::join_all;
use std::sync::Arc;

/// Result from a single agent execution.
pub struct AgentResult {
    pub agent_name: String,
    pub message: Option<Message>,
    pub error: Option<AgentError>,
}

/// Agent that executes multiple agents concurrently and combines their results.
///
/// All agents receive the same input message and execute in parallel.
/// Results are combined into a single output message.
///
/// # Example
///
/// ```no_run
/// use agenkit::composition::ParallelAgent;
/// use agenkit::core::{Agent, Message};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let expert1: Arc<dyn Agent> = todo!();
/// # let expert2: Arc<dyn Agent> = todo!();
/// # let expert3: Arc<dyn Agent> = todo!();
/// let parallel = ParallelAgent::new(
///     "ensemble",
///     vec![expert1, expert2, expert3]
/// )?;
///
/// let message = Message::with_text("user", "Analyze this");
/// let result = parallel.process(message).await?;
/// # Ok(())
/// # }
/// ```
pub struct ParallelAgent {
    name: String,
    agents: Vec<Arc<dyn Agent>>,
}

impl ParallelAgent {
    /// Create a new parallel agent.
    ///
    /// # Arguments
    ///
    /// * `name` - Name of this parallel agent
    /// * `agents` - List of agents to execute in parallel
    ///
    /// # Errors
    ///
    /// Returns an error if agents list is empty.
    pub fn new(name: impl Into<String>, agents: Vec<Arc<dyn Agent>>) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "Parallel agent requires at least one agent".to_string(),
            ));
        }

        Ok(Self {
            name: name.into(),
            agents,
        })
    }

    /// Get the list of agents that run in parallel.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }

    /// Execute a single agent and return the result.
    async fn execute_agent(&self, agent: Arc<dyn Agent>, message: Message) -> AgentResult {
        match agent.process(message).await {
            Ok(msg) => AgentResult {
                agent_name: agent.name().to_string(),
                message: Some(msg),
                error: None,
            },
            Err(err) => AgentResult {
                agent_name: agent.name().to_string(),
                message: None,
                error: Some(err),
            },
        }
    }

    /// Combine multiple agent responses into a single message.
    fn combine_responses(&self, results: Vec<AgentResult>) -> Message {
        let mut content_parts = Vec::new();
        let mut combined_metadata = std::collections::HashMap::new();

        for result in results {
            if let Some(message) = result.message {
                let content = message.content_as_str().unwrap_or("");
                content_parts.push(format!("[{}]: {}", result.agent_name, content));

                // Merge metadata with agent name prefix
                for (key, value) in message.metadata.iter() {
                    let prefixed_key = format!("{}.{}", result.agent_name, key);
                    combined_metadata.insert(prefixed_key, value.clone());
                }
            }
        }

        let combined_content = content_parts.join("\n");
        let mut message = Message::with_text("agent", combined_content);
        message.metadata = combined_metadata;
        message
    }
}

#[async_trait]
impl Agent for ParallelAgent {
    fn name(&self) -> &str {
        &self.name
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

        capabilities
    }

    /// Execute all agents in parallel and combine their results.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Combined message with results from all agents
    ///
    /// # Errors
    ///
    /// Returns an error if any agent fails.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Create tasks for all agents
        let tasks: Vec<_> = self
            .agents
            .iter()
            .map(|agent| self.execute_agent(agent.clone(), message.clone()))
            .collect();

        // Wait for all agents to complete
        let results = join_all(tasks).await;

        // Check for errors
        let errors: Vec<String> = results
            .iter()
            .filter_map(|r| {
                r.error
                    .as_ref()
                    .map(|e| format!("{}: {}", r.agent_name, e))
            })
            .collect();

        if !errors.is_empty() {
            return Err(AgentError::ProcessingError(format!(
                "Parallel execution had errors: {}",
                errors.join("; ")
            )));
        }

        // Combine all responses
        Ok(self.combine_responses(results))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct CounterAgent {
        name: String,
        count: i32,
    }

    #[async_trait]
    impl Agent for CounterAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["count".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text(
                "agent",
                format!("{}: {}", self.name, self.count),
            ))
        }
    }

    struct ErrorAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for ErrorAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["error".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError("Intentional error".to_string()))
        }
    }

    #[tokio::test]
    async fn test_parallel_execution() {
        let agent1 = Arc::new(CounterAgent {
            name: "agent1".to_string(),
            count: 1,
        });
        let agent2 = Arc::new(CounterAgent {
            name: "agent2".to_string(),
            count: 2,
        });
        let agent3 = Arc::new(CounterAgent {
            name: "agent3".to_string(),
            count: 3,
        });

        let parallel = ParallelAgent::new("ensemble", vec![agent1, agent2, agent3]).unwrap();

        let input = Message::with_text("user", "test");
        let result = parallel.process(input).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("[agent1]: agent1: 1"));
        assert!(content.contains("[agent2]: agent2: 2"));
        assert!(content.contains("[agent3]: agent3: 3"));
    }

    #[tokio::test]
    async fn test_parallel_empty_agents() {
        let result = ParallelAgent::new("test", vec![]);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_parallel_error_propagation() {
        let agent1 = Arc::new(CounterAgent {
            name: "agent1".to_string(),
            count: 1,
        });
        let agent2 = Arc::new(ErrorAgent {
            name: "error-agent".to_string(),
        });
        let agent3 = Arc::new(CounterAgent {
            name: "agent3".to_string(),
            count: 3,
        });

        let parallel = ParallelAgent::new("ensemble", vec![agent1, agent2, agent3]).unwrap();

        let input = Message::with_text("user", "test");
        let result = parallel.process(input).await;

        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(err_msg.contains("Parallel execution had errors"));
    }

    #[tokio::test]
    async fn test_parallel_capabilities() {
        let agent1 = Arc::new(CounterAgent {
            name: "agent1".to_string(),
            count: 1,
        });
        let agent2 = Arc::new(CounterAgent {
            name: "agent2".to_string(),
            count: 2,
        });

        let parallel = ParallelAgent::new("ensemble", vec![agent1, agent2]).unwrap();

        let capabilities = parallel.capabilities();
        assert!(capabilities.contains(&"count".to_string()));
        assert!(capabilities.contains(&"parallel".to_string()));
    }
}
