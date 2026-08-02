///! Sequential agent composition pattern.
///!
///! Executes multiple agents in sequence where the output of one agent
///! becomes the input to the next agent.
use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use std::sync::Arc;

/// Agent that executes multiple agents in sequence.
///
/// The output of one agent becomes the input to the next agent.
/// This is useful for building processing pipelines.
///
/// # Example
///
/// ```no_run
/// use agenkit::composition::SequentialAgent;
/// use agenkit::core::{Agent, Message};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let extract_agent: Arc<dyn Agent> = todo!();
/// # let translate_agent: Arc<dyn Agent> = todo!();
/// # let summarize_agent: Arc<dyn Agent> = todo!();
/// let sequential = SequentialAgent::new(
///     "pipeline",
///     vec![extract_agent, translate_agent, summarize_agent]
/// )?;
///
/// let message = Message::with_text("user", "Process this");
/// let result = sequential.process(message).await?;
/// # Ok(())
/// # }
/// ```
pub struct SequentialAgent {
    name: String,
    agents: Vec<Arc<dyn Agent>>,
}

impl SequentialAgent {
    /// Create a new sequential agent.
    ///
    /// # Arguments
    ///
    /// * `name` - Name of this sequential agent
    /// * `agents` - List of agents to execute in sequence
    ///
    /// # Errors
    ///
    /// Returns an error if agents list is empty.
    pub fn new(name: impl Into<String>, agents: Vec<Arc<dyn Agent>>) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "Sequential agent requires at least one agent".to_string(),
            ));
        }

        Ok(Self {
            name: name.into(),
            agents,
        })
    }

    /// Get the list of agents in the sequence.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }
}

#[async_trait]
impl Agent for SequentialAgent {
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
        capabilities.push("sequential".to_string());

        capabilities
    }

    /// Execute all agents in sequence.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Output message from the last agent in the sequence
    ///
    /// # Errors
    ///
    /// Returns an error if any agent in the sequence fails.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut current = message;

        for (i, agent) in self.agents.iter().enumerate() {
            match agent.process(current).await {
                Ok(result) => {
                    current = result;
                }
                Err(err) => {
                    return Err(AgentError::ProcessingError(format!(
                        "Step {} ({}) failed: {}",
                        i + 1,
                        agent.name(),
                        err
                    )));
                }
            }
        }

        Ok(current)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct EchoAgent {
        name: String,
        prefix: String,
    }

    #[async_trait]
    impl Agent for EchoAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["echo".to_string()]
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            let content = message.content_as_str().unwrap_or("");
            let new_content = format!("{}{}", self.prefix, content);
            Ok(Message::with_text("agent", new_content))
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
    async fn test_sequential_execution() {
        let agent1 = Arc::new(EchoAgent {
            name: "agent1".to_string(),
            prefix: "A:".to_string(),
        });
        let agent2 = Arc::new(EchoAgent {
            name: "agent2".to_string(),
            prefix: "B:".to_string(),
        });
        let agent3 = Arc::new(EchoAgent {
            name: "agent3".to_string(),
            prefix: "C:".to_string(),
        });

        let sequential = SequentialAgent::new("pipeline", vec![agent1, agent2, agent3]).unwrap();

        let input = Message::with_text("user", "test");
        let result = sequential.process(input).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "C:B:A:test");
    }

    #[tokio::test]
    async fn test_sequential_empty_agents() {
        let result = SequentialAgent::new("test", vec![]);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_sequential_error_propagation() {
        let agent1 = Arc::new(EchoAgent {
            name: "agent1".to_string(),
            prefix: "A:".to_string(),
        });
        let agent2 = Arc::new(ErrorAgent {
            name: "error-agent".to_string(),
        });
        let agent3 = Arc::new(EchoAgent {
            name: "agent3".to_string(),
            prefix: "C:".to_string(),
        });

        let sequential = SequentialAgent::new("pipeline", vec![agent1, agent2, agent3]).unwrap();

        let input = Message::with_text("user", "test");
        let result = sequential.process(input).await;

        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(err_msg.contains("Step 2"));
        assert!(err_msg.contains("error-agent"));
    }

    #[tokio::test]
    async fn test_sequential_capabilities() {
        let agent1 = Arc::new(EchoAgent {
            name: "agent1".to_string(),
            prefix: "A:".to_string(),
        });
        let agent2 = Arc::new(EchoAgent {
            name: "agent2".to_string(),
            prefix: "B:".to_string(),
        });

        let sequential = SequentialAgent::new("pipeline", vec![agent1, agent2]).unwrap();

        let capabilities = sequential.capabilities();
        assert!(capabilities.contains(&"echo".to_string()));
        assert!(capabilities.contains(&"sequential".to_string()));
    }
}
