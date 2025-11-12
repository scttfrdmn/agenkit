/*
Middleware overhead benchmarks for agenkit-go.

These benchmarks measure the performance impact of middleware decorators on agent processing.

Methodology:
1. Baseline: Agent without middleware
2. Single middleware: Agent with one middleware (retry, metrics, circuit breaker, rate limiter)
3. Stacked middleware: Agent with multiple middleware layers
4. Measure overhead: (middleware - baseline) / baseline

Target: <20% overhead for single middleware, <50% for stacked middleware

Production Impact: Middleware overhead is negligible compared to actual agent work:
- Measured overhead: ~0.001-0.01ms per middleware
- Typical LLM call: ~100-1000ms
- Production overhead: <0.01% of total execution time

The benefits of middleware (resilience, observability, rate limiting) far outweigh
the minimal performance cost.

Run benchmarks with: go test -bench=. -benchmem
*/

package benchmarks

import (
	"context"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/middleware"
)

// ============================================
// Benchmark Agent
// ============================================

// FastAgent is an agent that succeeds immediately (no I/O delay).
type FastAgent struct{}

func (f *FastAgent) Name() string {
	return "fast-agent"
}

func (f *FastAgent) Capabilities() []string {
	return []string{}
}

func (f *FastAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("agent", "Processed: "+message.Content), nil
}

// ============================================
// Single Middleware Benchmarks
// ============================================

// BenchmarkBaseline measures baseline agent performance without middleware.
func BenchmarkBaseline(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := agent.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkRetryMiddleware measures retry middleware overhead (success case).
//
// Target: <15% overhead when no retries are needed
//
// In the success case, retry middleware only adds:
// - Attempt counter increment
// - Success check (no error)
func BenchmarkRetryMiddleware(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	retryAgent := middleware.NewRetryDecorator(agent, middleware.RetryConfig{
		MaxAttempts:    3,
		InitialBackoff: 100 * time.Millisecond,
		MaxBackoff:     1000 * time.Millisecond,
	})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := retryAgent.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkMetricsMiddleware measures metrics middleware overhead.
//
// Target: <10% overhead for metrics collection
//
// Metrics middleware adds:
// - Request counter increment
// - Timer start/stop
// - Success/error tracking
func BenchmarkMetricsMiddleware(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	metricsAgent := middleware.NewMetricsDecorator(agent)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := metricsAgent.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkCircuitBreakerMiddleware measures circuit breaker middleware overhead (closed state).
//
// Target: <20% overhead in CLOSED state (normal operation)
//
// Circuit breaker adds:
// - State check (CLOSED)
// - Success counter increment
// - Failure tracking (none in success case)
func BenchmarkCircuitBreakerMiddleware(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	cbAgent := middleware.NewCircuitBreakerDecorator(agent, middleware.CircuitBreakerConfig{
		FailureThreshold: 5,
		RecoveryTimeout:  1.0,
		SuccessThreshold: 2,
	})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := cbAgent.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkRateLimiterMiddleware measures rate limiter middleware overhead (tokens available).
//
// Target: <20% overhead when tokens are available
//
// Rate limiter adds:
// - Lock acquisition
// - Token refill calculation
// - Token consumption
func BenchmarkRateLimiterMiddleware(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	rlAgent := middleware.NewRateLimiterDecorator(agent, middleware.RateLimiterConfig{
		Rate:             100000000.0, // 100M tokens/sec = 100 tokens/µs (FastAgent runs at 70ns/op = 14 ops/µs)
		Capacity:         100000000,
		TokensPerRequest: 1,
	})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := rlAgent.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkTimeoutMiddleware measures timeout middleware overhead (no timeout).
//
// Target: <15% overhead when requests complete within timeout
//
// Timeout middleware adds:
// - Context with timeout setup
// - Timer start/stop
// - Success/timeout tracking
func BenchmarkTimeoutMiddleware(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	timeoutAgent := middleware.NewTimeoutDecorator(agent, middleware.TimeoutConfig{
		Timeout: 30 * time.Second, // 30 second timeout, agent responds instantly
	})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := timeoutAgent.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkBatchingMiddleware measures batching middleware overhead (batch size 1).
//
// Target: <20% overhead when batch size is 1 (no actual batching)
//
// Batching middleware adds:
// - Channel enqueue/dequeue
// - Result channel creation and coordination
// - Background goroutine batch processor coordination
//
// Note: With batch_size=1, each request is processed individually,
// measuring pure batching infrastructure overhead.
func BenchmarkBatchingMiddleware(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	batchingAgent := middleware.NewBatchingDecorator(agent, middleware.BatchingConfig{
		MaxBatchSize: 1,
		MaxWaitTime:  1 * time.Millisecond,
		MaxQueueSize: 1000,
	})
	defer batchingAgent.Shutdown()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := batchingAgent.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// ============================================
// Stacked Middleware Benchmarks
// ============================================

// BenchmarkStackedMiddleware measures multiple middleware layers.
//
// Target: <60% overhead for 5 middleware layers (timeout + retry + metrics + CB + RL)
//
// This represents a realistic production setup with full observability
// and resilience patterns.
func BenchmarkStackedMiddleware(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	// Build stack: Metrics → Retry → Timeout → Circuit Breaker → Rate Limiter → Agent

	// Layer 1: Rate limiter (innermost)
	agentWithRL := middleware.NewRateLimiterDecorator(agent, middleware.RateLimiterConfig{
		Rate:             1000000.0,
		Capacity:         1000000,
		TokensPerRequest: 1,
	})

	// Layer 2: Circuit breaker
	agentWithCB := middleware.NewCircuitBreakerDecorator(agentWithRL, middleware.CircuitBreakerConfig{
		FailureThreshold: 5,
		RecoveryTimeout:  1.0,
		SuccessThreshold: 2,
	})

	// Layer 3: Timeout
	agentWithTimeout := middleware.NewTimeoutDecorator(agentWithCB, middleware.TimeoutConfig{
		Timeout: 30 * time.Second,
	})

	// Layer 4: Retry
	agentWithRetry := middleware.NewRetryDecorator(agentWithTimeout, middleware.RetryConfig{
		MaxAttempts:    3,
		InitialBackoff: 100 * time.Millisecond,
		MaxBackoff:     1000 * time.Millisecond,
	})

	// Layer 5: Metrics (outermost)
	agentWithAll := middleware.NewMetricsDecorator(agentWithRetry)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := agentWithAll.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkMinimalStack measures minimal production stack (metrics + retry).
//
// Target: <25% overhead for 2 middleware layers
//
// This represents a minimal production setup with basic observability
// and resilience.
func BenchmarkMinimalStack(b *testing.B) {
	ctx := context.Background()
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	// Build stack: Metrics → Retry → Agent

	// Layer 1: Retry
	agentWithRetry := middleware.NewRetryDecorator(agent, middleware.RetryConfig{
		MaxAttempts:    3,
		InitialBackoff: 100 * time.Millisecond,
		MaxBackoff:     1000 * time.Millisecond,
	})

	// Layer 2: Metrics
	agentWithMetrics := middleware.NewMetricsDecorator(agentWithRetry)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := agentWithMetrics.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// ============================================
// Comparison Benchmarks
// ============================================

// BenchmarkRetryMiddleware_Success is identical to BenchmarkRetryMiddleware
// but with an explicit name for comparison.
func BenchmarkRetryMiddleware_Success(b *testing.B) {
	BenchmarkRetryMiddleware(b)
}

// BenchmarkMetricsMiddleware_Success is identical to BenchmarkMetricsMiddleware
// but with an explicit name for comparison.
func BenchmarkMetricsMiddleware_Success(b *testing.B) {
	BenchmarkMetricsMiddleware(b)
}

// BenchmarkCircuitBreakerMiddleware_Closed is identical to BenchmarkCircuitBreakerMiddleware
// but with an explicit name for comparison.
func BenchmarkCircuitBreakerMiddleware_Closed(b *testing.B) {
	BenchmarkCircuitBreakerMiddleware(b)
}

// BenchmarkRateLimiterMiddleware_TokensAvailable is identical to BenchmarkRateLimiterMiddleware
// but with an explicit name for comparison.
func BenchmarkRateLimiterMiddleware_TokensAvailable(b *testing.B) {
	BenchmarkRateLimiterMiddleware(b)
}

// ============================================
// Parallel Benchmarks
// ============================================

// BenchmarkBaselineParallel measures baseline agent performance with parallelism.
func BenchmarkBaselineParallel(b *testing.B) {
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	b.RunParallel(func(pb *testing.PB) {
		ctx := context.Background()
		for pb.Next() {
			_, err := agent.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

// BenchmarkStackedMiddlewareParallel measures stacked middleware with parallelism.
func BenchmarkStackedMiddlewareParallel(b *testing.B) {
	agent := &FastAgent{}
	msg := agenkit.NewMessage("user", "test")

	// Build full stack: Metrics → Retry → Timeout → Circuit Breaker → Rate Limiter → Agent

	agentWithRL := middleware.NewRateLimiterDecorator(agent, middleware.RateLimiterConfig{
		Rate:             1000000.0,
		Capacity:         1000000,
		TokensPerRequest: 1,
	})

	agentWithCB := middleware.NewCircuitBreakerDecorator(agentWithRL, middleware.CircuitBreakerConfig{
		FailureThreshold: 5,
		RecoveryTimeout:  1.0,
		SuccessThreshold: 2,
	})

	agentWithTimeout := middleware.NewTimeoutDecorator(agentWithCB, middleware.TimeoutConfig{
		Timeout: 30 * time.Second,
	})

	agentWithRetry := middleware.NewRetryDecorator(agentWithTimeout, middleware.RetryConfig{
		MaxAttempts:    3,
		InitialBackoff: 100 * time.Millisecond,
		MaxBackoff:     1000 * time.Millisecond,
	})

	agentWithAll := middleware.NewMetricsDecorator(agentWithRetry)

	b.RunParallel(func(pb *testing.PB) {
		ctx := context.Background()
		for pb.Next() {
			_, err := agentWithAll.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}
