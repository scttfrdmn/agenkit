package composition

import (
	"context"
	"fmt"
	"strings"

	"github.com/agenkit/agenkit-go/agenkit"
)

// FallbackAgent tries agents in order until one succeeds.
// This implements the Fallback/Retry pattern for reliability.
type FallbackAgent struct {
	name   string
	agents []agenkit.Agent
}

// Verify that FallbackAgent implements Agent interface.
var _ agenkit.Agent = (*FallbackAgent)(nil)

// NewFallbackAgent creates a new fallback agent.
func NewFallbackAgent(name string, agents ...agenkit.Agent) (*FallbackAgent, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("fallback agent requires at least one agent")
	}
	return &FallbackAgent{
		name:   name,
		agents: agents,
	}, nil
}

// Name returns the name of the fallback agent.
func (f *FallbackAgent) Name() string {
	return f.name
}

// Capabilities returns combined capabilities of all agents.
func (f *FallbackAgent) Capabilities() []string {
	capsSet := make(map[string]bool)
	for _, agent := range f.agents {
		for _, cap := range agent.Capabilities() {
			capsSet[cap] = true
		}
	}

	caps := make([]string, 0, len(capsSet))
	for cap := range capsSet {
		caps = append(caps, cap)
	}
	caps = append(caps, "fallback")
	return caps
}

// Process tries each agent in order until one succeeds.
func (f *FallbackAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	var errors []string

	for i, agent := range f.agents {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("fallback execution cancelled at attempt %d: %w", i+1, ctx.Err())
		default:
		}

		// Try this agent
		result, err := agent.Process(ctx, message)
		if err == nil {
			// Success! Add metadata about which agent was used
			result.Metadata["fallback_agent_used"] = agent.Name()
			result.Metadata["fallback_attempt"] = i + 1
			return result, nil
		}

		// Record error and try next agent
		errors = append(errors, fmt.Sprintf("agent %d (%s): %v", i+1, agent.Name(), err))
	}

	// All agents failed
	return nil, fmt.Errorf("all %d agents failed: %s", len(f.agents), strings.Join(errors, "; "))
}

// GetAgents returns the list of fallback agents.
func (f *FallbackAgent) GetAgents() []agenkit.Agent {
	return f.agents
}
