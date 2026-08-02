//! Task Pattern - One-shot Agent Execution with Lifecycle Management
//!
//! The Task pattern wraps an Agent for single-use execution with automatic
//! resource cleanup and explicit lifecycle management.
//!
//! # Key Concepts
//!
//! - **One-shot Semantics**: Execute once, then cleanup
//! - **Resource Management**: Automatic cleanup after completion
//! - **Retry Logic**: Exponential backoff on failures
//! - **Timeout Support**: Configurable execution timeout
//! - **Reuse Prevention**: Cannot execute the same Task twice
//!
//! # Use Cases
//!
//! - Single-purpose operations (summarize, classify, extract)
//! - Tasks requiring explicit resource cleanup
//! - Operations needing timeout/retry at task level
//! - Batch processing with independent tasks
//!
//! # Agent vs Task
//!
//! - **Agent**: Multi-turn conversation with state
//! - **Task**: One-shot execution, then cleanup
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{Task, TaskConfig};
//! use std::sync::Arc;
//! use std::time::Duration;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let agent: Arc<dyn Agent> = todo!();
//! let task = Task::new(agent, TaskConfig {
//!     timeout: Some(Duration::from_secs(30)),
//!     retries: 2,
//! });
//!
//! let message = Message::with_text("user", "Summarize this document...");
//! let result = task.execute(message).await?;
//!
//! // Task automatically marked as completed, cannot reuse
//! # Ok(())
//! # }
//! ```
//!
//! # References
//!
//! - Task-oriented architecture patterns
//! - Resource management best practices

use std::sync::{Arc, Mutex};
use std::time::Duration;

use crate::core::{Agent, AgentError, Message};
use crate::runtime;

#[cfg(test)]
use async_trait::async_trait;

/// Configuration for Task execution.
#[derive(Clone)]
#[derive(Default)]
pub struct TaskConfig {
    /// Timeout for task execution (None means no timeout)
    pub timeout: Option<Duration>,
    /// Number of retry attempts on failure (default: 0)
    pub retries: usize,
}


/// One-shot agent execution with lifecycle management.
///
/// A Task wraps an Agent for single-use execution, providing:
/// - Explicit one-shot semantics
/// - Automatic resource cleanup
/// - Task-specific configuration (timeout, retries)
/// - Prevention of reuse after completion
///
/// # Key Distinction
///
/// - **Agent**: Multi-turn conversation with state
/// - **Task**: One-shot execution, then cleanup
///
/// # Performance Characteristics
///
/// - O(1) execution
/// - O(retries) retry attempts
/// - Automatic cleanup prevents resource leaks
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{Task, TaskConfig};
/// use std::sync::Arc;
/// use std::time::Duration;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent: Arc<dyn Agent> = todo!();
/// let task = Task::new(agent, TaskConfig {
///     timeout: Some(Duration::from_secs(30)),
///     retries: 2,
/// });
///
/// let result = task.execute(
///     Message::with_text("user", "Task input")
/// ).await?;
/// # Ok(())
/// # }
/// ```
pub struct Task {
    agent: Arc<dyn Agent>,
    timeout_duration: Option<Duration>,
    retries: usize,
    state: Arc<Mutex<TaskState>>,
}

struct TaskState {
    completed: bool,
    result: Option<Message>,
}

impl Task {
    /// Creates a new Task.
    ///
    /// # Arguments
    ///
    /// * `agent` - The agent to execute
    /// * `config` - Configuration for timeout and retries
    pub fn new(agent: Arc<dyn Agent>, config: TaskConfig) -> Self {
        Self {
            agent,
            timeout_duration: config.timeout,
            retries: config.retries,
            state: Arc::new(Mutex::new(TaskState {
                completed: false,
                result: None,
            })),
        }
    }

    /// Execute the task once.
    ///
    /// This method can only be called once per Task instance. After execution
    /// completes (successfully or with error), the Task is marked as completed
    /// and cannot be reused.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message for the agent
    ///
    /// # Returns
    ///
    /// The agent's response as a Message
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - Task already completed
    /// - Execution exceeds timeout
    /// - All retry attempts fail
    pub async fn execute(&self, message: Message) -> Result<Message, AgentError> {
        // Check if already completed
        {
            let state = self.state.lock().unwrap();
            if state.completed {
                return Err(AgentError::InvalidInput(
                    "Task already completed. Create a new Task for another execution.".to_string(),
                ));
            }
        }

        let attempts = self.retries + 1; // retries=0 means 1 attempt
        let mut last_error_message = None;

        for attempt in 0..attempts {
            // Execute with optional timeout
            let result = if let Some(timeout_duration) = self.timeout_duration {
                match runtime::timeout(timeout_duration, self.agent.process(message.clone())).await
                {
                    Ok(Ok(response)) => Ok(response),
                    Ok(Err(e)) => Err(e),
                    Err(_) => Err(AgentError::Timeout(format!(
                        "Task timed out after {:?}",
                        timeout_duration
                    ))),
                }
            } else {
                self.agent.process(message.clone()).await
            };

            match result {
                Ok(response) => {
                    // Success - mark completed and return
                    let mut state = self.state.lock().unwrap();
                    state.completed = true;
                    state.result = Some(response.clone());
                    return Ok(response);
                }
                Err(e) => {
                    let is_timeout = matches!(e, AgentError::Timeout(_));
                    let error_msg = e.to_string();
                    last_error_message = Some(error_msg.clone());

                    // If it was a timeout or this was the last attempt, fail
                    if is_timeout || attempt == attempts - 1 {
                        let mut state = self.state.lock().unwrap();
                        state.completed = true;
                        return Err(e);
                    }

                    // Otherwise, retry after exponential backoff
                    let backoff = Duration::from_millis(100 * (attempt as u64 + 1));
                    runtime::sleep(backoff).await;
                }
            }
        }

        // Mark as completed and return error
        let mut state = self.state.lock().unwrap();
        state.completed = true;

        Err(AgentError::ProcessingError(
            last_error_message.unwrap_or_else(|| "Task execution failed".to_string()),
        ))
    }

    /// Check if the task has been completed.
    pub fn completed(&self) -> bool {
        self.state.lock().unwrap().completed
    }

    /// Get the result of the task (if completed successfully).
    pub fn result(&self) -> Option<Message> {
        self.state.lock().unwrap().result.clone()
    }

    /// Clean up resources after task completion.
    ///
    /// This method is provided as a hook for custom cleanup logic.
    /// In production use, override this in a wrapper to:
    /// - Close network connections
    /// - Release memory/resources
    /// - Save state to disk
    /// - Send telemetry
    pub fn cleanup(&self) {
        // Default implementation - hook for custom implementations
    }
}

/// Execute a task with automatic cleanup.
///
/// Convenience function that wraps Task creation and execution.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{execute_task, TaskConfig};
/// use std::sync::Arc;
/// use std::time::Duration;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent: Arc<dyn Agent> = todo!();
/// let result = execute_task(
///     agent,
///     Message::with_text("user", "Summarize this text..."),
///     TaskConfig {
///         timeout: Some(Duration::from_secs(30)),
///         retries: 2,
///     }
/// ).await?;
/// # Ok(())
/// # }
/// ```
pub async fn execute_task(
    agent: Arc<dyn Agent>,
    message: Message,
    config: TaskConfig,
) -> Result<Message, AgentError> {
    let task = Task::new(agent, config);
    let result = task.execute(message).await;
    task.cleanup();
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    // Mock agent for testing
    struct MockAgent {
        response: String,
        call_count: Arc<AtomicUsize>,
        fail_times: usize,
        delay: Option<Duration>,
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock_agent"
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["mock".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let count = self.call_count.fetch_add(1, Ordering::SeqCst);

            // Add delay if specified
            if let Some(delay) = self.delay {
                runtime::sleep(delay).await;
            }

            // Fail for first N attempts
            if count < self.fail_times {
                return Err(AgentError::ProcessingError(format!(
                    "Attempt {} failed",
                    count + 1
                )));
            }

            Ok(Message::with_text("assistant", &self.response))
        }
    }

    #[tokio::test]
    async fn test_task_basic() {
        let agent = Arc::new(MockAgent {
            response: "Task completed".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            fail_times: 0,
            delay: None,
        });

        let task = Task::new(agent, TaskConfig::default());

        let message = Message::with_text("user", "Test input");
        let result = task.execute(message).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "Task completed");
        assert!(task.completed());
        assert!(task.result().is_some());
    }

    #[tokio::test]
    async fn test_task_cannot_reuse() {
        let agent = Arc::new(MockAgent {
            response: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            fail_times: 0,
            delay: None,
        });

        let task = Task::new(agent, TaskConfig::default());

        // First execution succeeds
        let message = Message::with_text("user", "Test");
        task.execute(message.clone()).await.unwrap();

        // Second execution should fail
        let result = task.execute(message).await;
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("already completed"));
    }

    #[tokio::test]
    async fn test_task_with_retries() {
        let call_count = Arc::new(AtomicUsize::new(0));
        let agent = Arc::new(MockAgent {
            response: "Success".to_string(),
            call_count: call_count.clone(),
            fail_times: 2, // Fail first 2 attempts
            delay: None,
        });

        let task = Task::new(
            agent,
            TaskConfig {
                timeout: None,
                retries: 2,
            },
        );

        let message = Message::with_text("user", "Test");
        let result = task.execute(message).await.unwrap();

        // Should succeed on 3rd attempt
        assert_eq!(result.content_as_str().unwrap(), "Success");
        assert_eq!(call_count.load(Ordering::SeqCst), 3);
    }

    #[tokio::test]
    async fn test_task_timeout() {
        let agent = Arc::new(MockAgent {
            response: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            fail_times: 0,
            delay: Some(Duration::from_millis(200)), // Longer than timeout
        });

        let task = Task::new(
            agent,
            TaskConfig {
                timeout: Some(Duration::from_millis(100)),
                retries: 0,
            },
        );

        let message = Message::with_text("user", "Test");
        let result = task.execute(message).await;

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AgentError::Timeout(_)));
        assert!(task.completed());
    }

    #[tokio::test]
    async fn test_task_exhausted_retries() {
        let agent = Arc::new(MockAgent {
            response: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            fail_times: 10, // Always fail
            delay: None,
        });

        let task = Task::new(
            agent,
            TaskConfig {
                timeout: None,
                retries: 2,
            },
        );

        let message = Message::with_text("user", "Test");
        let result = task.execute(message).await;

        assert!(result.is_err());
        assert!(task.completed());
    }

    #[tokio::test]
    async fn test_execute_task_convenience() {
        let agent = Arc::new(MockAgent {
            response: "Success".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            fail_times: 0,
            delay: None,
        });

        let result = execute_task(
            agent,
            Message::with_text("user", "Test"),
            TaskConfig {
                timeout: Some(Duration::from_secs(5)),
                retries: 1,
            },
        )
        .await
        .unwrap();

        assert_eq!(result.content_as_str().unwrap(), "Success");
    }

    #[tokio::test]
    async fn test_task_cleanup() {
        let agent = Arc::new(MockAgent {
            response: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            fail_times: 0,
            delay: None,
        });

        let task = Task::new(agent, TaskConfig::default());

        let message = Message::with_text("user", "Test");
        let _ = task.execute(message).await;

        // Cleanup should not panic
        task.cleanup();
    }

    #[tokio::test]
    async fn test_task_result() {
        let agent = Arc::new(MockAgent {
            response: "Test result".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
            fail_times: 0,
            delay: None,
        });

        let task = Task::new(agent, TaskConfig::default());

        // Before execution
        assert!(task.result().is_none());

        let message = Message::with_text("user", "Test");
        task.execute(message).await.unwrap();

        // After successful execution
        let result = task.result().unwrap();
        assert_eq!(result.content_as_str().unwrap(), "Test result");
    }
}
