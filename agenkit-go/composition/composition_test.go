package composition

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// TestAgent is a configurable test agent
type TestAgent struct {
	name     string
	response string
	err      error
	delay    time.Duration
	calls    int
}

func (t *TestAgent) Name() string {
	return t.name
}

func (t *TestAgent) Capabilities() []string {
	return []string{"test"}
}

func (t *TestAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	t.calls++
	if t.delay > 0 {
		select {
		case <-time.After(t.delay):
			// Delay completed
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
	if t.err != nil {
		return nil, t.err
	}
	return agenkit.NewMessage("agent", t.response), nil
}

// Sequential Agent Tests

func TestSequentialAgentBasic(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", response: "step1"}
	agent2 := &TestAgent{name: "agent2", response: "step2"}
	agent3 := &TestAgent{name: "agent3", response: "step3"}

	seq, err := NewSequentialAgent("sequential", agent1, agent2, agent3)
	if err != nil {
		t.Fatalf("Failed to create sequential agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "start")
	result, err := seq.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Final result should be from last agent
	if result.Content != "step3" {
		t.Errorf("Expected final result 'step3', got '%s'", result.Content)
	}

	// All agents should have been called
	if agent1.calls != 1 || agent2.calls != 1 || agent3.calls != 1 {
		t.Errorf("Expected all agents called once, got %d, %d, %d",
			agent1.calls, agent2.calls, agent3.calls)
	}
}

func TestSequentialAgentError(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", response: "step1"}
	agent2 := &TestAgent{name: "agent2", err: errors.New("agent2 failed")}
	agent3 := &TestAgent{name: "agent3", response: "step3"}

	seq, err := NewSequentialAgent("sequential", agent1, agent2, agent3)
	if err != nil {
		t.Fatalf("Failed to create sequential agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "start")
	_, err = seq.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected error from failing agent")
	}

	// Should stop at agent2
	if agent1.calls != 1 {
		t.Errorf("Expected agent1 called once, got %d", agent1.calls)
	}
	if agent2.calls != 1 {
		t.Errorf("Expected agent2 called once, got %d", agent2.calls)
	}
	if agent3.calls != 0 {
		t.Errorf("Expected agent3 not called, got %d calls", agent3.calls)
	}
}

func TestSequentialAgentEmpty(t *testing.T) {
	_, err := NewSequentialAgent("sequential")
	if err == nil {
		t.Fatal("Expected error when creating sequential agent with no agents")
	}
}

func TestSequentialAgentContextCancellation(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()

	agent1 := &TestAgent{name: "agent1", response: "step1", delay: 50 * time.Millisecond}
	agent2 := &TestAgent{name: "agent2", response: "step2"}

	seq, _ := NewSequentialAgent("sequential", agent1, agent2)

	msg := agenkit.NewMessage("user", "start")
	_, err := seq.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected error from context cancellation")
	}

	// Verify it's a context error
	if !strings.Contains(err.Error(), "context") && !strings.Contains(err.Error(), "deadline") {
		t.Errorf("Expected context error, got: %v", err)
	}
}

// Parallel Agent Tests

func TestParallelAgentBasic(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", response: "response1"}
	agent2 := &TestAgent{name: "agent2", response: "response2"}
	agent3 := &TestAgent{name: "agent3", response: "response3"}

	par, err := NewParallelAgent("parallel", agent1, agent2, agent3)
	if err != nil {
		t.Fatalf("Failed to create parallel agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "query")
	result, err := par.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// All agents should have been called
	if agent1.calls != 1 || agent2.calls != 1 || agent3.calls != 1 {
		t.Errorf("Expected all agents called once, got %d, %d, %d",
			agent1.calls, agent2.calls, agent3.calls)
	}

	// Result should contain all responses
	content := result.Content
	if !strings.Contains(content, "agent1") || !strings.Contains(content, "response1") {
		t.Errorf("Expected agent1 response in combined result")
	}
	if !strings.Contains(content, "agent2") || !strings.Contains(content, "response2") {
		t.Errorf("Expected agent2 response in combined result")
	}
	if !strings.Contains(content, "agent3") || !strings.Contains(content, "response3") {
		t.Errorf("Expected agent3 response in combined result")
	}
}

func TestParallelAgentError(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", response: "response1"}
	agent2 := &TestAgent{name: "agent2", err: errors.New("agent2 failed")}
	agent3 := &TestAgent{name: "agent3", response: "response3"}

	par, err := NewParallelAgent("parallel", agent1, agent2, agent3)
	if err != nil {
		t.Fatalf("Failed to create parallel agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "query")
	_, err = par.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected error from failing agent")
	}

	// All agents should still have been called
	if agent1.calls != 1 || agent2.calls != 1 || agent3.calls != 1 {
		t.Errorf("Expected all agents called once, got %d, %d, %d",
			agent1.calls, agent2.calls, agent3.calls)
	}
}

func TestParallelAgentEmpty(t *testing.T) {
	_, err := NewParallelAgent("parallel")
	if err == nil {
		t.Fatal("Expected error when creating parallel agent with no agents")
	}
}

func TestParallelAgentConcurrency(t *testing.T) {
	ctx := context.Background()

	// Create agents with delays to test true parallelism
	agent1 := &TestAgent{name: "agent1", response: "response1", delay: 100 * time.Millisecond}
	agent2 := &TestAgent{name: "agent2", response: "response2", delay: 100 * time.Millisecond}
	agent3 := &TestAgent{name: "agent3", response: "response3", delay: 100 * time.Millisecond}

	par, _ := NewParallelAgent("parallel", agent1, agent2, agent3)

	start := time.Now()
	msg := agenkit.NewMessage("user", "query")
	_, err := par.Process(ctx, msg)
	duration := time.Since(start)

	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should complete in ~100ms (parallel) not ~300ms (sequential)
	if duration > 200*time.Millisecond {
		t.Errorf("Parallel execution took too long: %v (expected ~100ms)", duration)
	}
}

// Fallback Agent Tests

func TestFallbackAgentFirstSucceeds(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", response: "success1"}
	agent2 := &TestAgent{name: "agent2", response: "success2"}
	agent3 := &TestAgent{name: "agent3", response: "success3"}

	fallback, err := NewFallbackAgent("fallback", agent1, agent2, agent3)
	if err != nil {
		t.Fatalf("Failed to create fallback agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "query")
	result, err := fallback.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should use first agent
	if result.Content != "success1" {
		t.Errorf("Expected response from agent1, got '%s'", result.Content)
	}

	// Only first agent should be called
	if agent1.calls != 1 {
		t.Errorf("Expected agent1 called once, got %d", agent1.calls)
	}
	if agent2.calls != 0 || agent3.calls != 0 {
		t.Errorf("Expected agent2 and agent3 not called")
	}

	// Check metadata
	if result.Metadata["fallback_agent_used"] != "agent1" {
		t.Errorf("Expected fallback_agent_used=agent1")
	}
}

func TestFallbackAgentSecondSucceeds(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", err: errors.New("agent1 failed")}
	agent2 := &TestAgent{name: "agent2", response: "success2"}
	agent3 := &TestAgent{name: "agent3", response: "success3"}

	fallback, _ := NewFallbackAgent("fallback", agent1, agent2, agent3)

	msg := agenkit.NewMessage("user", "query")
	result, err := fallback.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should use second agent
	if result.Content != "success2" {
		t.Errorf("Expected response from agent2, got '%s'", result.Content)
	}

	// First two agents should be called
	if agent1.calls != 1 || agent2.calls != 1 {
		t.Errorf("Expected agent1 and agent2 called, got %d, %d", agent1.calls, agent2.calls)
	}
	if agent3.calls != 0 {
		t.Errorf("Expected agent3 not called")
	}
}

func TestFallbackAgentAllFail(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", err: errors.New("agent1 failed")}
	agent2 := &TestAgent{name: "agent2", err: errors.New("agent2 failed")}
	agent3 := &TestAgent{name: "agent3", err: errors.New("agent3 failed")}

	fallback, _ := NewFallbackAgent("fallback", agent1, agent2, agent3)

	msg := agenkit.NewMessage("user", "query")
	_, err := fallback.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected error when all agents fail")
	}

	// All agents should have been tried
	if agent1.calls != 1 || agent2.calls != 1 || agent3.calls != 1 {
		t.Errorf("Expected all agents called, got %d, %d, %d",
			agent1.calls, agent2.calls, agent3.calls)
	}
}

func TestFallbackAgentEmpty(t *testing.T) {
	_, err := NewFallbackAgent("fallback")
	if err == nil {
		t.Fatal("Expected error when creating fallback agent with no agents")
	}
}

// Conditional Agent Tests

func TestConditionalAgentRouting(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", response: "handled by agent1"}
	agent2 := &TestAgent{name: "agent2", response: "handled by agent2"}
	defaultAgent := &TestAgent{name: "default", response: "handled by default"}

	cond := NewConditionalAgent("conditional", defaultAgent)
	cond.AddRoute(ContentContains("hello"), agent1)
	cond.AddRoute(ContentContains("goodbye"), agent2)

	// Test first route
	msg1 := agenkit.NewMessage("user", "hello world")
	result1, err := cond.Process(ctx, msg1)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if result1.Content != "handled by agent1" {
		t.Errorf("Expected agent1 response, got '%s'", result1.Content)
	}
	if agent1.calls != 1 {
		t.Errorf("Expected agent1 called once, got %d", agent1.calls)
	}

	// Test second route
	msg2 := agenkit.NewMessage("user", "goodbye world")
	result2, err := cond.Process(ctx, msg2)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if result2.Content != "handled by agent2" {
		t.Errorf("Expected agent2 response, got '%s'", result2.Content)
	}
	if agent2.calls != 1 {
		t.Errorf("Expected agent2 called once, got %d", agent2.calls)
	}

	// Test default route
	msg3 := agenkit.NewMessage("user", "other message")
	result3, err := cond.Process(ctx, msg3)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if result3.Content != "handled by default" {
		t.Errorf("Expected default agent response, got '%s'", result3.Content)
	}
	if defaultAgent.calls != 1 {
		t.Errorf("Expected default agent called once, got %d", defaultAgent.calls)
	}
}

func TestConditionalAgentNoDefault(t *testing.T) {
	ctx := context.Background()

	agent1 := &TestAgent{name: "agent1", response: "handled by agent1"}

	cond := NewConditionalAgent("conditional", nil)
	cond.AddRoute(ContentContains("hello"), agent1)

	// Test no match and no default
	msg := agenkit.NewMessage("user", "other message")
	_, err := cond.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected error when no route matches and no default agent")
	}
}

func TestConditionHelpers(t *testing.T) {
	// Test ContentContains
	msg1 := agenkit.NewMessage("user", "hello world")
	if !ContentContains("hello")(msg1) {
		t.Error("ContentContains failed")
	}

	// Test RoleEquals
	msg2 := agenkit.NewMessage("user", "test")
	if !RoleEquals("user")(msg2) {
		t.Error("RoleEquals failed")
	}

	// Test MetadataHasKey
	msg3 := agenkit.NewMessage("user", "test").WithMetadata("key", "value")
	if !MetadataHasKey("key")(msg3) {
		t.Error("MetadataHasKey failed")
	}

	// Test MetadataEquals
	if !MetadataEquals("key", "value")(msg3) {
		t.Error("MetadataEquals failed")
	}

	// Test And
	msg4 := agenkit.NewMessage("user", "hello").WithMetadata("key", "value")
	andCond := And(ContentContains("hello"), MetadataHasKey("key"))
	if !andCond(msg4) {
		t.Error("And condition failed")
	}

	// Test Or
	msg5 := agenkit.NewMessage("user", "test")
	orCond := Or(ContentContains("hello"), ContentContains("test"))
	if !orCond(msg5) {
		t.Error("Or condition failed")
	}

	// Test Not
	msg6 := agenkit.NewMessage("user", "test")
	notCond := Not(ContentContains("hello"))
	if !notCond(msg6) {
		t.Error("Not condition failed")
	}
}

// Test that all composition agents implement Agent interface
func TestCompositionAgentsImplementInterface(t *testing.T) {
	agent := &TestAgent{name: "test", response: "test"}

	seq, _ := NewSequentialAgent("seq", agent)
	var _ agenkit.Agent = seq

	par, _ := NewParallelAgent("par", agent)
	var _ agenkit.Agent = par

	fallback, _ := NewFallbackAgent("fallback", agent)
	var _ agenkit.Agent = fallback

	cond := NewConditionalAgent("cond", agent)
	var _ agenkit.Agent = cond
}
