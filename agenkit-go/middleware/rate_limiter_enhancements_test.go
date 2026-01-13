package middleware

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ============================================
// Max Wait Timeout Tests
// ============================================

func TestRateLimiterMaxWaitTimeout(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)

	config := RateLimiterConfig{
		Rate:             1.0,                      // 1 token per second
		Capacity:         1,                        // Only 1 token capacity
		TokensPerRequest: 1,                        // Each request consumes 1 token
		MaxWaitTimeout:   100 * time.Millisecond,   // Max wait 100ms
	}

	rateLimiter := NewRateLimiterDecorator(agent, config)

	msg := &agenkit.Message{
		Role:    "user",
		Content: "test",
	}

	// First request should succeed immediately
	_, err := rateLimiter.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("First request should succeed, got %v", err)
	}

	// Second request should fail due to max wait timeout
	// (would need to wait ~1s for tokens, but max wait is 100ms)
	_, err = rateLimiter.Process(context.Background(), msg)
	if err == nil {
		t.Error("Second request should fail due to max wait timeout")
	}

	if _, ok := err.(*RateLimitError); !ok {
		t.Errorf("Expected RateLimitError, got %T: %v", err, err)
	}

	// Check metrics
	metrics := rateLimiter.Metrics()
	if metrics.AllowedRequests != 1 {
		t.Errorf("Expected 1 allowed request, got %d", metrics.AllowedRequests)
	}
	if metrics.RejectedRequests != 1 {
		t.Errorf("Expected 1 rejected request, got %d", metrics.RejectedRequests)
	}
}

func TestRateLimiterMaxWaitTimeoutDisabled(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)

	config := RateLimiterConfig{
		Rate:             5.0, // 5 tokens per second
		Capacity:         2,
		TokensPerRequest: 2,
		MaxWaitTimeout:   0, // Disabled (wait indefinitely)
	}

	rateLimiter := NewRateLimiterDecorator(agent, config)

	msg := &agenkit.Message{
		Role:    "user",
		Content: "test",
	}

	// First request should succeed immediately (uses 2 tokens)
	_, err := rateLimiter.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("First request should succeed, got %v", err)
	}

	// Second request should wait and succeed (waits for 2 tokens)
	start := time.Now()
	_, err = rateLimiter.Process(context.Background(), msg)
	elapsed := time.Since(start)

	if err != nil {
		t.Fatalf("Second request should succeed after waiting, got %v", err)
	}

	// Should have waited approximately 400ms (2 tokens at 5/sec)
	expectedWait := 400 * time.Millisecond
	tolerance := 150 * time.Millisecond
	if elapsed < expectedWait-tolerance || elapsed > expectedWait+tolerance {
		t.Errorf("Expected wait time ~%v, got %v", expectedWait, elapsed)
	}
}

// ============================================
// Per-User Rate Limiter Tests
// ============================================

func TestPerUserRateLimiterBasic(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)

	config := PerUserRateLimiterConfig{
		Rate:             0.1, // Very slow refill (0.1 tokens per second)
		Capacity:         2,
		TokensPerRequest: 1,
		MaxWaitTimeout:   50 * time.Millisecond, // Don't wait long
	}

	perUserLimiter := NewPerUserRateLimiterDecorator(agent, config)

	// User 1 makes two requests (should succeed)
	msg1 := &agenkit.Message{
		Role:    "user",
		Content: "user1 request",
		Metadata: map[string]interface{}{
			"user_id": "user1",
		},
	}

	_, err := perUserLimiter.Process(context.Background(), msg1)
	if err != nil {
		t.Fatalf("User1 first request should succeed, got %v", err)
	}

	_, err = perUserLimiter.Process(context.Background(), msg1)
	if err != nil {
		t.Fatalf("User1 second request should succeed, got %v", err)
	}

	// User 1 third request should be rate limited (tokens exhausted)
	_, err = perUserLimiter.Process(context.Background(), msg1)
	if err == nil {
		t.Error("User1 third request should be rate limited")
	}

	// User 2 should have independent rate limit (should succeed)
	msg2 := &agenkit.Message{
		Role:    "user",
		Content: "user2 request",
		Metadata: map[string]interface{}{
			"user_id": "user2",
		},
	}

	_, err = perUserLimiter.Process(context.Background(), msg2)
	if err != nil {
		t.Fatalf("User2 first request should succeed, got %v", err)
	}

	// Check metrics
	metrics := perUserLimiter.Metrics()
	if metrics.TotalRequests != 4 {
		t.Errorf("Expected 4 total requests, got %d", metrics.TotalRequests)
	}
	if metrics.AllowedRequests != 3 {
		t.Errorf("Expected 3 allowed requests, got %d", metrics.AllowedRequests)
	}
	if metrics.RejectedRequests != 1 {
		t.Errorf("Expected 1 rejected request, got %d", metrics.RejectedRequests)
	}
	if metrics.ActiveUsers != 2 {
		t.Errorf("Expected 2 active users, got %d", metrics.ActiveUsers)
	}
}

func TestPerUserRateLimiterAnonymousUser(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)

	config := PerUserRateLimiterConfig{
		Rate:             0.1, // Very slow refill
		Capacity:         1,
		TokensPerRequest: 1,
		MaxWaitTimeout:   50 * time.Millisecond,
	}

	perUserLimiter := NewPerUserRateLimiterDecorator(agent, config)

	// Request without user_id (should fall back to "anonymous")
	msg := &agenkit.Message{
		Role:    "user",
		Content: "anonymous request",
	}

	_, err := perUserLimiter.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("First anonymous request should succeed, got %v", err)
	}

	// Second anonymous request should be rate limited
	_, err = perUserLimiter.Process(context.Background(), msg)
	if err == nil {
		t.Error("Second anonymous request should be rate limited")
	}

	// Check that anonymous users are tracked
	metrics := perUserLimiter.Metrics()
	if metrics.ActiveUsers != 1 {
		t.Errorf("Expected 1 active user (anonymous), got %d", metrics.ActiveUsers)
	}
}

func TestPerUserRateLimiterCustomExtractor(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)

	config := PerUserRateLimiterConfig{
		Rate:             0.1, // Very slow refill
		Capacity:         2,
		TokensPerRequest: 1,
		MaxWaitTimeout:   50 * time.Millisecond,
		// Custom extractor that uses "client_id" instead of "user_id"
		UserIDExtractor: func(msg *agenkit.Message) string {
			if msg.Metadata == nil {
				return ""
			}
			if clientID, ok := msg.Metadata["client_id"].(string); ok {
				return clientID
			}
			return ""
		},
	}

	perUserLimiter := NewPerUserRateLimiterDecorator(agent, config)

	// Request with custom client_id field
	msg := &agenkit.Message{
		Role:    "user",
		Content: "client request",
		Metadata: map[string]interface{}{
			"client_id": "client-123",
		},
	}

	_, err := perUserLimiter.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("First request should succeed, got %v", err)
	}

	_, err = perUserLimiter.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("Second request should succeed, got %v", err)
	}

	// Third request should be rate limited
	_, err = perUserLimiter.Process(context.Background(), msg)
	if err == nil {
		t.Error("Third request should be rate limited")
	}
}

func TestPerUserRateLimiterMaxWaitTimeout(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)

	config := PerUserRateLimiterConfig{
		Rate:             1.0,                      // 1 token per second
		Capacity:         1,
		TokensPerRequest: 1,
		MaxWaitTimeout:   100 * time.Millisecond,   // Max wait 100ms
	}

	perUserLimiter := NewPerUserRateLimiterDecorator(agent, config)

	msg := &agenkit.Message{
		Role:    "user",
		Content: "test",
		Metadata: map[string]interface{}{
			"user_id": "user1",
		},
	}

	// First request should succeed
	_, err := perUserLimiter.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("First request should succeed, got %v", err)
	}

	// Second request should fail due to max wait timeout
	_, err = perUserLimiter.Process(context.Background(), msg)
	if err == nil {
		t.Error("Second request should fail due to max wait timeout")
	}

	if _, ok := err.(*RateLimitError); !ok {
		t.Errorf("Expected RateLimitError, got %T: %v", err, err)
	}
}

func TestPerUserRateLimiterConcurrentUsers(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)

	config := PerUserRateLimiterConfig{
		Rate:             10.0, // 10 tokens per second per user
		Capacity:         5,
		TokensPerRequest: 1,
	}

	perUserLimiter := NewPerUserRateLimiterDecorator(agent, config)

	// Simulate 5 concurrent users, each making 5 requests
	userCount := 5
	requestsPerUser := 5
	done := make(chan bool, userCount)

	for i := 0; i < userCount; i++ {
		userID := fmt.Sprintf("user%d", i)
		go func(uid string) {
			defer func() { done <- true }()

			for j := 0; j < requestsPerUser; j++ {
				msg := &agenkit.Message{
					Role:    "user",
					Content: fmt.Sprintf("%s request %d", uid, j),
					Metadata: map[string]interface{}{
						"user_id": uid,
					},
				}

				_, err := perUserLimiter.Process(context.Background(), msg)
				if err != nil {
					t.Errorf("User %s request %d failed: %v", uid, j, err)
				}
			}
		}(userID)
	}

	// Wait for all goroutines
	for i := 0; i < userCount; i++ {
		<-done
	}

	// Check metrics
	metrics := perUserLimiter.Metrics()
	expectedTotal := userCount * requestsPerUser
	if metrics.TotalRequests != int64(expectedTotal) {
		t.Errorf("Expected %d total requests, got %d", expectedTotal, metrics.TotalRequests)
	}
	if metrics.AllowedRequests != int64(expectedTotal) {
		t.Errorf("Expected %d allowed requests, got %d", expectedTotal, metrics.AllowedRequests)
	}
	if metrics.ActiveUsers != userCount {
		t.Errorf("Expected %d active users, got %d", userCount, metrics.ActiveUsers)
	}
}
