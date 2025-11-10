package middleware

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// FailingAgent fails a specified number of times before succeeding.
type FailingAgent struct {
	failCount   int
	attempts    int
	successMsg  string
	failureMsg  string
}

func (f *FailingAgent) Name() string {
	return "failing-agent"
}

func (f *FailingAgent) Capabilities() []string {
	return []string{}
}

func (f *FailingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	f.attempts++
	if f.attempts <= f.failCount {
		return nil, errors.New(f.failureMsg)
	}
	return agenkit.NewMessage("agent", f.successMsg), nil
}

func TestRetrySuccess(t *testing.T) {
	ctx := context.Background()

	// Agent that fails twice then succeeds
	agent := &FailingAgent{
		failCount:   2,
		successMsg:  "success after retries",
		failureMsg:  "temporary failure",
	}

	retry := NewRetryDecorator(agent, RetryConfig{
		MaxAttempts:       3,
		InitialBackoff:    10 * time.Millisecond,
		BackoffMultiplier: 2.0,
	})

	msg := agenkit.NewMessage("user", "test")
	response, err := retry.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Expected success after retries, got error: %v", err)
	}

	if response.Content != "success after retries" {
		t.Errorf("Expected content 'success after retries', got '%s'", response.Content)
	}

	if agent.attempts != 3 {
		t.Errorf("Expected 3 attempts, got %d", agent.attempts)
	}
}

func TestRetryMaxAttemptsExceeded(t *testing.T) {
	ctx := context.Background()

	// Agent that always fails
	agent := &FailingAgent{
		failCount:   10,
		successMsg:  "should not succeed",
		failureMsg:  "persistent failure",
	}

	retry := NewRetryDecorator(agent, RetryConfig{
		MaxAttempts:       3,
		InitialBackoff:    10 * time.Millisecond,
		BackoffMultiplier: 2.0,
	})

	msg := agenkit.NewMessage("user", "test")
	_, err := retry.Process(ctx, msg)

	if err == nil {
		t.Fatal("Expected error after max retries, got nil")
	}

	if agent.attempts != 3 {
		t.Errorf("Expected 3 attempts, got %d", agent.attempts)
	}

	// Verify error message contains attempt count
	expectedMsg := "max retry attempts (3) exceeded"
	if !contains(err.Error(), expectedMsg) {
		t.Errorf("Expected error containing '%s', got '%s'", expectedMsg, err.Error())
	}
}

func TestRetryFirstAttemptSuccess(t *testing.T) {
	ctx := context.Background()

	// Agent that succeeds immediately
	agent := &FailingAgent{
		failCount:   0,
		successMsg:  "immediate success",
		failureMsg:  "",
	}

	retry := NewRetryDecorator(agent, DefaultRetryConfig())

	msg := agenkit.NewMessage("user", "test")
	response, err := retry.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Expected immediate success, got error: %v", err)
	}

	if response.Content != "immediate success" {
		t.Errorf("Expected content 'immediate success', got '%s'", response.Content)
	}

	if agent.attempts != 1 {
		t.Errorf("Expected 1 attempt, got %d", agent.attempts)
	}
}

func TestRetryContextCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())

	// Agent that always fails
	agent := &FailingAgent{
		failCount:   10,
		successMsg:  "should not succeed",
		failureMsg:  "persistent failure",
	}

	retry := NewRetryDecorator(agent, RetryConfig{
		MaxAttempts:       5,
		InitialBackoff:    50 * time.Millisecond,
		BackoffMultiplier: 2.0,
	})

	// Cancel after first failure
	go func() {
		time.Sleep(60 * time.Millisecond)
		cancel()
	}()

	msg := agenkit.NewMessage("user", "test")
	_, err := retry.Process(ctx, msg)

	if err == nil {
		t.Fatal("Expected error due to context cancellation, got nil")
	}

	// Should fail early due to cancellation
	if agent.attempts >= 5 {
		t.Errorf("Expected fewer than 5 attempts due to cancellation, got %d", agent.attempts)
	}

	// Verify error mentions cancellation
	if !contains(err.Error(), "retry cancelled") {
		t.Errorf("Expected error containing 'retry cancelled', got '%s'", err.Error())
	}
}

func TestRetryExponentialBackoff(t *testing.T) {
	ctx := context.Background()

	// Agent that fails twice
	agent := &FailingAgent{
		failCount:   2,
		successMsg:  "success",
		failureMsg:  "failure",
	}

	start := time.Now()

	retry := NewRetryDecorator(agent, RetryConfig{
		MaxAttempts:       3,
		InitialBackoff:    100 * time.Millisecond,
		BackoffMultiplier: 2.0,
	})

	msg := agenkit.NewMessage("user", "test")
	_, err := retry.Process(ctx, msg)

	duration := time.Since(start)

	if err != nil {
		t.Fatalf("Expected success, got error: %v", err)
	}

	// Expected: ~100ms (first backoff) + ~200ms (second backoff) = ~300ms
	// Allow some tolerance
	expectedMin := 250 * time.Millisecond
	expectedMax := 400 * time.Millisecond

	if duration < expectedMin || duration > expectedMax {
		t.Errorf("Expected duration between %v and %v, got %v", expectedMin, expectedMax, duration)
	}
}

func TestRetryMaxBackoff(t *testing.T) {
	ctx := context.Background()

	// Agent that fails 3 times
	agent := &FailingAgent{
		failCount:   3,
		successMsg:  "success",
		failureMsg:  "failure",
	}

	retry := NewRetryDecorator(agent, RetryConfig{
		MaxAttempts:       4,
		InitialBackoff:    100 * time.Millisecond,
		MaxBackoff:        150 * time.Millisecond, // Cap backoff at 150ms
		BackoffMultiplier: 3.0,                    // Would be 300ms without cap
	})

	start := time.Now()

	msg := agenkit.NewMessage("user", "test")
	_, err := retry.Process(ctx, msg)

	duration := time.Since(start)

	if err != nil {
		t.Fatalf("Expected success, got error: %v", err)
	}

	// Expected: ~100ms + ~150ms (capped) + ~150ms (capped) = ~400ms
	expectedMin := 350 * time.Millisecond
	expectedMax := 500 * time.Millisecond

	if duration < expectedMin || duration > expectedMax {
		t.Errorf("Expected duration between %v and %v (with backoff cap), got %v", expectedMin, expectedMax, duration)
	}
}

// RetriableError is an error that should trigger retries.
type RetriableError struct {
	message string
}

func (e *RetriableError) Error() string {
	return e.message
}

// NonRetriableError is an error that should not trigger retries.
type NonRetriableError struct {
	message string
}

func (e *NonRetriableError) Error() string {
	return e.message
}

// SelectiveFailingAgent can return different error types.
type SelectiveFailingAgent struct {
	errorType string
	attempts  int
}

func (s *SelectiveFailingAgent) Name() string {
	return "selective-failing-agent"
}

func (s *SelectiveFailingAgent) Capabilities() []string {
	return []string{}
}

func (s *SelectiveFailingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	s.attempts++
	if s.errorType == "retriable" {
		return nil, &RetriableError{message: "retriable error"}
	}
	return nil, &NonRetriableError{message: "non-retriable error"}
}

func TestRetryShouldRetryPredicate(t *testing.T) {
	ctx := context.Background()

	// Test retriable error
	retriableAgent := &SelectiveFailingAgent{errorType: "retriable"}
	retry := NewRetryDecorator(retriableAgent, RetryConfig{
		MaxAttempts:    3,
		InitialBackoff: 10 * time.Millisecond,
		ShouldRetry: func(err error) bool {
			_, ok := err.(*RetriableError)
			return ok
		},
	})

	msg := agenkit.NewMessage("user", "test")
	_, err := retry.Process(ctx, msg)

	if err == nil {
		t.Fatal("Expected error after max retries")
	}

	if retriableAgent.attempts != 3 {
		t.Errorf("Retriable error: expected 3 attempts, got %d", retriableAgent.attempts)
	}

	// Test non-retriable error
	nonRetriableAgent := &SelectiveFailingAgent{errorType: "non-retriable"}
	retry2 := NewRetryDecorator(nonRetriableAgent, RetryConfig{
		MaxAttempts:    3,
		InitialBackoff: 10 * time.Millisecond,
		ShouldRetry: func(err error) bool {
			_, ok := err.(*RetriableError)
			return ok
		},
	})

	_, err = retry2.Process(ctx, msg)

	if err == nil {
		t.Fatal("Expected error for non-retriable error")
	}

	if nonRetriableAgent.attempts != 1 {
		t.Errorf("Non-retriable error: expected 1 attempt, got %d", nonRetriableAgent.attempts)
	}

	if !contains(err.Error(), "non-retryable error") {
		t.Errorf("Expected error containing 'non-retryable error', got '%s'", err.Error())
	}
}

func TestRetryDefaultConfig(t *testing.T) {
	config := DefaultRetryConfig()

	if config.MaxAttempts != 3 {
		t.Errorf("Expected MaxAttempts=3, got %d", config.MaxAttempts)
	}

	if config.InitialBackoff != 100*time.Millisecond {
		t.Errorf("Expected InitialBackoff=100ms, got %v", config.InitialBackoff)
	}

	if config.MaxBackoff != 10*time.Second {
		t.Errorf("Expected MaxBackoff=10s, got %v", config.MaxBackoff)
	}

	if config.BackoffMultiplier != 2.0 {
		t.Errorf("Expected BackoffMultiplier=2.0, got %f", config.BackoffMultiplier)
	}

	if config.ShouldRetry != nil {
		t.Error("Expected ShouldRetry=nil")
	}
}

func TestRetryZeroValues(t *testing.T) {
	ctx := context.Background()

	agent := &FailingAgent{
		failCount:   2,
		successMsg:  "success",
		failureMsg:  "failure",
	}

	// Pass zero values - should use defaults
	retry := NewRetryDecorator(agent, RetryConfig{})

	msg := agenkit.NewMessage("user", "test")
	response, err := retry.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Expected success with default config, got error: %v", err)
	}

	if response.Content != "success" {
		t.Errorf("Expected content 'success', got '%s'", response.Content)
	}

	if agent.attempts != 3 {
		t.Errorf("Expected 3 attempts with default config, got %d", agent.attempts)
	}
}

// Helper function
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && findSubstring(s, substr))
}

func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
