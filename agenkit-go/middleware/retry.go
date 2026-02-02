// Package middleware provides reusable middleware for agents.
package middleware

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// RetryMetrics tracks retry middleware metrics.
type RetryMetrics struct {
	mu sync.RWMutex

	// TotalAttempts is the total number of requests (including retries).
	TotalAttempts int64

	// SuccessfulFirstAttempt is the number of requests that succeeded on first try.
	SuccessfulFirstAttempt int64

	// SuccessfulOnRetry is the number of requests that succeeded after retry.
	SuccessfulOnRetry int64

	// FailedAfterRetries is the number of requests that failed after all retries.
	FailedAfterRetries int64

	// TotalRetries is the total number of retry attempts across all requests.
	TotalRetries int64
}

// Snapshot returns a copy of the current metrics.
func (m *RetryMetrics) Snapshot() RetryMetrics {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return RetryMetrics{
		TotalAttempts:          m.TotalAttempts,
		SuccessfulFirstAttempt: m.SuccessfulFirstAttempt,
		SuccessfulOnRetry:      m.SuccessfulOnRetry,
		FailedAfterRetries:     m.FailedAfterRetries,
		TotalRetries:           m.TotalRetries,
	}
}

// RetryConfig configures retry behavior.
type RetryConfig struct {
	// MaxRetries is the maximum number of retry attempts.
	// Default: 3
	MaxRetries int

	// InitialRetryDelay is the initial delay before the first retry.
	// Default: 100ms
	InitialRetryDelay time.Duration

	// MaxRetryDelay is the maximum delay between retries.
	// Default: 10s
	MaxRetryDelay time.Duration

	// RetryMultiplier is the multiplier for exponential backoff.
	// Default: 2.0
	RetryMultiplier float64

	// ShouldRetry determines if an error should trigger a retry.
	// If nil, all errors trigger retries.
	ShouldRetry func(error) bool
}

// DefaultRetryConfig returns a retry config with sensible defaults.
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{
		MaxRetries:        3,
		InitialRetryDelay: 100 * time.Millisecond,
		MaxRetryDelay:     10 * time.Second,
		RetryMultiplier:   2.0,
		ShouldRetry:       nil, // Retry all errors
	}
}

// RetryDecorator wraps an agent with retry logic.
type RetryDecorator struct {
	agent   agenkit.Agent
	config  RetryConfig
	metrics *RetryMetrics
}

// Verify that RetryDecorator implements Agent interface.
var _ agenkit.Agent = (*RetryDecorator)(nil)

// NewRetryDecorator creates a new retry decorator.
func NewRetryDecorator(agent agenkit.Agent, config RetryConfig) *RetryDecorator {
	// Apply defaults
	if config.MaxRetries <= 0 {
		config.MaxRetries = 3
	}
	if config.InitialRetryDelay <= 0 {
		config.InitialRetryDelay = 100 * time.Millisecond
	}
	if config.MaxRetryDelay <= 0 {
		config.MaxRetryDelay = 10 * time.Second
	}
	if config.RetryMultiplier <= 0 {
		config.RetryMultiplier = 2.0
	}

	return &RetryDecorator{
		agent:   agent,
		config:  config,
		metrics: &RetryMetrics{},
	}
}

// Name returns the name of the underlying agent.
func (r *RetryDecorator) Name() string {
	return r.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent.
func (r *RetryDecorator) Capabilities() []string {
	return r.agent.Capabilities()
}

// Introspect returns the introspection result of the underlying agent.
func (r *RetryDecorator) Introspect() *agenkit.IntrospectionResult {
	return r.agent.Introspect()
}

// Metrics returns the current retry metrics.
func (r *RetryDecorator) Metrics() *RetryMetrics {
	return r.metrics
}

// Process implements the Agent interface with retry logic.
func (r *RetryDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	var lastErr error
	backoff := r.config.InitialRetryDelay

	for attempt := 1; attempt <= r.config.MaxRetries; attempt++ {
		// Track attempt
		r.metrics.mu.Lock()
		r.metrics.TotalAttempts++
		r.metrics.mu.Unlock()

		// Try the operation
		response, err := r.agent.Process(ctx, message)

		// Success
		if err == nil {
			// Track success
			r.metrics.mu.Lock()
			if attempt == 1 {
				r.metrics.SuccessfulFirstAttempt++
			} else {
				r.metrics.SuccessfulOnRetry++
			}
			r.metrics.mu.Unlock()

			return response, nil
		}

		// Save the error
		lastErr = err

		// Check if we should retry this error
		if r.config.ShouldRetry != nil && !r.config.ShouldRetry(err) {
			r.metrics.mu.Lock()
			r.metrics.FailedAfterRetries++
			r.metrics.mu.Unlock()
			return nil, fmt.Errorf("non-retryable error on attempt %d/%d: %w", attempt, r.config.MaxRetries, err)
		}

		// Don't sleep after the last attempt
		if attempt == r.config.MaxRetries {
			break
		}

		// Track retry
		r.metrics.mu.Lock()
		r.metrics.TotalRetries++
		r.metrics.mu.Unlock()

		// Wait before retrying
		select {
		case <-ctx.Done():
			r.metrics.mu.Lock()
			r.metrics.FailedAfterRetries++
			r.metrics.mu.Unlock()
			return nil, fmt.Errorf("retry cancelled after %d attempts: %w", attempt, ctx.Err())
		case <-time.After(backoff):
			// Calculate next backoff
			backoff = time.Duration(float64(backoff) * r.config.RetryMultiplier)
			if backoff > r.config.MaxRetryDelay {
				backoff = r.config.MaxRetryDelay
			}
		}
	}

	// All attempts failed
	r.metrics.mu.Lock()
	r.metrics.FailedAfterRetries++
	r.metrics.mu.Unlock()

	return nil, fmt.Errorf("max retry attempts (%d) exceeded: %w", r.config.MaxRetries, lastErr)
}
