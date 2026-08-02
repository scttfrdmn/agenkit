//! Multi-Agent Collaboration Pattern
//!
//! Enables multiple agents to work together on complex tasks through:
//! - **Coordination**: Agents working on different parts simultaneously
//! - **Delegation**: Agents delegating subtasks to specialists
//! - **Consensus**: Agents reaching agreement through discussion
//!
//! # Key Concepts
//!
//! - **Orchestration**: Coordinate multiple agents with different strategies
//! - **Sequential**: Execute agents one after another
//! - **Parallel**: Execute agents simultaneously
//! - **Delegation**: Main agent delegates to specialists
//! - **Consensus**: Combine perspectives from multiple agents
//!
//! # Use Cases
//!
//! - Complex tasks requiring diverse expertise
//! - Parallelizable workflows
//! - Problems benefiting from multiple perspectives
//! - Ensemble approaches for reliability
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{MultiAgentOrchestrator, OrchestrationStrategy};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let research_agent: Arc<dyn Agent> = todo!();
//! # let writing_agent: Arc<dyn Agent> = todo!();
//! let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
//! orchestrator.register_agent("researcher", research_agent);
//! orchestrator.register_agent("writer", writing_agent);
//!
//! let message = Message::with_text("user", "Write a research report");
//! let result = orchestrator.process(message).await?;
//! # Ok(())
//! # }
//! ```
//!
//! # References
//!
//! - Multi-agent systems
//! - Consensus mechanisms
//! - Ensemble learning

use std::collections::HashMap;
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};

#[cfg(test)]
use async_trait::async_trait;

/// Task execution status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum TaskStatus {
    /// Task not yet started
    Pending,
    /// Task currently executing
    InProgress,
    /// Task completed successfully
    Completed,
    /// Task failed with error
    Failed,
}

impl std::fmt::Display for TaskStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TaskStatus::Pending => write!(f, "pending"),
            TaskStatus::InProgress => write!(f, "in_progress"),
            TaskStatus::Completed => write!(f, "completed"),
            TaskStatus::Failed => write!(f, "failed"),
        }
    }
}

/// A task assigned to an agent.
#[derive(Debug, Clone)]
pub struct AgentTask {
    /// Name of the agent assigned to this task
    pub agent_name: String,
    /// Task description
    pub description: String,
    /// Task result (if completed)
    pub result: Option<String>,
    /// Current task status
    pub status: TaskStatus,
    /// Error message (if failed)
    pub error: Option<String>,
}

impl AgentTask {
    /// Create a new agent task.
    pub fn new(agent_name: String, description: String) -> Self {
        Self {
            agent_name,
            description,
            result: None,
            status: TaskStatus::Pending,
            error: None,
        }
    }
}

/// Orchestration strategy for coordinating multiple agents.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum OrchestrationStrategy {
    /// Execute agents one after another
    #[default]
    Sequential,
    /// Execute agents simultaneously
    Parallel,
    /// Main agent delegates to specialists
    Delegate,
}

/// Voting strategy for consensus building.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum VotingStrategy {
    /// Use majority vote
    #[default]
    Majority,
    /// Require unanimous agreement
    Unanimous,
    /// Use weighted voting
    Weighted,
}

/// Orchestrates multiple agents working together.
///
/// The MultiAgentOrchestrator coordinates multiple agents to work on tasks,
/// supporting different orchestration strategies:
///
/// - **Sequential**: Agents execute one after another
/// - **Parallel**: Agents execute simultaneously
/// - **Delegate**: Main agent delegates to specialists
///
/// # Use Cases
///
/// - Tasks requiring diverse expertise
/// - Work that can be parallelized
/// - Composing multiple agents
///
/// # Performance Characteristics
///
/// - Sequential: O(n) agents executed serially
/// - Parallel: O(1) agents executed concurrently
/// - Memory: O(n) for task history
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{MultiAgentOrchestrator, OrchestrationStrategy};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let research_agent: Arc<dyn Agent> = todo!();
/// # let writing_agent: Arc<dyn Agent> = todo!();
/// # let editor_agent: Arc<dyn Agent> = todo!();
/// let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
/// orchestrator.register_agent("researcher", research_agent);
/// orchestrator.register_agent("writer", writing_agent);
/// orchestrator.register_agent("editor", editor_agent);
///
/// let result = orchestrator.process(
///     Message::with_text("user", "Create a comprehensive report on AI")
/// ).await?;
/// // Each agent processes the message in sequence
/// # Ok(())
/// # }
/// ```
pub struct MultiAgentOrchestrator {
    agents: HashMap<String, Arc<dyn Agent>>,
    strategy: OrchestrationStrategy,
    tasks: Vec<AgentTask>,
}

impl MultiAgentOrchestrator {
    /// Create a new multi-agent orchestrator.
    ///
    /// # Arguments
    ///
    /// * `strategy` - Orchestration strategy to use
    pub fn new(strategy: OrchestrationStrategy) -> Self {
        Self {
            agents: HashMap::new(),
            strategy,
            tasks: Vec::new(),
        }
    }

    /// Get the orchestration strategy.
    pub fn strategy(&self) -> OrchestrationStrategy {
        self.strategy
    }

    /// Register an agent that can be used.
    ///
    /// # Arguments
    ///
    /// * `name` - Unique name for the agent
    /// * `agent` - Agent instance
    pub fn register_agent(&mut self, name: impl Into<String>, agent: Arc<dyn Agent>) {
        self.agents.insert(name.into(), agent);
    }

    /// Remove a registered agent.
    ///
    /// # Arguments
    ///
    /// * `name` - Name of the agent to remove
    pub fn unregister_agent(&mut self, name: &str) {
        self.agents.remove(name);
    }

    /// Get list of registered agent names.
    pub fn list_agents(&self) -> Vec<String> {
        self.agents.keys().cloned().collect()
    }

    /// Get all tasks that have been executed.
    pub fn get_tasks(&self) -> Vec<AgentTask> {
        self.tasks.clone()
    }

    /// Process message by coordinating multiple agents.
    ///
    /// Currently implements sequential strategy where all agents process
    /// the message one after another. Results are combined into a single
    /// response.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Combined response from all agents
    pub async fn process(&mut self, message: Message) -> Result<Message, AgentError> {
        let mut results = Vec::new();

        for (agent_name, agent) in &self.agents {
            let mut task = AgentTask::new(
                agent_name.clone(),
                message.content_as_str().unwrap_or("").to_string(),
            );
            task.status = TaskStatus::InProgress;
            self.tasks.push(task.clone());
            let task_idx = self.tasks.len() - 1;

            match agent.process(message.clone()).await {
                Ok(response) => {
                    let content = response.content_as_str().unwrap_or("");
                    self.tasks[task_idx].result = Some(content.to_string());
                    self.tasks[task_idx].status = TaskStatus::Completed;
                    results.push(format!("{}: {}", agent_name, content));
                }
                Err(e) => {
                    let error_msg = e.to_string();
                    self.tasks[task_idx].error = Some(error_msg.clone());
                    self.tasks[task_idx].status = TaskStatus::Failed;
                    results.push(format!("{}: Failed - {}", agent_name, error_msg));
                }
            }
        }

        let combined_result = results.join("\n\n");
        Ok(Message::with_text("assistant", combined_result))
    }
}

/// Reaches consensus among multiple agents.
///
/// The ConsensusAgent collects responses from multiple agents and combines
/// them into a single consensus response.
///
/// # Use Cases
///
/// - Getting multiple perspectives on a problem
/// - Validating decisions across multiple models
/// - Ensemble approaches to improve reliability
///
/// # Performance Characteristics
///
/// - O(n) agents executed sequentially
/// - Memory: O(n) for responses
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{ConsensusAgent, VotingStrategy};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let conservative_agent: Arc<dyn Agent> = todo!();
/// # let creative_agent: Arc<dyn Agent> = todo!();
/// # let analytical_agent: Arc<dyn Agent> = todo!();
/// let mut consensus = ConsensusAgent::new(VotingStrategy::Majority);
/// consensus.add_agent(conservative_agent);
/// consensus.add_agent(creative_agent);
/// consensus.add_agent(analytical_agent);
///
/// let result = consensus.process(
///     Message::with_text("user", "What's the best approach?")
/// ).await?;
/// // Result combines perspectives from all three agents
/// # Ok(())
/// # }
/// ```
pub struct ConsensusAgent {
    agents: Vec<Arc<dyn Agent>>,
    voting_strategy: VotingStrategy,
}

impl ConsensusAgent {
    /// Create a new consensus agent.
    ///
    /// # Arguments
    ///
    /// * `voting_strategy` - Strategy for reaching consensus
    pub fn new(voting_strategy: VotingStrategy) -> Self {
        Self {
            agents: Vec::new(),
            voting_strategy,
        }
    }

    /// Get the voting strategy.
    pub fn voting_strategy(&self) -> VotingStrategy {
        self.voting_strategy
    }

    /// Get the list of agents.
    pub fn agents(&self) -> Vec<Arc<dyn Agent>> {
        self.agents.clone()
    }

    /// Add an agent to the consensus group.
    ///
    /// # Arguments
    ///
    /// * `agent` - Agent to add
    pub fn add_agent(&mut self, agent: Arc<dyn Agent>) {
        self.agents.push(agent);
    }
}

#[async_trait::async_trait]
impl Agent for ConsensusAgent {
    fn name(&self) -> &str {
        "ConsensusAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        // Combine capabilities from all agents
        let mut caps = std::collections::HashSet::new();
        for agent in &self.agents {
            for cap in agent.capabilities() {
                caps.insert(cap);
            }
        }
        caps.into_iter().collect()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut responses = Vec::new();

        for agent in &self.agents {
            let response = agent.process(message.clone()).await?;
            responses.push(response.content_as_str().unwrap_or("").to_string());
        }

        // Simple consensus: combine all responses
        let mut consensus = format!("Consensus from {} agents:\n\n", responses.len());

        for (i, resp) in responses.iter().enumerate() {
            if i > 0 {
                consensus.push_str("\n\n");
            }
            consensus.push_str(&format!("Agent {}: {}", i + 1, resp));
        }

        Ok(Message::with_text("assistant", consensus))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    // Mock agent for testing
    struct MockAgent {
        name: String,
        response: String,
        fail: bool,
        call_count: Arc<AtomicUsize>,
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec![format!("{}_capability", self.name)]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let _ = self.call_count.fetch_add(1, Ordering::SeqCst);

            if self.fail {
                return Err(AgentError::ProcessingError(format!("{} failed", self.name)));
            }

            Ok(Message::with_text("assistant", &self.response))
        }
    }

    #[tokio::test]
    async fn test_orchestrator_basic() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "Response 1".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "Response 2".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
        orchestrator.register_agent("agent1", agent1);
        orchestrator.register_agent("agent2", agent2);

        let message = Message::with_text("user", "Test input");
        let result = orchestrator.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("agent1: Response 1"));
        assert!(content.contains("agent2: Response 2"));

        // Check tasks were recorded
        let tasks = orchestrator.get_tasks();
        assert_eq!(tasks.len(), 2);

        // Verify both tasks completed (HashMap iteration order not guaranteed)
        assert!(tasks.iter().all(|t| t.status == TaskStatus::Completed));
    }

    #[tokio::test]
    async fn test_orchestrator_with_failure() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "Response 1".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "".to_string(),
            fail: true,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
        orchestrator.register_agent("agent1", agent1);
        orchestrator.register_agent("agent2", agent2);

        let message = Message::with_text("user", "Test input");
        let result = orchestrator.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("agent1: Response 1"));
        assert!(content.contains("agent2: Failed"));

        // Check tasks
        let tasks = orchestrator.get_tasks();
        assert_eq!(tasks.len(), 2);

        // Find tasks by agent name (HashMap iteration order not guaranteed)
        let agent1_task = tasks.iter().find(|t| t.agent_name == "agent1").unwrap();
        let agent2_task = tasks.iter().find(|t| t.agent_name == "agent2").unwrap();

        assert_eq!(agent1_task.status, TaskStatus::Completed);
        assert_eq!(agent2_task.status, TaskStatus::Failed);
        assert!(agent2_task.error.is_some());
    }

    #[tokio::test]
    async fn test_orchestrator_registration() {
        let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);

        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "Response".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        orchestrator.register_agent("agent1", agent1.clone());
        assert_eq!(orchestrator.list_agents().len(), 1);

        orchestrator.register_agent("agent2", agent1);
        assert_eq!(orchestrator.list_agents().len(), 2);

        orchestrator.unregister_agent("agent1");
        assert_eq!(orchestrator.list_agents().len(), 1);
        assert_eq!(orchestrator.list_agents()[0], "agent2");
    }

    #[tokio::test]
    async fn test_consensus_basic() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "Opinion 1".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "Opinion 2".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent3 = Arc::new(MockAgent {
            name: "agent3".to_string(),
            response: "Opinion 3".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let mut consensus = ConsensusAgent::new(VotingStrategy::Majority);
        consensus.add_agent(agent1);
        consensus.add_agent(agent2);
        consensus.add_agent(agent3);

        let message = Message::with_text("user", "What do you think?");
        let result = consensus.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("Consensus from 3 agents"));
        assert!(content.contains("Agent 1: Opinion 1"));
        assert!(content.contains("Agent 2: Opinion 2"));
        assert!(content.contains("Agent 3: Opinion 3"));
    }

    #[tokio::test]
    async fn test_consensus_with_failure() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "Opinion 1".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "".to_string(),
            fail: true,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let mut consensus = ConsensusAgent::new(VotingStrategy::Majority);
        consensus.add_agent(agent1);
        consensus.add_agent(agent2);

        let message = Message::with_text("user", "What do you think?");
        let result = consensus.process(message).await;

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("failed"));
    }

    #[tokio::test]
    async fn test_consensus_capabilities() {
        let agent1 = Arc::new(MockAgent {
            name: "agent1".to_string(),
            response: "Response".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent2 = Arc::new(MockAgent {
            name: "agent2".to_string(),
            response: "Response".to_string(),
            fail: false,
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let mut consensus = ConsensusAgent::new(VotingStrategy::Majority);
        consensus.add_agent(agent1);
        consensus.add_agent(agent2);

        let caps = consensus.capabilities();
        assert!(caps.contains(&"agent1_capability".to_string()));
        assert!(caps.contains(&"agent2_capability".to_string()));
    }

    #[tokio::test]
    async fn test_consensus_voting_strategy() {
        let consensus = ConsensusAgent::new(VotingStrategy::Unanimous);
        assert_eq!(consensus.voting_strategy(), VotingStrategy::Unanimous);

        let consensus = ConsensusAgent::new(VotingStrategy::Weighted);
        assert_eq!(consensus.voting_strategy(), VotingStrategy::Weighted);
    }

    #[tokio::test]
    async fn test_orchestrator_strategy() {
        let orch = MultiAgentOrchestrator::new(OrchestrationStrategy::Parallel);
        assert_eq!(orch.strategy(), OrchestrationStrategy::Parallel);

        let orch = MultiAgentOrchestrator::new(OrchestrationStrategy::Delegate);
        assert_eq!(orch.strategy(), OrchestrationStrategy::Delegate);
    }

    #[tokio::test]
    async fn test_task_status() {
        let task = AgentTask::new("agent1".to_string(), "description".to_string());
        assert_eq!(task.status, TaskStatus::Pending);
        assert_eq!(task.status.to_string(), "pending");
        assert_eq!(task.agent_name, "agent1");
        assert_eq!(task.description, "description");
        assert!(task.result.is_none());
        assert!(task.error.is_none());
    }

    #[tokio::test]
    async fn test_empty_orchestrator() {
        let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);

        let message = Message::with_text("user", "Test");
        let result = orchestrator.process(message).await.unwrap();

        // Empty orchestrator returns empty combined result
        assert_eq!(result.content_as_str().unwrap(), "");
        assert_eq!(orchestrator.get_tasks().len(), 0);
    }

    #[tokio::test]
    async fn test_empty_consensus() {
        let consensus = ConsensusAgent::new(VotingStrategy::Majority);

        let message = Message::with_text("user", "Test");
        let result = consensus.process(message).await.unwrap();

        assert!(result
            .content_as_str()
            .unwrap()
            .contains("Consensus from 0 agents"));
    }
}
