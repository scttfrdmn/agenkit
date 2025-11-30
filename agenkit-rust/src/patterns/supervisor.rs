//! Supervisor Pattern - Hierarchical Agent Coordination
//!
//! Implements hierarchical coordination where a central supervisor agent plans
//! task decomposition, delegates to specialist agents, and synthesizes their
//! results into a final response.
//!
//! # Key Concepts
//!
//! - **Central planner**: Supervisor for coordination and planning
//! - **Specialist agents**: Domain-specific agents for specific tasks
//! - **Task decomposition**: Breaking complex tasks into subtasks
//! - **Result synthesis**: Combining specialist outputs into final response
//!
//! # Use Cases
//!
//! - Software development: planner coordinates coder, tester, reviewer
//! - Research: planner coordinates searcher, analyzer, writer
//! - Data processing: planner coordinates extractor, transformer, validator
//! - Customer service: planner coordinates billing, technical, account specialists
//!
//! # Performance Characteristics
//!
//! - **Time**: O(planning + max(specialist) + synthesis)
//! - **Memory**: O(n specialists * message size)
//! - Hierarchical execution model
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{SupervisorAgent, SimplePlanner};
//! use std::sync::Arc;
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let llm_agent: Arc<dyn Agent> = todo!();
//! # let coder: Arc<dyn Agent> = todo!();
//! # let tester: Arc<dyn Agent> = todo!();
//! # let reviewer: Arc<dyn Agent> = todo!();
//! let planner = SimplePlanner::new(llm_agent);
//! let mut specialists = HashMap::new();
//! specialists.insert("coder".to_string(), coder);
//! specialists.insert("tester".to_string(), tester);
//! specialists.insert("reviewer".to_string(), reviewer);
//!
//! let supervisor = SupervisorAgent::new(Arc::new(planner), specialists)?;
//! let result = supervisor.process(Message::with_text("user", "Build a feature")).await?;
//! # Ok(())
//! # }
//! ```

use std::collections::HashMap;
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};
use serde_json::json;

/// Subtask represents a decomposed task for a specialist agent.
#[derive(Debug, Clone)]
pub struct Subtask {
    /// Type identifies which specialist should handle this subtask
    pub subtask_type: String,
    /// Message is the input for the specialist
    pub message: Message,
    /// Metadata contains additional task information
    pub metadata: HashMap<String, serde_json::Value>,
}

impl Subtask {
    /// Create a new subtask.
    pub fn new(subtask_type: String, message: Message) -> Self {
        Self {
            subtask_type,
            message,
            metadata: HashMap::new(),
        }
    }

    /// Add metadata to the subtask.
    pub fn with_metadata(
        mut self,
        key: impl Into<String>,
        value: serde_json::Value,
    ) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

/// PlannerAgent is responsible for task decomposition and result synthesis.
///
/// The planner receives the initial message and breaks it down into subtasks
/// for specialist agents. After specialists complete their work, the planner
/// synthesizes their results into a final response.
#[async_trait::async_trait]
pub trait PlannerAgent: Agent {
    /// Plan decomposes a message into subtasks for specialists.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message to decompose
    ///
    /// # Returns
    ///
    /// List of subtasks for specialists to execute
    async fn plan(&self, message: &Message) -> Result<Vec<Subtask>, AgentError>;

    /// Synthesize combines specialist results into final response.
    ///
    /// # Arguments
    ///
    /// * `original` - Original input message
    /// * `results` - Map of specialist results keyed by specialist type
    ///
    /// # Returns
    ///
    /// Final synthesized response
    async fn synthesize(
        &self,
        original: &Message,
        results: HashMap<String, Message>,
    ) -> Result<Message, AgentError>;
}

/// Supervisor agent that coordinates specialist agents.
///
/// The supervisor uses a planner agent to decompose complex tasks into subtasks,
/// delegates each subtask to an appropriate specialist, and synthesizes the
/// specialist results into a coherent final response.
///
/// The supervisor pattern is ideal when tasks have clear domain boundaries
/// and benefit from specialized expertise.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{SupervisorAgent, SimplePlanner};
/// use std::sync::Arc;
/// use std::collections::HashMap;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let planner_agent: Arc<dyn Agent> = todo!();
/// # let extractor: Arc<dyn Agent> = todo!();
/// # let transformer: Arc<dyn Agent> = todo!();
/// # let validator: Arc<dyn Agent> = todo!();
/// let planner = SimplePlanner::new(planner_agent);
/// let mut specialists = HashMap::new();
/// specialists.insert("extractor".to_string(), extractor);
/// specialists.insert("transformer".to_string(), transformer);
/// specialists.insert("validator".to_string(), validator);
///
/// let supervisor = SupervisorAgent::new(Arc::new(planner), specialists)?;
/// let result = supervisor.process(Message::with_text("user", "Process data")).await?;
/// # Ok(())
/// # }
/// ```
pub struct SupervisorAgent {
    planner: Arc<dyn PlannerAgent>,
    specialists: HashMap<String, Arc<dyn Agent>>,
}

impl SupervisorAgent {
    /// Create a new supervisor agent.
    ///
    /// # Arguments
    ///
    /// * `planner` - Agent responsible for planning and synthesis
    /// * `specialists` - Map of specialist agents keyed by their domain/type
    ///
    /// The planner's plan method should return subtasks with type values that
    /// match keys in the specialists map.
    ///
    /// # Errors
    ///
    /// Returns an error if specialists map is empty.
    pub fn new(
        planner: Arc<dyn PlannerAgent>,
        specialists: HashMap<String, Arc<dyn Agent>>,
    ) -> Result<Self, AgentError> {
        if specialists.is_empty() {
            return Err(AgentError::InvalidInput(
                "at least one specialist is required".to_string(),
            ));
        }

        Ok(Self {
            planner,
            specialists,
        })
    }

    /// Get the planner agent.
    pub fn planner(&self) -> &Arc<dyn PlannerAgent> {
        &self.planner
    }

    /// Get the specialist agents.
    pub fn specialists(&self) -> &HashMap<String, Arc<dyn Agent>> {
        &self.specialists
    }
}

#[async_trait::async_trait]
impl Agent for SupervisorAgent {
    fn name(&self) -> &str {
        "SupervisorAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut cap_set = std::collections::HashSet::new();

        // Add planner capabilities
        for cap in self.planner.capabilities() {
            cap_set.insert(cap);
        }

        // Add specialist capabilities
        for specialist in self.specialists.values() {
            for cap in specialist.capabilities() {
                cap_set.insert(cap);
            }
        }

        let mut capabilities: Vec<String> = cap_set.into_iter().collect();
        capabilities.push("supervisor".to_string());
        capabilities.push("hierarchical".to_string());
        capabilities.push("coordination".to_string());

        capabilities
    }

    /// Execute the supervisor pattern: plan, delegate, synthesize.
    ///
    /// The process follows these steps:
    /// 1. Planning: Planner decomposes the task into subtasks
    /// 2. Delegation: Each subtask is routed to appropriate specialist
    /// 3. Execution: Specialists process their assigned subtasks
    /// 4. Synthesis: Planner combines specialist results into final response
    ///
    /// If any subtask references an unknown specialist type, an error is returned.
    /// If any specialist fails, the error is returned immediately.
    ///
    /// The final message includes metadata about the planning and delegation process.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Synthesized response from specialist results
    ///
    /// # Errors
    ///
    /// Returns an error if planning fails, specialist not found, specialist fails,
    /// or synthesis fails.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Step 1: Plan - decompose task into subtasks
        let subtasks = self.planner.plan(&message).await.map_err(|e| {
            AgentError::ProcessingError(format!("planning failed: {}", e))
        })?;

        if subtasks.is_empty() {
            // No subtasks - let planner handle directly
            return self.planner.process(message).await;
        }

        // Step 2: Validate specialist availability
        for (i, subtask) in subtasks.iter().enumerate() {
            if !self.specialists.contains_key(&subtask.subtask_type) {
                let available_types: Vec<_> = self.specialists.keys().cloned().collect();
                return Err(AgentError::ProcessingError(format!(
                    "subtask {} references unknown specialist type '{}' (available: {})",
                    i,
                    subtask.subtask_type,
                    available_types.join(", ")
                )));
            }
        }

        // Step 3: Execute subtasks with specialists
        let mut results = HashMap::new();
        let mut execution_order = Vec::with_capacity(subtasks.len());

        for (i, subtask) in subtasks.iter().enumerate() {
            let specialist = &self.specialists[&subtask.subtask_type];

            // Execute subtask
            let result = specialist
                .process(subtask.message.clone())
                .await
                .map_err(|e| {
                    AgentError::ProcessingError(format!(
                        "specialist '{}' failed on subtask {}: {}",
                        subtask.subtask_type, i, e
                    ))
                })?;

            // Store result keyed by specialist type and index for synthesis
            let result_key = format!("{}_{}", subtask.subtask_type, i);
            results.insert(result_key, result);

            // Track execution order
            execution_order.push(json!({
                "index": i,
                "type": subtask.subtask_type,
                "specialist": specialist.name(),
            }));
        }

        // Step 4: Synthesize - combine specialist results
        let mut final_message = self
            .planner
            .synthesize(&message, results)
            .await
            .map_err(|e| AgentError::ProcessingError(format!("synthesis failed: {}", e)))?;

        // Add supervisor metadata
        final_message
            .metadata
            .insert("supervisor_subtasks".to_string(), json!(subtasks.len()));
        final_message.metadata.insert(
            "supervisor_specialists".to_string(),
            json!(self.specialists.len()),
        );
        final_message
            .metadata
            .insert("execution_order".to_string(), json!(execution_order));

        Ok(final_message)
    }
}

/// SimplePlanner provides a basic planner implementation.
///
/// This planner uses an LLM agent to handle both planning and synthesis.
/// For production use, consider implementing a custom PlannerAgent with
/// domain-specific planning and synthesis logic.
pub struct SimplePlanner {
    agent: Arc<dyn Agent>,
}

impl SimplePlanner {
    /// Create a basic planner using an LLM agent.
    pub fn new(agent: Arc<dyn Agent>) -> Self {
        Self { agent }
    }

    /// Get the underlying agent.
    pub fn agent(&self) -> &Arc<dyn Agent> {
        &self.agent
    }
}

#[async_trait::async_trait]
impl Agent for SimplePlanner {
    fn name(&self) -> &str {
        "SimplePlanner"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut caps = self.agent.capabilities();
        caps.push("planning".to_string());
        caps.push("synthesis".to_string());
        caps
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        self.agent.process(message).await
    }
}

#[async_trait::async_trait]
impl PlannerAgent for SimplePlanner {
    /// Plan uses the LLM to decompose tasks (simplified implementation).
    ///
    /// Note: This is a basic implementation. Production code should parse
    /// the LLM response and create proper Subtask structures.
    async fn plan(&self, _message: &Message) -> Result<Vec<Subtask>, AgentError> {
        // In a real implementation, this would prompt the LLM to create a plan
        // and parse the response into Subtask structures.
        // For now, return empty to trigger direct processing.
        Ok(Vec::new())
    }

    /// Synthesize combines specialist results (simplified implementation).
    async fn synthesize(
        &self,
        _original: &Message,
        results: HashMap<String, Message>,
    ) -> Result<Message, AgentError> {
        // Combine all results
        let mut combined = String::from("Synthesis of specialist results:\n\n");

        for (key, result) in results.iter() {
            combined.push_str(&format!(
                "Result from {}:\n{}\n\n",
                key,
                result.content_as_str().unwrap_or("")
            ));
        }

        Ok(Message::with_text("assistant", combined))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct MockAgent {
        name: String,
        prefix: String,
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
            let content = message.content_as_str().unwrap_or("");
            Ok(Message::with_text(
                "assistant",
                format!("{}:{}", self.prefix, content),
            ))
        }
    }

    // Mock planner for testing
    struct MockPlanner {
        agent: Arc<dyn Agent>,
        subtasks: Vec<Subtask>,
    }

    #[async_trait::async_trait]
    impl Agent for MockPlanner {
        fn name(&self) -> &str {
            "MockPlanner"
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            self.agent.process(message).await
        }
    }

    #[async_trait::async_trait]
    impl PlannerAgent for MockPlanner {
        async fn plan(&self, _message: &Message) -> Result<Vec<Subtask>, AgentError> {
            Ok(self.subtasks.clone())
        }

        async fn synthesize(
            &self,
            _original: &Message,
            results: HashMap<String, Message>,
        ) -> Result<Message, AgentError> {
            let mut combined = String::new();
            for (key, result) in results.iter() {
                if !combined.is_empty() {
                    combined.push_str(" | ");
                }
                combined.push_str(&format!("{}={}", key, result.content_as_str().unwrap_or("")));
            }
            Ok(Message::with_text("assistant", combined))
        }
    }

    #[tokio::test]
    async fn test_supervisor_basic() {
        let base_agent = Arc::new(MockAgent {
            name: "base".to_string(),
            prefix: "BASE".to_string(),
        });

        let specialist1 = Arc::new(MockAgent {
            name: "spec1".to_string(),
            prefix: "S1".to_string(),
        });

        let specialist2 = Arc::new(MockAgent {
            name: "spec2".to_string(),
            prefix: "S2".to_string(),
        });

        let mut specialists = HashMap::new();
        specialists.insert("type1".to_string(), specialist1 as Arc<dyn Agent>);
        specialists.insert("type2".to_string(), specialist2 as Arc<dyn Agent>);

        let subtasks = vec![
            Subtask::new("type1".to_string(), Message::with_text("user", "task1")),
            Subtask::new("type2".to_string(), Message::with_text("user", "task2")),
        ];

        let planner = Arc::new(MockPlanner {
            agent: base_agent,
            subtasks,
        });

        let supervisor = SupervisorAgent::new(planner, specialists).unwrap();

        let message = Message::with_text("user", "complex task");
        let result = supervisor.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("type1_0=S1:task1"));
        assert!(content.contains("type2_1=S2:task2"));

        assert_eq!(result.metadata.get("supervisor_subtasks"), Some(&json!(2)));
    }

    #[tokio::test]
    async fn test_supervisor_unknown_specialist() {
        let base_agent = Arc::new(MockAgent {
            name: "base".to_string(),
            prefix: "BASE".to_string(),
        });

        let specialist1 = Arc::new(MockAgent {
            name: "spec1".to_string(),
            prefix: "S1".to_string(),
        });

        let mut specialists = HashMap::new();
        specialists.insert("type1".to_string(), specialist1 as Arc<dyn Agent>);

        let subtasks = vec![Subtask::new(
            "unknown_type".to_string(),
            Message::with_text("user", "task1"),
        )];

        let planner = Arc::new(MockPlanner {
            agent: base_agent,
            subtasks,
        });

        let supervisor = SupervisorAgent::new(planner, specialists).unwrap();

        let message = Message::with_text("user", "task");
        let result = supervisor.process(message).await;

        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("unknown specialist type"));
    }

    #[tokio::test]
    async fn test_supervisor_empty_specialists() {
        let base_agent = Arc::new(MockAgent {
            name: "base".to_string(),
            prefix: "BASE".to_string(),
        });

        let planner = Arc::new(MockPlanner {
            agent: base_agent,
            subtasks: vec![],
        });

        let result = SupervisorAgent::new(planner, HashMap::new());
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("at least one specialist"));
    }

    #[tokio::test]
    async fn test_simple_planner() {
        let agent = Arc::new(MockAgent {
            name: "llm".to_string(),
            prefix: "LLM".to_string(),
        });

        let planner = SimplePlanner::new(agent);

        let caps = planner.capabilities();
        assert!(caps.contains(&"planning".to_string()));
        assert!(caps.contains(&"synthesis".to_string()));

        // Test direct processing (no subtasks)
        let message = Message::with_text("user", "test");
        let result = planner.process(message).await.unwrap();
        assert_eq!(result.content_as_str(), Some("LLM:test"));

        // Test synthesis
        let mut results = HashMap::new();
        results.insert(
            "spec1".to_string(),
            Message::with_text("assistant", "result1"),
        );
        results.insert(
            "spec2".to_string(),
            Message::with_text("assistant", "result2"),
        );

        let synthesized = planner
            .synthesize(&Message::with_text("user", "orig"), results)
            .await
            .unwrap();

        let content = synthesized.content_as_str().unwrap();
        assert!(content.contains("Synthesis"));
        assert!(content.contains("result1"));
        assert!(content.contains("result2"));
    }
}
