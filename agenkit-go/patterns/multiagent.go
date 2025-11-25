// Package patterns provides the Multi-Agent Collaboration pattern.
//
// Enables multiple agents to work together on complex tasks through:
//   - Coordination: Agents working on different parts simultaneously
//   - Delegation: Agents delegating subtasks to specialists
//   - Consensus: Agents reaching agreement through discussion
//
// This pattern is useful for:
//   - Complex tasks requiring diverse expertise
//   - Parallelizable workflows
//   - Problems benefiting from multiple perspectives
//
// Example:
//
//	orchestrator := patterns.NewMultiAgentOrchestrator("sequential")
//	orchestrator.RegisterAgent("researcher", researchAgent)
//	orchestrator.RegisterAgent("writer", writingAgent)
//
//	result, _ := orchestrator.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "Write a research report",
//	})
package patterns

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TaskStatus represents task execution status.
type TaskStatus string

const (
	// TaskStatusPending indicates task not yet started
	TaskStatusPending TaskStatus = "pending"
	// TaskStatusInProgress indicates task currently executing
	TaskStatusInProgress TaskStatus = "in_progress"
	// TaskStatusCompleted indicates task completed successfully
	TaskStatusCompleted TaskStatus = "completed"
	// TaskStatusFailed indicates task failed with error
	TaskStatusFailed TaskStatus = "failed"
)

// AgentTask represents a task assigned to an agent.
type AgentTask struct {
	// AgentName is the name of the agent assigned to this task
	AgentName string
	// Description is the task description
	Description string
	// Result is the task result (if completed)
	Result interface{}
	// Status is the current task status
	Status TaskStatus
	// Error is the error message (if failed)
	Error string
}

// OrchestrationStrategy defines how multiple agents are coordinated.
type OrchestrationStrategy string

const (
	// StrategySequential executes agents one after another
	StrategySequential OrchestrationStrategy = "sequential"
	// StrategyParallel executes agents simultaneously
	StrategyParallel OrchestrationStrategy = "parallel"
	// StrategyDelegate has main agent delegate to specialists
	StrategyDelegate OrchestrationStrategy = "delegate"
)

// VotingStrategy defines how consensus is reached.
type VotingStrategy string

const (
	// VotingMajority uses majority vote
	VotingMajority VotingStrategy = "majority"
	// VotingUnanimous requires unanimous agreement
	VotingUnanimous VotingStrategy = "unanimous"
	// VotingWeighted uses weighted voting
	VotingWeighted VotingStrategy = "weighted"
)

// MultiAgentOrchestrator coordinates multiple agents working together.
//
// The MultiAgentOrchestrator coordinates multiple agents to work on tasks,
// supporting different orchestration strategies:
//
//   - **sequential**: Agents execute one after another
//   - **parallel**: Agents execute simultaneously
//   - **delegate**: Main agent delegates to specialists
//
// Use this when:
//   - Tasks require diverse expertise
//   - Work can be parallelized
//   - You need to compose multiple agents
//
// Example:
//
//	orchestrator := NewMultiAgentOrchestrator("sequential")
//	orchestrator.RegisterAgent("researcher", researchAgent)
//	orchestrator.RegisterAgent("writer", writingAgent)
//	orchestrator.RegisterAgent("editor", editorAgent)
//
//	result, _ := orchestrator.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "Create a comprehensive report on AI",
//	})
//	// Each agent processes the message in sequence
type MultiAgentOrchestrator struct {
	name     string
	agents   map[string]agenkit.Agent
	strategy OrchestrationStrategy
	tasks    []AgentTask
}

// NewMultiAgentOrchestrator creates a new multi-agent orchestrator.
func NewMultiAgentOrchestrator(strategy OrchestrationStrategy) *MultiAgentOrchestrator {
	if strategy == "" {
		strategy = StrategySequential
	}

	return &MultiAgentOrchestrator{
		name:     "MultiAgentOrchestrator",
		agents:   make(map[string]agenkit.Agent),
		strategy: strategy,
		tasks:    make([]AgentTask, 0),
	}
}

// Name returns the orchestrator name.
func (m *MultiAgentOrchestrator) Name() string {
	return m.name
}

// Capabilities returns combined capabilities of all agents.
func (m *MultiAgentOrchestrator) Capabilities() []string {
	// Return all unique capabilities from registered agents
	capsMap := make(map[string]struct{})
	for _, agent := range m.agents {
		for _, cap := range agent.Capabilities() {
			capsMap[cap] = struct{}{}
		}
	}

	caps := make([]string, 0, len(capsMap))
	for cap := range capsMap {
		caps = append(caps, cap)
	}
	return caps
}

// Strategy returns the orchestration strategy.
func (m *MultiAgentOrchestrator) Strategy() OrchestrationStrategy {
	return m.strategy
}

// RegisterAgent registers an agent that can be used.
func (m *MultiAgentOrchestrator) RegisterAgent(name string, agent agenkit.Agent) {
	m.agents[name] = agent
}

// UnregisterAgent removes a registered agent.
func (m *MultiAgentOrchestrator) UnregisterAgent(name string) {
	delete(m.agents, name)
}

// ListAgents returns list of registered agent names.
func (m *MultiAgentOrchestrator) ListAgents() []string {
	names := make([]string, 0, len(m.agents))
	for name := range m.agents {
		names = append(names, name)
	}
	return names
}

// Process processes message by coordinating multiple agents.
//
// Currently implements sequential strategy where all agents process
// the message one after another. Results are combined into a single
// response.
func (m *MultiAgentOrchestrator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	results := make([]string, 0, len(m.agents))

	for agentName, agent := range m.agents {
		task := AgentTask{
			AgentName:   agentName,
			Description: message.Content,
			Status:      TaskStatusInProgress,
		}
		m.tasks = append(m.tasks, task)
		taskIdx := len(m.tasks) - 1

		response, err := agent.Process(ctx, message)
		if err != nil {
			m.tasks[taskIdx].Error = err.Error()
			m.tasks[taskIdx].Status = TaskStatusFailed
			results = append(results, fmt.Sprintf("%s: Failed - %s", agentName, err.Error()))
		} else {
			m.tasks[taskIdx].Result = response.Content
			m.tasks[taskIdx].Status = TaskStatusCompleted
			results = append(results, fmt.Sprintf("%s: %s", agentName, response.Content))
		}
	}

	combinedResult := strings.Join(results, "\n\n")
	return &agenkit.Message{
		Role:    "assistant",
		Content: combinedResult,
	}, nil
}

// GetTasks returns all tasks that have been executed.
func (m *MultiAgentOrchestrator) GetTasks() []AgentTask {
	// Return a copy
	tasksCopy := make([]AgentTask, len(m.tasks))
	copy(tasksCopy, m.tasks)
	return tasksCopy
}

// ConsensusAgent reaches consensus among multiple agents.
//
// The ConsensusAgent collects responses from multiple agents and combines
// them into a single consensus response. This is useful for:
//
//   - Getting multiple perspectives on a problem
//   - Validating decisions across multiple models
//   - Ensemble approaches to improve reliability
//
// Example:
//
//	consensus := NewConsensusAgent(VotingMajority)
//	consensus.AddAgent(conservativeAgent)
//	consensus.AddAgent(creativeAgent)
//	consensus.AddAgent(analyticalAgent)
//
//	result, _ := consensus.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "What's the best approach?",
//	})
//	// Result combines perspectives from all three agents
type ConsensusAgent struct {
	name           string
	agents         []agenkit.Agent
	votingStrategy VotingStrategy
}

// NewConsensusAgent creates a new consensus agent.
func NewConsensusAgent(votingStrategy VotingStrategy) *ConsensusAgent {
	if votingStrategy == "" {
		votingStrategy = VotingMajority
	}

	return &ConsensusAgent{
		name:           "ConsensusAgent",
		agents:         make([]agenkit.Agent, 0),
		votingStrategy: votingStrategy,
	}
}

// Name returns the agent name.
func (c *ConsensusAgent) Name() string {
	return c.name
}

// Capabilities returns combined capabilities of all agents.
func (c *ConsensusAgent) Capabilities() []string {
	capsMap := make(map[string]struct{})
	for _, agent := range c.agents {
		for _, cap := range agent.Capabilities() {
			capsMap[cap] = struct{}{}
		}
	}

	caps := make([]string, 0, len(capsMap))
	for cap := range capsMap {
		caps = append(caps, cap)
	}
	return caps
}

// VotingStrategy returns the voting strategy.
func (c *ConsensusAgent) VotingStrategy() VotingStrategy {
	return c.votingStrategy
}

// Agents returns the list of agents.
func (c *ConsensusAgent) Agents() []agenkit.Agent {
	// Return a copy
	agentsCopy := make([]agenkit.Agent, len(c.agents))
	copy(agentsCopy, c.agents)
	return agentsCopy
}

// AddAgent adds an agent to the consensus group.
func (c *ConsensusAgent) AddAgent(agent agenkit.Agent) {
	c.agents = append(c.agents, agent)
}

// Process gets responses from all agents and forms consensus.
//
// Currently implements a simple consensus approach where all responses
// are combined into a formatted summary showing each agent's perspective.
func (c *ConsensusAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	responses := make([]string, 0, len(c.agents))

	for _, agent := range c.agents {
		response, err := agent.Process(ctx, message)
		if err != nil {
			return nil, fmt.Errorf("agent %s failed: %w", agent.Name(), err)
		}
		responses = append(responses, response.Content)
	}

	// Simple consensus: combine all responses
	var consensus strings.Builder
	consensus.WriteString(fmt.Sprintf("Consensus from %d agents:\n\n", len(responses)))

	for i, resp := range responses {
		if i > 0 {
			consensus.WriteString("\n\n")
		}
		consensus.WriteString(fmt.Sprintf("Agent %d: %s", i+1, resp))
	}

	return &agenkit.Message{
		Role:    "assistant",
		Content: consensus.String(),
	}, nil
}
