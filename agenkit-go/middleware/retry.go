// Package middleware provides reusable middleware for agents.
package middleware

import (
	"context"
	"fmt"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// RetryConfig configures retry behavior.
type RetryConfig struct {
	// MaxAttempts is the maximum number of attempts (including the initial attempt).
	// Default: 3
	MaxAttempts int

	// InitialBackoff is the initial backoff duration.
	// Default: 100ms
	InitialBackoff time.Duration

	// MaxBackoff is the maximum backoff duration.
	// Default: 10s
	MaxBackoff time.Duration

	// BackoffMultiplier is the multiplier for exponential backoff.
	// Default: 2.0
	BackoffMultiplier float64

	// ShouldRetry determines if an error should trigger a retry.
	// If nil, all errors trigger retries.
	ShouldRetry func(error) bool
}

// DefaultRetryConfig returns a retry config with sensible defaults.
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{
		MaxAttempts:       3,
		InitialBackoff:    100 * time.Millisecond,
		MaxBackoff:        10 * time.Second,
		BackoffMultiplier: 2.0,
		ShouldRetry:       nil, // Retry all errors
	}
}

// RetryDecorator wraps an agent with retry logic.
type RetryDecorator struct {
	agent  agenkit.Agent
	config RetryConfig
}

// Verify that RetryDecorator implements Agent interface.
var _ agenkit.Agent = (*RetryDecorator)(nil)

// NewRetryDecorator creates a new retry decorator.
func NewRetryDecorator(agent agenkit.Agent, config RetryConfig) *RetryDecorator {
	// Apply defaults
	if config.MaxAttempts <= 0 {
		config.MaxAttempts = 3
	}
	if config.InitialBackoff <= 0 {
		config.InitialBackoff = 100 * time.Millisecond
	}
	if config.MaxBackoff <= 0 {
		config.MaxBackoff = 10 * time.Second
	}
	if config.BackoffMultiplier <= 0 {
		config.BackoffMultiplier = 2.0
	}

	return &RetryDecorator{
		agent:  agent,
		config: config,
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

// Process implements the Agent interface with retry logic.
func (r *RetryDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	var lastErr error
	backoff := r.config.InitialBackoff

	for attempt := 1; attempt <= r.config.MaxAttempts; attempt++ {
		// Try the operation
		response, err := r.agent.Process(ctx, message)

		// Success
		if err == nil {
			return response, nil
		}

		// Save the error
		lastErr = err

		// Check if we should retry this error
		if r.config.ShouldRetry != nil && !r.config.ShouldRetry(err) {
			return nil, fmt.Errorf("non-retryable error on attempt %d/%d: %w", attempt, r.config.MaxAttempts, err)
		}

		// Don't sleep after the last attempt
		if attempt == r.config.MaxAttempts {
			break
		}

		// Wait before retrying
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("retry cancelled after %d attempts: %w", attempt, ctx.Err())
		case <-time.After(backoff):
			// Calculate next backoff
			backoff = time.Duration(float64(backoff) * r.config.BackoffMultiplier)
			if backoff > r.config.MaxBackoff {
				backoff = r.config.MaxBackoff
			}
		}
	}

	return nil, fmt.Errorf("max retry attempts (%d) exceeded: %w", r.config.MaxAttempts, lastErr)
}
