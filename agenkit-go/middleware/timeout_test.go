package middleware

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// ============================================
// Test Agent Implementations
// ============================================

// FastAgent responds quickly.
type FastAgent struct {
	delay time.Duration
}

func NewFastAgent(delay time.Duration) *FastAgent {
	return &FastAgent{delay: delay}
}

func (a *FastAgent) Name() string {
	return "fast-agent"
}

func (a *FastAgent) Capabilities() []string {
	return []string{}
}

func (a *FastAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(a.delay)
	return &agenkit.Message{
		Role:    "agent",
		Content: "Processed: " + message.Content,
	}, nil
}

// SlowAgent takes a long time to respond.
type SlowAgent struct {
	delay time.Duration
}

func NewSlowAgent(delay time.Duration) *SlowAgent {
	return &SlowAgent{delay: delay}
}

func (a *SlowAgent) Name() string {
	return "slow-agent"
}

func (a *SlowAgent) Capabilities() []string {
	return []string{}
}

func (a *SlowAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(a.delay)
	return &agenkit.Message{
		Role:    "agent",
		Content: "Processed after delay: " + message.Content,
	}, nil
}

// AlwaysFailingAgent always returns an error.
type AlwaysFailingAgent struct{}

func (a *AlwaysFailingAgent) Name() string {
	return "always-failing-agent"
}

func (a *AlwaysFailingAgent) Capabilities() []string {
	return []string{}
}

func (a *AlwaysFailingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return nil, fmt.Errorf("Intentional failure for testing")
}

// VariableAgent alternates between fast and slow responses.
type VariableAgent struct {
	counter int
}

func (a *VariableAgent) Name() string {
	return "variable-agent"
}

func (a *VariableAgent) Capabilities() []string {
	return []string{}
}

func (a *VariableAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	a.counter++
	// Odd requests are fast, even requests are slow
	var delay time.Duration
	if a.counter%2 == 1 {
		delay = 10 * time.Millisecond
	} else {
		delay = 5 * time.Second
	}
	time.Sleep(delay)
	return &agenkit.Message{
		Role:    "agent",
		Content: "Response",
	}, nil
}

// ============================================
// Configuration Tests
// ============================================

func TestTimeoutConfigValidation(t *testing.T) {
	// Valid config
	config := TimeoutConfig{Timeout: 10 * time.Second}
	if config.Timeout != 10*time.Second {
		t.Errorf("Expected timeout 10s, got %v", config.Timeout)
	}

	// Default config
	defaultConfig := DefaultTimeoutConfig()
	if defaultConfig.Timeout != 30*time.Second {
		t.Errorf("Expected default timeout 30s, got %v", defaultConfig.Timeout)
	}
}

func TestTimeoutConfigWithInvalidTimeout(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)

	// Negative timeout should be converted to default
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: -1 * time.Second})
	if timeoutAgent.config.Timeout != 30*time.Second {
		t.Errorf("Expected default timeout 30s for negative input, got %v", timeoutAgent.config.Timeout)
	}

	// Zero timeout should be converted to default
	timeoutAgent = NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 0})
	if timeoutAgent.config.Timeout != 30*time.Second {
		t.Errorf("Expected default timeout 30s for zero input, got %v", timeoutAgent.config.Timeout)
	}
}

// ============================================
// Success Cases
// ============================================

func TestTimeoutAllowsFastAgent(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 1 * time.Second})

	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := timeoutAgent.Process(context.Background(), msg)

	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}

	if response.Content != "Processed: test" {
		t.Errorf("Expected 'Processed: test', got '%s'", response.Content)
	}

	// Check metrics
	metrics := timeoutAgent.Metrics()
	if metrics.TotalRequests != 1 {
		t.Errorf("Expected 1 total request, got %d", metrics.TotalRequests)
	}
	if metrics.SuccessfulRequests != 1 {
		t.Errorf("Expected 1 successful request, got %d", metrics.SuccessfulRequests)
	}
	if metrics.TimedOutRequests != 0 {
		t.Errorf("Expected 0 timed out requests, got %d", metrics.TimedOutRequests)
	}
	if metrics.FailedRequests != 0 {
		t.Errorf("Expected 0 failed requests, got %d", metrics.FailedRequests)
	}
	if metrics.MinDuration == nil || metrics.MaxDuration == nil {
		t.Error("Expected min and max duration to be set")
	}
}

func TestTimeoutMultipleSuccessfulRequests(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 1 * time.Second})

	// Send 5 requests
	for i := 0; i < 5; i++ {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		response, err := timeoutAgent.Process(context.Background(), msg)

		if err != nil {
			t.Fatalf("Request %d: expected no error, got %v", i, err)
		}

		if response.Content != "Processed: test" {
			t.Errorf("Request %d: expected 'Processed: test', got '%s'", i, response.Content)
		}
	}

	// Check metrics
	metrics := timeoutAgent.Metrics()
	if metrics.TotalRequests != 5 {
		t.Errorf("Expected 5 total requests, got %d", metrics.TotalRequests)
	}
	if metrics.SuccessfulRequests != 5 {
		t.Errorf("Expected 5 successful requests, got %d", metrics.SuccessfulRequests)
	}
	if metrics.TimedOutRequests != 0 {
		t.Errorf("Expected 0 timed out requests, got %d", metrics.TimedOutRequests)
	}
}

// ============================================
// Timeout Cases
// ============================================

func TestTimeoutStopsSlowAgent(t *testing.T) {
	agent := NewSlowAgent(5 * time.Second)
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 100 * time.Millisecond})

	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := timeoutAgent.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("Expected timeout error, got nil")
	}

	timeoutErr, ok := err.(*TimeoutError)
	if !ok {
		t.Fatalf("Expected TimeoutError, got %T: %v", err, err)
	}

	if timeoutErr.AgentName != "slow-agent" {
		t.Errorf("Expected agent name 'slow-agent', got '%s'", timeoutErr.AgentName)
	}

	if response != nil {
		t.Error("Expected nil response on timeout")
	}

	// Check metrics
	metrics := timeoutAgent.Metrics()
	if metrics.TotalRequests != 1 {
		t.Errorf("Expected 1 total request, got %d", metrics.TotalRequests)
	}
	if metrics.SuccessfulRequests != 0 {
		t.Errorf("Expected 0 successful requests, got %d", metrics.SuccessfulRequests)
	}
	if metrics.TimedOutRequests != 1 {
		t.Errorf("Expected 1 timed out request, got %d", metrics.TimedOutRequests)
	}
}

func TestTimeoutReportsAgentName(t *testing.T) {
	agent := NewSlowAgent(5 * time.Second)
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 100 * time.Millisecond})

	msg := &agenkit.Message{Role: "user", Content: "test"}
	_, err := timeoutAgent.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("Expected timeout error, got nil")
	}

	timeoutErr, ok := err.(*TimeoutError)
	if !ok {
		t.Fatalf("Expected TimeoutError, got %T", err)
	}

	if timeoutErr.AgentName != "slow-agent" {
		t.Errorf("Expected agent name 'slow-agent', got '%s'", timeoutErr.AgentName)
	}
}

func TestTimeoutBoundaryCase(t *testing.T) {
	// Agent takes 100ms, timeout is 150ms - should succeed
	agent := NewFastAgent(100 * time.Millisecond)
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 150 * time.Millisecond})

	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := timeoutAgent.Process(context.Background(), msg)

	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}

	if response.Content != "Processed: test" {
		t.Errorf("Expected 'Processed: test', got '%s'", response.Content)
	}

	if timeoutAgent.Metrics().SuccessfulRequests != 1 {
		t.Errorf("Expected 1 successful request, got %d", timeoutAgent.Metrics().SuccessfulRequests)
	}
}

func TestTimeoutMixedRequests(t *testing.T) {
	agent := &VariableAgent{}
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 100 * time.Millisecond})

	// Request 1: Fast (succeeds)
	msg1 := &agenkit.Message{Role: "user", Content: "1"}
	response1, err1 := timeoutAgent.Process(context.Background(), msg1)
	if err1 != nil {
		t.Fatalf("Request 1: expected no error, got %v", err1)
	}
	if response1.Content != "Response" {
		t.Errorf("Request 1: expected 'Response', got '%s'", response1.Content)
	}

	// Request 2: Slow (times out)
	msg2 := &agenkit.Message{Role: "user", Content: "2"}
	_, err2 := timeoutAgent.Process(context.Background(), msg2)
	if err2 == nil {
		t.Fatal("Request 2: expected timeout error, got nil")
	}
	if _, ok := err2.(*TimeoutError); !ok {
		t.Fatalf("Request 2: expected TimeoutError, got %T", err2)
	}

	// Request 3: Fast (succeeds)
	msg3 := &agenkit.Message{Role: "user", Content: "3"}
	response3, err3 := timeoutAgent.Process(context.Background(), msg3)
	if err3 != nil {
		t.Fatalf("Request 3: expected no error, got %v", err3)
	}
	if response3.Content != "Response" {
		t.Errorf("Request 3: expected 'Response', got '%s'", response3.Content)
	}

	// Check metrics
	metrics := timeoutAgent.Metrics()
	if metrics.TotalRequests != 3 {
		t.Errorf("Expected 3 total requests, got %d", metrics.TotalRequests)
	}
	if metrics.SuccessfulRequests != 2 {
		t.Errorf("Expected 2 successful requests, got %d", metrics.SuccessfulRequests)
	}
	if metrics.TimedOutRequests != 1 {
		t.Errorf("Expected 1 timed out request, got %d", metrics.TimedOutRequests)
	}
	if metrics.FailedRequests != 0 {
		t.Errorf("Expected 0 failed requests, got %d", metrics.FailedRequests)
	}
}

// ============================================
// Error Handling
// ============================================

func TestTimeoutPreservesOtherErrors(t *testing.T) {
	agent := &AlwaysFailingAgent{}
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 1 * time.Second})

	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := timeoutAgent.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	if err.Error() != "Intentional failure for testing" {
		t.Errorf("Expected 'Intentional failure for testing', got '%s'", err.Error())
	}

	if response != nil {
		t.Error("Expected nil response on error")
	}

	// Check metrics
	metrics := timeoutAgent.Metrics()
	if metrics.TotalRequests != 1 {
		t.Errorf("Expected 1 total request, got %d", metrics.TotalRequests)
	}
	if metrics.SuccessfulRequests != 0 {
		t.Errorf("Expected 0 successful requests, got %d", metrics.SuccessfulRequests)
	}
	if metrics.TimedOutRequests != 0 {
		t.Errorf("Expected 0 timed out requests, got %d", metrics.TimedOutRequests)
	}
	if metrics.FailedRequests != 1 {
		t.Errorf("Expected 1 failed request, got %d", metrics.FailedRequests)
	}
}

func TestTimeoutWithAgentThatFailsFast(t *testing.T) {
	agent := &AlwaysFailingAgent{}
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 5 * time.Second})

	msg := &agenkit.Message{Role: "user", Content: "test"}
	_, err := timeoutAgent.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	// Should get the agent's error, not a timeout
	if _, ok := err.(*TimeoutError); ok {
		t.Error("Expected regular error, got TimeoutError")
	}

	// Metrics should show failed request, not timeout
	metrics := timeoutAgent.Metrics()
	if metrics.TimedOutRequests != 0 {
		t.Errorf("Expected 0 timed out requests, got %d", metrics.TimedOutRequests)
	}
	if metrics.FailedRequests != 1 {
		t.Errorf("Expected 1 failed request, got %d", metrics.FailedRequests)
	}
}

// ============================================
// Metrics Tests
// ============================================

func TestTimeoutMetricsDurationTracking(t *testing.T) {
	agent := NewFastAgent(50 * time.Millisecond)
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 1 * time.Second})

	// Send 3 requests
	for i := 0; i < 3; i++ {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		_, err := timeoutAgent.Process(context.Background(), msg)
		if err != nil {
			t.Fatalf("Request %d: expected no error, got %v", i, err)
		}
	}

	metrics := timeoutAgent.Metrics()
	if metrics.TotalRequests != 3 {
		t.Errorf("Expected 3 total requests, got %d", metrics.TotalRequests)
	}
	if metrics.MinDuration == nil {
		t.Error("Expected MinDuration to be set")
	}
	if metrics.MaxDuration == nil {
		t.Error("Expected MaxDuration to be set")
	}

	avgDuration := metrics.AvgDuration()
	if avgDuration < 40*time.Millisecond || avgDuration > 100*time.Millisecond {
		t.Errorf("Expected avg duration ~50ms, got %v", avgDuration)
	}
}

func TestTimeoutMetricsTracksTimeoutDuration(t *testing.T) {
	agent := NewSlowAgent(10 * time.Second)
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 100 * time.Millisecond})

	msg := &agenkit.Message{Role: "user", Content: "test"}
	_, err := timeoutAgent.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("Expected timeout error, got nil")
	}

	metrics := timeoutAgent.Metrics()
	if metrics.TimedOutRequests != 1 {
		t.Errorf("Expected 1 timed out request, got %d", metrics.TimedOutRequests)
	}

	avgDuration := metrics.AvgDuration()
	if avgDuration < 90*time.Millisecond || avgDuration > 200*time.Millisecond {
		t.Errorf("Expected avg duration ~100ms, got %v", avgDuration)
	}
}

// ============================================
// Agent Interface Tests
// ============================================

func TestTimeoutDecoratorPreservesAgentInterface(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)
	timeoutAgent := NewTimeoutDecorator(agent, TimeoutConfig{Timeout: 1 * time.Second})

	// Should have correct name
	if timeoutAgent.Name() != "fast-agent" {
		t.Errorf("Expected name 'fast-agent', got '%s'", timeoutAgent.Name())
	}

	// Should have correct capabilities
	capabilities := timeoutAgent.Capabilities()
	if len(capabilities) != 0 {
		t.Errorf("Expected 0 capabilities, got %d", len(capabilities))
	}
}

// ============================================
// Default Configuration Tests
// ============================================

func TestTimeoutDefaultConfig(t *testing.T) {
	agent := NewFastAgent(10 * time.Millisecond)
	config := DefaultTimeoutConfig()
	timeoutAgent := NewTimeoutDecorator(agent, config)

	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := timeoutAgent.Process(context.Background(), msg)

	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}

	if response.Content != "Processed: test" {
		t.Errorf("Expected 'Processed: test', got '%s'", response.Content)
	}

	if timeoutAgent.Metrics().SuccessfulRequests != 1 {
		t.Errorf("Expected 1 successful request, got %d", timeoutAgent.Metrics().SuccessfulRequests)
	}
}

func TestTimeoutDefaultIs30Seconds(t *testing.T) {
	agent := NewSlowAgent(500 * time.Millisecond)
	config := DefaultTimeoutConfig()
	timeoutAgent := NewTimeoutDecorator(agent, config)

	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := timeoutAgent.Process(context.Background(), msg)

	if err != nil {
		t.Fatalf("Expected no error with 30s timeout, got %v", err)
	}

	if response.Content != "Processed after delay: test" {
		t.Errorf("Expected 'Processed after delay: test', got '%s'", response.Content)
	}

	// Verify the default timeout is 30 seconds
	if config.Timeout != 30*time.Second {
		t.Errorf("Expected default timeout 30s, got %v", config.Timeout)
	}
}
