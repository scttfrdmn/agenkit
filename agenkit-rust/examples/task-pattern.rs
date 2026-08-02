//! Task Pattern Example
//!
//! Demonstrates the Task pattern for one-shot agent execution with
//! automatic resource cleanup and lifecycle management.
//!
//! Run with: cargo run --example task_pattern

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{execute_task, Task, TaskConfig};
use async_trait::async_trait;
use std::sync::Arc;
use std::time::Duration;

/// Mock agent that simulates document summarization
struct SummarizationAgent {
    model: String,
}

#[async_trait]
impl Agent for SummarizationAgent {
    fn name(&self) -> &str {
        "Summarization"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["summarization".to_string(), "text-processing".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");

        // Simulate processing time
        tokio::time::sleep(Duration::from_millis(100)).await;

        if content.contains("document") {
            let summary = format!(
                "[{}] Summary: This document discusses key concepts and provides examples.",
                self.model
            );
            Ok(Message::with_text("assistant", summary))
        } else if content.contains("article") {
            let summary = format!(
                "[{}] Summary: The article explores recent developments in the field.",
                self.model
            );
            Ok(Message::with_text("assistant", summary))
        } else {
            let summary = format!(
                "[{}] Summary: Brief overview of the provided text.",
                self.model
            );
            Ok(Message::with_text("assistant", summary))
        }
    }
}

/// Mock agent that may fail
struct UnreliableAgent {
    fail_rate: f32,
    attempt: std::sync::Arc<std::sync::Mutex<usize>>,
}

#[async_trait]
impl Agent for UnreliableAgent {
    fn name(&self) -> &str {
        "Unreliable"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["unstable".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut attempt_count = self.attempt.lock().unwrap();
        *attempt_count += 1;
        let attempt_num = *attempt_count;

        // Fail based on fail rate and attempt number
        if attempt_num == 1 || (attempt_num == 2 && self.fail_rate > 0.5) {
            return Err(AgentError::ProcessingError(format!(
                "Attempt {} failed",
                attempt_num
            )));
        }

        let content = message.content_as_str().unwrap_or("unknown");
        Ok(Message::with_text(
            "assistant",
            format!("Processed after {} attempts: {}", attempt_num, content),
        ))
    }
}

/// Mock slow agent for timeout demonstration
struct SlowAgent {
    delay: Duration,
}

#[async_trait]
impl Agent for SlowAgent {
    fn name(&self) -> &str {
        "Slow"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["slow".to_string()]
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        tokio::time::sleep(self.delay).await;
        Ok(Message::with_text("assistant", "Completed after delay"))
    }
}

/// Example 1: Basic task execution
async fn example_basic_task() -> Result<(), AgentError> {
    println!("\n=== Example 1: Basic Task Execution ===\n");

    let agent = Arc::new(SummarizationAgent {
        model: "GPT-4".to_string(),
    });

    let task = Task::new(agent, TaskConfig::default());

    println!("Executing summarization task...");
    let message = Message::with_text("user", "Please summarize this document about AI agents.");
    let result = task.execute(message).await?;

    println!("Result: {}\n", result.content_as_str().unwrap());
    println!("Task completed: {}", task.completed());
    println!("Task has result: {}", task.result().is_some());

    // Cleanup
    task.cleanup();

    Ok(())
}

/// Example 2: Task with timeout
async fn example_timeout() -> Result<(), AgentError> {
    println!("\n=== Example 2: Task with Timeout ===\n");

    let agent = Arc::new(SlowAgent {
        delay: Duration::from_millis(500),
    });

    let task = Task::new(
        agent,
        TaskConfig {
            timeout: Some(Duration::from_millis(200)),
            retries: 0,
        },
    );

    println!("Executing task with 200ms timeout (agent takes 500ms)...");
    let message = Message::with_text("user", "Process this");
    let result = task.execute(message).await;

    match result {
        Ok(_) => println!("Task succeeded"),
        Err(e) => {
            println!("Task failed as expected: {}", e);
            if matches!(e, AgentError::Timeout(_)) {
                println!("✓ Timeout error correctly detected");
            }
        }
    }

    println!("Task marked as completed: {}\n", task.completed());

    Ok(())
}

/// Example 3: Task with retries
async fn example_retries() -> Result<(), AgentError> {
    println!("\n=== Example 3: Task with Retries ===\n");

    let attempt_counter = Arc::new(std::sync::Mutex::new(0));
    let agent = Arc::new(UnreliableAgent {
        fail_rate: 0.7,
        attempt: attempt_counter.clone(),
    });

    let task = Task::new(
        agent,
        TaskConfig {
            timeout: None,
            retries: 2,
        },
    );

    println!("Executing unreliable task with 2 retries...");
    let message = Message::with_text("user", "Test input");
    let result = task.execute(message).await?;

    let attempts = *attempt_counter.lock().unwrap();
    println!("Result: {}", result.content_as_str().unwrap());
    println!("Total attempts made: {}\n", attempts);

    Ok(())
}

/// Example 4: Cannot reuse task
async fn example_reuse_prevention() -> Result<(), AgentError> {
    println!("\n=== Example 4: Reuse Prevention ===\n");

    let agent = Arc::new(SummarizationAgent {
        model: "GPT-4".to_string(),
    });

    let task = Task::new(agent, TaskConfig::default());

    // First execution
    println!("First execution...");
    let message = Message::with_text("user", "Summarize article A");
    let result1 = task.execute(message.clone()).await?;
    println!("Result 1: {}\n", result1.content_as_str().unwrap());

    // Try to execute again
    println!("Attempting second execution on same task...");
    let result2 = task.execute(message).await;

    match result2 {
        Ok(_) => println!("Unexpectedly succeeded!"),
        Err(e) => {
            println!("Second execution failed as expected:");
            println!("Error: {}", e);
            println!("✓ Task reuse correctly prevented\n");
        }
    }

    Ok(())
}

/// Example 5: Convenience function
async fn example_convenience_function() -> Result<(), AgentError> {
    println!("\n=== Example 5: Convenience Function ===\n");

    let agent = Arc::new(SummarizationAgent {
        model: "Claude".to_string(),
    });

    println!("Using execute_task() convenience function...");

    let result = execute_task(
        agent,
        Message::with_text("user", "Summarize this document."),
        TaskConfig {
            timeout: Some(Duration::from_secs(5)),
            retries: 1,
        },
    )
    .await?;

    println!("Result: {}", result.content_as_str().unwrap());
    println!("✓ Task executed and cleaned up automatically\n");

    Ok(())
}

/// Example 6: Batch processing with tasks
async fn example_batch_processing() -> Result<(), AgentError> {
    println!("\n=== Example 6: Batch Processing ===\n");

    let documents = [
        "Process document 1 about machine learning",
        "Process document 2 about neural networks",
        "Process document 3 about deep learning",
    ];

    println!("Processing {} documents in parallel...\n", documents.len());

    let mut handles = vec![];

    for (i, doc) in documents.iter().enumerate() {
        let agent = Arc::new(SummarizationAgent {
            model: format!("Worker-{}", i + 1),
        });

        let doc_content = doc.to_string();
        let handle = tokio::spawn(async move {
            let result = execute_task(
                agent,
                Message::with_text("user", &doc_content),
                TaskConfig {
                    timeout: Some(Duration::from_secs(2)),
                    retries: 1,
                },
            )
            .await;
            (i + 1, result)
        });

        handles.push(handle);
    }

    // Wait for all tasks to complete
    for handle in handles {
        let (doc_num, result) = handle.await.unwrap();
        match result {
            Ok(message) => {
                println!(
                    "Document {}: {}",
                    doc_num,
                    message.content_as_str().unwrap()
                );
            }
            Err(e) => {
                println!("Document {}: Error - {}", doc_num, e);
            }
        }
    }

    println!("\n✓ All tasks completed\n");

    Ok(())
}

/// Example 7: Task lifecycle
async fn example_lifecycle() -> Result<(), AgentError> {
    println!("\n=== Example 7: Task Lifecycle ===\n");

    let agent = Arc::new(SummarizationAgent {
        model: "GPT-4".to_string(),
    });

    let task = Task::new(
        agent,
        TaskConfig {
            timeout: Some(Duration::from_secs(5)),
            retries: 0,
        },
    );

    println!("Initial state:");
    println!("  Completed: {}", task.completed());
    println!("  Has result: {}\n", task.result().is_some());

    println!("Executing task...");
    let message = Message::with_text("user", "Summarize document");
    task.execute(message).await?;

    println!("\nAfter execution:");
    println!("  Completed: {}", task.completed());
    println!("  Has result: {}", task.result().is_some());

    if let Some(result) = task.result() {
        println!("  Result content: {}", result.content_as_str().unwrap());
    }

    println!("\nPerforming cleanup...");
    task.cleanup();
    println!("✓ Lifecycle complete\n");

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    println!("Task Pattern Examples");
    println!("====================");

    // Run all examples
    example_basic_task().await?;
    example_timeout().await?;
    example_retries().await?;
    example_reuse_prevention().await?;
    example_convenience_function().await?;
    example_batch_processing().await?;
    example_lifecycle().await?;

    println!("✓ All examples completed successfully!");

    Ok(())
}
