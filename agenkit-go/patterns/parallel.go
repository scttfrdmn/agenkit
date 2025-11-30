// Package patterns provides reusable agent composition patterns.
//
// Parallel pattern enables concurrent execution of multiple agents with
// result aggregation. This is ideal for ensemble methods, multi-perspective
// analysis, or parallelizing independent tasks.
//
// Key concepts:
//   - Concurrent agent execution using goroutines
//   - Custom aggregation function for combining results
//   - All agents receive the same input message
//   - Results collected and aggregated after all complete
//
// Performance characteristics:
//   - Time: O(max agent time) - parallel execution
//   - Memory: O(n * message size) for concurrent processing
//   - Thread-safe with proper synchronization
package patterns

import (
	"context"
	"fmt"
	"sync"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// AggregatorFunc is a function that combines multiple agent responses into one.
//
// The function receives all agent responses and should return a single
// aggregated response. Common aggregation strategies include:
//   - Voting: Select most common response
//   - Averaging: Combine numeric results
//   - Concatenation: Merge all responses
//   - First-success: Return first successful result
//   - Consensus: Require agreement threshold
type AggregatorFunc func([]*agenkit.Message) *agenkit.Message

// ParallelAgent executes multiple agents concurrently and aggregates results.
//
// All agents receive the same input message and execute concurrently.
// Results are collected and passed to the aggregator function which
// produces the final output.
//
// Example use cases:
//   - Multi-model ensemble for improved accuracy
//   - Parallel document analysis (sentiment, entities, topics)
//   - A/B testing different agent implementations
//   - Redundant processing for reliability
//
// If any agent fails, the error is collected but other agents continue.
// The aggregator receives all successful results.
type ParallelAgent struct {
	name       string
	agents     []agenkit.Agent
	aggregator AggregatorFunc
}

// NewParallelAgent creates a new parallel execution agent.
//
// Parameters:
//   - agents: List of agents to execute concurrently (must have at least one)
//   - aggregator: Function to combine agent results into final output
//
// The aggregator function is called with all successful agent responses
// and must return a single aggregated message.
func NewParallelAgent(agents []agenkit.Agent, aggregator AggregatorFunc) (*ParallelAgent, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("at least one agent is required")
	}
	if aggregator == nil {
		return nil, fmt.Errorf("aggregator function is required")
	}

	return &ParallelAgent{
		name:       "ParallelAgent",
		agents:     agents,
		aggregator: aggregator,
	}, nil
}

// Name returns the agent's identifier.
func (p *ParallelAgent) Name() string {
	return p.name
}

// Capabilities returns the combined capabilities of all agents.
func (p *ParallelAgent) Capabilities() []string {
	capMap := make(map[string]bool)
	for _, agent := range p.agents {
		for _, cap := range agent.Capabilities() {
			capMap[cap] = true
		}
	}

	capabilities := make([]string, 0, len(capMap))
	for cap := range capMap {
		capabilities = append(capabilities, cap)
	}
	capabilities = append(capabilities, "parallel", "ensemble")

	return capabilities
}

// agentResult holds the result or error from an agent execution.
type agentResult struct {
	agentName string
	message   *agenkit.Message
	err       error
}

// Process executes all agents concurrently and aggregates results.
//
// All agents receive the same input message and execute in parallel using
// goroutines. Results are collected as they complete. Once all agents finish
// (or fail), successful results are passed to the aggregator function.
//
// If all agents fail, an error is returned. If some agents succeed, their
// results are aggregated and any errors are recorded in metadata.
//
// The final message includes metadata about:
//   - Total agents executed
//   - Successful agent results
//   - Any errors that occurred
func (p *ParallelAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if message == nil {
		return nil, fmt.Errorf("message cannot be nil")
	}

	// Channel for collecting results
	resultsCh := make(chan agentResult, len(p.agents))

	// WaitGroup to track completion
	var wg sync.WaitGroup

	// Launch all agents concurrently
	for _, agent := range p.agents {
		wg.Add(1)
		go func(a agenkit.Agent) {
			defer wg.Done()

			// Process with agent
			result, err := a.Process(ctx, message)

			// Send result to channel
			resultsCh <- agentResult{
				agentName: a.Name(),
				message:   result,
				err:       err,
			}
		}(agent)
	}

	// Close results channel when all agents complete
	go func() {
		wg.Wait()
		close(resultsCh)
	}()

	// Collect all results
	var successes []*agenkit.Message
	var errors []map[string]interface{}

	for result := range resultsCh {
		if result.err != nil {
			errors = append(errors, map[string]interface{}{
				"agent": result.agentName,
				"error": result.err.Error(),
			})
		} else {
			successes = append(successes, result.message)
		}
	}

	// Check if all agents failed
	if len(successes) == 0 {
		return nil, fmt.Errorf("all agents failed: %v", errors)
	}

	// Aggregate successful results
	aggregated := p.aggregator(successes)

	// Add parallel execution metadata
	if aggregated.Metadata == nil {
		aggregated.Metadata = make(map[string]interface{})
	}
	aggregated.Metadata["parallel_agents"] = len(p.agents)
	aggregated.Metadata["successful_agents"] = len(successes)
	if len(errors) > 0 {
		aggregated.Metadata["errors"] = errors
	}

	return aggregated, nil
}

// DefaultAggregators provides common aggregation strategies.
var DefaultAggregators = struct {
	// First returns the first successful result
	First AggregatorFunc

	// Concatenate combines all results with separator
	Concatenate AggregatorFunc

	// MajorityVote returns the most common response
	MajorityVote AggregatorFunc
}{
	First: func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("assistant", "No results to aggregate")
		}
		return messages[0]
	},

	Concatenate: func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("assistant", "No results to aggregate")
		}

		var combined string
		for i, msg := range messages {
			if i > 0 {
				combined += "\n\n---\n\n"
			}
			combined += msg.Content
		}

		return agenkit.NewMessage("assistant", combined)
	},

	MajorityVote: func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("assistant", "No results to aggregate")
		}

		// Count occurrences of each response
		votes := make(map[string]int)
		msgByContent := make(map[string]*agenkit.Message)

		for _, msg := range messages {
			votes[msg.Content]++
			msgByContent[msg.Content] = msg
		}

		// Find most common response
		var maxVotes int
		var winner string
		for content, count := range votes {
			if count > maxVotes {
				maxVotes = count
				winner = content
			}
		}

		result := msgByContent[winner]
		result.WithMetadata("votes", maxVotes).
			WithMetadata("total_agents", len(messages))

		return result
	},
}
