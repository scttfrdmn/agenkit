//! Orchestration Patterns for Agent Composition
//!
//! Core orchestration patterns for composing agents:
//! - **Sequential**: Execute agents one after another (pipeline)
//! - **Parallel**: Execute agents concurrently (fan-out)
//!
//! # Design Principles
//!
//! - Simple, obvious implementations
//! - No magic, no surprises
//! - Composable (patterns can contain patterns)
//! - Observable (hooks for monitoring)
//!
//! # Examples
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{SequentialPattern, ParallelPattern};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let agent1: Arc<dyn Agent> = todo!();
//! # let agent2: Arc<dyn Agent> = todo!();
//! # let agent3: Arc<dyn Agent> = todo!();
//! // Sequential: agent1 → agent2 → agent3
//! let pipeline = SequentialPattern::new(vec![agent1, agent2, agent3])?;
//! let message = Message::with_text("user", "input");
//! let result = pipeline.process(message).await?;
//!
//! # let agent_a: Arc<dyn Agent> = todo!();
//! # let agent_b: Arc<dyn Agent> = todo!();
//! # let agent_c: Arc<dyn Agent> = todo!();
//! // Parallel: all agents receive same input, results aggregated
//! let parallel = ParallelPattern::new(vec![agent_a, agent_b, agent_c])?;
//! let message = Message::with_text("user", "input");
//! let result = parallel.process(message).await?;
//! # Ok(())
//! # }
//! ```

use async_trait::async_trait;
use futures::future::join_all;
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};

/// Execute agents sequentially - output of one becomes input of next.
///
/// This is the simplest and most common pattern: agent1 → agent2 → agent3
///
/// # Performance Characteristics
///
/// - No overhead vs calling agents directly
/// - Agents execute in order (no parallelism)
/// - Short-circuits on error (stops at first failure)
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::SequentialPattern;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent1: Arc<dyn Agent> = todo!();
/// # let agent2: Arc<dyn Agent> = todo!();
/// # let agent3: Arc<dyn Agent> = todo!();
/// let pipeline = SequentialPattern::new(vec![agent1, agent2, agent3])?;
/// let result = pipeline.process(Message::with_text("user", "input")).await?;
/// # Ok(())
/// # }
/// ```
pub struct SequentialPattern {
    agents: Vec<Arc<dyn Agent>>,
    pattern_name: String,
}

impl SequentialPattern {
    /// Creates a new sequential execution pattern.
    ///
    /// # Arguments
    ///
    /// * `agents` - List of agents to execute in order
    ///
    /// # Errors
    ///
    /// Returns an error if agents list is empty.
    pub fn new(agents: Vec<Arc<dyn Agent>>) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "Sequential pattern requires at least one agent".to_string(),
            ));
        }

        Ok(Self {
            agents,
            pattern_name: "sequential".to_string(),
        })
    }

    /// Creates a new sequential pattern with custom name.
    pub fn with_name(agents: Vec<Arc<dyn Agent>>, name: impl Into<String>) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "Sequential pattern requires at least one agent".to_string(),
            ));
        }

        Ok(Self {
            agents,
            pattern_name: name.into(),
        })
    }

    /// Get the underlying agents list.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }
}

#[async_trait]
impl Agent for SequentialPattern {
    fn name(&self) -> &str {
        &self.pattern_name
    }

    fn capabilities(&self) -> Vec<String> {
        // Combined capabilities of all agents
        let mut caps = std::collections::HashSet::new();
        for agent in &self.agents {
            for cap in agent.capabilities() {
                caps.insert(cap);
            }
        }
        caps.into_iter().collect()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut current = message;

        for agent in &self.agents {
            current = agent.process(current).await?;
        }

        Ok(current)
    }
}

/// Execute agents in parallel and aggregate results.
///
/// All agents receive the same input, execute concurrently, results are combined.
///
/// # Performance Characteristics
///
/// - True parallelism (uses tokio join/futures)
/// - Bounded by slowest agent
/// - Memory: O(n) where n = number of agents
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::ParallelPattern;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent1: Arc<dyn Agent> = todo!();
/// # let agent2: Arc<dyn Agent> = todo!();
/// # let agent3: Arc<dyn Agent> = todo!();
/// let parallel = ParallelPattern::new(vec![agent1, agent2, agent3])?;
/// let result = parallel.process(Message::with_text("user", "input")).await?;
/// # Ok(())
/// # }
/// ```
pub struct ParallelPattern {
    agents: Vec<Arc<dyn Agent>>,
    pattern_name: String,
}

impl ParallelPattern {
    /// Creates a new parallel execution pattern.
    ///
    /// Uses default aggregation strategy (returns first result with all results in metadata).
    ///
    /// # Arguments
    ///
    /// * `agents` - List of agents to execute concurrently
    ///
    /// # Errors
    ///
    /// Returns an error if agents list is empty.
    pub fn new(agents: Vec<Arc<dyn Agent>>) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "Parallel pattern requires at least one agent".to_string(),
            ));
        }

        Ok(Self {
            agents,
            pattern_name: "parallel".to_string(),
        })
    }

    /// Creates a new parallel pattern with custom name.
    pub fn with_name(agents: Vec<Arc<dyn Agent>>, name: impl Into<String>) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "Parallel pattern requires at least one agent".to_string(),
            ));
        }

        Ok(Self {
            agents,
            pattern_name: name.into(),
        })
    }

    /// Get the underlying agents list.
    pub fn agents(&self) -> &[Arc<dyn Agent>] {
        &self.agents
    }

    /// Default aggregation: combine all content into metadata, return first.
    fn default_aggregator(messages: Vec<Message>) -> Result<Message, AgentError> {
        if messages.is_empty() {
            return Err(AgentError::ProcessingError(
                "No messages to aggregate".to_string(),
            ));
        }

        let first = messages[0].clone();

        // Put all results in metadata for inspection
        let all_results: Vec<serde_json::Value> = messages
            .iter()
            .map(|msg| {
                serde_json::json!({
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.metadata
                })
            })
            .collect();

        let mut metadata = first.metadata.clone();
        metadata.insert(
            "parallel_results".to_string(),
            serde_json::Value::Array(all_results),
        );

        Ok(Message {
            role: first.role,
            content: first.content,
            metadata,
            timestamp: first.timestamp,
        })
    }
}

#[async_trait]
impl Agent for ParallelPattern {
    fn name(&self) -> &str {
        &self.pattern_name
    }

    fn capabilities(&self) -> Vec<String> {
        // Combined capabilities of all agents
        let mut caps = std::collections::HashSet::new();
        for agent in &self.agents {
            for cap in agent.capabilities() {
                caps.insert(cap);
            }
        }
        caps.into_iter().collect()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Execute all agents concurrently using futures::join_all (works in both native and WASM)
        let futures: Vec<_> = self
            .agents
            .iter()
            .map(|agent| {
                let msg = message.clone();
                let agent = agent.clone();
                async move { agent.process(msg).await }
            })
            .collect();

        let results: Vec<Result<Message, AgentError>> = join_all(futures).await;

        // Convert to Vec<Message>, short-circuit on first error
        let mut messages = Vec::new();
        for result in results {
            messages.push(result?);
        }

        // Aggregate results
        Self::default_aggregator(messages)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    // Mock agent for testing
    struct MockAgent {
        agent_name: String,
        call_count: Arc<AtomicUsize>,
        prefix: String,
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            &self.agent_name
        }

        fn capabilities(&self) -> Vec<String> {
            vec![format!("cap_{}", self.agent_name)]
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            self.call_count.fetch_add(1, Ordering::SeqCst);
            let content = message.content_as_str().unwrap_or("");
            let new_content = format!("{}{}", self.prefix, content);
            Ok(Message::with_text("assistant", new_content))
        }
    }

    #[tokio::test]
    async fn test_sequential_basic() {
        let agent1 = Arc::new(MockAgent {
            agent_name: "agent1".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "A:".to_string(),
        });

        let agent2 = Arc::new(MockAgent {
            agent_name: "agent2".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "B:".to_string(),
        });

        let agent3 = Arc::new(MockAgent {
            agent_name: "agent3".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "C:".to_string(),
        });

        let pipeline = SequentialPattern::new(vec![agent1, agent2, agent3]).unwrap();

        assert_eq!(pipeline.name(), "sequential");

        let message = Message::with_text("user", "input");
        let result = pipeline.process(message).await.unwrap();

        // Sequential: input -> A:input -> B:A:input -> C:B:A:input
        assert_eq!(result.content_as_str().unwrap(), "C:B:A:input");
    }

    #[tokio::test]
    async fn test_sequential_empty_agents() {
        let result = SequentialPattern::new(vec![]);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_sequential_capabilities() {
        let agent1 = Arc::new(MockAgent {
            agent_name: "agent1".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "A:".to_string(),
        });

        let agent2 = Arc::new(MockAgent {
            agent_name: "agent2".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "B:".to_string(),
        });

        let pipeline = SequentialPattern::new(vec![agent1, agent2]).unwrap();

        let caps = pipeline.capabilities();
        assert!(caps.contains(&"cap_agent1".to_string()));
        assert!(caps.contains(&"cap_agent2".to_string()));
    }

    #[tokio::test]
    async fn test_parallel_basic() {
        let agent1 = Arc::new(MockAgent {
            agent_name: "agent1".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "A:".to_string(),
        });

        let agent2 = Arc::new(MockAgent {
            agent_name: "agent2".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "B:".to_string(),
        });

        let agent3 = Arc::new(MockAgent {
            agent_name: "agent3".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "C:".to_string(),
        });

        let parallel = ParallelPattern::new(vec![agent1, agent2, agent3]).unwrap();

        assert_eq!(parallel.name(), "parallel");

        let message = Message::with_text("user", "input");
        let result = parallel.process(message).await.unwrap();

        // Parallel: all agents get "input", first result is returned
        assert_eq!(result.content_as_str().unwrap(), "A:input");

        // All results should be in metadata
        let parallel_results = result.metadata.get("parallel_results").unwrap();
        assert!(parallel_results.is_array());
        let results_array = parallel_results.as_array().unwrap();
        assert_eq!(results_array.len(), 3);
    }

    #[tokio::test]
    async fn test_parallel_empty_agents() {
        let result = ParallelPattern::new(vec![]);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_parallel_capabilities() {
        let agent1 = Arc::new(MockAgent {
            agent_name: "agent1".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "A:".to_string(),
        });

        let agent2 = Arc::new(MockAgent {
            agent_name: "agent2".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "B:".to_string(),
        });

        let parallel = ParallelPattern::new(vec![agent1, agent2]).unwrap();

        let caps = parallel.capabilities();
        assert!(caps.contains(&"cap_agent1".to_string()));
        assert!(caps.contains(&"cap_agent2".to_string()));
    }

    #[tokio::test]
    async fn test_sequential_single_agent() {
        let agent1 = Arc::new(MockAgent {
            agent_name: "agent1".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "A:".to_string(),
        });

        let pipeline = SequentialPattern::new(vec![agent1]).unwrap();

        let message = Message::with_text("user", "input");
        let result = pipeline.process(message).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "A:input");
    }

    #[tokio::test]
    async fn test_parallel_single_agent() {
        let agent1 = Arc::new(MockAgent {
            agent_name: "agent1".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            prefix: "A:".to_string(),
        });

        let parallel = ParallelPattern::new(vec![agent1]).unwrap();

        let message = Message::with_text("user", "input");
        let result = parallel.process(message).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "A:input");
    }
}
