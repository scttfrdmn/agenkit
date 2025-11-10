// Package composition provides agent composition patterns.
package composition

import (
	"context"
	"fmt"

	"github.com/agenkit/agenkit-go/agenkit"
)

// SequentialAgent executes multiple agents in sequence, passing output from
// one agent as input to the next.
type SequentialAgent struct {
	name   string
	agents []agenkit.Agent
}

// Verify that SequentialAgent implements Agent interface.
var _ agenkit.Agent = (*SequentialAgent)(nil)

// NewSequentialAgent creates a new sequential agent.
func NewSequentialAgent(name string, agents ...agenkit.Agent) (*SequentialAgent, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("sequential agent requires at least one agent")
	}
	return &SequentialAgent{
		name:   name,
		agents: agents,
	}, nil
}

// Name returns the name of the sequential agent.
func (s *SequentialAgent) Name() string {
	return s.name
}

// Capabilities returns combined capabilities of all agents.
func (s *SequentialAgent) Capabilities() []string {
	capsSet := make(map[string]bool)
	for _, agent := range s.agents {
		for _, cap := range agent.Capabilities() {
			capsSet[cap] = true
		}
	}

	caps := make([]string, 0, len(capsSet))
	for cap := range capsSet {
		caps = append(caps, cap)
	}
	caps = append(caps, "sequential")
	return caps
}

// Process executes all agents in sequence.
func (s *SequentialAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	current := message

	for i, agent := range s.agents {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("sequential execution cancelled at step %d: %w", i+1, ctx.Err())
		default:
		}

		// Process through agent
		result, err := agent.Process(ctx, current)
		if err != nil {
			return nil, fmt.Errorf("step %d (%s) failed: %w", i+1, agent.Name(), err)
		}

		// Output becomes input for next agent
		current = result
	}

	return current, nil
}

// GetAgents returns the list of agents in the sequence.
func (s *SequentialAgent) GetAgents() []agenkit.Agent {
	return s.agents
}
