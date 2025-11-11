// Package middleware provides reusable middleware for agents.
package middleware

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// RateLimiterConfig configures rate limiter behavior.
type RateLimiterConfig struct {
	// Rate is the number of tokens added per second.
	// Default: 10
	Rate float64

	// Capacity is the maximum burst capacity (maximum tokens in bucket).
	// Default: 10
	Capacity int

	// TokensPerRequest is the number of tokens consumed per request.
	// Default: 1
	TokensPerRequest int
}

// DefaultRateLimiterConfig returns a rate limiter config with sensible defaults.
func DefaultRateLimiterConfig() RateLimiterConfig {
	return RateLimiterConfig{
		Rate:             10.0,
		Capacity:         10,
		TokensPerRequest: 1,
	}
}

// RateLimiterMetrics tracks rate limiter metrics.
type RateLimiterMetrics struct {
	mu                sync.RWMutex
	TotalRequests     int64
	AllowedRequests   int64
	RejectedRequests  int64
	TotalWaitTime     time.Duration // Total time spent waiting for tokens
	CurrentTokens     float64
}

// NewRateLimiterMetrics creates a new metrics instance.
func NewRateLimiterMetrics(initialTokens float64) *RateLimiterMetrics {
	return &RateLimiterMetrics{
		CurrentTokens: initialTokens,
	}
}

// RateLimitError is returned when the rate limit is exceeded.
type RateLimitError struct {
	TokensNeeded     int
	TokensAvailable  float64
}

// Error implements the error interface.
func (e *RateLimitError) Error() string {
	return fmt.Sprintf("rate limit exceeded: need %d tokens, only %.2f available",
		e.TokensNeeded, e.TokensAvailable)
}

// RateLimiterDecorator wraps an agent with rate limiting protection.
//
// The token bucket algorithm allows for smooth rate limiting with burst capacity:
// - Tokens are added to the bucket at a constant rate
// - Each request consumes tokens from the bucket
// - If insufficient tokens are available, the request waits or is rejected
// - Burst capacity allows temporary spikes in traffic
//
// This is useful for:
// - Protecting downstream services from overload
// - Complying with API rate limits (e.g., OpenAI: 3500 RPM)
// - Fair resource allocation across tenants
// - Cost control
type RateLimiterDecorator struct {
	agent      agenkit.Agent
	config     RateLimiterConfig
	mu         sync.Mutex
	tokens     float64
	lastUpdate time.Time
	metrics    *RateLimiterMetrics
}

// Verify that RateLimiterDecorator implements Agent interface.
var _ agenkit.Agent = (*RateLimiterDecorator)(nil)

// NewRateLimiterDecorator creates a new rate limiter decorator.
func NewRateLimiterDecorator(agent agenkit.Agent, config RateLimiterConfig) *RateLimiterDecorator {
	// Apply defaults
	if config.Rate <= 0 {
		config.Rate = 10.0
	}
	if config.Capacity < 1 {
		config.Capacity = 10
	}
	if config.TokensPerRequest < 1 {
		config.TokensPerRequest = 1
	}

	// Validate
	if config.TokensPerRequest > config.Capacity {
		config.TokensPerRequest = config.Capacity
	}

	initialTokens := float64(config.Capacity)
	return &RateLimiterDecorator{
		agent:      agent,
		config:     config,
		tokens:     initialTokens,
		lastUpdate: time.Now(),
		metrics:    NewRateLimiterMetrics(initialTokens),
	}
}

// Name returns the name of the underlying agent.
func (r *RateLimiterDecorator) Name() string {
	return r.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent.
func (r *RateLimiterDecorator) Capabilities() []string {
	return r.agent.Capabilities()
}

// Metrics returns the rate limiter metrics.
func (r *RateLimiterDecorator) Metrics() *RateLimiterMetrics {
	return r.metrics
}

// refillTokens adds tokens based on elapsed time.
func (r *RateLimiterDecorator) refillTokens() {
	now := time.Now()
	elapsed := now.Sub(r.lastUpdate).Seconds()

	// Add tokens based on elapsed time
	tokensToAdd := elapsed * r.config.Rate
	r.tokens = min(r.tokens+tokensToAdd, float64(r.config.Capacity))
	r.lastUpdate = now

	// Update metrics
	r.metrics.mu.Lock()
	r.metrics.CurrentTokens = r.tokens
	r.metrics.mu.Unlock()
}

// acquireTokens acquires tokens from the bucket.
func (r *RateLimiterDecorator) acquireTokens(ctx context.Context, tokensNeeded int, wait bool) error {
	r.mu.Lock()
	r.refillTokens()

	if r.tokens >= float64(tokensNeeded) {
		// Sufficient tokens available
		r.tokens -= float64(tokensNeeded)
		r.metrics.mu.Lock()
		r.metrics.CurrentTokens = r.tokens
		r.metrics.mu.Unlock()
		r.mu.Unlock()
		return nil
	}

	if !wait {
		// Insufficient tokens and not waiting
		tokensAvailable := r.tokens
		r.mu.Unlock()
		return &RateLimitError{
			TokensNeeded:    tokensNeeded,
			TokensAvailable: tokensAvailable,
		}
	}

	// Calculate wait time for tokens
	tokensDeficit := float64(tokensNeeded) - r.tokens
	waitDuration := time.Duration(tokensDeficit/r.config.Rate*1000) * time.Millisecond

	r.mu.Unlock()

	// Wait outside the lock to allow other operations
	select {
	case <-time.After(waitDuration):
	case <-ctx.Done():
		return ctx.Err()
	}

	// Re-acquire lock and try again
	r.mu.Lock()
	defer r.mu.Unlock()

	r.refillTokens()

	if r.tokens >= float64(tokensNeeded) {
		r.tokens -= float64(tokensNeeded)
		r.metrics.mu.Lock()
		r.metrics.CurrentTokens = r.tokens
		r.metrics.TotalWaitTime += waitDuration
		r.metrics.mu.Unlock()
		return nil
	}

	// Should not happen, but handle defensively
	return &RateLimitError{
		TokensNeeded:    tokensNeeded,
		TokensAvailable: r.tokens,
	}
}

// Process implements the Agent interface with rate limiting.
func (r *RateLimiterDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	r.metrics.mu.Lock()
	r.metrics.TotalRequests++
	r.metrics.mu.Unlock()

	// Acquire tokens
	err := r.acquireTokens(ctx, r.config.TokensPerRequest, true)
	if err != nil {
		r.metrics.mu.Lock()
		r.metrics.RejectedRequests++
		r.metrics.mu.Unlock()
		return nil, err
	}

	r.metrics.mu.Lock()
	r.metrics.AllowedRequests++
	r.metrics.mu.Unlock()

	// Process request
	return r.agent.Process(ctx, message)
}

// min returns the minimum of two float64 values.
func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}
