// Package patterns provides reusable agent composition patterns.
//
// Fallback pattern implements sequential retry across multiple agents.
// If one agent fails, the next agent is tried until one succeeds or
// all agents are exhausted.
//
// Key concepts:
//   - Sequential attempt order
//   - Automatic failover on errors
//   - First successful result wins
//   - Error collection for debugging
//
// Performance characteristics:
//   - Best case: O(first agent) - immediate success
//   - Worst case: O(sum of all agents) - all fail
//   - Early termination on first success
package patterns

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// FallbackAgent tries agents in sequence until one succeeds.
//
// Each agent is attempted in order. The first agent to return a successful
// response wins, and that response is returned immediately. If an agent
// fails, the next agent is tried. If all agents fail, an error combining
// all failure reasons is returned.
//
// Example use cases:
//   - High availability: fallback from primary to backup systems
//   - Multi-provider: try different LLM providers until one succeeds
//   - Graceful degradation: try advanced model, fallback to simple model
//   - Retry with alternatives: different strategies for same task
//   - Error recovery: fallback to cached/default responses
//
// The fallback pattern is ideal when you need resilience and have
// multiple ways to accomplish the same task.
type FallbackAgent struct {
	name   string
	agents []agenkit.Agent
}

// NewFallbackAgent creates a new fallback agent.
//
// Parameters:
//   - agents: List of agents to try in order (must have at least one)
//
// Agents are tried in the order provided. The first successful response
// is returned immediately without trying remaining agents.
func NewFallbackAgent(agents []agenkit.Agent) (*FallbackAgent, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("at least one agent is required")
	}

	return &FallbackAgent{
		name:   "FallbackAgent",
		agents: agents,
	}, nil
}

// Name returns the agent's identifier.
func (f *FallbackAgent) Name() string {
	return f.name
}

// Capabilities returns the combined capabilities of all agents.
func (f *FallbackAgent) Capabilities() []string {
	capMap := make(map[string]bool)

	for _, agent := range f.agents {
		for _, cap := range agent.Capabilities() {
			capMap[cap] = true
		}
	}

	capabilities := make([]string, 0, len(capMap))
	for cap := range capMap {
		capabilities = append(capabilities, cap)
	}
	capabilities = append(capabilities, "fallback", "retry", "high-availability")

	return capabilities
}

// attemptResult holds the result of a single agent attempt.
type attemptResult struct {
	agentIndex int
	agentName  string
	success    bool
	message    *agenkit.Message
	err        error
}

// Process tries agents sequentially until one succeeds.
//
// Each agent is attempted in order. If an agent succeeds, its response
// is returned immediately with metadata about the attempt. If an agent
// fails, the next agent is tried.
//
// If all agents fail, an error is returned that includes information
// about all failed attempts.
//
// The successful message includes metadata about:
//   - Which agent succeeded
//   - How many attempts were made
//   - Which agents were tried
func (f *FallbackAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if message == nil {
		return nil, fmt.Errorf("message cannot be nil")
	}

	attempts := make([]attemptResult, 0, len(f.agents))

	for i, agent := range f.agents {
		// Check for context cancellation
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("fallback cancelled after %d attempts: %w", i, ctx.Err())
		default:
		}

		// Try agent
		result, err := agent.Process(ctx, message)

		// Record attempt
		attempt := attemptResult{
			agentIndex: i,
			agentName:  agent.Name(),
			success:    err == nil,
			message:    result,
			err:        err,
		}
		attempts = append(attempts, attempt)

		// If successful, return immediately
		if err == nil {
			return f.buildSuccessResult(result, attempts), nil
		}

		// Agent failed, try next (if available)
		// Error will be included in final error if all fail
	}

	// All agents failed
	return nil, f.buildFailureError(attempts)
}

// buildSuccessResult adds fallback metadata to successful response.
func (f *FallbackAgent) buildSuccessResult(message *agenkit.Message, attempts []attemptResult) *agenkit.Message {
	if message.Metadata == nil {
		message.Metadata = make(map[string]interface{})
	}

	successfulAttempt := attempts[len(attempts)-1]

	message.Metadata["fallback_attempts"] = len(attempts)
	message.Metadata["fallback_success_index"] = successfulAttempt.agentIndex
	message.Metadata["fallback_success_agent"] = successfulAttempt.agentName
	message.Metadata["fallback_total_agents"] = len(f.agents)

	// Include failed attempts for observability
	if len(attempts) > 1 {
		failedAttempts := make([]map[string]interface{}, 0, len(attempts)-1)
		for i := 0; i < len(attempts)-1; i++ {
			failedAttempts = append(failedAttempts, map[string]interface{}{
				"index": attempts[i].agentIndex,
				"agent": attempts[i].agentName,
				"error": attempts[i].err.Error(),
			})
		}
		message.Metadata["fallback_failed_attempts"] = failedAttempts
	}

	return message
}

// buildFailureError creates a comprehensive error from all failed attempts.
func (f *FallbackAgent) buildFailureError(attempts []attemptResult) error {
	var errorMsg strings.Builder
	errorMsg.WriteString(fmt.Sprintf("all %d agents failed:\n", len(attempts)))

	for _, attempt := range attempts {
		errorMsg.WriteString(fmt.Sprintf("  [%d] %s: %v\n",
			attempt.agentIndex, attempt.agentName, attempt.err))
	}

	return fmt.Errorf("%s", errorMsg.String())
}

// WithRecovery wraps an agent with automatic error recovery.
//
// This helper creates a fallback agent with a primary agent and a recovery
// function that generates fallback responses when the primary fails.
//
// Example:
//
//	primaryAgent := myLLMAgent
//	recoveryFunc := func(ctx context.Context, msg *agenkit.Message, err error) (*agenkit.Message, error) {
//	    return agenkit.NewMessage("assistant", "I'm experiencing technical difficulties. Please try again."), nil
//	}
//	agent := patterns.WithRecovery(primaryAgent, recoveryFunc)
type RecoveryFunc func(ctx context.Context, message *agenkit.Message, originalError error) (*agenkit.Message, error)

// RecoveryAgent wraps an agent with a recovery function.
type RecoveryAgent struct {
	name         string
	agent        agenkit.Agent
	recoveryFunc RecoveryFunc
}

// WithRecovery creates a fallback agent with custom recovery logic.
func WithRecovery(agent agenkit.Agent, recovery RecoveryFunc) *RecoveryAgent {
	return &RecoveryAgent{
		name:         fmt.Sprintf("%s+Recovery", agent.Name()),
		agent:        agent,
		recoveryFunc: recovery,
	}
}

// Name returns the agent's identifier.
func (r *RecoveryAgent) Name() string {
	return r.name
}

// Capabilities returns the agent's capabilities plus recovery.
func (r *RecoveryAgent) Capabilities() []string {
	caps := r.agent.Capabilities()
	return append(caps, "recovery", "error-handling")
}

// Process executes the agent with recovery on failure.
func (r *RecoveryAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	result, err := r.agent.Process(ctx, message)
	if err == nil {
		return result, nil
	}

	// Primary agent failed, try recovery
	recovered, recoveryErr := r.recoveryFunc(ctx, message, err)
	if recoveryErr != nil {
		return nil, fmt.Errorf("primary agent failed: %w; recovery failed: %v", err, recoveryErr)
	}

	// Add recovery metadata
	if recovered.Metadata == nil {
		recovered.Metadata = make(map[string]interface{})
	}
	recovered.Metadata["recovery_used"] = true
	recovered.Metadata["original_error"] = err.Error()

	return recovered, nil
}

// DefaultRecovery provides common recovery strategies.
var DefaultRecovery = struct {
	// StaticMessage returns a fixed fallback message
	StaticMessage func(message string) RecoveryFunc

	// RetryOnce attempts the agent one more time
	RetryOnce RecoveryFunc

	// EmptyResponse returns an empty but valid response
	EmptyResponse RecoveryFunc
}{
	StaticMessage: func(message string) RecoveryFunc {
		return func(ctx context.Context, msg *agenkit.Message, originalError error) (*agenkit.Message, error) {
			return agenkit.NewMessage("assistant", message), nil
		}
	},

	RetryOnce: func(ctx context.Context, msg *agenkit.Message, originalError error) (*agenkit.Message, error) {
		// This is a placeholder - actual retry would need the agent reference
		return nil, fmt.Errorf("retry not available in this context: %w", originalError)
	},

	EmptyResponse: func(ctx context.Context, msg *agenkit.Message, originalError error) (*agenkit.Message, error) {
		return agenkit.NewMessage("assistant", ""), nil
	},
}
