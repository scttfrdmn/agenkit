// Package middleware provides reusable middleware for agents.
package middleware

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// CircuitState represents the state of the circuit breaker.
type CircuitState int

const (
	// StateClosed means the circuit is closed and requests pass through normally.
	StateClosed CircuitState = iota
	// StateOpen means the circuit is open and requests fail fast.
	StateOpen
	// StateHalfOpen means the circuit is testing if the service has recovered.
	StateHalfOpen
)

// String returns the string representation of the circuit state.
func (s CircuitState) String() string {
	switch s {
	case StateClosed:
		return "closed"
	case StateOpen:
		return "open"
	case StateHalfOpen:
		return "half_open"
	default:
		return "unknown"
	}
}

// CircuitBreakerConfig configures circuit breaker behavior.
type CircuitBreakerConfig struct {
	// FailureThreshold is the number of failures before opening the circuit.
	// Default: 5
	FailureThreshold int

	// RecoveryTimeout is the duration before attempting recovery from open state.
	// Default: 60s
	RecoveryTimeout time.Duration

	// SuccessThreshold is the number of successful calls in half-open state to close the circuit.
	// Default: 2
	SuccessThreshold int

	// Timeout is the request timeout duration.
	// Default: 30s
	Timeout time.Duration
}

// DefaultCircuitBreakerConfig returns a circuit breaker config with sensible defaults.
func DefaultCircuitBreakerConfig() CircuitBreakerConfig {
	return CircuitBreakerConfig{
		FailureThreshold: 5,
		RecoveryTimeout:  60 * time.Second,
		SuccessThreshold: 2,
		Timeout:          30 * time.Second,
	}
}

// CircuitBreakerMetrics tracks circuit breaker metrics.
type CircuitBreakerMetrics struct {
	mu                 sync.RWMutex
	TotalRequests      int64
	SuccessfulRequests int64
	FailedRequests     int64
	RejectedRequests   int64 // Rejected due to open circuit
	StateChanges       map[string]int64
	LastStateChange    *time.Time
	CurrentState       CircuitState
}

// NewCircuitBreakerMetrics creates a new metrics instance.
func NewCircuitBreakerMetrics() *CircuitBreakerMetrics {
	return &CircuitBreakerMetrics{
		StateChanges: make(map[string]int64),
		CurrentState: StateClosed,
	}
}

// CircuitBreakerError is returned when the circuit breaker is open.
type CircuitBreakerError struct {
	FailureCount int
}

// Error implements the error interface.
func (e *CircuitBreakerError) Error() string {
	return fmt.Sprintf("circuit breaker is OPEN (failed %d times)", e.FailureCount)
}

// CircuitBreakerDecorator wraps an agent with circuit breaker protection.
//
// The circuit breaker prevents cascading failures by failing fast when
// a service is unhealthy. It has three states:
//
// - CLOSED: Normal operation, requests pass through
// - OPEN: Failure threshold exceeded, fail fast without calling agent
// - HALF_OPEN: Testing if service has recovered
//
// State transitions:
// - CLOSED -> OPEN: After FailureThreshold consecutive failures
// - OPEN -> HALF_OPEN: After RecoveryTimeout seconds
// - HALF_OPEN -> CLOSED: After SuccessThreshold consecutive successes
// - HALF_OPEN -> OPEN: On any failure
type CircuitBreakerDecorator struct {
	agent            agenkit.Agent
	config           CircuitBreakerConfig
	mu               sync.Mutex
	state            CircuitState
	failureCount     int
	successCount     int
	lastFailureTime  *time.Time
	metrics          *CircuitBreakerMetrics
}

// Verify that CircuitBreakerDecorator implements Agent interface.
var _ agenkit.Agent = (*CircuitBreakerDecorator)(nil)

// NewCircuitBreakerDecorator creates a new circuit breaker decorator.
func NewCircuitBreakerDecorator(agent agenkit.Agent, config CircuitBreakerConfig) *CircuitBreakerDecorator {
	// Apply defaults
	if config.FailureThreshold <= 0 {
		config.FailureThreshold = 5
	}
	if config.RecoveryTimeout <= 0 {
		config.RecoveryTimeout = 60 * time.Second
	}
	if config.SuccessThreshold <= 0 {
		config.SuccessThreshold = 2
	}
	if config.Timeout <= 0 {
		config.Timeout = 30 * time.Second
	}

	return &CircuitBreakerDecorator{
		agent:   agent,
		config:  config,
		state:   StateClosed,
		metrics: NewCircuitBreakerMetrics(),
	}
}

// Name returns the name of the underlying agent.
func (c *CircuitBreakerDecorator) Name() string {
	return c.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent.
func (c *CircuitBreakerDecorator) Capabilities() []string {
	return c.agent.Capabilities()
}

// State returns the current circuit breaker state.
func (c *CircuitBreakerDecorator) State() CircuitState {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.state
}

// Metrics returns the circuit breaker metrics.
func (c *CircuitBreakerDecorator) Metrics() *CircuitBreakerMetrics {
	return c.metrics
}

// changeState transitions the circuit breaker to a new state.
func (c *CircuitBreakerDecorator) changeState(newState CircuitState) {
	if c.state != newState {
		oldState := c.state
		c.state = newState

		// Update metrics
		c.metrics.mu.Lock()
		c.metrics.CurrentState = newState
		now := time.Now()
		c.metrics.LastStateChange = &now
		transition := fmt.Sprintf("%s->%s", oldState, newState)
		c.metrics.StateChanges[transition]++
		c.metrics.mu.Unlock()
	}
}

// shouldAttemptReset checks if the circuit should attempt to reset from OPEN to HALF_OPEN.
func (c *CircuitBreakerDecorator) shouldAttemptReset() bool {
	if c.lastFailureTime == nil {
		return false
	}
	elapsed := time.Since(*c.lastFailureTime)
	return elapsed >= c.config.RecoveryTimeout
}

// onSuccess handles a successful request.
func (c *CircuitBreakerDecorator) onSuccess() {
	c.metrics.mu.Lock()
	c.metrics.SuccessfulRequests++
	c.metrics.mu.Unlock()

	if c.state == StateHalfOpen {
		c.successCount++
		if c.successCount >= c.config.SuccessThreshold {
			// Recovered! Close the circuit
			c.changeState(StateClosed)
			c.failureCount = 0
			c.successCount = 0
		}
	} else if c.state == StateClosed {
		// Reset failure count on success
		c.failureCount = 0
	}
}

// onFailure handles a failed request.
func (c *CircuitBreakerDecorator) onFailure() {
	c.metrics.mu.Lock()
	c.metrics.FailedRequests++
	c.metrics.mu.Unlock()

	c.failureCount++
	now := time.Now()
	c.lastFailureTime = &now

	if c.state == StateHalfOpen {
		// Failed during recovery test, reopen circuit
		c.changeState(StateOpen)
		c.successCount = 0
	} else if c.state == StateClosed {
		if c.failureCount >= c.config.FailureThreshold {
			// Too many failures, open circuit
			c.changeState(StateOpen)
		}
	}
}

// Process implements the Agent interface with circuit breaker protection.
func (c *CircuitBreakerDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	c.mu.Lock()

	// Update metrics
	c.metrics.mu.Lock()
	c.metrics.TotalRequests++
	c.metrics.mu.Unlock()

	// Check if circuit is open
	if c.state == StateOpen {
		// Check if we should attempt recovery
		if c.shouldAttemptReset() {
			c.changeState(StateHalfOpen)
			c.successCount = 0
		} else {
			// Still open, fail fast
			c.metrics.mu.Lock()
			c.metrics.RejectedRequests++
			c.metrics.mu.Unlock()
			c.mu.Unlock()
			return nil, &CircuitBreakerError{FailureCount: c.failureCount}
		}
	}

	c.mu.Unlock()

	// Create timeout context
	timeoutCtx, cancel := context.WithTimeout(ctx, c.config.Timeout)
	defer cancel()

	// Attempt request with timeout
	response, err := c.agent.Process(timeoutCtx, message)

	c.mu.Lock()
	defer c.mu.Unlock()

	if err != nil {
		// Check if it's a timeout error
		if errors.Is(err, context.DeadlineExceeded) {
			c.onFailure()
			return nil, fmt.Errorf("request exceeded timeout of %v: %w", c.config.Timeout, err)
		}

		// Other error
		c.onFailure()
		return nil, err
	}

	// Success
	c.onSuccess()
	return response, nil
}
