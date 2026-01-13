// Package middleware provides reusable middleware for agents.
package middleware

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
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

	// MaxWaitTimeout is the maximum time to wait for tokens before failing.
	// If 0 (default), waits indefinitely (or until context is cancelled).
	// This prevents requests from waiting too long when the rate limiter is heavily loaded.
	// Example: time.Second * 5 means requests will wait at most 5 seconds for tokens.
	MaxWaitTimeout time.Duration
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
	mu               sync.RWMutex
	TotalRequests    int64
	AllowedRequests  int64
	RejectedRequests int64
	TotalWaitTime    time.Duration // Total time spent waiting for tokens
	CurrentTokens    float64
}

// NewRateLimiterMetrics creates a new metrics instance.
func NewRateLimiterMetrics(initialTokens float64) *RateLimiterMetrics {
	return &RateLimiterMetrics{
		CurrentTokens: initialTokens,
	}
}

// RateLimitError is returned when the rate limit is exceeded.
type RateLimitError struct {
	TokensNeeded    int
	TokensAvailable float64
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

// Introspect returns the introspection result of the underlying agent.
func (r *RateLimiterDecorator) Introspect() *agenkit.IntrospectionResult {
	return r.agent.Introspect()
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

	// Apply max wait timeout if configured
	if r.config.MaxWaitTimeout > 0 && waitDuration > r.config.MaxWaitTimeout {
		tokensAvailable := r.tokens
		r.mu.Unlock()
		return &RateLimitError{
			TokensNeeded:    tokensNeeded,
			TokensAvailable: tokensAvailable,
		}
	}

	r.mu.Unlock()

	// Wait outside the lock to allow other operations
	waitStart := time.Now()
	select {
	case <-time.After(waitDuration):
	case <-ctx.Done():
		return ctx.Err()
	}
	actualWaitDuration := time.Since(waitStart)

	// Re-acquire lock and try again
	r.mu.Lock()
	defer r.mu.Unlock()

	// Refill tokens based on actual elapsed time
	r.refillTokens()

	// Use small epsilon for floating point comparison to avoid precision issues
	// Need epsilon >= 0.005 since error message uses %.2f formatting
	const epsilon = 0.01
	if r.tokens >= float64(tokensNeeded)-epsilon {
		r.tokens -= float64(tokensNeeded)
		r.metrics.mu.Lock()
		r.metrics.CurrentTokens = r.tokens
		r.metrics.TotalWaitTime += actualWaitDuration
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

// Stream implements the StreamingAgent interface by passing through to the underlying agent.
// If the underlying agent doesn't support streaming, it returns an error.
// Note: Rate limiting is applied per Stream() call, not per chunk.
func (r *RateLimiterDecorator) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	// Check if underlying agent supports streaming
	streamingAgent, ok := r.agent.(agenkit.StreamingAgent)
	if !ok {
		// Return channels with error
		messageChan := make(chan *agenkit.Message)
		errorChan := make(chan error, 1)
		close(messageChan)
		errorChan <- fmt.Errorf("underlying agent does not support streaming")
		close(errorChan)
		return messageChan, errorChan
	}

	// Acquire tokens before streaming (rate limit the Stream call itself)
	tokensNeeded := r.config.TokensPerRequest
	if err := r.acquireTokens(ctx, tokensNeeded, true); err != nil {
		// Return channels with error
		messageChan := make(chan *agenkit.Message)
		errorChan := make(chan error, 1)
		close(messageChan)
		errorChan <- err
		close(errorChan)

		r.metrics.mu.Lock()
		r.metrics.RejectedRequests++
		r.metrics.mu.Unlock()
		return messageChan, errorChan
	}

	r.metrics.mu.Lock()
	r.metrics.AllowedRequests++
	r.metrics.mu.Unlock()

	// Pass through to underlying streaming agent
	return streamingAgent.Stream(ctx, message)
}

// min returns the minimum of two float64 values.
func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

// ==================== Per-User Rate Limiter ====================

// PerUserRateLimiterConfig configures per-user rate limiter behavior.
type PerUserRateLimiterConfig struct {
	// Rate is the number of tokens added per second per user.
	// Default: 10
	Rate float64

	// Capacity is the maximum burst capacity per user (maximum tokens in bucket).
	// Default: 10
	Capacity int

	// TokensPerRequest is the number of tokens consumed per request.
	// Default: 1
	TokensPerRequest int

	// MaxWaitTimeout is the maximum time to wait for tokens before failing.
	// If 0 (default), waits indefinitely (or until context is cancelled).
	MaxWaitTimeout time.Duration

	// UserIDExtractor is a function that extracts the user ID from a message.
	// If not provided, defaults to checking message.Metadata["user_id"].
	// The function should return an empty string for anonymous/unknown users.
	UserIDExtractor func(*agenkit.Message) string
}

// DefaultPerUserRateLimiterConfig returns a per-user rate limiter config with sensible defaults.
func DefaultPerUserRateLimiterConfig() PerUserRateLimiterConfig {
	return PerUserRateLimiterConfig{
		Rate:             10.0,
		Capacity:         10,
		TokensPerRequest: 1,
		UserIDExtractor: func(msg *agenkit.Message) string {
			if msg.Metadata == nil {
				return ""
			}
			if userID, ok := msg.Metadata["user_id"].(string); ok {
				return userID
			}
			return ""
		},
	}
}

// userBucket represents a token bucket for a single user.
type userBucket struct {
	tokens     float64
	lastUpdate time.Time
}

// PerUserRateLimiterMetrics tracks per-user rate limiter metrics.
type PerUserRateLimiterMetrics struct {
	mu               sync.RWMutex
	TotalRequests    int64
	AllowedRequests  int64
	RejectedRequests int64
	TotalWaitTime    time.Duration
	ActiveUsers      int // Number of users with active buckets
}

// NewPerUserRateLimiterMetrics creates a new per-user metrics instance.
func NewPerUserRateLimiterMetrics() *PerUserRateLimiterMetrics {
	return &PerUserRateLimiterMetrics{}
}

// PerUserRateLimiterDecorator wraps an agent with per-user rate limiting protection.
//
// Unlike the global RateLimiterDecorator, this maintains separate token buckets for each user,
// providing fair resource allocation across multiple users/tenants. This is essential for:
//
// - Multi-tenant applications where each user should have independent rate limits
// - Preventing a single user from monopolizing resources
// - Implementing tiered access (different rates for different user tiers)
// - Fair queuing across concurrent users
//
// Example:
//
//	agent := &MyAgent{}
//	perUserLimiter := middleware.NewPerUserRateLimiterDecorator(
//		agent,
//		middleware.PerUserRateLimiterConfig{
//			Rate:     5.0,  // 5 requests per second per user
//			Capacity: 10,   // Allow burst of 10 requests
//		},
//	)
type PerUserRateLimiterDecorator struct {
	agent   agenkit.Agent
	config  PerUserRateLimiterConfig
	mu      sync.Mutex
	buckets map[string]*userBucket
	metrics *PerUserRateLimiterMetrics
}

// Verify that PerUserRateLimiterDecorator implements Agent interface.
var _ agenkit.Agent = (*PerUserRateLimiterDecorator)(nil)

// NewPerUserRateLimiterDecorator creates a new per-user rate limiter decorator.
func NewPerUserRateLimiterDecorator(agent agenkit.Agent, config PerUserRateLimiterConfig) *PerUserRateLimiterDecorator {
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
	if config.UserIDExtractor == nil {
		config.UserIDExtractor = func(msg *agenkit.Message) string {
			if msg.Metadata == nil {
				return ""
			}
			if userID, ok := msg.Metadata["user_id"].(string); ok {
				return userID
			}
			return ""
		}
	}

	// Validate
	if config.TokensPerRequest > config.Capacity {
		config.TokensPerRequest = config.Capacity
	}

	return &PerUserRateLimiterDecorator{
		agent:   agent,
		config:  config,
		buckets: make(map[string]*userBucket),
		metrics: NewPerUserRateLimiterMetrics(),
	}
}

// Name returns the name of the underlying agent.
func (r *PerUserRateLimiterDecorator) Name() string {
	return r.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent.
func (r *PerUserRateLimiterDecorator) Capabilities() []string {
	return r.agent.Capabilities()
}

// Introspect returns the introspection result of the underlying agent.
func (r *PerUserRateLimiterDecorator) Introspect() *agenkit.IntrospectionResult {
	return r.agent.Introspect()
}

// Metrics returns the per-user rate limiter metrics.
func (r *PerUserRateLimiterDecorator) Metrics() *PerUserRateLimiterMetrics {
	return r.metrics
}

// getUserBucket gets or creates a token bucket for the specified user.
func (r *PerUserRateLimiterDecorator) getUserBucket(userID string) *userBucket {
	// Check if bucket exists
	if bucket, ok := r.buckets[userID]; ok {
		return bucket
	}

	// Create new bucket
	bucket := &userBucket{
		tokens:     float64(r.config.Capacity),
		lastUpdate: time.Now(),
	}
	r.buckets[userID] = bucket

	// Update metrics
	r.metrics.mu.Lock()
	r.metrics.ActiveUsers = len(r.buckets)
	r.metrics.mu.Unlock()

	return bucket
}

// refillUserTokens adds tokens to a user's bucket based on elapsed time.
func (r *PerUserRateLimiterDecorator) refillUserTokens(bucket *userBucket) {
	now := time.Now()
	elapsed := now.Sub(bucket.lastUpdate).Seconds()

	// Add tokens based on elapsed time
	tokensToAdd := elapsed * r.config.Rate
	bucket.tokens = min(bucket.tokens+tokensToAdd, float64(r.config.Capacity))
	bucket.lastUpdate = now
}

// acquireUserTokens acquires tokens from a specific user's bucket.
func (r *PerUserRateLimiterDecorator) acquireUserTokens(ctx context.Context, userID string, tokensNeeded int, wait bool) error {
	r.mu.Lock()

	bucket := r.getUserBucket(userID)
	r.refillUserTokens(bucket)

	if bucket.tokens >= float64(tokensNeeded) {
		// Sufficient tokens available
		bucket.tokens -= float64(tokensNeeded)
		r.mu.Unlock()
		return nil
	}

	if !wait {
		// Insufficient tokens and not waiting
		tokensAvailable := bucket.tokens
		r.mu.Unlock()
		return &RateLimitError{
			TokensNeeded:    tokensNeeded,
			TokensAvailable: tokensAvailable,
		}
	}

	// Calculate wait time for tokens
	tokensDeficit := float64(tokensNeeded) - bucket.tokens
	waitDuration := time.Duration(tokensDeficit/r.config.Rate*1000) * time.Millisecond

	// Apply max wait timeout if configured
	if r.config.MaxWaitTimeout > 0 && waitDuration > r.config.MaxWaitTimeout {
		tokensAvailable := bucket.tokens
		r.mu.Unlock()
		return &RateLimitError{
			TokensNeeded:    tokensNeeded,
			TokensAvailable: tokensAvailable,
		}
	}

	r.mu.Unlock()

	// Wait outside the lock to allow other operations
	waitStart := time.Now()
	select {
	case <-time.After(waitDuration):
	case <-ctx.Done():
		return ctx.Err()
	}
	actualWaitDuration := time.Since(waitStart)

	// Re-acquire lock and try again
	r.mu.Lock()
	defer r.mu.Unlock()

	// Refill tokens based on actual elapsed time
	r.refillUserTokens(bucket)

	// Use small epsilon for floating point comparison
	const epsilon = 0.01
	if bucket.tokens >= float64(tokensNeeded)-epsilon {
		bucket.tokens -= float64(tokensNeeded)
		r.metrics.mu.Lock()
		r.metrics.TotalWaitTime += actualWaitDuration
		r.metrics.mu.Unlock()
		return nil
	}

	// Should not happen, but handle defensively
	return &RateLimitError{
		TokensNeeded:    tokensNeeded,
		TokensAvailable: bucket.tokens,
	}
}

// Process implements the Agent interface with per-user rate limiting.
func (r *PerUserRateLimiterDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	r.metrics.mu.Lock()
	r.metrics.TotalRequests++
	r.metrics.mu.Unlock()

	// Extract user ID
	userID := r.config.UserIDExtractor(message)
	if userID == "" {
		// Fallback to anonymous user
		userID = "anonymous"
	}

	// Acquire tokens for this user
	err := r.acquireUserTokens(ctx, userID, r.config.TokensPerRequest, true)
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

// Stream implements the StreamingAgent interface by passing through to the underlying agent.
// If the underlying agent doesn't support streaming, it returns an error.
// Note: Rate limiting is applied per Stream() call per user, not per chunk.
func (r *PerUserRateLimiterDecorator) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	// Check if underlying agent supports streaming
	streamingAgent, ok := r.agent.(agenkit.StreamingAgent)
	if !ok {
		// Return channels with error
		messageChan := make(chan *agenkit.Message)
		errorChan := make(chan error, 1)
		close(messageChan)
		errorChan <- fmt.Errorf("underlying agent does not support streaming")
		close(errorChan)
		return messageChan, errorChan
	}

	// Extract user ID
	userID := r.config.UserIDExtractor(message)
	if userID == "" {
		userID = "anonymous"
	}

	// Acquire tokens for this user before streaming
	tokensNeeded := r.config.TokensPerRequest
	if err := r.acquireUserTokens(ctx, userID, tokensNeeded, true); err != nil {
		// Return channels with error
		messageChan := make(chan *agenkit.Message)
		errorChan := make(chan error, 1)
		close(messageChan)
		errorChan <- err
		close(errorChan)

		r.metrics.mu.Lock()
		r.metrics.RejectedRequests++
		r.metrics.mu.Unlock()
		return messageChan, errorChan
	}

	r.metrics.mu.Lock()
	r.metrics.AllowedRequests++
	r.metrics.mu.Unlock()

	// Pass through to underlying streaming agent
	return streamingAgent.Stream(ctx, message)
}
