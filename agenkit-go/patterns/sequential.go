// Package patterns provides reusable agent composition patterns.
//
// Sequential pattern enables pipeline-style agent composition where each agent
// processes the output of the previous agent. This is ideal for multi-stage
// processing workflows.
//
// Key concepts:
//   - Linear processing pipeline
//   - Output of agent N becomes input of agent N+1
//   - Early termination on errors
//   - Preserves metadata across pipeline stages
//
// Performance characteristics:
//   - Time: O(sum of agent times) - sequential execution
//   - Memory: O(1) for message passing (no accumulation)
//   - Each agent sees only previous agent's output
package patterns

import (
	"context"
	"fmt"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// SequentialAgent executes a pipeline of agents in order.
//
// Each agent receives the output of the previous agent as input.
// The final agent's output is returned as the result.
//
// Example use cases:
//   - Document processing: extract -> translate -> summarize
//   - Data pipeline: validate -> transform -> enrich
//   - Content generation: draft -> review -> format
//
// The pipeline stops immediately if any agent returns an error.
type SequentialAgent struct {
	name   string
	agents []agenkit.Agent
}

// NewSequentialAgent creates a new sequential pipeline agent.
//
// Parameters:
//   - agents: List of agents to execute in order (must have at least one)
//
// The agents will be executed in the order provided. Each agent's output
// becomes the input for the next agent.
func NewSequentialAgent(agents []agenkit.Agent) (*SequentialAgent, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("at least one agent is required")
	}

	return &SequentialAgent{
		name:   "SequentialAgent",
		agents: agents,
	}, nil
}

// Name returns the agent's identifier.
func (s *SequentialAgent) Name() string {
	return s.name
}

// Capabilities returns the combined capabilities of all agents in the pipeline.
func (s *SequentialAgent) Capabilities() []string {
	capMap := make(map[string]bool)
	for _, agent := range s.agents {
		for _, cap := range agent.Capabilities() {
			capMap[cap] = true
		}
	}

	capabilities := make([]string, 0, len(capMap))
	for cap := range capMap {
		capabilities = append(capabilities, cap)
	}
	capabilities = append(capabilities, "sequential", "pipeline")

	return capabilities
}

// Process executes the agent pipeline sequentially.
//
// The message is passed through each agent in order. Each agent's output
// becomes the input for the next agent. If any agent returns an error,
// the pipeline stops and the error is returned immediately.
//
// Metadata from each agent is preserved in the final message under the
// "pipeline_stages" key, allowing inspection of intermediate results.
func (s *SequentialAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if message == nil {
		return nil, fmt.Errorf("message cannot be nil")
	}

	// Track pipeline stages for observability
	stages := make([]map[string]interface{}, 0, len(s.agents))

	// Pass message through each agent
	current := message
	for i, agent := range s.agents {
		// Check for context cancellation
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("pipeline cancelled at stage %d: %w", i, ctx.Err())
		default:
		}

		// Process with current agent
		result, err := agent.Process(ctx, current)
		if err != nil {
			return nil, fmt.Errorf("agent %d (%s) failed: %w", i, agent.Name(), err)
		}

		// Record stage metadata
		stageInfo := map[string]interface{}{
			"agent": agent.Name(),
			"stage": i,
		}
		if result.Metadata != nil {
			stageInfo["metadata"] = result.Metadata
		}
		stages = append(stages, stageInfo)

		// Use result as input for next agent
		current = result
	}

	// Add pipeline metadata to final result
	if current.Metadata == nil {
		current.Metadata = make(map[string]interface{})
	}
	current.Metadata["pipeline_stages"] = stages
	current.Metadata["pipeline_length"] = len(s.agents)

	return current, nil
}
