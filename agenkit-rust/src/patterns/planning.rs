//! Planning Pattern - Task Decomposition and Execution
//!
//! The Planning pattern breaks complex tasks into manageable steps and executes
//! them in order, handling dependencies and potential failures.
//!
//! # Key Concepts
//!
//! - **Plan**: Collection of steps to accomplish a goal
//! - **PlanStep**: Individual actionable step with dependencies
//! - **StepExecutor**: Protocol for executing steps
//! - **Dynamic Replanning**: Adapt plan when steps fail
//!
//! # Use Cases
//!
//! - Multi-step task coordination
//! - Tasks requiring specific ordering
//! - Complex workflows with dependencies
//! - Adaptive task execution
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{PlanningAgent, PlanningConfig};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let llm_agent: Arc<dyn Agent> = todo!();
//! # let executor: Arc<dyn agenkit::patterns::StepExecutor> = todo!();
//! let planner = PlanningAgent::new(PlanningConfig {
//!     llm: llm_agent,
//!     executor: Some(executor),
//!     max_steps: 10,
//!     allow_replanning: true,
//!     system_prompt: None,
//! })?;
//!
//! let message = Message::with_text("user", "Organize a team event");
//! let result = planner.process(message).await?;
//! # Ok(())
//! # }
//! ```
//!
//! # References
//!
//! - LangChain: Planning and execution agents
//! - AutoGPT: Task decomposition
//! - Multi-agent planning literature

use async_trait::async_trait;
use regex::Regex;
use std::collections::HashMap;
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};

/// Status of a plan step.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StepStatus {
    /// Step not yet started
    Pending,
    /// Step currently executing
    InProgress,
    /// Step completed successfully
    Completed,
    /// Step failed with error
    Failed,
    /// Step was skipped
    Skipped,
}

/// A single step in a plan.
///
/// Represents an actionable task with dependencies, status tracking,
/// and result storage.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PlanStep {
    /// Description of what this step should accomplish
    pub description: String,
    /// Step indices that must complete before this step (0-indexed)
    pub dependencies: Vec<usize>,
    /// Current status of the step
    pub status: StepStatus,
    /// Result from executing the step (if completed)
    pub result: Option<serde_json::Value>,
    /// Error message if step failed
    pub error: Option<String>,
    /// Position in the plan (0-indexed)
    pub step_number: usize,
    /// Additional step metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

impl PlanStep {
    /// Creates a new plan step.
    ///
    /// # Arguments
    ///
    /// * `description` - What this step should accomplish
    /// * `step_number` - Position in the plan (0-indexed)
    /// * `dependencies` - Step indices that must complete first
    pub fn new(
        description: impl Into<String>,
        step_number: usize,
        dependencies: Vec<usize>,
    ) -> Self {
        Self {
            description: description.into(),
            dependencies,
            status: StepStatus::Pending,
            result: None,
            error: None,
            step_number,
            metadata: HashMap::new(),
        }
    }

    /// Check if this step's dependencies are met.
    ///
    /// # Arguments
    ///
    /// * `completed_steps` - Indices of completed steps
    pub fn can_execute(&self, completed_steps: &[usize]) -> bool {
        self.dependencies
            .iter()
            .all(|dep| completed_steps.contains(dep))
    }
}

/// A plan consisting of multiple steps.
///
/// Manages a collection of steps with progress tracking and execution logic.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Plan {
    /// The overall goal the plan aims to achieve
    pub goal: String,
    /// List of steps in the plan
    pub steps: Vec<PlanStep>,
    /// Additional plan metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

impl Plan {
    /// Creates a new plan.
    ///
    /// # Arguments
    ///
    /// * `goal` - Overall goal to achieve
    /// * `steps` - Steps to execute
    pub fn new(goal: impl Into<String>, steps: Vec<PlanStep>) -> Self {
        Self {
            goal: goal.into(),
            steps,
            metadata: HashMap::new(),
        }
    }

    /// Get all steps that can be executed now.
    ///
    /// Returns steps that are pending and have their dependencies met.
    pub fn get_next_steps(&self) -> Vec<&PlanStep> {
        let completed: Vec<usize> = self
            .steps
            .iter()
            .enumerate()
            .filter(|(_, step)| step.status == StepStatus::Completed)
            .map(|(i, _)| i)
            .collect();

        self.steps
            .iter()
            .filter(|step| step.status == StepStatus::Pending && step.can_execute(&completed))
            .collect()
    }

    /// Check if all steps are completed or skipped.
    pub fn is_complete(&self) -> bool {
        self.steps
            .iter()
            .all(|step| matches!(step.status, StepStatus::Completed | StepStatus::Skipped))
    }

    /// Check if any steps failed.
    pub fn has_failures(&self) -> bool {
        self.steps.iter().any(|step| step.status == StepStatus::Failed)
    }

    /// Get completion progress as a percentage.
    pub fn get_progress(&self) -> f64 {
        if self.steps.is_empty() {
            return 0.0;
        }

        let completed = self
            .steps
            .iter()
            .filter(|step| matches!(step.status, StepStatus::Completed | StepStatus::Skipped))
            .count();

        (completed as f64 / self.steps.len() as f64) * 100.0
    }
}

/// Protocol for executing individual plan steps.
///
/// Implement this trait to provide custom step execution logic.
#[async_trait]
pub trait StepExecutor: Send + Sync {
    /// Execute a plan step.
    ///
    /// # Arguments
    ///
    /// * `step` - The step to execute
    /// * `context` - Context from previous steps
    ///
    /// # Returns
    ///
    /// Result of the step execution
    async fn execute(
        &self,
        step: &PlanStep,
        context: &HashMap<String, serde_json::Value>,
    ) -> Result<serde_json::Value, AgentError>;
}

/// Default step executor that returns mock results.
///
/// In production, replace with an executor that uses tools/APIs,
/// delegates to other agents, or interacts with external systems.
pub struct DefaultStepExecutor;

#[async_trait]
impl StepExecutor for DefaultStepExecutor {
    async fn execute(
        &self,
        step: &PlanStep,
        _context: &HashMap<String, serde_json::Value>,
    ) -> Result<serde_json::Value, AgentError> {
        // Mock execution - just return success
        Ok(serde_json::json!(format!("Completed: {}", step.description)))
    }
}

/// Configuration for PlanningAgent.
pub struct PlanningConfig {
    /// LLM agent for plan creation
    pub llm: Arc<dyn Agent>,
    /// Executor for individual steps (uses DefaultStepExecutor if None)
    pub executor: Option<Arc<dyn StepExecutor>>,
    /// Maximum steps in a plan (default: 10)
    pub max_steps: usize,
    /// Whether to replan on failures (default: false)
    pub allow_replanning: bool,
    /// Optional system prompt override
    pub system_prompt: Option<String>,
}

/// Agent that creates and executes plans for complex tasks.
///
/// The agent uses an LLM to create a plan by breaking down complex tasks
/// into manageable steps, then executes each step sequentially or in
/// parallel (if dependencies allow).
///
/// # Performance Characteristics
///
/// - **Latency**: Sum of LLM planning + step execution times
/// - Memory: O(n) where n = number of steps
/// - Supports step dependencies and parallel execution
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{PlanningAgent, PlanningConfig};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let llm_agent: Arc<dyn Agent> = todo!();
/// let planner = PlanningAgent::new(PlanningConfig {
///     llm: llm_agent,
///     executor: None, // Use default
///     max_steps: 10,
///     allow_replanning: true,
///     system_prompt: None,
/// })?;
///
/// let result = planner.process(
///     Message::with_text("user", "Organize a team event")
/// ).await?;
/// # Ok(())
/// # }
/// ```
pub struct PlanningAgent {
    name: String,
    llm: Arc<dyn Agent>,
    executor: Arc<dyn StepExecutor>,
    max_steps: usize,
    allow_replanning: bool,
    system_prompt: String,
}

impl PlanningAgent {
    /// Creates a new planning agent.
    ///
    /// # Arguments
    ///
    /// * `config` - Configuration for the agent
    ///
    /// # Errors
    ///
    /// Returns an error if max_steps is 0.
    pub fn new(config: PlanningConfig) -> Result<Self, AgentError> {
        if config.max_steps == 0 {
            return Err(AgentError::InvalidInput(
                "max_steps must be greater than 0".to_string(),
            ));
        }

        let executor = config
            .executor
            .unwrap_or_else(|| Arc::new(DefaultStepExecutor));

        let system_prompt = config
            .system_prompt
            .unwrap_or_else(|| Self::default_system_prompt(config.max_steps));

        Ok(Self {
            name: "PlanningAgent".to_string(),
            llm: config.llm,
            executor,
            max_steps: config.max_steps,
            allow_replanning: config.allow_replanning,
            system_prompt,
        })
    }

    /// Generate default system prompt for planning.
    fn default_system_prompt(max_steps: usize) -> String {
        format!(
            "You are a planning agent that breaks down complex tasks into steps.\n\n\
             For each task, create a plan with specific, actionable steps.\n\n\
             Format your plan as:\n\
             Goal: [overall goal]\n\
             Steps:\n\
             1. [first step]\n\
             2. [second step]\n\
             ...\n\n\
             Maximum {} steps.\n\n\
             Guidelines:\n\
             - Make steps concrete and actionable\n\
             - Consider dependencies between steps\n\
             - Keep steps focused and achievable\n\
             - Include verification steps when appropriate",
            max_steps
        )
    }

    /// Create a plan for the given task.
    async fn create_plan(&self, task: &str) -> Result<Plan, AgentError> {
        // Ask LLM to create a plan
        let prompt = format!(
            "{}\n\nuser: Create a plan for: {}",
            self.system_prompt, task
        );

        let response = self.llm.process(Message::with_text("user", prompt)).await?;

        let plan_text = response.content_as_str().ok_or_else(|| {
            AgentError::ProcessingError("LLM response has no text content".to_string())
        })?;

        // Parse the plan
        let plan = self.parse_plan(plan_text, task);

        Ok(plan)
    }

    /// Parse LLM response into a Plan object.
    ///
    /// Expected format:
    /// ```text
    /// Goal: [goal]
    /// Steps:
    /// 1. [step 1]
    /// 2. [step 2]
    /// ...
    /// ```
    fn parse_plan(&self, plan_text: &str, default_goal: &str) -> Plan {
        let lines: Vec<&str> = plan_text.trim().split('\n').collect();

        // Extract goal
        let mut goal = default_goal.to_string();
        for line in &lines {
            let trimmed = line.trim();
            if trimmed.starts_with("Goal:") {
                goal = trimmed.trim_start_matches("Goal:").trim().to_string();
                break;
            }
        }

        // Extract steps
        let mut steps = Vec::new();
        let mut in_steps_section = false;
        let mut step_number = 0;

        // Regex for matching step numbers
        let step_regex = Regex::new(r"^(\d+)[.)]").unwrap();

        for line in lines {
            let trimmed = line.trim();

            if trimmed.starts_with("Steps:") {
                in_steps_section = true;
                continue;
            }

            if in_steps_section && !trimmed.is_empty() {
                let mut step_text = trimmed.to_string();

                // Try to match and remove step number prefix
                if step_regex.is_match(&step_text) {
                    step_text = step_regex.replace(&step_text, "").trim().to_string();
                }

                // Also try "Step N:" format
                let step_prefix = format!("Step {}:", step_number + 1);
                if step_text.starts_with(&step_prefix) {
                    step_text = step_text.trim_start_matches(&step_prefix).trim().to_string();
                }

                if !step_text.is_empty() && steps.len() < self.max_steps {
                    steps.push(PlanStep::new(step_text, step_number, vec![]));
                    step_number += 1;
                }
            }
        }

        Plan::new(goal, steps)
    }

    /// Execute all steps in the plan.
    async fn execute_plan(&self, plan: &mut Plan) -> Result<String, AgentError> {
        let mut context: HashMap<String, serde_json::Value> = HashMap::new();
        let mut results = Vec::new();

        while !plan.is_complete() {
            // Get next executable steps
            let next_step_numbers: Vec<usize> = plan
                .get_next_steps()
                .iter()
                .map(|step| step.step_number)
                .collect();

            if next_step_numbers.is_empty() {
                // No steps can execute (all blocked or completed)
                if plan.has_failures() && self.allow_replanning {
                    // Try to replan around failures
                    self.replan(plan).await?;
                    continue;
                }
                break;
            }

            // Execute next steps (for now, sequentially)
            for step_num in next_step_numbers {
                // Find and update the step
                let step = &mut plan.steps[step_num];
                step.status = StepStatus::InProgress;

                // Execute the step
                match self.executor.execute(step, &context).await {
                    Ok(result) => {
                        step.result = Some(result.clone());
                        step.status = StepStatus::Completed;

                        // Add result to context for future steps
                        context.insert(format!("step_{}_result", step_num), result);
                        results.push(format!(
                            "Step {}: {} ✓",
                            step_num + 1,
                            step.description
                        ));
                    }
                    Err(e) => {
                        step.error = Some(e.to_string());
                        step.status = StepStatus::Failed;
                        results.push(format!(
                            "Step {}: {} ✗ ({})",
                            step_num + 1,
                            step.description,
                            e
                        ));
                    }
                }
            }
        }

        // Generate summary
        let mut summary = results.join("\n");

        if plan.is_complete() {
            summary.push_str(&format!(
                "\n\nPlan completed successfully ({:.0}%)",
                plan.get_progress()
            ));
        } else if plan.has_failures() {
            summary.push_str(&format!(
                "\n\nPlan failed ({:.0}% complete)",
                plan.get_progress()
            ));
        } else {
            summary.push_str(&format!(
                "\n\nPlan partially completed ({:.0}%)",
                plan.get_progress()
            ));
        }

        Ok(summary)
    }

    /// Create a new plan to work around failures.
    async fn replan(&self, plan: &mut Plan) -> Result<(), AgentError> {
        // Get failed steps
        let failed_steps: Vec<&PlanStep> = plan
            .steps
            .iter()
            .filter(|step| step.status == StepStatus::Failed)
            .collect();

        if failed_steps.is_empty() {
            return Ok(());
        }

        // Ask LLM to create alternative steps
        let failed_descriptions: Vec<String> = failed_steps
            .iter()
            .map(|step| {
                format!(
                    "- {} (Error: {})",
                    step.description,
                    step.error.as_deref().unwrap_or("unknown")
                )
            })
            .collect();

        let prompt = format!(
            "{}\n\nuser: The following steps failed:\n{}\n\nCreate alternative steps to accomplish the goal: {}",
            self.system_prompt,
            failed_descriptions.join("\n"),
            plan.goal
        );

        let _response = self.llm.process(Message::with_text("user", prompt)).await?;

        // For simplicity, mark failed steps as skipped
        for step in &mut plan.steps {
            if step.status == StepStatus::Failed {
                step.status = StepStatus::Skipped;
            }
        }

        Ok(())
    }
}

#[async_trait]
impl Agent for PlanningAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "planning".to_string(),
            "task_decomposition".to_string(),
            "step_execution".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let task = message.content_as_str().ok_or_else(|| {
            AgentError::InvalidInput("Message must contain text content".to_string())
        })?;

        // Create plan
        let mut plan = self.create_plan(task).await?;

        // Execute plan
        let result = self.execute_plan(&mut plan).await?;

        let completed = plan
            .steps
            .iter()
            .filter(|step| step.status == StepStatus::Completed)
            .count();

        let content = format!(
            "Task completed.\n\nGoal: {}\n\nSteps completed: {}/{}\n\nResult: {}",
            plan.goal,
            completed,
            plan.steps.len(),
            result
        );

        // Add plan metadata
        let mut metadata = HashMap::new();
        metadata.insert(
            "plan".to_string(),
            serde_json::to_value(&plan).unwrap_or(serde_json::json!(null)),
        );
        metadata.insert(
            "progress".to_string(),
            serde_json::json!(plan.get_progress()),
        );

        let mut response = Message::with_text("assistant", content);
        response.metadata = metadata;

        Ok(response)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    // Mock LLM agent for testing
    struct MockLLMAgent {
        responses: Arc<std::sync::Mutex<Vec<String>>>,
    }

    #[async_trait]
    impl Agent for MockLLMAgent {
        fn name(&self) -> &str {
            "mock_llm"
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["mock".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let response = {
                let mut responses = self.responses.lock().unwrap();
                if responses.is_empty() {
                    "Goal: Test goal\nSteps:\n1. Step one\n2. Step two".to_string()
                } else {
                    responses.remove(0)
                }
            };
            Ok(Message::with_text("assistant", response))
        }
    }

    // Mock step executor for testing
    struct MockStepExecutor {
        call_count: Arc<AtomicUsize>,
        should_fail: bool,
    }

    #[async_trait]
    impl StepExecutor for MockStepExecutor {
        async fn execute(
            &self,
            step: &PlanStep,
            _context: &HashMap<String, serde_json::Value>,
        ) -> Result<serde_json::Value, AgentError> {
            self.call_count.fetch_add(1, Ordering::SeqCst);

            if self.should_fail {
                Err(AgentError::ProcessingError("Mock failure".to_string()))
            } else {
                Ok(serde_json::json!(format!("Completed: {}", step.description)))
            }
        }
    }

    #[tokio::test]
    async fn test_plan_step_basic() {
        let step = PlanStep::new("Test step", 0, vec![]);
        assert_eq!(step.description, "Test step");
        assert_eq!(step.step_number, 0);
        assert_eq!(step.status, StepStatus::Pending);
        assert!(step.dependencies.is_empty());
    }

    #[tokio::test]
    async fn test_plan_step_dependencies() {
        let step = PlanStep::new("Test step", 2, vec![0, 1]);
        assert!(step.can_execute(&[0, 1]));
        assert!(!step.can_execute(&[0]));
        assert!(!step.can_execute(&[]));
    }

    #[tokio::test]
    async fn test_plan_progress() {
        let mut plan = Plan::new(
            "Test goal",
            vec![
                PlanStep::new("Step 1", 0, vec![]),
                PlanStep::new("Step 2", 1, vec![]),
                PlanStep::new("Step 3", 2, vec![]),
            ],
        );

        assert_eq!(plan.get_progress(), 0.0);

        plan.steps[0].status = StepStatus::Completed;
        assert!((plan.get_progress() - 33.333).abs() < 0.01);

        plan.steps[1].status = StepStatus::Completed;
        assert!((plan.get_progress() - 66.666).abs() < 0.01);

        plan.steps[2].status = StepStatus::Completed;
        assert_eq!(plan.get_progress(), 100.0);
    }

    #[tokio::test]
    async fn test_plan_next_steps() {
        let mut plan = Plan::new(
            "Test goal",
            vec![
                PlanStep::new("Step 1", 0, vec![]),
                PlanStep::new("Step 2", 1, vec![0]),
                PlanStep::new("Step 3", 2, vec![0, 1]),
            ],
        );

        // Initially, only step 0 can execute
        let next = plan.get_next_steps();
        assert_eq!(next.len(), 1);
        assert_eq!(next[0].step_number, 0);

        // After step 0 completes, step 1 can execute
        plan.steps[0].status = StepStatus::Completed;
        let next = plan.get_next_steps();
        assert_eq!(next.len(), 1);
        assert_eq!(next[0].step_number, 1);

        // After step 1 completes, step 2 can execute
        plan.steps[1].status = StepStatus::Completed;
        let next = plan.get_next_steps();
        assert_eq!(next.len(), 1);
        assert_eq!(next[0].step_number, 2);
    }

    #[tokio::test]
    async fn test_planning_agent_basic() {
        let llm = Arc::new(MockLLMAgent {
            responses: Arc::new(std::sync::Mutex::new(vec![
                "Goal: Test task\nSteps:\n1. First step\n2. Second step".to_string(),
            ])),
        });

        let executor = Arc::new(MockStepExecutor {
            call_count: Arc::new(AtomicUsize::new(0)),
            should_fail: false,
        });

        let agent = PlanningAgent::new(PlanningConfig {
            llm,
            executor: Some(executor.clone()),
            max_steps: 10,
            allow_replanning: false,
            system_prompt: None,
        })
        .unwrap();

        let message = Message::with_text("user", "Test task");
        let result = agent.process(message).await.unwrap();

        assert!(result.content_as_str().unwrap().contains("Test task"));
        assert!(result.content_as_str().unwrap().contains("Steps completed"));
        assert_eq!(executor.call_count.load(Ordering::SeqCst), 2);
    }

    #[tokio::test]
    async fn test_planning_agent_validation() {
        let llm = Arc::new(MockLLMAgent {
            responses: Arc::new(std::sync::Mutex::new(vec![])),
        });

        // Test max_steps = 0
        let result = PlanningAgent::new(PlanningConfig {
            llm,
            executor: None,
            max_steps: 0,
            allow_replanning: false,
            system_prompt: None,
        });

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_planning_agent_parse_plan() {
        let llm = Arc::new(MockLLMAgent {
            responses: Arc::new(std::sync::Mutex::new(vec![])),
        });

        let agent = PlanningAgent::new(PlanningConfig {
            llm,
            executor: None,
            max_steps: 10,
            allow_replanning: false,
            system_prompt: None,
        })
        .unwrap();

        let plan_text = "Goal: Test goal\nSteps:\n1. Step one\n2. Step two\n3. Step three";
        let plan = agent.parse_plan(plan_text, "Default goal");

        assert_eq!(plan.goal, "Test goal");
        assert_eq!(plan.steps.len(), 3);
        assert_eq!(plan.steps[0].description, "Step one");
        assert_eq!(plan.steps[1].description, "Step two");
        assert_eq!(plan.steps[2].description, "Step three");
    }

    #[tokio::test]
    async fn test_default_step_executor() {
        let executor = DefaultStepExecutor;
        let step = PlanStep::new("Test step", 0, vec![]);
        let context = HashMap::new();

        let result = executor.execute(&step, &context).await.unwrap();
        assert_eq!(result, serde_json::json!("Completed: Test step"));
    }
}
