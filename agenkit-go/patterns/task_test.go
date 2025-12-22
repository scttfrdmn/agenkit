package patterns

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockTaskAgent is a mock agent for testing tasks.
type mockTaskAgent struct {
	name        string
	response    string
	err         error
	delay       time.Duration
	callCount   int
	shouldBlock bool
}

func (m *mockTaskAgent) Name() string {
	return m.name
}

func (m *mockTaskAgent) Capabilities() []string {
	return []string{"test"}
}

func (m *mockTaskAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *mockTaskAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	m.callCount++

	// Simulate delay if specified
	if m.delay > 0 {
		select {
		case <-time.After(m.delay):
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}

	// Block if requested (for timeout testing)
	if m.shouldBlock {
		<-ctx.Done()
		return nil, ctx.Err()
	}

	// Return error if specified
	if m.err != nil {
		return nil, m.err
	}

	return &agenkit.Message{
		Role:    "assistant",
		Content: m.response,
	}, nil
}

// ============================================================================
// Basic Execution Tests
// ============================================================================

func TestTask_BasicExecution(t *testing.T) {
	agent := &mockTaskAgent{name: "test", response: "Hello"}
	task := NewTask(agent, nil)

	result, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Content != "Hello" {
		t.Errorf("expected 'Hello', got %s", result.Content)
	}
	if !task.Completed() {
		t.Error("expected task to be completed")
	}
	if task.Result().Content != "Hello" {
		t.Error("expected result to be stored")
	}
}

func TestTask_CannotReuseAfterCompletion(t *testing.T) {
	agent := &mockTaskAgent{name: "test", response: "Hello"}
	task := NewTask(agent, nil)

	// First execution succeeds
	_, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})
	if err != nil {
		t.Fatalf("first execution failed: %v", err)
	}

	// Second execution should fail
	_, err = task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test2",
	})
	if err == nil {
		t.Error("expected error on reuse, got nil")
	}
	if !strings.Contains(err.Error(), "already completed") {
		t.Errorf("expected 'already completed' error, got %v", err)
	}
}

func TestTask_WithConfig(t *testing.T) {
	agent := &mockTaskAgent{name: "test", response: "Hello"}
	task := NewTask(agent, &TaskConfig{
		Timeout: 5 * time.Second,
		Retries: 2,
	})

	result, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Content != "Hello" {
		t.Errorf("expected 'Hello', got %s", result.Content)
	}
}

// ============================================================================
// Timeout Tests
// ============================================================================

func TestTask_Timeout(t *testing.T) {
	agent := &mockTaskAgent{
		name:        "test",
		response:    "Hello",
		shouldBlock: true,
	}
	task := NewTask(agent, &TaskConfig{
		Timeout: 100 * time.Millisecond,
	})

	_, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err == nil {
		t.Fatal("expected timeout error, got nil")
	}

	var timeoutErr *TimeoutError
	if !errors.As(err, &timeoutErr) {
		t.Errorf("expected TimeoutError, got %T: %v", err, err)
	}

	if !task.Completed() {
		t.Error("expected task to be marked completed after timeout")
	}
}

func TestTask_NoTimeout(t *testing.T) {
	agent := &mockTaskAgent{
		name:     "test",
		response: "Hello",
		delay:    50 * time.Millisecond,
	}
	task := NewTask(agent, &TaskConfig{
		Timeout: 0, // No timeout
	})

	result, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Content != "Hello" {
		t.Errorf("expected 'Hello', got %s", result.Content)
	}
}

// ============================================================================
// Retry Tests
// ============================================================================

func TestTask_RetryOnFailure(t *testing.T) {
	agent := &mockTaskAgent{
		name:     "test",
		response: "Success",
		err:      errors.New("temporary failure"),
	}
	task := NewTask(agent, &TaskConfig{
		Retries: 2,
	})

	// First 2 attempts fail, but we only have 2 retries (3 total attempts)
	_, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err == nil {
		t.Fatal("expected error after retries exhausted")
	}

	// Should have tried 3 times (initial + 2 retries)
	if agent.callCount != 3 {
		t.Errorf("expected 3 attempts, got %d", agent.callCount)
	}

	var taskErr *TaskError
	if !errors.As(err, &taskErr) {
		t.Errorf("expected TaskError, got %T", err)
	}
}

func TestTask_RetrySucceedsOnSecondAttempt(t *testing.T) {
	// Agent that fails on first call, succeeds on second
	agent := &mockFailThenSucceedAgent{
		response:    "Success",
		failCount:   1,
		currentCall: 0,
	}

	task := NewTask(agent, &TaskConfig{
		Retries: 2,
	})

	result, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "Success" {
		t.Errorf("expected 'Success', got %s", result.Content)
	}

	// Should have tried 2 times (first fail, second success)
	if agent.currentCall != 2 {
		t.Errorf("expected 2 attempts, got %d", agent.currentCall)
	}
}

// mockFailThenSucceedAgent fails for first N calls, then succeeds
type mockFailThenSucceedAgent struct {
	response    string
	failCount   int
	currentCall int
}

func (m *mockFailThenSucceedAgent) Name() string {
	return "fail-then-succeed"
}

func (m *mockFailThenSucceedAgent) Capabilities() []string {
	return []string{"test"}
}

func (m *mockFailThenSucceedAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *mockFailThenSucceedAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	m.currentCall++
	if m.currentCall <= m.failCount {
		return nil, errors.New("intentional failure")
	}
	return &agenkit.Message{
		Role:    "assistant",
		Content: m.response,
	}, nil
}

func TestTask_NoRetries(t *testing.T) {
	agent := &mockTaskAgent{
		name: "test",
		err:  errors.New("failure"),
	}
	task := NewTask(agent, &TaskConfig{
		Retries: 0,
	})

	_, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err == nil {
		t.Fatal("expected error, got nil")
	}

	// Should have tried only once
	if agent.callCount != 1 {
		t.Errorf("expected 1 attempt, got %d", agent.callCount)
	}
}

// ============================================================================
// Cleanup Tests
// ============================================================================

func TestTask_CleanupDoesNotPanic(t *testing.T) {
	agent := &mockTaskAgent{name: "test", response: "Hello"}
	task := NewTask(agent, nil)

	result, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Content != "Hello" {
		t.Errorf("expected 'Hello', got %s", result.Content)
	}

	// Manually call cleanup - should not panic
	task.Cleanup()
}

// ============================================================================
// ExecuteTask Helper Tests
// ============================================================================

func TestExecuteTask_Success(t *testing.T) {
	agent := &mockTaskAgent{name: "test", response: "Hello"}

	result, err := ExecuteTask(context.Background(), agent, &agenkit.Message{
		Role:    "user",
		Content: "Test",
	}, nil)

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Content != "Hello" {
		t.Errorf("expected 'Hello', got %s", result.Content)
	}
}

func TestExecuteTask_WithTimeout(t *testing.T) {
	agent := &mockTaskAgent{
		name:        "test",
		response:    "Hello",
		shouldBlock: true,
	}

	_, err := ExecuteTask(context.Background(), agent, &agenkit.Message{
		Role:    "user",
		Content: "Test",
	}, &TaskConfig{
		Timeout: 100 * time.Millisecond,
	})

	if err == nil {
		t.Fatal("expected timeout error, got nil")
	}

	var timeoutErr *TimeoutError
	if !errors.As(err, &timeoutErr) {
		t.Errorf("expected TimeoutError, got %T", err)
	}
}

func TestExecuteTask_WithRetries(t *testing.T) {
	agent := &mockTaskAgent{
		name: "test",
		err:  errors.New("failure"),
	}

	_, err := ExecuteTask(context.Background(), agent, &agenkit.Message{
		Role:    "user",
		Content: "Test",
	}, &TaskConfig{
		Retries: 2,
	})

	if err == nil {
		t.Fatal("expected error, got nil")
	}

	// Should have tried 3 times
	if agent.callCount != 3 {
		t.Errorf("expected 3 attempts, got %d", agent.callCount)
	}
}

// ============================================================================
// Context Cancellation Tests
// ============================================================================

func TestTask_ContextCancellation(t *testing.T) {
	agent := &mockTaskAgent{
		name:        "test",
		response:    "Hello",
		shouldBlock: true,
	}
	task := NewTask(agent, nil)

	ctx, cancel := context.WithCancel(context.Background())

	// Cancel immediately
	cancel()

	_, err := task.Execute(ctx, &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err == nil {
		t.Fatal("expected context cancellation error, got nil")
	}

	if !task.Completed() {
		t.Error("expected task to be marked completed after cancellation")
	}
}

func TestTask_ContextCancellationDuringRetry(t *testing.T) {
	agent := &mockTaskAgent{
		name: "test",
		err:  errors.New("failure"),
	}
	task := NewTask(agent, &TaskConfig{
		Retries: 5,
	})

	ctx, cancel := context.WithCancel(context.Background())

	// Start execution
	errCh := make(chan error, 1)
	go func() {
		_, err := task.Execute(ctx, &agenkit.Message{
			Role:    "user",
			Content: "Test",
		})
		errCh <- err
	}()

	// Wait for first attempt to fail and retry to start
	time.Sleep(150 * time.Millisecond)

	// Cancel context during backoff
	cancel()

	// Wait for error
	err := <-errCh
	if err == nil {
		t.Fatal("expected error, got nil")
	}

	if !strings.Contains(err.Error(), "cancelled") {
		t.Errorf("expected cancellation error, got %v", err)
	}
}

// ============================================================================
// Edge Cases
// ============================================================================

func TestTask_NilConfig(t *testing.T) {
	agent := &mockTaskAgent{name: "test", response: "Hello"}
	task := NewTask(agent, nil)

	result, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Content != "Hello" {
		t.Errorf("expected 'Hello', got %s", result.Content)
	}
}

func TestTask_ResultAccessBeforeCompletion(t *testing.T) {
	agent := &mockTaskAgent{name: "test", response: "Hello"}
	task := NewTask(agent, nil)

	if task.Result() != nil {
		t.Error("expected nil result before execution")
	}

	_, _ = task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if task.Result() == nil {
		t.Error("expected non-nil result after execution")
	}
}

func TestTask_CompletedProperty(t *testing.T) {
	agent := &mockTaskAgent{name: "test", response: "Hello"}
	task := NewTask(agent, nil)

	if task.Completed() {
		t.Error("expected task not completed initially")
	}

	_, _ = task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if !task.Completed() {
		t.Error("expected task completed after execution")
	}
}

func TestTask_ErrorTypes(t *testing.T) {
	// Test TaskError
	agent := &mockTaskAgent{
		name: "test",
		err:  errors.New("test error"),
	}
	task := NewTask(agent, &TaskConfig{Retries: 0})

	_, err := task.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	var taskErr *TaskError
	if !errors.As(err, &taskErr) {
		t.Errorf("expected TaskError, got %T", err)
	}
	if taskErr.Unwrap() == nil {
		t.Error("expected TaskError to wrap original error")
	}

	// Test TimeoutError
	agent2 := &mockTaskAgent{
		name:        "test",
		shouldBlock: true,
	}
	task2 := NewTask(agent2, &TaskConfig{
		Timeout: 100 * time.Millisecond,
	})

	_, err2 := task2.Execute(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	var timeoutErr *TimeoutError
	if !errors.As(err2, &timeoutErr) {
		t.Errorf("expected TimeoutError, got %T", err2)
	}
}
