package composition

import (
	"context"
	"fmt"
	"strings"
	"sync"

	"github.com/agenkit/agenkit-go/agenkit"
)

// ParallelAgent executes multiple agents concurrently and combines their results.
type ParallelAgent struct {
	name   string
	agents []agenkit.Agent
}

// Verify that ParallelAgent implements Agent interface.
var _ agenkit.Agent = (*ParallelAgent)(nil)

// NewParallelAgent creates a new parallel agent.
func NewParallelAgent(name string, agents ...agenkit.Agent) (*ParallelAgent, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("parallel agent requires at least one agent")
	}
	return &ParallelAgent{
		name:   name,
		agents: agents,
	}, nil
}

// Name returns the name of the parallel agent.
func (p *ParallelAgent) Name() string {
	return p.name
}

// Capabilities returns combined capabilities of all agents.
func (p *ParallelAgent) Capabilities() []string {
	capsSet := make(map[string]bool)
	for _, agent := range p.agents {
		for _, cap := range agent.Capabilities() {
			capsSet[cap] = true
		}
	}

	caps := make([]string, 0, len(capsSet))
	for cap := range capsSet {
		caps = append(caps, cap)
	}
	caps = append(caps, "parallel")
	return caps
}

// AgentResult holds the result from a single agent execution.
type AgentResult struct {
	AgentName string
	Message   *agenkit.Message
	Error     error
}

// Process executes all agents in parallel and combines their results.
func (p *ParallelAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	results := make(chan *AgentResult, len(p.agents))
	var wg sync.WaitGroup

	// Start all agents concurrently
	for _, agent := range p.agents {
		wg.Add(1)
		go func(a agenkit.Agent) {
			defer wg.Done()

			result, err := a.Process(ctx, message)
			results <- &AgentResult{
				AgentName: a.Name(),
				Message:   result,
				Error:     err,
			}
		}(agent)
	}

	// Wait for all agents to complete
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect results
	var responses []*AgentResult
	for result := range results {
		responses = append(responses, result)
	}

	// Check for errors
	var errors []string
	for _, result := range responses {
		if result.Error != nil {
			errors = append(errors, fmt.Sprintf("%s: %v", result.AgentName, result.Error))
		}
	}

	if len(errors) > 0 {
		return nil, fmt.Errorf("parallel execution had errors: %s", strings.Join(errors, "; "))
	}

	// Combine all responses
	combined := p.combineResponses(responses)
	return combined, nil
}

// combineResponses combines multiple agent responses into a single message.
func (p *ParallelAgent) combineResponses(results []*AgentResult) *agenkit.Message {
	var contentParts []string
	combinedMetadata := make(map[string]interface{})

	for _, result := range results {
		if result.Message != nil {
			contentParts = append(contentParts, fmt.Sprintf("[%s]: %s", result.AgentName, result.Message.Content))

			// Merge metadata with agent name prefix
			for key, value := range result.Message.Metadata {
				prefixedKey := fmt.Sprintf("%s.%s", result.AgentName, key)
				combinedMetadata[prefixedKey] = value
			}
		}
	}

	response := agenkit.NewMessage("agent", strings.Join(contentParts, "\n"))
	response.Metadata = combinedMetadata
	return response
}

// GetAgents returns the list of agents that run in parallel.
func (p *ParallelAgent) GetAgents() []agenkit.Agent {
	return p.agents
}
