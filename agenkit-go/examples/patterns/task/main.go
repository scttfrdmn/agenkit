// Package main demonstrates the Task pattern for one-shot agent execution.
//
// The Task pattern provides lifecycle management for single-execution agents
// with automatic resource cleanup, timeout handling, and retry logic.
//
// This example shows:
//   - Basic task execution with lifecycle management
//   - Timeout handling for long-running tasks
//   - Retry logic for unreliable operations
//   - Task reuse prevention
//   - Batch processing with concurrent tasks
//
// Run with: go run task_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// SummarizationAgent simulates document summarization
type SummarizationAgent struct {
	model string
}

func (s *SummarizationAgent) Name() string {
	return "Summarization"
}

func (s *SummarizationAgent) Capabilities() []string {
	return []string{"summarization", "text-processing"}
}

func (s *SummarizationAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    s.Name(),
		Capabilities: s.Capabilities(),
	}
}

func (s *SummarizationAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content

	// Simulate processing time
	time.Sleep(100 * time.Millisecond)

	var summary string
	if strings.Contains(content, "document") {
		summary = fmt.Sprintf("[%s] Summary: This document discusses key concepts and provides examples.", s.model)
	} else if strings.Contains(content, "article") {
		summary = fmt.Sprintf("[%s] Summary: The article explores recent developments in the field.", s.model)
	} else {
		summary = fmt.Sprintf("[%s] Summary: Brief overview of the provided text.", s.model)
	}

	return agenkit.NewMessage("assistant", summary), nil
}

// UnreliableAgent simulates an agent that may fail
type UnreliableAgent struct {
	failRate int
	attempt  int
	mu       sync.Mutex
}

func (u *UnreliableAgent) Name() string {
	return "Unreliable"
}

func (u *UnreliableAgent) Capabilities() []string {
	return []string{"unstable"}
}

func (u *UnreliableAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    u.Name(),
		Capabilities: u.Capabilities(),
	}
}

func (u *UnreliableAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	u.mu.Lock()
	u.attempt++
	attemptNum := u.attempt
	u.mu.Unlock()

	// Fail based on fail rate and attempt number
	if attemptNum == 1 || (attemptNum == 2 && u.failRate > 50) {
		return nil, fmt.Errorf("attempt %d failed", attemptNum)
	}

	content := message.Content
	result := fmt.Sprintf("Processed after %d attempts: %s", attemptNum, content)
	return agenkit.NewMessage("assistant", result), nil
}

// SlowAgent simulates a slow operation
type SlowAgent struct {
	delay time.Duration
}

func (s *SlowAgent) Name() string {
	return "Slow"
}

func (s *SlowAgent) Capabilities() []string {
	return []string{"slow"}
}

func (s *SlowAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    s.Name(),
		Capabilities: s.Capabilities(),
	}
}

func (s *SlowAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(s.delay)
	return agenkit.NewMessage("assistant", "Completed after delay"), nil
}

// Example 1: Basic task execution
func exampleBasicTask() error {
	fmt.Println("\n=== Example 1: Basic Task Execution ===")

	agent := &SummarizationAgent{model: "GPT-4"}

	config := patterns.TaskConfig{
		Timeout: 0,
		Retries: 0,
	}

	task := patterns.NewTask(agent, &config)

	fmt.Println("Executing summarization task...")
	message := agenkit.NewMessage("user", "Please summarize this document about AI agents.")
	result, err := task.Execute(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("Result: %s\n\n", result.Content)
	fmt.Printf("Task completed: %t\n", task.Completed())
	fmt.Printf("Task has result: %t\n", task.Result() != nil)

	// Cleanup
	task.Cleanup()

	return nil
}

// Example 2: Task with timeout
func exampleTimeout() error {
	fmt.Println("\n=== Example 2: Task with Timeout ===")

	agent := &SlowAgent{delay: 500 * time.Millisecond}

	config := patterns.TaskConfig{
		Timeout: 200 * time.Millisecond,
		Retries: 0,
	}

	task := patterns.NewTask(agent, &config)

	fmt.Println("Executing task with 200ms timeout (agent takes 500ms)...")
	message := agenkit.NewMessage("user", "Process this")
	_, err := task.Execute(context.Background(), message)

	if err != nil {
		fmt.Printf("Task failed as expected: %v\n", err)
		if strings.Contains(err.Error(), "timeout") || strings.Contains(err.Error(), "context deadline exceeded") {
			fmt.Println("✓ Timeout error correctly detected")
		}
	} else {
		fmt.Println("Task succeeded")
	}

	fmt.Printf("Task marked as completed: %t\n\n", task.Completed())

	return nil
}

// Example 3: Task with retries
func exampleRetries() error {
	fmt.Println("\n=== Example 3: Task with Retries ===")

	agent := &UnreliableAgent{failRate: 70}

	config := patterns.TaskConfig{
		Timeout: 0,
		Retries: 2,
	}

	task := patterns.NewTask(agent, &config)

	fmt.Println("Executing unreliable task with 2 retries...")
	message := agenkit.NewMessage("user", "Test input")
	result, err := task.Execute(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("Result: %s\n", result.Content)
	fmt.Printf("Total attempts made: %d\n\n", agent.attempt)

	return nil
}

// Example 4: Cannot reuse task
func exampleReusePrevention() error {
	fmt.Println("\n=== Example 4: Reuse Prevention ===")

	agent := &SummarizationAgent{model: "GPT-4"}

	config := patterns.TaskConfig{
		Timeout: 0,
		Retries: 0,
	}

	task := patterns.NewTask(agent, &config)

	// First execution
	fmt.Println("First execution...")
	message := agenkit.NewMessage("user", "Summarize article A")
	result1, err := task.Execute(context.Background(), message)
	if err != nil {
		return err
	}
	fmt.Printf("Result 1: %s\n\n", result1.Content)

	// Try to execute again
	fmt.Println("Attempting second execution on same task...")
	_, err = task.Execute(context.Background(), message)

	if err != nil {
		fmt.Println("Second execution failed as expected:")
		fmt.Printf("Error: %v\n", err)
		fmt.Println("✓ Task reuse correctly prevented")
	} else {
		fmt.Println("Unexpectedly succeeded!")
	}

	return nil
}

// Example 5: Convenience function
func exampleConvenienceFunction() error {
	fmt.Println("\n=== Example 5: Convenience Function ===")

	agent := &SummarizationAgent{model: "Claude"}

	fmt.Println("Using ExecuteTask() convenience function...")

	config := patterns.TaskConfig{
		Timeout: 5 * time.Second,
		Retries: 1,
	}

	result, err := patterns.ExecuteTask(
		context.Background(),
		agent,
		agenkit.NewMessage("user", "Summarize this document."),
		&config,
	)
	if err != nil {
		return err
	}

	fmt.Printf("Result: %s\n", result.Content)
	fmt.Println("✓ Task executed and cleaned up automatically")

	return nil
}

// Example 6: Batch processing with tasks
func exampleBatchProcessing() error {
	fmt.Println("\n=== Example 6: Batch Processing ===")

	documents := []string{
		"Process document 1 about machine learning",
		"Process document 2 about neural networks",
		"Process document 3 about deep learning",
	}

	fmt.Printf("Processing %d documents in parallel...\n\n", len(documents))

	type result struct {
		docNum  int
		message *agenkit.Message
		err     error
	}

	results := make(chan result, len(documents))
	var wg sync.WaitGroup

	for i, doc := range documents {
		wg.Add(1)
		go func(docNum int, docContent string) {
			defer wg.Done()

			agent := &SummarizationAgent{model: fmt.Sprintf("Worker-%d", docNum+1)}
			config := patterns.TaskConfig{
				Timeout: 2 * time.Second,
				Retries: 1,
			}

			msg, err := patterns.ExecuteTask(
				context.Background(),
				agent,
				agenkit.NewMessage("user", docContent),
				&config,
			)

			results <- result{docNum: docNum + 1, message: msg, err: err}
		}(i, doc)
	}

	// Wait for all tasks to complete
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect results
	for res := range results {
		if res.err != nil {
			fmt.Printf("Document %d: Error - %v\n", res.docNum, res.err)
		} else {
			fmt.Printf("Document %d: %s\n", res.docNum, res.message.Content)
		}
	}

	fmt.Println("\n✓ All tasks completed")

	return nil
}

// Example 7: Task lifecycle
func exampleLifecycle() error {
	fmt.Println("\n=== Example 7: Task Lifecycle ===")

	agent := &SummarizationAgent{model: "GPT-4"}

	config := patterns.TaskConfig{
		Timeout: 5 * time.Second,
		Retries: 0,
	}

	task := patterns.NewTask(agent, &config)

	fmt.Println("Initial state:")
	fmt.Printf("  Completed: %t\n", task.Completed())
	fmt.Printf("  Has result: %t\n\n", task.Result() != nil)

	fmt.Println("Executing task...")
	message := agenkit.NewMessage("user", "Summarize document")
	_, err := task.Execute(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Println("\nAfter execution:")
	fmt.Printf("  Completed: %t\n", task.Completed())
	fmt.Printf("  Has result: %t\n", task.Result() != nil)

	if result := task.Result(); result != nil {
		fmt.Printf("  Result content: %s\n", result.Content)
	}

	fmt.Println("\nPerforming cleanup...")
	task.Cleanup()
	fmt.Println("✓ Lifecycle complete")

	return nil
}

func main() {
	fmt.Println("Task Pattern Examples")
	fmt.Println(strings.Repeat("=", 60))

	// Run all examples
	if err := exampleBasicTask(); err != nil {
		log.Fatalf("Example 1 failed: %v", err)
	}

	if err := exampleTimeout(); err != nil {
		log.Fatalf("Example 2 failed: %v", err)
	}

	if err := exampleRetries(); err != nil {
		log.Fatalf("Example 3 failed: %v", err)
	}

	if err := exampleReusePrevention(); err != nil {
		log.Fatalf("Example 4 failed: %v", err)
	}

	if err := exampleConvenienceFunction(); err != nil {
		log.Fatalf("Example 5 failed: %v", err)
	}

	if err := exampleBatchProcessing(); err != nil {
		log.Fatalf("Example 6 failed: %v", err)
	}

	if err := exampleLifecycle(); err != nil {
		log.Fatalf("Example 7 failed: %v", err)
	}

	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("✓ All examples completed successfully!")
	fmt.Println("\n💡 Key takeaways:")
	fmt.Println("   - Tasks provide one-shot execution with cleanup")
	fmt.Println("   - Timeout protection prevents hanging operations")
	fmt.Println("   - Retry logic handles transient failures")
	fmt.Println("   - Reuse prevention ensures task safety")
	fmt.Println()
	fmt.Println("🎯 When to use Task:")
	fmt.Println("   - One-time agent invocations")
	fmt.Println("   - Batch processing with concurrent execution")
	fmt.Println("   - Operations requiring timeout/retry handling")
	fmt.Println("   - Scenarios needing explicit lifecycle management")
}
