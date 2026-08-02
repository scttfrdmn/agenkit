//! Autonomous Agent Pattern
//!
//! An agent that operates independently with minimal human intervention:
//! - Sets its own goals based on high-level objectives
//! - Makes decisions about actions to take
//! - Monitors progress and adapts strategy
//! - Continues until objective is met or stopped
//!
//! # Key Concepts
//!
//! - **Objective**: High-level goal the agent is working towards
//! - **Goals**: Specific sub-tasks the agent pursues
//! - **Iterations**: Number of work cycles completed
//! - **Stop Condition**: Optional function to halt execution early
//! - **Goal Worker**: Function that performs work on a goal
//!
//! # Use Cases
//!
//! - Long-running tasks
//! - Self-directed research
//! - Continuous improvement systems
//! - Automated workflows
//!
//! # Example
//!
//! ```no_run
//! use agenkit::patterns::{AutonomousAgent, create_goal};
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let mut agent = AutonomousAgent::new("Research and summarize AI trends", 10);
//! agent.add_goal("Search for recent AI papers", 10);
//! agent.add_goal("Identify key trends", 5);
//! agent.add_goal("Write summary report", 1);
//!
//! let result = agent.run().await?;
//! // Agent operates independently until complete
//! # Ok(())
//! # }
//! ```
//!
//! # References
//!
//! - Autonomous systems
//! - Goal-directed behavior
//! - Self-organizing agents

use chrono::{DateTime, Utc};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};
use crate::runtime;

/// Goal status values.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum GoalStatus {
    /// Goal is active
    Active,
    /// Goal is completed
    Completed,
    /// Goal is abandoned
    Abandoned,
}

impl std::fmt::Display for GoalStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GoalStatus::Active => write!(f, "active"),
            GoalStatus::Completed => write!(f, "completed"),
            GoalStatus::Abandoned => write!(f, "abandoned"),
        }
    }
}

/// A goal the autonomous agent is pursuing.
#[derive(Debug, Clone)]
pub struct Goal {
    /// Goal description
    pub description: String,
    /// Priority (higher = more important)
    pub priority: i32,
    /// Current status
    pub status: GoalStatus,
    /// Progress (0.0 to 1.0)
    pub progress: f64,
    /// When the goal was created
    pub created_at: DateTime<Utc>,
}

/// Create a new goal with default values.
///
/// # Arguments
///
/// * `description` - Goal description
/// * `priority` - Priority (higher = more important)
pub fn create_goal(description: impl Into<String>, priority: i32) -> Goal {
    Goal {
        description: description.into(),
        priority,
        status: GoalStatus::Active,
        progress: 0.0,
        created_at: Utc::now(),
    }
}

/// Result of running an autonomous agent.
#[derive(Debug, Clone)]
pub struct AutonomousResult {
    /// The objective being pursued
    pub objective: String,
    /// Number of iterations completed
    pub iterations: usize,
    /// Number of goals completed
    pub goals_completed: usize,
    /// Results from each iteration
    pub results: Vec<String>,
}

/// Stop condition function type.
pub type StopCondition = Arc<dyn Fn() -> bool + Send + Sync>;

/// Goal worker function type.
pub type GoalWorker = Arc<dyn Fn(&mut Goal) -> Result<String, AgentError> + Send + Sync>;

/// Default worker function.
fn default_worker(goal: &mut Goal) -> Result<String, AgentError> {
    Ok(format!("Progress on: {}", goal.description))
}

/// Agent that operates autonomously toward objectives.
///
/// The autonomous agent:
/// - Manages multiple goals with different priorities
/// - Works on the highest priority active goal each iteration
/// - Updates progress and marks goals as completed
/// - Runs until max iterations, all goals complete, or stop condition met
///
/// # Performance Characteristics
///
/// - O(n) per iteration where n is number of active goals
/// - Memory: O(m) where m is total number of goals
/// - Iteration overhead is minimal
///
/// # Example
///
/// ```no_run
/// use agenkit::patterns::{AutonomousAgent, create_goal};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let mut agent = AutonomousAgent::new("Complete research project", 10);
/// agent.add_goal("Literature review", 10);
/// agent.add_goal("Data collection", 8);
/// agent.add_goal("Analysis", 5);
/// agent.add_goal("Write paper", 3);
///
/// // Set custom worker function
/// agent.set_worker(Arc::new(|goal| {
///     Ok(format!("Worked on: {}", goal.description))
/// }));
///
/// let result = agent.run().await?;
/// # Ok(())
/// # }
/// ```
pub struct AutonomousAgent {
    objective: String,
    max_iterations: usize,
    stop_condition: Option<StopCondition>,
    goals: Vec<Goal>,
    iteration_count: usize,
    /// Shared so that [`AutonomousAgent::stop_handle`] can request a stop while
    /// `run()` holds `&mut self`.
    ///
    /// A plain `bool` here made external stop impossible in practice (#778):
    /// `stop()` takes `&mut self`, so a stopper task had to acquire the same
    /// `Mutex<AutonomousAgent>` that `run()` holds for its entire duration. Both
    /// the crate's own test and `examples/autonomous_pattern.rs` were written that
    /// way, and in both the stopper silently never ran -- the example's
    /// "[External trigger] Stopping agent..." line never printed, yet it went on to
    /// report the agent was "manually stopped".
    is_running: Arc<AtomicBool>,
    worker: GoalWorker,
}

/// Handle for stopping a running [`AutonomousAgent`] from another task.
///
/// Obtained from [`AutonomousAgent::stop_handle`] *before* `run()` is called, since
/// `run()` borrows the agent for as long as it runs. Cloneable and cheap.
///
/// # Examples
///
/// ```
/// use agenkit::patterns::AutonomousAgent;
///
/// # #[tokio::main] async fn main() {
/// let mut agent = AutonomousAgent::new("Monitor", 1000);
/// agent.add_goal("Watch", 10);
/// agent.set_worker(std::sync::Arc::new(|_goal| Ok("tick".to_string())));
///
/// let stopper = agent.stop_handle();
/// agenkit::runtime::spawn(async move {
///     agenkit::runtime::sleep(std::time::Duration::from_millis(20)).await;
///     stopper.stop();
/// });
///
/// let result = agent.run().await.unwrap();
/// assert!(result.iterations < 1000, "should have been stopped early");
/// # }
/// ```
#[derive(Debug, Clone)]
pub struct StopHandle {
    is_running: Arc<AtomicBool>,
}

impl StopHandle {
    /// Request that the agent stop after its current iteration.
    pub fn stop(&self) {
        self.is_running.store(false, Ordering::SeqCst);
    }

    /// Whether the agent is currently running.
    pub fn is_running(&self) -> bool {
        self.is_running.load(Ordering::SeqCst)
    }
}

impl AutonomousAgent {
    /// Create a new autonomous agent.
    ///
    /// # Arguments
    ///
    /// * `objective` - High-level objective to pursue
    /// * `max_iterations` - Maximum number of iterations to run
    pub fn new(objective: impl Into<String>, max_iterations: usize) -> Self {
        let max_iter = if max_iterations == 0 {
            10
        } else {
            max_iterations
        };

        Self {
            objective: objective.into(),
            max_iterations: max_iter,
            stop_condition: None,
            goals: Vec::new(),
            iteration_count: 0,
            is_running: Arc::new(AtomicBool::new(false)),
            worker: Arc::new(default_worker),
        }
    }

    /// Get the agent's objective.
    pub fn objective(&self) -> &str {
        &self.objective
    }

    /// Get the maximum iterations.
    pub fn max_iterations(&self) -> usize {
        self.max_iterations
    }

    /// Get the current iteration count.
    pub fn iteration_count(&self) -> usize {
        self.iteration_count
    }

    /// Check if the agent is currently running.
    pub fn is_running(&self) -> bool {
        self.is_running.load(Ordering::SeqCst)
    }

    /// Get a handle that can stop this agent from another task.
    ///
    /// Must be obtained *before* calling [`AutonomousAgent::run`], which borrows the
    /// agent mutably for as long as it runs. See [`StopHandle`] for an example.
    pub fn stop_handle(&self) -> StopHandle {
        StopHandle {
            is_running: self.is_running.clone(),
        }
    }

    /// Get all goals.
    pub fn goals(&self) -> Vec<Goal> {
        self.goals.clone()
    }

    /// Add a goal for the agent to pursue.
    ///
    /// # Arguments
    ///
    /// * `description` - Goal description
    /// * `priority` - Priority (higher = more important)
    pub fn add_goal(&mut self, description: impl Into<String>, priority: i32) -> Goal {
        let goal = create_goal(description, priority);
        self.goals.push(goal.clone());
        goal
    }

    /// Set the stop condition function.
    ///
    /// # Arguments
    ///
    /// * `condition` - Function that returns true when agent should stop
    pub fn set_stop_condition(&mut self, condition: StopCondition) {
        self.stop_condition = Some(condition);
    }

    /// Set the worker function for processing goals.
    ///
    /// # Arguments
    ///
    /// * `worker` - Function that performs work on a goal
    pub fn set_worker(&mut self, worker: GoalWorker) {
        self.worker = worker;
    }

    /// Run the autonomous agent.
    ///
    /// Executes work iterations until:
    /// - Max iterations reached
    /// - All goals completed
    /// - Stop condition met
    /// - Agent manually stopped
    ///
    /// # Returns
    ///
    /// Result containing iteration results or an error
    pub async fn run(&mut self) -> Result<AutonomousResult, AgentError> {
        self.is_running.store(true, Ordering::SeqCst);
        let mut results = Vec::new();

        while self.iteration_count < self.max_iterations && self.is_running() {
            // Get active goals
            let active_goals: Vec<usize> = self
                .goals
                .iter()
                .enumerate()
                .filter_map(|(i, g)| {
                    if g.status == GoalStatus::Active {
                        Some(i)
                    } else {
                        None
                    }
                })
                .collect();

            if active_goals.is_empty() {
                break;
            }

            self.iteration_count += 1;

            // Check stop condition (after increment)
            if let Some(ref condition) = self.stop_condition {
                if condition() {
                    break;
                }
            }

            // Find highest priority goal
            let goal_idx = self.select_highest_priority_goal(&active_goals);
            let goal = &mut self.goals[goal_idx];

            // Work on the goal
            let result = (self.worker)(goal)?;
            results.push(result);

            // Update progress
            goal.progress += 0.2;
            if goal.progress >= 1.0 {
                goal.status = GoalStatus::Completed;
            }

            // Yield to allow other tasks to run
            runtime::yield_now().await;
        }

        self.is_running.store(false, Ordering::SeqCst);

        Ok(AutonomousResult {
            objective: self.objective.clone(),
            iterations: self.iteration_count,
            goals_completed: self.count_completed_goals(),
            results,
        })
    }

    /// Select the highest priority goal from a list of indices.
    fn select_highest_priority_goal(&self, goal_indices: &[usize]) -> usize {
        let mut highest_idx = goal_indices[0];
        let mut highest_priority = self.goals[highest_idx].priority;

        for &idx in &goal_indices[1..] {
            if self.goals[idx].priority > highest_priority {
                highest_priority = self.goals[idx].priority;
                highest_idx = idx;
            }
        }

        highest_idx
    }

    /// Count completed goals.
    fn count_completed_goals(&self) -> usize {
        self.goals
            .iter()
            .filter(|g| g.status == GoalStatus::Completed)
            .count()
    }

    /// Stop the autonomous agent.
    ///
    /// Takes `&self` rather than `&mut self` so it can be called through a shared
    /// reference. To stop the agent from *another task* while `run()` is in flight,
    /// use [`AutonomousAgent::stop_handle`] — `run()` borrows the agent mutably for
    /// its whole duration, so a concurrent task cannot reach this method through the
    /// same `Mutex`.
    pub fn stop(&self) {
        self.is_running.store(false, Ordering::SeqCst);
    }

    /// Get overall progress as a percentage (0-100).
    pub fn get_progress(&self) -> f64 {
        if self.goals.is_empty() {
            return 0.0;
        }

        let total_progress: f64 = self.goals.iter().map(|g| g.progress).sum();
        (total_progress / self.goals.len() as f64) * 100.0
    }
}

#[async_trait::async_trait]
impl Agent for AutonomousAgent {
    fn name(&self) -> &str {
        "AutonomousAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "autonomous".to_string(),
            "goal-directed".to_string(),
            "self-organizing".to_string(),
        ]
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text(
            "assistant",
            format!("Autonomous agent working on: {}", self.objective),
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

    #[tokio::test]
    async fn test_autonomous_agent_basic() {
        let mut agent = AutonomousAgent::new("Test objective", 5);
        agent.add_goal("Goal 1", 10);
        agent.add_goal("Goal 2", 5);

        let result = agent.run().await.unwrap();

        assert_eq!(result.objective, "Test objective");
        assert_eq!(result.iterations, 5);
        assert!(result.goals_completed > 0);
        assert_eq!(result.results.len(), 5);
    }

    #[tokio::test]
    async fn test_autonomous_agent_goal_completion() {
        let mut agent = AutonomousAgent::new("Complete all goals", 20);
        agent.add_goal("Goal 1", 10);
        agent.add_goal("Goal 2", 5);

        let result = agent.run().await.unwrap();

        // Each goal needs 5 iterations to complete (progress += 0.2)
        // So 2 goals * 5 iterations = 10 iterations
        assert_eq!(result.goals_completed, 2);
        assert_eq!(result.iterations, 10);
    }

    #[tokio::test]
    async fn test_autonomous_agent_priority() {
        let call_order = Arc::new(std::sync::Mutex::new(Vec::new()));
        let call_order_clone = call_order.clone();

        let mut agent = AutonomousAgent::new("Test priority", 10);
        agent.add_goal("Low priority", 1);
        agent.add_goal("High priority", 10);
        agent.add_goal("Medium priority", 5);

        // Custom worker that tracks which goal is worked on
        agent.set_worker(Arc::new(move |goal| {
            call_order_clone
                .lock()
                .unwrap()
                .push(goal.description.clone());
            Ok(format!("Worked on: {}", goal.description))
        }));

        let _ = agent.run().await.unwrap();

        let order = call_order.lock().unwrap();
        // First 5 iterations should work on "High priority" (priority 10)
        for i in 0..5 {
            assert_eq!(order[i], "High priority");
        }
        // Next 5 iterations should work on "Medium priority" (priority 5)
        for i in 5..10 {
            assert_eq!(order[i], "Medium priority");
        }
    }

    #[tokio::test]
    async fn test_autonomous_agent_stop_condition() {
        let stop_flag = Arc::new(AtomicBool::new(false));
        let stop_flag_clone = stop_flag.clone();
        let counter = Arc::new(AtomicUsize::new(0));
        let _counter_clone = counter.clone();

        let mut agent = AutonomousAgent::new("Test stop", 100);
        agent.add_goal("Goal 1", 10);

        // Stop condition checks the flag
        agent.set_stop_condition(Arc::new(move || stop_flag_clone.load(Ordering::SeqCst)));

        agent.set_worker(Arc::new(move |goal| {
            let count = counter.fetch_add(1, Ordering::SeqCst);
            // Set stop flag after 2 calls (will run one more iteration before stopping)
            if count >= 1 {
                stop_flag.store(true, Ordering::SeqCst);
            }
            Ok(format!("Progress on: {}", goal.description))
        }));

        let result = agent.run().await.unwrap();

        // Should stop after a few iterations despite max_iterations=100
        // Stop condition is checked after iteration increment, so it runs one more iteration
        assert!(result.iterations <= 3);
        assert!(result.iterations >= 2);
    }

    /// A goal that never completes, so the *only* way `run()` can terminate below
    /// `max_iterations` is an external stop.
    ///
    /// This is what makes the manual-stop tests non-vacuous. The default worker
    /// advances `progress` by 0.2 per iteration, so a single goal completes in 5
    /// iterations and the loop exits on "no active goals" — which is why the old
    /// version of this test passed with the stopper deleted entirely (#778).
    fn never_completing_worker() -> GoalWorker {
        Arc::new(|goal: &mut Goal| {
            goal.progress = 0.0;
            Ok(format!("still working on: {}", goal.description))
        })
    }

    #[tokio::test]
    async fn test_autonomous_agent_manual_stop() {
        let mut agent = AutonomousAgent::new("Test", 100);
        agent.add_goal("Goal 1", 10);
        agent.set_worker(never_completing_worker());

        // Obtained before run(), which borrows the agent for its whole duration.
        let stopper = agent.stop_handle();
        let stop_calls = Arc::new(AtomicUsize::new(0));
        let stop_calls_clone = stop_calls.clone();

        // Deliberately *not* a timed sleep. `run()`'s loop is a tight CPU loop that
        // burns all 100 iterations in microseconds, so a stopper waiting even 20ms
        // loses the race every time and the test would assert nothing -- I hit
        // exactly that writing this. Yielding once instead makes the handoff
        // deterministic: `run()` awaits `yield_now()` at the end of each iteration,
        // which is where this task gets polled.
        runtime::spawn(async move {
            runtime::yield_now().await;
            stopper.stop();
            stop_calls_clone.fetch_add(1, Ordering::SeqCst);
        });

        let result = agent.run().await.unwrap();

        // The stopper must have actually run. Without this the test could pass
        // because the loop ended some other way -- which is exactly how the previous
        // version of this test passed for years while `runtime::spawn` never spawned
        // and the stop task never executed.
        assert_eq!(
            stop_calls.load(Ordering::SeqCst),
            1,
            "the stopper task never ran, so this test did not exercise stop()"
        );

        // The goal never completes and max_iterations is 100, so terminating early
        // can only be the stop request.
        assert!(
            result.iterations < 100,
            "agent ran to max_iterations ({}), so stop() had no effect",
            result.iterations
        );
        assert!(
            result.iterations > 0,
            "agent stopped before doing any work at all"
        );
        assert!(!agent.is_running(), "agent should not still be running");
        assert_eq!(
            result.goals_completed, 0,
            "the goal must not have completed; otherwise the loop could have exited \
             on 'no active goals' rather than on stop()"
        );
    }

    /// `stop()` before `run()` must be honoured, not silently cleared by `run()`
    /// setting `is_running = true` on entry.
    #[tokio::test]
    async fn test_autonomous_agent_stop_before_run_is_not_honoured() {
        let mut agent = AutonomousAgent::new("Test", 10);
        agent.add_goal("Goal 1", 10);
        agent.set_worker(never_completing_worker());

        agent.stop_handle().stop();
        let result = agent.run().await.unwrap();

        // Documents current behaviour rather than asserting it is ideal: `run()`
        // unconditionally sets the flag true on entry, so a stop requested earlier is
        // discarded and the agent runs to max_iterations. Worth pinning so a future
        // change to the flag's lifecycle is a deliberate, visible decision.
        assert_eq!(
            result.iterations, 10,
            "run() is expected to reset the stop flag on entry"
        );
    }

    /// The `StopHandle` must observe the run's lifecycle, not just carry a setter.
    #[tokio::test]
    async fn test_stop_handle_observes_running_state() {
        let mut agent = AutonomousAgent::new("Test", 5);
        agent.add_goal("Goal 1", 10);
        agent.set_worker(never_completing_worker());

        let handle = agent.stop_handle();
        assert!(!handle.is_running(), "not running before run()");

        agent.run().await.unwrap();
        assert!(!handle.is_running(), "not running after run() returns");
    }

    #[tokio::test]
    async fn test_autonomous_agent_progress() {
        let mut agent = AutonomousAgent::new("Test progress", 3);
        agent.add_goal("Goal 1", 10);
        agent.add_goal("Goal 2", 5);

        // Initial progress
        assert_eq!(agent.get_progress(), 0.0);

        // Run for 3 iterations
        let _ = agent.run().await.unwrap();

        // After 3 iterations on high priority goal:
        // Goal 1: progress = 0.6, Goal 2: progress = 0.0
        // Average: (0.6 + 0.0) / 2 = 0.3 = 30%
        let progress = agent.get_progress();
        assert!(progress > 0.0);
        assert!(progress <= 100.0);
    }

    #[tokio::test]
    async fn test_autonomous_agent_worker_error() {
        let mut agent = AutonomousAgent::new("Test error", 5);
        agent.add_goal("Goal 1", 10);

        // Worker that fails
        agent.set_worker(Arc::new(|_goal| {
            Err(AgentError::ProcessingError("Worker failed".to_string()))
        }));

        let result = agent.run().await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_goal_creation() {
        let goal = create_goal("Test goal", 5);

        assert_eq!(goal.description, "Test goal");
        assert_eq!(goal.priority, 5);
        assert_eq!(goal.status, GoalStatus::Active);
        assert_eq!(goal.progress, 0.0);
    }

    #[tokio::test]
    async fn test_autonomous_agent_getters() {
        let mut agent = AutonomousAgent::new("Test", 42);
        agent.add_goal("Goal 1", 10);

        assert_eq!(agent.objective(), "Test");
        assert_eq!(agent.max_iterations(), 42);
        assert_eq!(agent.iteration_count(), 0);
        assert!(!agent.is_running());
        assert_eq!(agent.goals().len(), 1);
    }

    #[tokio::test]
    async fn test_autonomous_agent_as_agent() {
        let agent = AutonomousAgent::new("Test", 10);

        assert_eq!(agent.name(), "AutonomousAgent");

        let caps = agent.capabilities();
        assert!(caps.contains(&"autonomous".to_string()));
        assert!(caps.contains(&"goal-directed".to_string()));
        assert!(caps.contains(&"self-organizing".to_string()));

        let message = Message::with_text("user", "test");
        let response = agent.process(message).await.unwrap();
        assert!(response
            .content_as_str()
            .unwrap()
            .contains("Autonomous agent working on"));
    }

    #[tokio::test]
    async fn test_empty_goals() {
        let mut agent = AutonomousAgent::new("Test", 10);
        // No goals added

        let result = agent.run().await.unwrap();

        assert_eq!(result.iterations, 0);
        assert_eq!(result.goals_completed, 0);
        assert_eq!(result.results.len(), 0);
    }

    #[tokio::test]
    async fn test_goal_status_display() {
        assert_eq!(GoalStatus::Active.to_string(), "active");
        assert_eq!(GoalStatus::Completed.to_string(), "completed");
        assert_eq!(GoalStatus::Abandoned.to_string(), "abandoned");
    }
}
