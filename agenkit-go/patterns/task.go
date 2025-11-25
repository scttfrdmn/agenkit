// Package patterns provides the Task pattern for one-shot agent execution.
//
// This module provides the Task pattern, which wraps an Agent for single-use
// execution with automatic resource cleanup.
//
// Key features:
//   - One-shot execution semantics
//   - Automatic resource cleanup
//   - Timeout support
//   - Retry logic with exponential backoff
//   - Prevention of reuse after completion
//
// Example:
//
//	// Basic usage
//	task := patterns.NewTask(agent, &patterns.TaskConfig{
//	    Timeout: 30 * time.Second,
//	    Retries: 2,
//	})
//	result, err := task.Execute(ctx, message)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	task.Cleanup()
//
//	// With automatic cleanup
//	result, err := patterns.ExecuteTask(ctx, agent, message, &patterns.TaskConfig{
//	    Timeout: 30 * time.Second,
//	    Retries: 2,
//	})
//
// Performance characteristics:
//   - O(1) execution
//   - O(retries) retry attempts
//   - Automatic cleanup prevents resource leaks
package patterns

import (
	"context"
	"fmt"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TaskConfig configures a Task.
type TaskConfig struct {
	// Timeout for task execution (0 means no timeout)
	Timeout time.Duration
	// Retries is the number of retry attempts on failure (default: 0)
	Retries int
}

// Task provides one-shot agent execution with lifecycle management.
//
// A Task wraps an Agent for single-use execution, providing:
//   - Explicit one-shot semantics
//   - Automatic resource cleanup
//   - Task-specific configuration (timeout, retries)
//   - Prevention of reuse after completion
//
// Key distinction:
//   - **Agent**: Multi-turn conversation with state
//   - **Task**: One-shot execution, then cleanup
//
// Use Task when:
//   - Single purpose operation that needs cleanup
//   - You want explicit resource management
//   - You need timeout/retry at task level
//
// Examples: summarize_document, classify_text, extract_entities
type Task struct {
	agent     agenkit.Agent
	timeout   time.Duration
	retries   int
	completed bool
	result    *agenkit.Message
}

// TaskError wraps errors from task execution.
type TaskError struct {
	Message string
	Cause   error
}

func (e *TaskError) Error() string {
	if e.Cause != nil {
		return fmt.Sprintf("%s: %v", e.Message, e.Cause)
	}
	return e.Message
}

func (e *TaskError) Unwrap() error {
	return e.Cause
}

// TimeoutError indicates task execution exceeded timeout.
type TimeoutError struct {
	Duration time.Duration
}

func (e *TimeoutError) Error() string {
	return fmt.Sprintf("task timed out after %v", e.Duration)
}

// NewTask creates a new Task.
func NewTask(agent agenkit.Agent, config *TaskConfig) *Task {
	if config == nil {
		config = &TaskConfig{}
	}

	return &Task{
		agent:     agent,
		timeout:   config.Timeout,
		retries:   config.Retries,
		completed: false,
		result:    nil,
	}
}

// Execute executes the task once.
//
// This method can only be called once per Task instance. After execution
// completes (successfully or with error), the Task is marked as completed
// and cannot be reused.
//
// Returns an error if task already completed or execution fails.
func (t *Task) Execute(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if t.completed {
		return nil, &TaskError{
			Message: "task already completed. Create a new Task for another execution",
		}
	}

	attempts := t.retries + 1 // retries=0 means 1 attempt
	var lastError error

	for attempt := 0; attempt < attempts; attempt++ {
		// Create context with timeout if specified
		execCtx := ctx
		var cancel context.CancelFunc
		if t.timeout > 0 {
			execCtx, cancel = context.WithTimeout(ctx, t.timeout)
			defer cancel()
		}

		// Execute the agent
		result, err := t.agent.Process(execCtx, message)

		if err == nil {
			// Success - mark completed and return
			t.completed = true
			t.result = result
			return result, nil
		}

		lastError = err

		// Check if it was a timeout
		if execCtx.Err() == context.DeadlineExceeded {
			t.completed = true
			t.Cleanup()
			return nil, &TimeoutError{Duration: t.timeout}
		}

		// If this was the last attempt, fail
		if attempt == attempts-1 {
			t.completed = true
			t.Cleanup()
			return nil, &TaskError{
				Message: fmt.Sprintf("task execution failed after %d attempts", attempts),
				Cause:   lastError,
			}
		}

		// Otherwise, retry after exponential backoff
		backoff := time.Duration(100*(attempt+1)) * time.Millisecond
		select {
		case <-time.After(backoff):
			// Continue to next retry
		case <-ctx.Done():
			// Context cancelled, abort
			t.completed = true
			t.Cleanup()
			return nil, &TaskError{
				Message: "task cancelled during retry backoff",
				Cause:   ctx.Err(),
			}
		}
	}

	// Should never reach here, but just in case
	t.completed = true
	t.Cleanup()
	return nil, &TaskError{
		Message: "task execution failed",
		Cause:   lastError,
	}
}

// Cleanup cleans up resources after task completion.
//
// This method is called automatically when:
//   - Task execution fails with an error
//   - Using ExecuteTask() (automatic cleanup)
//
// You can also call it manually after successful execution.
//
// Override this method in custom implementations to add cleanup logic:
//   - Close network connections
//   - Release memory/resources
//   - Save state to disk
//   - Send telemetry
func (t *Task) Cleanup() {
	// Default implementation - hook for custom implementations
	// Could close agent connections, release middleware resources, etc.
}

// Completed returns whether the task has been completed.
func (t *Task) Completed() bool {
	return t.completed
}

// Result returns the result of the task (if completed successfully).
func (t *Task) Result() *agenkit.Message {
	return t.result
}

// ExecuteTask executes a task with automatic cleanup.
//
// Convenience function that wraps Task creation, execution, and cleanup.
//
// Example:
//
//	result, err := patterns.ExecuteTask(ctx, agent, message, &patterns.TaskConfig{
//	    Timeout: 30 * time.Second,
//	    Retries: 2,
//	})
func ExecuteTask(ctx context.Context, agent agenkit.Agent, message *agenkit.Message, config *TaskConfig) (*agenkit.Message, error) {
	task := NewTask(agent, config)
	result, err := task.Execute(ctx, message)
	task.Cleanup()
	return result, err
}
