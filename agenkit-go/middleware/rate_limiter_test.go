package middleware

import (
	"context"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// SimpleAgent always succeeds immediately.
type SimpleAgent struct {
	callCount int
}

func (s *SimpleAgent) Name() string {
	return "simple-agent"
}

func (s *SimpleAgent) Capabilities() []string {
	return []string{}
}

func (s *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	s.callCount++
	return agenkit.NewMessage("agent", "success"), nil
}

// TestRateLimiterBasic tests basic rate limiting functionality.
func TestRateLimiterBasic(t *testing.T) {
	ctx := context.Background()
	agent := &SimpleAgent{}

	// 10 tokens/sec, capacity 10
	rl := NewRateLimiterDecorator(agent, RateLimiterConfig{
		Rate:             10.0,
		Capacity:         10,
		TokensPerRequest: 1,
	})

	// Should allow 10 requests immediately (full capacity)
	for i := 0; i < 10; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := rl.Process(ctx, msg)

		if err != nil {
			t.Fatalf("Request %d: Expected success, got error: %v", i+1, err)
		}
	}

	if agent.callCount != 10 {
		t.Errorf("Expected 10 calls to agent, got %d", agent.callCount)
	}

	metrics := rl.Metrics()
	if metrics.TotalRequests != 10 {
		t.Errorf("Expected 10 total requests, got %d", metrics.TotalRequests)
	}
	if metrics.AllowedRequests != 10 {
		t.Errorf("Expected 10 allowed requests, got %d", metrics.AllowedRequests)
	}
}

// TestRateLimiterRefill tests token refill over time.
func TestRateLimiterRefill(t *testing.T) {
	ctx := context.Background()
	agent := &SimpleAgent{}

	// 10 tokens/sec, capacity 5
	rl := NewRateLimiterDecorator(agent, RateLimiterConfig{
		Rate:             10.0,
		Capacity:         5,
		TokensPerRequest: 1,
	})

	// Consume all tokens
	for i := 0; i < 5; i++ {
		msg := agenkit.NewMessage("user", "test")
		rl.Process(ctx, msg)
	}

	// Wait for 500ms (should refill 5 tokens)
	time.Sleep(500 * time.Millisecond)

	// Should be able to make ~5 more requests
	successCount := 0
	for i := 0; i < 5; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := rl.Process(ctx, msg)
		if err == nil {
			successCount++
		} else {
			break // Stop on first error
		}
	}

	// Should have successfully made around 5 requests (allowing for timing variance)
	if successCount < 4 {
		t.Errorf("Expected at least 4 successful requests after refill, got %d", successCount)
	}
}

// TestRateLimiterWait tests waiting for tokens.
func TestRateLimiterWait(t *testing.T) {
	ctx := context.Background()
	agent := &SimpleAgent{}

	// 5 tokens/sec, capacity 5
	rl := NewRateLimiterDecorator(agent, RateLimiterConfig{
		Rate:             5.0,
		Capacity:         5,
		TokensPerRequest: 1,
	})

	// Consume all tokens
	for i := 0; i < 5; i++ {
		msg := agenkit.NewMessage("user", "test")
		rl.Process(ctx, msg)
	}

	// Next request should wait for tokens
	start := time.Now()
	msg := agenkit.NewMessage("user", "test")
	_, err := rl.Process(ctx, msg)
	elapsed := time.Since(start)

	if err != nil {
		t.Fatalf("Expected success after waiting, got error: %v", err)
	}

	// Should have waited approximately 200ms (1 token / 5 tokens per second)
	expectedWait := 200 * time.Millisecond
	if elapsed < expectedWait/2 {
		t.Errorf("Expected to wait at least %v, but only waited %v", expectedWait/2, elapsed)
	}

	metrics := rl.Metrics()
	if metrics.TotalWaitTime == 0 {
		t.Error("Expected non-zero total wait time")
	}
}

// TestRateLimiterBurst tests burst capacity.
func TestRateLimiterBurst(t *testing.T) {
	ctx := context.Background()
	agent := &SimpleAgent{}

	// 2 tokens/sec, but capacity 10 (allows bursts)
	rl := NewRateLimiterDecorator(agent, RateLimiterConfig{
		Rate:             2.0,
		Capacity:         10,
		TokensPerRequest: 1,
	})

	// Should allow 10 requests immediately despite low rate
	for i := 0; i < 10; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := rl.Process(ctx, msg)

		if err != nil {
			t.Fatalf("Request %d: Expected success in burst, got error: %v", i+1, err)
		}
	}

	if agent.callCount != 10 {
		t.Errorf("Expected 10 calls in burst, got %d", agent.callCount)
	}
}

// TestRateLimiterMultipleTokens tests requests requiring multiple tokens.
func TestRateLimiterMultipleTokens(t *testing.T) {
	ctx := context.Background()
	agent := &SimpleAgent{}

	// 10 tokens/sec, capacity 10, but 5 tokens per request
	rl := NewRateLimiterDecorator(agent, RateLimiterConfig{
		Rate:             10.0,
		Capacity:         10,
		TokensPerRequest: 5,
	})

	// Should allow 2 requests (2 * 5 = 10 tokens)
	for i := 0; i < 2; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := rl.Process(ctx, msg)

		if err != nil {
			t.Fatalf("Request %d: Expected success, got error: %v", i+1, err)
		}
	}

	if agent.callCount != 2 {
		t.Errorf("Expected 2 calls, got %d", agent.callCount)
	}
}

// TestRateLimiterContextCancellation tests context cancellation during wait.
func TestRateLimiterContextCancellation(t *testing.T) {
	agent := &SimpleAgent{}

	// 5 tokens/sec, capacity 1
	rl := NewRateLimiterDecorator(agent, RateLimiterConfig{
		Rate:             5.0,
		Capacity:         1,
		TokensPerRequest: 1,
	})

	// Consume the token
	msg := agenkit.NewMessage("user", "test")
	rl.Process(context.Background(), msg)

	// Create context with short timeout
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	// Next request should be cancelled before tokens refill
	msg = agenkit.NewMessage("user", "test")
	_, err := rl.Process(ctx, msg)

	if err == nil {
		t.Fatal("Expected context cancellation error, got nil")
	}

	if err != context.DeadlineExceeded && err.Error() != "context deadline exceeded" {
		t.Errorf("Expected context cancellation error, got: %v", err)
	}
}

// TestRateLimiterMetrics tests comprehensive metrics tracking.
func TestRateLimiterMetrics(t *testing.T) {
	ctx := context.Background()
	agent := &SimpleAgent{}

	// 10 tokens/sec, capacity 5
	rl := NewRateLimiterDecorator(agent, RateLimiterConfig{
		Rate:             10.0,
		Capacity:         5,
		TokensPerRequest: 1,
	})

	// Make 5 requests (consume all tokens)
	for i := 0; i < 5; i++ {
		msg := agenkit.NewMessage("user", "test")
		rl.Process(ctx, msg)
	}

	metrics := rl.Metrics()

	if metrics.TotalRequests != 5 {
		t.Errorf("Expected 5 total requests, got %d", metrics.TotalRequests)
	}

	if metrics.AllowedRequests != 5 {
		t.Errorf("Expected 5 allowed requests, got %d", metrics.AllowedRequests)
	}

	if metrics.RejectedRequests != 0 {
		t.Errorf("Expected 0 rejected requests, got %d", metrics.RejectedRequests)
	}

	// Current tokens should be near 0
	if metrics.CurrentTokens > 1.0 {
		t.Errorf("Expected current tokens near 0, got %.2f", metrics.CurrentTokens)
	}
}

// TestRateLimiterHighThroughput tests rate limiter under high load.
func TestRateLimiterHighThroughput(t *testing.T) {
	ctx := context.Background()
	agent := &SimpleAgent{}

	// 100 tokens/sec, capacity 100
	rl := NewRateLimiterDecorator(agent, RateLimiterConfig{
		Rate:             100.0,
		Capacity:         100,
		TokensPerRequest: 1,
	})

	// Should handle 100 requests immediately
	start := time.Now()
	for i := 0; i < 100; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := rl.Process(ctx, msg)

		if err != nil {
			t.Fatalf("Request %d: Expected success, got error: %v", i+1, err)
		}
	}
	elapsed := time.Since(start)

	// Should complete quickly (within 1 second)
	if elapsed > 1*time.Second {
		t.Errorf("Expected to complete within 1s, took %v", elapsed)
	}

	if agent.callCount != 100 {
		t.Errorf("Expected 100 calls, got %d", agent.callCount)
	}

	metrics := rl.Metrics()
	if metrics.AllowedRequests != 100 {
		t.Errorf("Expected 100 allowed requests, got %d", metrics.AllowedRequests)
	}
}
