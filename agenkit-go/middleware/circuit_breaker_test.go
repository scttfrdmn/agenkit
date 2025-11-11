package middleware

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// UnreliableAgent simulates an agent that fails based on a controllable pattern.
type UnreliableAgent struct {
	failurePattern []bool // true = fail, false = succeed
	attempts       int
	delay          time.Duration
}

func (u *UnreliableAgent) Name() string {
	return "unreliable-agent"
}

func (u *UnreliableAgent) Capabilities() []string {
	return []string{}
}

func (u *UnreliableAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if u.delay > 0 {
		// Respect context cancellation
		select {
		case <-time.After(u.delay):
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}

	index := u.attempts % len(u.failurePattern)
	u.attempts++

	if u.failurePattern[index] {
		return nil, errors.New("simulated failure")
	}
	return agenkit.NewMessage("agent", "success"), nil
}

// TestCircuitBreakerClosed tests normal operation in closed state.
func TestCircuitBreakerClosed(t *testing.T) {
	ctx := context.Background()

	// Agent that always succeeds
	agent := &UnreliableAgent{
		failurePattern: []bool{false, false, false},
	}

	cb := NewCircuitBreakerDecorator(agent, CircuitBreakerConfig{
		FailureThreshold: 3,
		RecoveryTimeout:  100 * time.Millisecond,
		SuccessThreshold: 2,
		Timeout:          1 * time.Second,
	})

	// Should succeed in closed state
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", "test")
		response, err := cb.Process(ctx, msg)

		if err != nil {
			t.Fatalf("Attempt %d: Expected success, got error: %v", i+1, err)
		}

		if response.Content != "success" {
			t.Errorf("Attempt %d: Expected 'success', got '%s'", i+1, response.Content)
		}
	}

	if cb.State() != StateClosed {
		t.Errorf("Expected StateClosed, got %s", cb.State())
	}

	metrics := cb.Metrics()
	if metrics.TotalRequests != 3 {
		t.Errorf("Expected 3 total requests, got %d", metrics.TotalRequests)
	}
	if metrics.SuccessfulRequests != 3 {
		t.Errorf("Expected 3 successful requests, got %d", metrics.SuccessfulRequests)
	}
}

// TestCircuitBreakerOpens tests circuit opening after threshold failures.
func TestCircuitBreakerOpens(t *testing.T) {
	ctx := context.Background()

	// Agent that always fails
	agent := &UnreliableAgent{
		failurePattern: []bool{true},
	}

	cb := NewCircuitBreakerDecorator(agent, CircuitBreakerConfig{
		FailureThreshold: 3,
		RecoveryTimeout:  100 * time.Millisecond,
		SuccessThreshold: 2,
		Timeout:          1 * time.Second,
	})

	// Trigger failures to open circuit
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := cb.Process(ctx, msg)

		if err == nil {
			t.Fatalf("Attempt %d: Expected error, got nil", i+1)
		}
	}

	// Circuit should be open
	if cb.State() != StateOpen {
		t.Errorf("Expected StateOpen, got %s", cb.State())
	}

	metrics := cb.Metrics()
	if metrics.FailedRequests != 3 {
		t.Errorf("Expected 3 failed requests, got %d", metrics.FailedRequests)
	}
}

// TestCircuitBreakerRejectsWhenOpen tests that open circuit rejects requests.
func TestCircuitBreakerRejectsWhenOpen(t *testing.T) {
	ctx := context.Background()

	// Agent that always fails
	agent := &UnreliableAgent{
		failurePattern: []bool{true},
	}

	cb := NewCircuitBreakerDecorator(agent, CircuitBreakerConfig{
		FailureThreshold: 2,
		RecoveryTimeout:  1 * time.Second, // Long timeout
		SuccessThreshold: 2,
		Timeout:          1 * time.Second,
	})

	// Open the circuit
	for i := 0; i < 2; i++ {
		msg := agenkit.NewMessage("user", "test")
		cb.Process(ctx, msg)
	}

	// Circuit should be open
	if cb.State() != StateOpen {
		t.Fatalf("Expected StateOpen, got %s", cb.State())
	}

	// Next request should be rejected immediately
	msg := agenkit.NewMessage("user", "test")
	_, err := cb.Process(ctx, msg)

	if err == nil {
		t.Fatal("Expected CircuitBreakerError, got nil")
	}

	var cbErr *CircuitBreakerError
	if !errors.As(err, &cbErr) {
		t.Errorf("Expected CircuitBreakerError, got %T: %v", err, err)
	}

	metrics := cb.Metrics()
	if metrics.RejectedRequests != 1 {
		t.Errorf("Expected 1 rejected request, got %d", metrics.RejectedRequests)
	}
}

// TestCircuitBreakerHalfOpen tests transition to half-open state.
func TestCircuitBreakerHalfOpen(t *testing.T) {
	ctx := context.Background()

	// Agent that fails then succeeds
	agent := &UnreliableAgent{
		failurePattern: []bool{true, true, false, false},
	}

	cb := NewCircuitBreakerDecorator(agent, CircuitBreakerConfig{
		FailureThreshold: 2,
		RecoveryTimeout:  50 * time.Millisecond,
		SuccessThreshold: 2,
		Timeout:          1 * time.Second,
	})

	// Open the circuit
	for i := 0; i < 2; i++ {
		msg := agenkit.NewMessage("user", "test")
		cb.Process(ctx, msg)
	}

	if cb.State() != StateOpen {
		t.Fatalf("Expected StateOpen, got %s", cb.State())
	}

	// Wait for recovery timeout
	time.Sleep(60 * time.Millisecond)

	// Next request should transition to half-open
	msg := agenkit.NewMessage("user", "test")
	response, err := cb.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Expected success in half-open, got error: %v", err)
	}

	if response.Content != "success" {
		t.Errorf("Expected 'success', got '%s'", response.Content)
	}

	// Should be in half-open state
	if cb.State() != StateHalfOpen {
		t.Errorf("Expected StateHalfOpen, got %s", cb.State())
	}
}

// TestCircuitBreakerRecovery tests full recovery (half-open -> closed).
func TestCircuitBreakerRecovery(t *testing.T) {
	ctx := context.Background()

	// Agent that fails then succeeds
	agent := &UnreliableAgent{
		failurePattern: []bool{true, true, false, false, false},
	}

	cb := NewCircuitBreakerDecorator(agent, CircuitBreakerConfig{
		FailureThreshold: 2,
		RecoveryTimeout:  50 * time.Millisecond,
		SuccessThreshold: 2,
		Timeout:          1 * time.Second,
	})

	// Open the circuit
	for i := 0; i < 2; i++ {
		msg := agenkit.NewMessage("user", "test")
		cb.Process(ctx, msg)
	}

	// Wait for recovery timeout
	time.Sleep(60 * time.Millisecond)

	// Make successful requests to close circuit
	for i := 0; i < 2; i++ {
		msg := agenkit.NewMessage("user", "test")
		response, err := cb.Process(ctx, msg)

		if err != nil {
			t.Fatalf("Attempt %d: Expected success, got error: %v", i+1, err)
		}

		if response.Content != "success" {
			t.Errorf("Attempt %d: Expected 'success', got '%s'", i+1, response.Content)
		}
	}

	// Circuit should be closed
	if cb.State() != StateClosed {
		t.Errorf("Expected StateClosed after recovery, got %s", cb.State())
	}

	metrics := cb.Metrics()
	if metrics.StateChanges["closed->open"] != 1 {
		t.Errorf("Expected 1 closed->open transition, got %d", metrics.StateChanges["closed->open"])
	}
	if metrics.StateChanges["open->half_open"] != 1 {
		t.Errorf("Expected 1 open->half_open transition, got %d", metrics.StateChanges["open->half_open"])
	}
	if metrics.StateChanges["half_open->closed"] != 1 {
		t.Errorf("Expected 1 half_open->closed transition, got %d", metrics.StateChanges["half_open->closed"])
	}
}

// TestCircuitBreakerReopensFromHalfOpen tests reopening on failure in half-open.
func TestCircuitBreakerReopensFromHalfOpen(t *testing.T) {
	ctx := context.Background()

	// Agent that fails, then succeeds once, then fails again
	agent := &UnreliableAgent{
		failurePattern: []bool{true, true, false, true},
	}

	cb := NewCircuitBreakerDecorator(agent, CircuitBreakerConfig{
		FailureThreshold: 2,
		RecoveryTimeout:  50 * time.Millisecond,
		SuccessThreshold: 2,
		Timeout:          1 * time.Second,
	})

	// Open the circuit
	for i := 0; i < 2; i++ {
		msg := agenkit.NewMessage("user", "test")
		cb.Process(ctx, msg)
	}

	// Wait for recovery timeout
	time.Sleep(60 * time.Millisecond)

	// First request succeeds (half-open)
	msg := agenkit.NewMessage("user", "test")
	cb.Process(ctx, msg)

	if cb.State() != StateHalfOpen {
		t.Errorf("Expected StateHalfOpen, got %s", cb.State())
	}

	// Second request fails, should reopen
	msg = agenkit.NewMessage("user", "test")
	_, err := cb.Process(ctx, msg)

	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	if cb.State() != StateOpen {
		t.Errorf("Expected StateOpen after failure in half-open, got %s", cb.State())
	}

	metrics := cb.Metrics()
	if metrics.StateChanges["half_open->open"] != 1 {
		t.Errorf("Expected 1 half_open->open transition, got %d", metrics.StateChanges["half_open->open"])
	}
}

// TestCircuitBreakerTimeout tests timeout handling.
func TestCircuitBreakerTimeout(t *testing.T) {
	ctx := context.Background()

	// Agent that takes too long
	agent := &UnreliableAgent{
		failurePattern: []bool{false},
		delay:          200 * time.Millisecond,
	}

	cb := NewCircuitBreakerDecorator(agent, CircuitBreakerConfig{
		FailureThreshold: 2,
		RecoveryTimeout:  100 * time.Millisecond,
		SuccessThreshold: 2,
		Timeout:          50 * time.Millisecond, // Timeout before agent response
	})

	// Trigger timeouts to open circuit
	for i := 0; i < 2; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := cb.Process(ctx, msg)

		if err == nil {
			t.Fatalf("Attempt %d: Expected timeout error, got nil", i+1)
		}

		if !contains(err.Error(), "timeout") {
			t.Errorf("Attempt %d: Expected timeout error, got: %v", i+1, err)
		}
	}

	// Circuit should be open due to timeouts
	if cb.State() != StateOpen {
		t.Errorf("Expected StateOpen after timeouts, got %s", cb.State())
	}

	metrics := cb.Metrics()
	if metrics.FailedRequests != 2 {
		t.Errorf("Expected 2 failed requests, got %d", metrics.FailedRequests)
	}
}

// TestCircuitBreakerMetrics tests metrics tracking.
func TestCircuitBreakerMetrics(t *testing.T) {
	ctx := context.Background()

	// Agent with mixed success/failure pattern
	agent := &UnreliableAgent{
		failurePattern: []bool{false, false, true, true, true},
	}

	cb := NewCircuitBreakerDecorator(agent, CircuitBreakerConfig{
		FailureThreshold: 3,
		RecoveryTimeout:  100 * time.Millisecond,
		SuccessThreshold: 2,
		Timeout:          1 * time.Second,
	})

	// Make requests
	for i := 0; i < 5; i++ {
		msg := agenkit.NewMessage("user", "test")
		cb.Process(ctx, msg)
	}

	metrics := cb.Metrics()

	if metrics.TotalRequests != 5 {
		t.Errorf("Expected 5 total requests, got %d", metrics.TotalRequests)
	}

	if metrics.SuccessfulRequests != 2 {
		t.Errorf("Expected 2 successful requests, got %d", metrics.SuccessfulRequests)
	}

	if metrics.FailedRequests != 3 {
		t.Errorf("Expected 3 failed requests, got %d", metrics.FailedRequests)
	}

	if metrics.CurrentState != StateOpen {
		t.Errorf("Expected StateOpen, got %s", metrics.CurrentState)
	}

	if metrics.LastStateChange == nil {
		t.Error("Expected LastStateChange to be set")
	}
}
