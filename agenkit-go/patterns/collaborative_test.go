package patterns

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestCollaborativeAgent_Constructor tests valid construction
func TestCollaborativeAgent_Constructor(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "r1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "r2"}

	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{agent1, agent2},
		MaxRounds: 3,
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if collab == nil {
		t.Fatal("expected non-nil CollaborativeAgent")
	}
	if collab.Name() != "CollaborativeAgent" {
		t.Errorf("expected name 'CollaborativeAgent', got '%s'", collab.Name())
	}
}

// TestCollaborativeAgent_ConstructorNilConfig tests error case with nil config
func TestCollaborativeAgent_ConstructorNilConfig(t *testing.T) {
	_, err := NewCollaborativeAgent(nil)
	if err == nil {
		t.Fatal("expected error for nil config")
	}
	if !strings.Contains(err.Error(), "config") {
		t.Errorf("expected 'config' error, got %v", err)
	}
}

// TestCollaborativeAgent_ConstructorSingleAgent tests error case with only one agent
func TestCollaborativeAgent_ConstructorSingleAgent(t *testing.T) {
	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{&extendedMockAgent{name: "agent1"}},
		MergeFunc: DefaultMergeFunc.First,
	}

	_, err := NewCollaborativeAgent(config)
	if err == nil {
		t.Fatal("expected error for single agent")
	}
	if !strings.Contains(err.Error(), "at least two agents") {
		t.Errorf("expected 'at least two agents' error, got %v", err)
	}
}

// TestCollaborativeAgent_ConstructorNilMergeFunc tests error case with nil merge function
func TestCollaborativeAgent_ConstructorNilMergeFunc(t *testing.T) {
	config := &CollaborativeConfig{
		Agents: []agenkit.Agent{
			&extendedMockAgent{name: "agent1"},
			&extendedMockAgent{name: "agent2"},
		},
		MergeFunc: nil,
	}

	_, err := NewCollaborativeAgent(config)
	if err == nil {
		t.Fatal("expected error for nil merge function")
	}
	if !strings.Contains(err.Error(), "merge function") {
		t.Errorf("expected 'merge function' error, got %v", err)
	}
}

// TestCollaborativeAgent_ConstructorDefaultMaxRounds tests default max rounds
func TestCollaborativeAgent_ConstructorDefaultMaxRounds(t *testing.T) {
	config := &CollaborativeConfig{
		Agents: []agenkit.Agent{
			&extendedMockAgent{name: "agent1"},
			&extendedMockAgent{name: "agent2"},
		},
		MaxRounds: 0, // Should default to 3
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if collab.maxRounds != 3 {
		t.Errorf("expected default maxRounds=3, got %d", collab.maxRounds)
	}
}

// TestCollaborativeAgent_BasicProcess tests simple success case
func TestCollaborativeAgent_BasicProcess(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "response1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "response2"}

	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{agent1, agent2},
		MaxRounds: 2,
		MergeFunc: DefaultMergeFunc.Concatenate,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test input")
	result, err := collab.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Result should contain concatenated responses
	if !strings.Contains(result.Content, "response1") || !strings.Contains(result.Content, "response2") {
		t.Errorf("expected concatenated responses, got '%s'", result.Content)
	}
}

// TestCollaborativeAgent_RoundIterations tests multiple rounds
func TestCollaborativeAgent_RoundIterations(t *testing.T) {
	callCount := 0
	agent1 := &extendedMockAgent{
		name: "agent1",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			callCount++
			return agenkit.NewMessage("assistant", fmt.Sprintf("agent1_round_%d", callCount)), nil
		},
	}
	agent2 := &extendedMockAgent{
		name: "agent2",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			callCount++
			return agenkit.NewMessage("assistant", fmt.Sprintf("agent2_round_%d", callCount)), nil
		},
	}

	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{agent1, agent2},
		MaxRounds: 3,
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := collab.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should have called each agent 3 times (3 rounds)
	expectedCalls := 3 * 2 // 3 rounds * 2 agents
	if callCount != expectedCalls {
		t.Errorf("expected %d calls, got %d", expectedCalls, callCount)
	}

	// Check metadata
	if result.Metadata["collaboration_rounds"] != 3 {
		t.Errorf("expected 3 rounds, got %v", result.Metadata["collaboration_rounds"])
	}
	if result.Metadata["stop_reason"] != "max_rounds" {
		t.Errorf("expected stop_reason='max_rounds', got %v", result.Metadata["stop_reason"])
	}
}

// TestCollaborativeAgent_EarlyConsensus tests consensus detection
func TestCollaborativeAgent_EarlyConsensus(t *testing.T) {
	roundCount := 0
	agent1 := &extendedMockAgent{
		name: "agent1",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			roundCount++
			return agenkit.NewMessage("assistant", "agreed"), nil
		},
	}
	agent2 := &extendedMockAgent{
		name: "agent2",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			return agenkit.NewMessage("assistant", "agreed"), nil
		},
	}

	config := &CollaborativeConfig{
		Agents:        []agenkit.Agent{agent1, agent2},
		MaxRounds:     5,
		ConsensusFunc: DefaultConsensusFunc.ExactMatch,
		MergeFunc:     DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := collab.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should stop early due to consensus
	actualRounds := result.Metadata["collaboration_rounds"].(int)
	if actualRounds >= 5 {
		t.Errorf("expected early termination (< 5 rounds), got %d rounds", actualRounds)
	}

	if result.Metadata["stop_reason"] != "consensus" {
		t.Errorf("expected stop_reason='consensus', got %v", result.Metadata["stop_reason"])
	}
}

// TestCollaborativeAgent_Metadata tests metadata handling
func TestCollaborativeAgent_Metadata(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "r1"}
	agent2 := &extendedMockAgent{name: "agent2", response: "r2"}
	agent3 := &extendedMockAgent{name: "agent3", response: "r3"}

	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{agent1, agent2, agent3},
		MaxRounds: 2,
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := collab.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check metadata
	if result.Metadata["collaboration_agents"] != 3 {
		t.Errorf("expected collaboration_agents=3, got %v", result.Metadata["collaboration_agents"])
	}
	if result.Metadata["collaboration_rounds"] != 2 {
		t.Errorf("expected collaboration_rounds=2, got %v", result.Metadata["collaboration_rounds"])
	}

	rounds, ok := result.Metadata["rounds"].([]map[string]interface{})
	if !ok {
		t.Fatal("expected rounds metadata")
	}
	if len(rounds) != 2 {
		t.Errorf("expected 2 round records, got %d", len(rounds))
	}
}

// TestCollaborativeAgent_AgentError tests error from agent
func TestCollaborativeAgent_AgentError(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "r1"}
	agent2 := &extendedMockAgent{name: "agent2", err: errors.New("agent2 failed")}

	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{agent1, agent2},
		MaxRounds: 2,
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = collab.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from failing agent")
	}
	if !strings.Contains(err.Error(), "agent2") || !strings.Contains(err.Error(), "failed") {
		t.Errorf("expected agent2 error, got: %v", err)
	}
}

// TestCollaborativeAgent_ContextCancellation tests context cancellation
func TestCollaborativeAgent_ContextCancellation(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", response: "r1"}
	agent2 := &extendedMockAgent{
		name: "agent2",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			default:
				return agenkit.NewMessage("assistant", "r2"), nil
			}
		},
	}

	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{agent1, agent2},
		MaxRounds: 3,
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	msg := agenkit.NewMessage("user", "test")
	_, err = collab.Process(ctx, msg)

	if err == nil {
		t.Fatal("expected error from cancelled context")
	}
	if !strings.Contains(err.Error(), "cancelled") {
		t.Errorf("expected cancellation error, got: %v", err)
	}
}

// TestCollaborativeAgent_NilMessage tests nil message handling
func TestCollaborativeAgent_NilMessage(t *testing.T) {
	config := &CollaborativeConfig{
		Agents: []agenkit.Agent{
			&extendedMockAgent{name: "agent1"},
			&extendedMockAgent{name: "agent2"},
		},
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = collab.Process(context.Background(), nil)
	if err == nil {
		t.Fatal("expected error for nil message")
	}
	if !strings.Contains(err.Error(), "cannot be nil") {
		t.Errorf("expected 'cannot be nil' error, got: %v", err)
	}
}

// TestCollaborativeAgent_Capabilities tests combined capabilities
func TestCollaborativeAgent_Capabilities(t *testing.T) {
	agent1 := &extendedMockAgent{name: "agent1", capabilities: []string{"cap1", "cap2"}}
	agent2 := &extendedMockAgent{name: "agent2", capabilities: []string{"cap2", "cap3"}}

	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{agent1, agent2},
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	caps := collab.Capabilities()

	expectedCaps := map[string]bool{
		"cap1":          true,
		"cap2":          true,
		"cap3":          true,
		"collaborative": true,
		"iterative":     true,
		"consensus":     true,
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d: %v", len(expectedCaps), len(caps), caps)
	}
}

// TestCollaborativeAgent_ConsensusExactMatch tests exact match consensus
func TestCollaborativeAgent_ConsensusExactMatch(t *testing.T) {
	messages := []*agenkit.Message{
		agenkit.NewMessage("assistant", "same"),
		agenkit.NewMessage("assistant", "same"),
		agenkit.NewMessage("assistant", "same"),
	}

	consensus := DefaultConsensusFunc.ExactMatch(messages)
	if !consensus {
		t.Error("expected consensus for exact matches")
	}

	// Test with different messages
	differentMessages := []*agenkit.Message{
		agenkit.NewMessage("assistant", "A"),
		agenkit.NewMessage("assistant", "B"),
	}

	consensus = DefaultConsensusFunc.ExactMatch(differentMessages)
	if consensus {
		t.Error("expected no consensus for different messages")
	}
}

// TestCollaborativeAgent_ConsensusMajorityAgreement tests majority agreement
func TestCollaborativeAgent_ConsensusMajorityAgreement(t *testing.T) {
	// Majority agrees
	messages := []*agenkit.Message{
		agenkit.NewMessage("assistant", "A"),
		agenkit.NewMessage("assistant", "A"),
		agenkit.NewMessage("assistant", "B"),
	}

	consensus := DefaultConsensusFunc.MajorityAgreement(messages)
	if !consensus {
		t.Error("expected consensus with majority agreement")
	}

	// No majority
	noMajority := []*agenkit.Message{
		agenkit.NewMessage("assistant", "A"),
		agenkit.NewMessage("assistant", "B"),
		agenkit.NewMessage("assistant", "C"),
	}

	consensus = DefaultConsensusFunc.MajorityAgreement(noMajority)
	if consensus {
		t.Error("expected no consensus without majority")
	}
}

// TestCollaborativeAgent_MergeFuncVote tests vote merge function
func TestCollaborativeAgent_MergeFuncVote(t *testing.T) {
	messages := []*agenkit.Message{
		agenkit.NewMessage("assistant", "A"),
		agenkit.NewMessage("assistant", "A"),
		agenkit.NewMessage("assistant", "B"),
	}

	result := DefaultMergeFunc.Vote(messages)
	if result.Content != "A" {
		t.Errorf("expected 'A' (most votes), got '%s'", result.Content)
	}
	if result.Metadata["votes"] != 2 {
		t.Errorf("expected votes=2, got %v", result.Metadata["votes"])
	}
}

// TestCollaborativeAgent_MergeFuncFirst tests first merge function
func TestCollaborativeAgent_MergeFuncFirst(t *testing.T) {
	messages := []*agenkit.Message{
		agenkit.NewMessage("assistant", "first"),
		agenkit.NewMessage("assistant", "second"),
	}

	result := DefaultMergeFunc.First(messages)
	if result.Content != "first" {
		t.Errorf("expected 'first', got '%s'", result.Content)
	}
}

// TestCollaborativeAgent_MergeFuncLast tests last merge function
func TestCollaborativeAgent_MergeFuncLast(t *testing.T) {
	messages := []*agenkit.Message{
		agenkit.NewMessage("assistant", "first"),
		agenkit.NewMessage("assistant", "last"),
	}

	result := DefaultMergeFunc.Last(messages)
	if result.Content != "last" {
		t.Errorf("expected 'last', got '%s'", result.Content)
	}
}

// TestCollaborativeAgent_ContextInMessages tests that context is passed through rounds
func TestCollaborativeAgent_ContextInMessages(t *testing.T) {
	var receivedMessages []string

	agent := &extendedMockAgent{
		name: "tracker",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			receivedMessages = append(receivedMessages, msg.Content)
			return agenkit.NewMessage("assistant", "response"), nil
		},
	}

	config := &CollaborativeConfig{
		Agents:    []agenkit.Agent{agent, agent}, // Same agent twice to see both calls
		MaxRounds: 2,
		MergeFunc: DefaultMergeFunc.First,
	}

	collab, err := NewCollaborativeAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "initial")
	_, err = collab.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Round 0: Both agents should see "=== Collaboration Round 0 ==="
	// Round 1: Both agents should see previous responses
	if len(receivedMessages) != 4 { // 2 agents * 2 rounds
		t.Errorf("expected 4 messages, got %d", len(receivedMessages))
	}

	// First round messages should contain "Round 0"
	if !strings.Contains(receivedMessages[0], "Round 0") {
		t.Errorf("expected first message to contain 'Round 0', got: %s", receivedMessages[0][:50])
	}

	// Second round messages should contain previous responses
	if !strings.Contains(receivedMessages[2], "Previous Responses") {
		t.Errorf("expected round 1 message to contain 'Previous Responses', got: %s", receivedMessages[2][:100])
	}
}
