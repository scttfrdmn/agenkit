//! Fallback Pattern - Sequential Retry with Error Recovery
//!
//! Implements sequential retry across multiple agents. If one agent fails,
//! the next agent is tried until one succeeds or all agents are exhausted.
//!
//! # Key Concepts
//!
//! - **Sequential attempts**: Agents tried in order
//! - **Automatic failover**: Next agent tried on errors
//! - **First success wins**: First successful result returned
//! - **Error collection**: All failures tracked for debugging
//!
//! # Use Cases
//!
//! - High availability: fallback from primary to backup systems
//! - Multi-provider: try different LLM providers until one succeeds
//! - Graceful degradation: try advanced model, fallback to simple model
//! - Retry with alternatives: different strategies for same task
//! - Error recovery: fallback to cached/default responses
//!
//! # Performance Characteristics
//!
//! - **Best case**: O(first agent) - immediate success
//! - **Worst case**: O(sum of all agents) - all fail
//! - Early termination on first success
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::FallbackAgent;
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let primary_llm: Arc<dyn Agent> = todo!();
//! # let backup_llm: Arc<dyn Agent> = todo!();
//! # let simple_llm: Arc<dyn Agent> = todo!();
//! let agents = vec![primary_llm, backup_llm, simple_llm];
//! let fallback = FallbackAgent::new(agents)?;
//!
//! let result = fallback.process(Message::with_text("user", "Generate response")).await?;
//! // Tries primary, falls back to backup, then simple if needed
//! # Ok(())
//! # }
//! ```

use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};
use serde_json::json;

/// Fallback agent that tries agents in sequence until one succeeds.
///
/// Each agent is attempted in order. The first agent to return a successful
/// response wins, and that response is returned immediately. If an agent
/// fails, the next agent is tried. If all agents fail, an error combining
/// all failure reasons is returned.
///
/// The fallback pattern is ideal when you need resilience and have
/// multiple ways to accomplish the same task.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::FallbackAgent;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let advanced_model: Arc<dyn Agent> = todo!();
/// # let standard_model: Arc<dyn Agent> = todo!();
/// # let simple_model: Arc<dyn Agent> = todo!();
/// let agents = vec![advanced_model, standard_model, simple_model];
/// let fallback = FallbackAgent::new(agents)?;
///
/// let input = Message::with_text("user", "Complex query");
/// let output = fallback.process(input).await?;
/// // Graceful degradation from advanced to simple models
/// # Ok(())
/// # }
/// ```
pub struct FallbackAgent {
    agents: Vec<Arc<dyn Agent>>,
}

impl FallbackAgent {
    /// Create a new fallback agent.
    ///
    /// # Arguments
    ///
    /// * `agents` - List of agents to try in order (must have at least one)
    ///
    /// Agents are tried in the order provided. The first successful response
    /// is returned immediately without trying remaining agents.
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

    /// Get the agents in the fallback chain.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }
}

#[async_trait::async_trait]
impl Agent for FallbackAgent {
    fn name(&self) -> &str {
        "FallbackAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut cap_set = std::collections::HashSet::new();

        for agent in &self.agents {
            for cap in agent.capabilities() {
                cap_set.insert(cap);
            }
        }

        let mut capabilities: Vec<String> = cap_set.into_iter().collect();
        capabilities.push("fallback".to_string());
        capabilities.push("retry".to_string());
        capabilities.push("high-availability".to_string());

        capabilities
    }

    /// Try agents sequentially until one succeeds.
    ///
    /// Each agent is attempted in order. If an agent succeeds, its response
    /// is returned immediately with metadata about the attempt. If an agent
    /// fails, the next agent is tried.
    ///
    /// If all agents fail, an error is returned that includes information
    /// about all failed attempts.
    ///
    /// The successful message includes metadata about:
    /// - Which agent succeeded
    /// - How many attempts were made
    /// - Which agents were tried
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
        let mut failed_attempts = Vec::new();

        for (i, agent) in self.agents.iter().enumerate() {
            // Try agent
            match agent.process(message.clone()).await {
                Ok(mut result) => {
                    // Success! Add metadata and return
                    result
                        .metadata
                        .insert("fallback_attempts".to_string(), json!(i + 1));
                    result
                        .metadata
                        .insert("fallback_success_index".to_string(), json!(i));
                    result
                        .metadata
                        .insert("fallback_success_agent".to_string(), json!(agent.name()));
                    result
                        .metadata
                        .insert("fallback_total_agents".to_string(), json!(self.agents.len()));

                    // Include failed attempts for observability
                    if !failed_attempts.is_empty() {
                        result.metadata.insert(
                            "fallback_failed_attempts".to_string(),
                            json!(failed_attempts),
                        );
                    }

                    return Ok(result);
                }
                Err(err) => {
                    // Agent failed, record and try next
                    failed_attempts.push(json!({
                        "index": i,
                        "agent": agent.name(),
                        "error": err.to_string(),
                    }));
                }
            }
        }

        // All agents failed
        let mut error_msg = format!("all {} agents failed:\n", failed_attempts.len());
        for attempt in &failed_attempts {
            if let Some(obj) = attempt.as_object() {
                error_msg.push_str(&format!(
                    "  [{}] {}: {}\n",
                    obj.get("index").and_then(|v| v.as_i64()).unwrap_or(0),
                    obj.get("agent").and_then(|v| v.as_str()).unwrap_or("unknown"),
                    obj.get("error").and_then(|v| v.as_str()).unwrap_or("unknown error")
                ));
            }
        }

        Err(AgentError::ProcessingError(error_msg))
    }
}

/// Function type for recovery from agent failures.
///
/// The function receives the original message and error, and should return
/// a fallback response or propagate the error.
pub type RecoveryFunc = Box<dyn Fn(Message, AgentError) -> Result<Message, AgentError> + Send + Sync>;

/// Recovery agent that wraps an agent with a recovery function.
///
/// The recovery agent tries the primary agent first. If it fails, the
/// recovery function is called to provide a fallback response.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message, AgentError};
/// use agenkit::patterns::{RecoveryAgent, DefaultRecovery};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let primary: Arc<dyn Agent> = todo!();
/// let recovery = RecoveryAgent::new(
///     primary,
///     DefaultRecovery::static_message("Service temporarily unavailable".to_string())
/// );
///
/// let result = recovery.process(Message::with_text("user", "Request")).await?;
/// # Ok(())
/// # }
/// ```
pub struct RecoveryAgent {
    agent: Arc<dyn Agent>,
    recovery_func: RecoveryFunc,
}

impl RecoveryAgent {
    /// Create a recovery agent with custom recovery logic.
    ///
    /// # Arguments
    ///
    /// * `agent` - Primary agent to try first
    /// * `recovery_func` - Function to call if agent fails
    pub fn new(agent: Arc<dyn Agent>, recovery_func: RecoveryFunc) -> Self {
        Self {
            agent,
            recovery_func,
        }
    }

    /// Get the underlying agent.
    pub fn agent(&self) -> &Arc<dyn Agent> {
        &self.agent
    }
}

#[async_trait::async_trait]
impl Agent for RecoveryAgent {
    fn name(&self) -> &str {
        "RecoveryAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut caps = self.agent.capabilities();
        caps.push("recovery".to_string());
        caps.push("error-handling".to_string());
        caps
    }

    /// Execute the agent with recovery on failure.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Response from primary agent or recovery function
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        match self.agent.process(message.clone()).await {
            Ok(result) => Ok(result),
            Err(err) => {
                // Primary agent failed, try recovery
                let mut recovered = (self.recovery_func)(message, err.clone())?;

                // Add recovery metadata
                recovered
                    .metadata
                    .insert("recovery_used".to_string(), json!(true));
                recovered
                    .metadata
                    .insert("original_error".to_string(), json!(err.to_string()));

                Ok(recovered)
            }
        }
    }
}

/// Default recovery strategies.
pub struct DefaultRecovery;

impl DefaultRecovery {
    /// Returns a fixed fallback message.
    pub fn static_message(message: String) -> RecoveryFunc {
        Box::new(move |_msg: Message, _err: AgentError| {
            Ok(Message::with_text("assistant", message.clone()))
        })
    }

    /// Returns an empty but valid response.
    pub fn empty_response() -> RecoveryFunc {
        Box::new(|_msg: Message, _err: AgentError| Ok(Message::with_text("assistant", "")))
    }

    /// Propagates the original error.
    pub fn propagate_error() -> RecoveryFunc {
        Box::new(|_msg: Message, err: AgentError| Err(err))
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
    async fn test_fallback_first_success() {
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

        let fallback = FallbackAgent::new(vec![agent1, agent2]).unwrap();

        let message = Message::with_text("user", "input");
        let result = fallback.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("Response 1"));
        assert_eq!(result.metadata.get("fallback_attempts"), Some(&json!(1)));
        assert_eq!(result.metadata.get("fallback_success_index"), Some(&json!(0)));
    }

    #[tokio::test]
    async fn test_fallback_second_success() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "".to_string(),
            fail: true,
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

        let fallback = FallbackAgent::new(vec![agent1, agent2, agent3]).unwrap();

        let message = Message::with_text("user", "input");
        let result = fallback.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("Response 2"));
        assert_eq!(result.metadata.get("fallback_attempts"), Some(&json!(2)));
        assert_eq!(result.metadata.get("fallback_success_index"), Some(&json!(1)));
        assert!(result.metadata.contains_key("fallback_failed_attempts"));
    }

    #[tokio::test]
    async fn test_fallback_all_fail() {
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

        let fallback = FallbackAgent::new(vec![agent1, agent2]).unwrap();

        let message = Message::with_text("user", "input");
        let result = fallback.process(message).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("all 2 agents failed"));
        assert!(err.to_string().contains("agent1"));
        assert!(err.to_string().contains("agent2"));
    }

    #[tokio::test]
    async fn test_fallback_empty_agents() {
        let result = FallbackAgent::new(vec![]);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("at least one agent"));
    }

    #[tokio::test]
    async fn test_fallback_capabilities() {
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

        let fallback = FallbackAgent::new(vec![agent1, agent2]).unwrap();

        let caps = fallback.capabilities();
        assert!(caps.contains(&"agent1_capability".to_string()));
        assert!(caps.contains(&"agent2_capability".to_string()));
        assert!(caps.contains(&"fallback".to_string()));
        assert!(caps.contains(&"retry".to_string()));
        assert!(caps.contains(&"high-availability".to_string()));
    }

    #[tokio::test]
    async fn test_recovery_agent_success() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "Success".to_string(),
            fail: false,
        });

        let recovery = RecoveryAgent::new(
            agent,
            DefaultRecovery::static_message("Fallback".to_string()),
        );

        let message = Message::with_text("user", "test");
        let result = recovery.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("Success"));
        assert!(!result.metadata.contains_key("recovery_used"));
    }

    #[tokio::test]
    async fn test_recovery_agent_failure() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "".to_string(),
            fail: true,
        });

        let recovery = RecoveryAgent::new(
            agent,
            DefaultRecovery::static_message("Fallback response".to_string()),
        );

        let message = Message::with_text("user", "test");
        let result = recovery.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("Fallback response"));
        assert_eq!(result.metadata.get("recovery_used"), Some(&json!(true)));
        assert!(result.metadata.contains_key("original_error"));
    }

    #[tokio::test]
    async fn test_recovery_empty_response() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "".to_string(),
            fail: true,
        });

        let recovery = RecoveryAgent::new(agent, DefaultRecovery::empty_response());

        let message = Message::with_text("user", "test");
        let result = recovery.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some(""));
        assert_eq!(result.metadata.get("recovery_used"), Some(&json!(true)));
    }

    #[tokio::test]
    async fn test_recovery_propagate_error() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "".to_string(),
            fail: true,
        });

        let recovery = RecoveryAgent::new(agent, DefaultRecovery::propagate_error());

        let message = Message::with_text("user", "test");
        let result = recovery.process(message).await;

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("agent failed"));
    }

    #[tokio::test]
    async fn test_recovery_capabilities() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "response".to_string(),
            fail: false,
        });

        let recovery = RecoveryAgent::new(
            agent,
            DefaultRecovery::static_message("fallback".to_string()),
        );

        let caps = recovery.capabilities();
        assert!(caps.contains(&"recovery".to_string()));
        assert!(caps.contains(&"error-handling".to_string()));
    }
}
