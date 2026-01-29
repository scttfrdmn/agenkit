///! Fallback agent composition pattern.
///!
///! Tries agents in order until one succeeds.
///! This implements the Fallback/Retry pattern for reliability.

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use serde_json::json;
use std::sync::Arc;

/// Agent that tries agents in order until one succeeds.
///
/// This is useful for building fault-tolerant systems where you want
/// to try multiple agents as fallbacks.
///
/// # Example
///
/// ```no_run
/// use agenkit::composition::FallbackAgent;
/// use agenkit::core::{Agent, Message};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let primary: Arc<dyn Agent> = todo!();
/// # let secondary: Arc<dyn Agent> = todo!();
/// # let last_resort: Arc<dyn Agent> = todo!();
/// let fallback = FallbackAgent::new(
///     "reliable",
///     vec![primary, secondary, last_resort]
/// )?;
///
/// let message = Message::with_text("user", "Process this");
/// let result = fallback.process(message).await?;
/// # Ok(())
/// # }
/// ```
pub struct FallbackAgent {
    name: String,
    agents: Vec<Arc<dyn Agent>>,
}

impl FallbackAgent {
    /// Create a new fallback agent.
    ///
    /// # Arguments
    ///
    /// * `name` - Name of this fallback agent
    /// * `agents` - List of agents to try in order
    ///
    /// # Errors
    ///
    /// Returns an error if agents list is empty.
    pub fn new(name: impl Into<String>, agents: Vec<Arc<dyn Agent>>) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "Fallback agent requires at least one agent".to_string(),
            ));
        }

        Ok(Self {
            name: name.into(),
            agents,
        })
    }

    /// Get the list of fallback agents.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }
}

#[async_trait]
impl Agent for FallbackAgent {
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
        capabilities.push("fallback".to_string());

        capabilities
    }

    /// Try each agent in order until one succeeds.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Response from the first successful agent
    ///
    /// # Errors
    ///
    /// Returns an error if all agents fail.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut errors = Vec::new();

        for (i, agent) in self.agents.iter().enumerate() {
            match agent.process(message.clone()).await {
                Ok(mut result) => {
                    // Success! Add metadata about which agent was used
                    result
                        .metadata
                        .insert("fallback_agent_used".to_string(), json!(agent.name()));
                    result
                        .metadata
                        .insert("fallback_attempt".to_string(), json!(i + 1));
                    return Ok(result);
                }
                Err(err) => {
                    errors.push(format!("agent {} ({}): {}", i + 1, agent.name(), err));
                }
            }
        }

        // All agents failed
        Err(AgentError::ProcessingError(format!(
            "All {} agents failed: {}",
            self.agents.len(),
            errors.join("; ")
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agents for testing
    struct ReliableAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for ReliableAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["reliable".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text(
                "agent",
                format!("Processed by {}", self.name),
            ))
        }
    }

    struct UnreliableAgent {
        name: String,
        should_fail: bool,
    }

    #[async_trait]
    impl Agent for UnreliableAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["unreliable".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            if self.should_fail {
                Err(AgentError::ProcessingError(format!(
                    "{} failed",
                    self.name
                )))
            } else {
                Ok(Message::with_text(
                    "agent",
                    format!("Processed by {}", self.name),
                ))
            }
        }
    }

    #[tokio::test]
    async fn test_fallback_first_success() {
        let primary = Arc::new(ReliableAgent {
            name: "primary".to_string(),
        });
        let secondary = Arc::new(ReliableAgent {
            name: "secondary".to_string(),
        });

        let fallback = FallbackAgent::new("reliable", vec![primary, secondary]).unwrap();

        let input = Message::with_text("user", "test");
        let result = fallback.process(input).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "Processed by primary");
        assert_eq!(
            result.metadata.get("fallback_agent_used").unwrap(),
            "primary"
        );
        assert_eq!(result.metadata.get("fallback_attempt").unwrap(), 1);
    }

    #[tokio::test]
    async fn test_fallback_to_secondary() {
        let primary = Arc::new(UnreliableAgent {
            name: "primary".to_string(),
            should_fail: true,
        });
        let secondary = Arc::new(ReliableAgent {
            name: "secondary".to_string(),
        });

        let fallback = FallbackAgent::new("reliable", vec![primary, secondary]).unwrap();

        let input = Message::with_text("user", "test");
        let result = fallback.process(input).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "Processed by secondary");
        assert_eq!(
            result.metadata.get("fallback_agent_used").unwrap(),
            "secondary"
        );
        assert_eq!(result.metadata.get("fallback_attempt").unwrap(), 2);
    }

    #[tokio::test]
    async fn test_fallback_all_fail() {
        let agent1 = Arc::new(UnreliableAgent {
            name: "agent1".to_string(),
            should_fail: true,
        });
        let agent2 = Arc::new(UnreliableAgent {
            name: "agent2".to_string(),
            should_fail: true,
        });

        let fallback = FallbackAgent::new("failing", vec![agent1, agent2]).unwrap();

        let input = Message::with_text("user", "test");
        let result = fallback.process(input).await;

        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(err_msg.contains("All 2 agents failed"));
    }

    #[tokio::test]
    async fn test_fallback_empty_agents() {
        let result = FallbackAgent::new("test", vec![]);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_fallback_capabilities() {
        let agent1 = Arc::new(ReliableAgent {
            name: "agent1".to_string(),
        });
        let agent2 = Arc::new(UnreliableAgent {
            name: "agent2".to_string(),
            should_fail: false,
        });

        let fallback = FallbackAgent::new("reliable", vec![agent1, agent2]).unwrap();

        let capabilities = fallback.capabilities();
        assert!(capabilities.contains(&"reliable".to_string()));
        assert!(capabilities.contains(&"unreliable".to_string()));
        assert!(capabilities.contains(&"fallback".to_string()));
    }
}
