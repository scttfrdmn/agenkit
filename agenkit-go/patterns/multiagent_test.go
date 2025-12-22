package patterns

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockMultiAgent is a mock agent for multiagent testing.
type mockMultiAgent struct {
	name         string
	response     string
	err          error
	capabilities []string
}

func (m *mockMultiAgent) Name() string {
	return m.name
}

func (m *mockMultiAgent) Capabilities() []string {
	if m.capabilities != nil {
		return m.capabilities
	}
	return []string{"test"}
}

func (m *mockMultiAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *mockMultiAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.err != nil {
		return nil, m.err
	}
	return &agenkit.Message{
		Role:    "assistant",
		Content: m.response,
	}, nil
}

// ============================================================================
// MultiAgentOrchestrator Tests
// ============================================================================

func TestMultiAgentOrchestrator_Creation(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)

	if orchestrator.Name() != "MultiAgentOrchestrator" {
		t.Errorf("expected name 'MultiAgentOrchestrator', got %s", orchestrator.Name())
	}

	if orchestrator.Strategy() != StrategySequential {
		t.Errorf("expected strategy sequential, got %s", orchestrator.Strategy())
	}

	if len(orchestrator.ListAgents()) != 0 {
		t.Error("expected no agents initially")
	}
}

func TestMultiAgentOrchestrator_DefaultStrategy(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator("")

	if orchestrator.Strategy() != StrategySequential {
		t.Errorf("expected default strategy sequential, got %s", orchestrator.Strategy())
	}
}

func TestMultiAgentOrchestrator_RegisterAgent(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)
	agent1 := &mockMultiAgent{name: "agent1", response: "Response 1"}
	agent2 := &mockMultiAgent{name: "agent2", response: "Response 2"}

	orchestrator.RegisterAgent("agent1", agent1)
	orchestrator.RegisterAgent("agent2", agent2)

	agents := orchestrator.ListAgents()
	if len(agents) != 2 {
		t.Errorf("expected 2 agents, got %d", len(agents))
	}

	// Check agents are registered
	found1, found2 := false, false
	for _, name := range agents {
		if name == "agent1" {
			found1 = true
		}
		if name == "agent2" {
			found2 = true
		}
	}

	if !found1 || !found2 {
		t.Error("expected both agents to be registered")
	}
}

func TestMultiAgentOrchestrator_UnregisterAgent(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)
	agent1 := &mockMultiAgent{name: "agent1", response: "Response 1"}
	agent2 := &mockMultiAgent{name: "agent2", response: "Response 2"}

	orchestrator.RegisterAgent("agent1", agent1)
	orchestrator.RegisterAgent("agent2", agent2)

	orchestrator.UnregisterAgent("agent1")

	agents := orchestrator.ListAgents()
	if len(agents) != 1 {
		t.Errorf("expected 1 agent after unregister, got %d", len(agents))
	}

	if agents[0] != "agent2" {
		t.Errorf("expected agent2 to remain, got %s", agents[0])
	}
}

func TestMultiAgentOrchestrator_Capabilities(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)
	agent1 := &mockMultiAgent{name: "agent1", capabilities: []string{"search", "summarize"}}
	agent2 := &mockMultiAgent{name: "agent2", capabilities: []string{"translate", "search"}}

	orchestrator.RegisterAgent("agent1", agent1)
	orchestrator.RegisterAgent("agent2", agent2)

	caps := orchestrator.Capabilities()

	// Should have 3 unique capabilities: search, summarize, translate
	if len(caps) != 3 {
		t.Errorf("expected 3 unique capabilities, got %d: %v", len(caps), caps)
	}

	// Check all capabilities are present
	capsMap := make(map[string]bool)
	for _, cap := range caps {
		capsMap[cap] = true
	}

	if !capsMap["search"] || !capsMap["summarize"] || !capsMap["translate"] {
		t.Errorf("missing expected capabilities, got: %v", caps)
	}
}

func TestMultiAgentOrchestrator_ProcessSuccess(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)
	agent1 := &mockMultiAgent{name: "agent1", response: "Response from agent1"}
	agent2 := &mockMultiAgent{name: "agent2", response: "Response from agent2"}

	orchestrator.RegisterAgent("agent1", agent1)
	orchestrator.RegisterAgent("agent2", agent2)

	result, err := orchestrator.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test message",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check result contains both agent responses
	if !strings.Contains(result.Content, "agent1: Response from agent1") {
		t.Error("expected result to contain agent1 response")
	}

	if !strings.Contains(result.Content, "agent2: Response from agent2") {
		t.Error("expected result to contain agent2 response")
	}

	// Check tasks were recorded
	tasks := orchestrator.GetTasks()
	if len(tasks) != 2 {
		t.Errorf("expected 2 tasks, got %d", len(tasks))
	}

	// Check task statuses
	for _, task := range tasks {
		if task.Status != TaskStatusCompleted {
			t.Errorf("expected task status completed, got %s", task.Status)
		}
	}
}

func TestMultiAgentOrchestrator_ProcessWithFailure(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)
	agent1 := &mockMultiAgent{name: "agent1", response: "Success"}
	agent2 := &mockMultiAgent{name: "agent2", err: errors.New("agent2 failed")}

	orchestrator.RegisterAgent("agent1", agent1)
	orchestrator.RegisterAgent("agent2", agent2)

	result, err := orchestrator.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Result should show failure
	if !strings.Contains(result.Content, "agent2: Failed - agent2 failed") {
		t.Error("expected result to show agent2 failure")
	}

	// Check tasks
	tasks := orchestrator.GetTasks()
	if len(tasks) != 2 {
		t.Errorf("expected 2 tasks, got %d", len(tasks))
	}

	// agent1 should be completed
	if tasks[0].Status != TaskStatusCompleted && tasks[1].Status != TaskStatusCompleted {
		t.Error("expected at least one task to be completed")
	}

	// agent2 should be failed
	foundFailed := false
	for _, task := range tasks {
		if task.Status == TaskStatusFailed {
			foundFailed = true
			if task.Error != "agent2 failed" {
				t.Errorf("expected error message 'agent2 failed', got %s", task.Error)
			}
		}
	}

	if !foundFailed {
		t.Error("expected one task to have failed status")
	}
}

func TestMultiAgentOrchestrator_GetTasks(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)
	agent := &mockMultiAgent{name: "agent1", response: "Response"}

	orchestrator.RegisterAgent("agent1", agent)

	_, _ = orchestrator.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	tasks := orchestrator.GetTasks()
	if len(tasks) != 1 {
		t.Errorf("expected 1 task, got %d", len(tasks))
	}

	// Verify it's a copy (modifying returned tasks shouldn't affect internal state)
	tasks[0].Status = TaskStatusFailed

	tasks2 := orchestrator.GetTasks()
	if tasks2[0].Status == TaskStatusFailed {
		t.Error("GetTasks should return a copy, not original slice")
	}
}

func TestMultiAgentOrchestrator_NoAgents(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)

	result, err := orchestrator.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "" {
		t.Errorf("expected empty result with no agents, got: %s", result.Content)
	}
}

// ============================================================================
// ConsensusAgent Tests
// ============================================================================

func TestConsensusAgent_Creation(t *testing.T) {
	consensus := NewConsensusAgent(VotingMajority)

	if consensus.Name() != "ConsensusAgent" {
		t.Errorf("expected name 'ConsensusAgent', got %s", consensus.Name())
	}

	if consensus.VotingStrategy() != VotingMajority {
		t.Errorf("expected voting strategy majority, got %s", consensus.VotingStrategy())
	}

	if len(consensus.Agents()) != 0 {
		t.Error("expected no agents initially")
	}
}

func TestConsensusAgent_DefaultVotingStrategy(t *testing.T) {
	consensus := NewConsensusAgent("")

	if consensus.VotingStrategy() != VotingMajority {
		t.Errorf("expected default voting strategy majority, got %s", consensus.VotingStrategy())
	}
}

func TestConsensusAgent_AddAgent(t *testing.T) {
	consensus := NewConsensusAgent(VotingMajority)
	agent1 := &mockMultiAgent{name: "agent1", response: "Response 1"}
	agent2 := &mockMultiAgent{name: "agent2", response: "Response 2"}

	consensus.AddAgent(agent1)
	consensus.AddAgent(agent2)

	agents := consensus.Agents()
	if len(agents) != 2 {
		t.Errorf("expected 2 agents, got %d", len(agents))
	}
}

func TestConsensusAgent_Capabilities(t *testing.T) {
	consensus := NewConsensusAgent(VotingMajority)
	agent1 := &mockMultiAgent{name: "agent1", capabilities: []string{"search", "summarize"}}
	agent2 := &mockMultiAgent{name: "agent2", capabilities: []string{"translate", "search"}}

	consensus.AddAgent(agent1)
	consensus.AddAgent(agent2)

	caps := consensus.Capabilities()

	// Should have 3 unique capabilities
	if len(caps) != 3 {
		t.Errorf("expected 3 unique capabilities, got %d: %v", len(caps), caps)
	}
}

func TestConsensusAgent_AgentsReturnsACopy(t *testing.T) {
	consensus := NewConsensusAgent(VotingMajority)
	agent := &mockMultiAgent{name: "agent1", response: "Response"}

	consensus.AddAgent(agent)

	agents := consensus.Agents()
	agents[0] = nil // Try to modify

	// Original should not be affected
	agents2 := consensus.Agents()
	if agents2[0] == nil {
		t.Error("Agents() should return a copy, not original slice")
	}
}

func TestConsensusAgent_ProcessSuccess(t *testing.T) {
	consensus := NewConsensusAgent(VotingMajority)
	agent1 := &mockMultiAgent{name: "agent1", response: "Answer A"}
	agent2 := &mockMultiAgent{name: "agent2", response: "Answer B"}
	agent3 := &mockMultiAgent{name: "agent3", response: "Answer C"}

	consensus.AddAgent(agent1)
	consensus.AddAgent(agent2)
	consensus.AddAgent(agent3)

	result, err := consensus.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "What is the answer?",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check result format
	if !strings.Contains(result.Content, "Consensus from 3 agents:") {
		t.Error("expected consensus header")
	}

	// Check all agent responses are included
	if !strings.Contains(result.Content, "Agent 1: Answer A") {
		t.Error("expected Agent 1 response")
	}

	if !strings.Contains(result.Content, "Agent 2: Answer B") {
		t.Error("expected Agent 2 response")
	}

	if !strings.Contains(result.Content, "Agent 3: Answer C") {
		t.Error("expected Agent 3 response")
	}
}

func TestConsensusAgent_ProcessWithFailure(t *testing.T) {
	consensus := NewConsensusAgent(VotingMajority)
	agent1 := &mockMultiAgent{name: "agent1", response: "Answer A"}
	agent2 := &mockMultiAgent{name: "agent2", err: errors.New("agent2 failed")}

	consensus.AddAgent(agent1)
	consensus.AddAgent(agent2)

	_, err := consensus.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err == nil {
		t.Fatal("expected error when agent fails")
	}

	if !strings.Contains(err.Error(), "agent2 failed") {
		t.Errorf("expected error to mention agent2 failure, got: %v", err)
	}
}

func TestConsensusAgent_NoAgents(t *testing.T) {
	consensus := NewConsensusAgent(VotingMajority)

	result, err := consensus.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should return consensus from 0 agents
	if !strings.Contains(result.Content, "Consensus from 0 agents:") {
		t.Errorf("expected consensus from 0 agents, got: %s", result.Content)
	}
}

func TestConsensusAgent_SingleAgent(t *testing.T) {
	consensus := NewConsensusAgent(VotingMajority)
	agent := &mockMultiAgent{name: "agent1", response: "Single answer"}

	consensus.AddAgent(agent)

	result, err := consensus.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !strings.Contains(result.Content, "Consensus from 1 agents:") {
		t.Error("expected consensus from 1 agent")
	}

	if !strings.Contains(result.Content, "Agent 1: Single answer") {
		t.Error("expected agent response")
	}
}

// ============================================================================
// Integration Tests
// ============================================================================

func TestMultiAgentOrchestrator_WithDifferentStrategies(t *testing.T) {
	strategies := []OrchestrationStrategy{
		StrategySequential,
		StrategyParallel,
		StrategyDelegate,
	}

	for _, strategy := range strategies {
		t.Run(string(strategy), func(t *testing.T) {
			orchestrator := NewMultiAgentOrchestrator(strategy)
			agent := &mockMultiAgent{name: "agent1", response: "Response"}

			orchestrator.RegisterAgent("agent1", agent)

			result, err := orchestrator.Process(context.Background(), &agenkit.Message{
				Role:    "user",
				Content: "Test",
			})

			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if result == nil {
				t.Fatal("expected non-nil result")
			}
		})
	}
}

func TestConsensusAgent_WithDifferentVotingStrategies(t *testing.T) {
	strategies := []VotingStrategy{
		VotingMajority,
		VotingUnanimous,
		VotingWeighted,
	}

	for _, strategy := range strategies {
		t.Run(string(strategy), func(t *testing.T) {
			consensus := NewConsensusAgent(strategy)
			agent := &mockMultiAgent{name: "agent1", response: "Response"}

			consensus.AddAgent(agent)

			result, err := consensus.Process(context.Background(), &agenkit.Message{
				Role:    "user",
				Content: "Test",
			})

			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if result == nil {
				t.Fatal("expected non-nil result")
			}
		})
	}
}

func TestMultiAgentOrchestrator_ContextCancellation(t *testing.T) {
	orchestrator := NewMultiAgentOrchestrator(StrategySequential)

	// Create an agent that will check context
	agent := &mockMultiAgent{name: "agent1", response: "Response"}
	orchestrator.RegisterAgent("agent1", agent)

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	// Process should still complete (context is passed but not currently enforced)
	result, err := orchestrator.Process(ctx, &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	// Current implementation doesn't enforce context cancellation
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result == nil {
		t.Fatal("expected non-nil result")
	}
}
