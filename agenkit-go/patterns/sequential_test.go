package patterns

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestSequentialAgent_Constructor tests valid construction
func TestSequentialAgent_Constructor(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "result1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "result2"}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if seq == nil {
		t.Fatal("expected non-nil SequentialAgent")
	}
	if seq.Name() != "SequentialAgent" {
		t.Errorf("expected name 'SequentialAgent', got '%s'", seq.Name())
	}
	if len(seq.agents) != 2 {
		t.Errorf("expected 2 agents, got %d", len(seq.agents))
	}
}

// TestSequentialAgent_ConstructorEmptyAgents tests error case with no agents
func TestSequentialAgent_ConstructorEmptyAgents(t *testing.T) {
	_, err := NewSequentialAgent([]agenkit.Agent{})
	if err == nil {
		t.Fatal("expected error for empty agents list")
	}
	if !strings.Contains(err.Error(), "at least one agent") {
		t.Errorf("expected 'at least one agent' error, got %v", err)
	}
}

// TestSequentialAgent_BasicProcess tests simple success case
func TestSequentialAgent_BasicProcess(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "step1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "step2"}
	agent3 := &extendedMockAgent{name: "agent3", response: "final"}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test input")
	result, err := seq.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "final" {
		t.Errorf("expected 'final', got '%s'", result.Content)
	}
}

// TestSequentialAgent_PipelineTransformation tests message passing through stages
func TestSequentialAgent_PipelineTransformation(t *testing.T) {
	// Each agent appends to the message
	agent1 := &extendedMockAgent{
		name: "agent1",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			return agenkit.NewMessage("assistant", msg.Content+" -> stage1"), nil
		},
	}
	agent2 := &extendedMockAgent{
		name: "agent2",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			return agenkit.NewMessage("assistant", msg.Content+" -> stage2"), nil
		},
	}
	agent3 := &extendedMockAgent{
		name: "agent3",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			return agenkit.NewMessage("assistant", msg.Content+" -> stage3"), nil
		},
	}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "input")
	result, err := seq.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	expected := "input -> stage1 -> stage2 -> stage3"
	if result.Content != expected {
		t.Errorf("expected '%s', got '%s'", expected, result.Content)
	}
}

// TestSequentialAgent_MetadataPreservation tests metadata handling across stages
func TestSequentialAgent_MetadataPreservation(t *testing.T) {
	agent1 := &extendedMockAgent{
		name: "agent1",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "stage1")
			resp.WithMetadata("stage1_key", "stage1_value")
			return resp, nil
		},
	}
	agent2 := &extendedMockAgent{
		name: "agent2",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "stage2")
			resp.WithMetadata("stage2_key", "stage2_value")
			return resp, nil
		},
	}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := seq.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check pipeline metadata
	if result.Metadata["pipeline_length"] != 2 {
		t.Errorf("expected pipeline_length=2, got %v", result.Metadata["pipeline_length"])
	}

	stages, ok := result.Metadata["pipeline_stages"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected pipeline_stages to be []map[string]interface{}")
	}
	if len(stages) != 2 {
		t.Errorf("expected 2 stages, got %d", len(stages))
	}
}

// TestSequentialAgent_ErrorHandling tests error propagation from agents
func TestSequentialAgent_ErrorHandling(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "success"}
	agent2 := &extendedMockAgent{name: "agent2", err: errors.New("agent2 failed")}
	agent3 := &extendedMockAgent{name: "agent3", response: "should not reach"}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := seq.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from failed agent")
	}
	if result != nil {
		t.Error("expected nil result on error")
	}
	if !strings.Contains(err.Error(), "agent2") {
		t.Errorf("expected error to mention agent2, got: %v", err)
	}
	if !strings.Contains(err.Error(), "agent2 failed") {
		t.Errorf("expected error to contain original error message, got: %v", err)
	}
}

// TestSequentialAgent_FirstAgentFailure tests failure at first stage
func TestSequentialAgent_FirstAgentFailure(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", err: errors.New("first agent error")}
	agent2 := &extendedMockAgent{name: "agent2", response: "should not execute"}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = seq.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from first agent")
	}
	if !strings.Contains(err.Error(), "agent 0") {
		t.Errorf("expected error to mention stage 0, got: %v", err)
	}
}

// TestSequentialAgent_ContextCancellation tests context cancellation handling
func TestSequentialAgent_ContextCancellation(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "stage1"}
	agent2 := &extendedMockAgent{
		name: "agent2",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			// Simulate work and check cancellation
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			default:
				return agenkit.NewMessage("assistant", "stage2"), nil
			}
		},
	}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	msg := agenkit.NewMessage("user", "test")
	_, err = seq.Process(ctx, msg)

	if err == nil {
		t.Fatal("expected error from cancelled context")
	}
	if !strings.Contains(err.Error(), "cancelled") {
		t.Errorf("expected cancellation error, got: %v", err)
	}
}

// TestSequentialAgent_NilMessage tests nil message handling
func TestSequentialAgent_NilMessage(t *testing.T) {
	agent := &extendedMockAgent{name: "agent1", response: "test"}
	seq, err := NewSequentialAgent([]agenkit.Agent{agent})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = seq.Process(context.Background(), nil)
	if err == nil {
		t.Fatal("expected error for nil message")
	}
	if !strings.Contains(err.Error(), "cannot be nil") {
		t.Errorf("expected 'cannot be nil' error, got: %v", err)
	}
}

// TestSequentialAgent_Capabilities tests combined capabilities
func TestSequentialAgent_Capabilities(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", capabilities: []string{"cap1", "cap2"}}
	agent2 := &extendedMockAgent{name: "agent2", capabilities: []string{"cap2", "cap3"}}
	agent3 := &extendedMockAgent{name: "agent3", capabilities: []string{"cap4"}}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	caps := seq.Capabilities()

	// Should have unique capabilities from all agents plus sequential/pipeline
	expectedCaps := map[string]bool{
		"cap1":       true,
		"cap2":       true,
		"cap3":       true,
		"cap4":       true,
		"sequential": true,
		"pipeline":   true,
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d: %v", len(expectedCaps), len(caps), caps)
	}

	for _, cap := range caps {
		if !expectedCaps[cap] {
			t.Errorf("unexpected capability: %s", cap)
		}
	}
}

// TestSequentialAgent_SingleAgent tests pipeline with single agent
func TestSequentialAgent_SingleAgent(t *testing.T) {
	agent := &extendedMockAgent{name: "solo", response: "result"}
	seq, err := NewSequentialAgent([]agenkit.Agent{agent})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "input")
	result, err := seq.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "result" {
		t.Errorf("expected 'result', got '%s'", result.Content)
	}

	// Check metadata
	if result.Metadata["pipeline_length"] != 1 {
		t.Errorf("expected pipeline_length=1, got %v", result.Metadata["pipeline_length"])
	}
}

// TestSequentialAgent_StageMetadata tests detailed stage metadata tracking
func TestSequentialAgent_StageMetadata(t *testing.T) {
	agent1 := &extendedMockAgent{name: "extractor", response: "extracted"}
	agent2 := &extendedMockAgent{name: "transformer", response: "transformed"}
	agent3 := &extendedMockAgent{name: "validator", response: "validated"}

	seq, err := NewSequentialAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "input")
	result, err := seq.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	stages, ok := result.Metadata["pipeline_stages"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected pipeline_stages metadata")
	}

	expectedAgents := []string{"extractor", "transformer", "validator"}
	for i, stage := range stages {
		agentName, ok := stage["agent"].(string)
		if !ok {
			t.Errorf("stage %d missing agent name", i)
			continue
		}
		if agentName != expectedAgents[i] {
			t.Errorf("stage %d: expected agent '%s', got '%s'", i, expectedAgents[i], agentName)
		}

		stageNum, ok := stage["stage"].(int)
		if !ok || stageNum != i {
			t.Errorf("stage %d: incorrect stage number %v", i, stage["stage"])
		}
	}
}
