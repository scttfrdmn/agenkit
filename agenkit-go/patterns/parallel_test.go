package patterns

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestParallelAgent_Constructor tests valid construction
func TestParallelAgent_Constructor(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "result1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "result2"}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return messages[0]
	}

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2}, aggregator)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if parallel == nil {
		t.Fatal("expected non-nil ParallelAgent")
	}
	if parallel.Name() != "ParallelAgent" {
		t.Errorf("expected name 'ParallelAgent', got '%s'", parallel.Name())
	}
}

// TestParallelAgent_ConstructorEmptyAgents tests error case with no agents
func TestParallelAgent_ConstructorEmptyAgents(t *testing.T) {
	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return messages[0]
	}

	_, err := NewParallelAgent([]agenkit.Agent{}, aggregator)
	if err == nil {
		t.Fatal("expected error for empty agents list")
	}
	if !strings.Contains(err.Error(), "at least one agent") {
		t.Errorf("expected 'at least one agent' error, got %v", err)
	}
}

// TestParallelAgent_ConstructorNilAggregator tests error case with nil aggregator
func TestParallelAgent_ConstructorNilAggregator(t *testing.T) {
	agent := &extendedMockAgent{name: "agent1", response: "result1"}

	_, err := NewParallelAgent([]agenkit.Agent{agent}, nil)
	if err == nil {
		t.Fatal("expected error for nil aggregator")
	}
	if !strings.Contains(err.Error(), "aggregator") {
		t.Errorf("expected 'aggregator' error, got %v", err)
	}
}

// TestParallelAgent_BasicProcess tests simple success case
func TestParallelAgent_BasicProcess(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "response1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "response2"}
	agent3 := &extendedMockAgent{name: "agent3", response: "response3"}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		// Count responses
		return agenkit.NewMessage("assistant", fmt.Sprintf("aggregated %d responses", len(messages)))
	}

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, aggregator)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test input")
	result, err := parallel.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "aggregated 3 responses" {
		t.Errorf("expected 'aggregated 3 responses', got '%s'", result.Content)
	}
}

// TestParallelAgent_ConcurrentExecution tests that agents run concurrently
func TestParallelAgent_ConcurrentExecution(t *testing.T) {
	var counter int32
	var maxConcurrent int32

	// Create agents that increment counter to test concurrency
	createAgent := func(name string) *extendedMockAgent {
		return &extendedMockAgent{
			name: name,
			processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
				current := atomic.AddInt32(&counter, 1)
				// Atomically update maxConcurrent if current is greater
				for {
					max := atomic.LoadInt32(&maxConcurrent)
					if current <= max || atomic.CompareAndSwapInt32(&maxConcurrent, max, current) {
						break
					}
				}

				// Sleep to ensure overlap
				time.Sleep(50 * time.Millisecond)

				atomic.AddInt32(&counter, -1)
				return agenkit.NewMessage("assistant", name), nil
			},
		}
	}

	agent1 := createAgent("agent1")
	agent2 := createAgent("agent2")
	agent3 := createAgent("agent3")

	aggregator := DefaultAggregators.First

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, aggregator)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = parallel.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// If truly concurrent, max should be > 1
	if maxConcurrent < 2 {
		t.Errorf("expected concurrent execution (maxConcurrent >= 2), got %d", maxConcurrent)
	}
}

// TestParallelAgent_Metadata tests metadata handling
func TestParallelAgent_Metadata(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "r1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "r2"}

	aggregator := DefaultAggregators.First

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2}, aggregator)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := parallel.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check metadata
	if result.Metadata["parallel_agents"] != 2 {
		t.Errorf("expected parallel_agents=2, got %v", result.Metadata["parallel_agents"])
	}
	if result.Metadata["successful_agents"] != 2 {
		t.Errorf("expected successful_agents=2, got %v", result.Metadata["successful_agents"])
	}
}

// TestParallelAgent_PartialFailure tests when some agents fail
func TestParallelAgent_PartialFailure(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "success"}
	agent2 := &extendedMockAgent{name: "agent2", err: errors.New("agent2 failed")}
	agent3 := &extendedMockAgent{name: "agent3", response: "success"}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		return agenkit.NewMessage("assistant", fmt.Sprintf("got %d successes", len(messages)))
	}

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, aggregator)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := parallel.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error on partial failure: %v", err)
	}

	// Should have 2 successes
	if result.Content != "got 2 successes" {
		t.Errorf("expected 'got 2 successes', got '%s'", result.Content)
	}

	// Check error metadata
	errors, ok := result.Metadata["errors"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected errors in metadata")
	}
	if len(errors) != 1 {
		t.Errorf("expected 1 error, got %d", len(errors))
	}
	if errors[0]["agent"] != "agent2" {
		t.Errorf("expected error from agent2, got %v", errors[0]["agent"])
	}
}

// TestParallelAgent_AllAgentsFail tests when all agents fail
func TestParallelAgent_AllAgentsFail(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", err: errors.New("error1")}
	agent2 := &extendedMockAgent{name: "agent2", err: errors.New("error2")}

	aggregator := DefaultAggregators.First

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2}, aggregator)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := parallel.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error when all agents fail")
	}
	if result != nil {
		t.Error("expected nil result when all agents fail")
	}
	if !strings.Contains(err.Error(), "all agents failed") {
		t.Errorf("expected 'all agents failed' error, got: %v", err)
	}
}

// TestParallelAgent_NilMessage tests nil message handling
func TestParallelAgent_NilMessage(t *testing.T) {
	agent := &extendedMockAgent{name: "agent1", response: "test"}
	parallel, err := NewParallelAgent([]agenkit.Agent{agent}, DefaultAggregators.First)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = parallel.Process(context.Background(), nil)
	if err == nil {
		t.Fatal("expected error for nil message")
	}
	if !strings.Contains(err.Error(), "cannot be nil") {
		t.Errorf("expected 'cannot be nil' error, got: %v", err)
	}
}

// TestParallelAgent_Capabilities tests combined capabilities
func TestParallelAgent_Capabilities(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", capabilities: []string{"cap1", "cap2"}}
	agent2 := &extendedMockAgent{name: "agent2", capabilities: []string{"cap2", "cap3"}}

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2}, DefaultAggregators.First)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	caps := parallel.Capabilities()

	// Should have unique capabilities plus parallel/ensemble
	expectedCaps := map[string]bool{
		"cap1":     true,
		"cap2":     true,
		"cap3":     true,
		"parallel": true,
		"ensemble": true,
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d: %v", len(expectedCaps), len(caps), caps)
	}
}

// TestParallelAgent_DefaultAggregatorFirst tests First aggregator
func TestParallelAgent_DefaultAggregatorFirst(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "first"}
	agent2 := &extendedMockAgent{name: "agent2", response: "second"}

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2}, DefaultAggregators.First)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := parallel.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// First should return one of the results (order may vary due to concurrency)
	if result.Content != "first" && result.Content != "second" {
		t.Errorf("expected 'first' or 'second', got '%s'", result.Content)
	}
}

// TestParallelAgent_DefaultAggregatorConcatenate tests Concatenate aggregator
func TestParallelAgent_DefaultAggregatorConcatenate(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "response1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "response2"}

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2}, DefaultAggregators.Concatenate)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := parallel.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should contain both responses with separator
	if !strings.Contains(result.Content, "response1") || !strings.Contains(result.Content, "response2") {
		t.Errorf("expected concatenated responses, got '%s'", result.Content)
	}
	if !strings.Contains(result.Content, "---") {
		t.Errorf("expected separator in concatenated result, got '%s'", result.Content)
	}
}

// TestParallelAgent_DefaultAggregatorMajorityVote tests MajorityVote aggregator
func TestParallelAgent_DefaultAggregatorMajorityVote(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "A"}
	agent2 := &extendedMockAgent{name: "agent2", response: "A"}
	agent3 := &extendedMockAgent{name: "agent3", response: "B"}

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, DefaultAggregators.MajorityVote)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := parallel.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should return "A" (majority)
	if result.Content != "A" {
		t.Errorf("expected 'A' (majority), got '%s'", result.Content)
	}

	// Check vote metadata
	if result.Metadata["votes"] != 2 {
		t.Errorf("expected votes=2, got %v", result.Metadata["votes"])
	}
	if result.Metadata["total_agents"] != 3 {
		t.Errorf("expected total_agents=3, got %v", result.Metadata["total_agents"])
	}
}

// TestParallelAgent_CustomAggregator tests custom aggregator function
func TestParallelAgent_CustomAggregator(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "10"}
	agent2 := &extendedMockAgent{name: "agent2", response: "20"}
	agent3 := &extendedMockAgent{name: "agent3", response: "30"}

	// Custom aggregator that sums numeric responses
	sumAggregator := func(messages []*agenkit.Message) *agenkit.Message {
		sum := 0
		for _, msg := range messages {
			var num int
			if _, err := fmt.Sscanf(msg.Content, "%d", &num); err == nil {
				sum += num
			}
		}
		return agenkit.NewMessage("assistant", fmt.Sprintf("%d", sum))
	}

	parallel, err := NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, sumAggregator)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := parallel.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "60" {
		t.Errorf("expected '60', got '%s'", result.Content)
	}
}
