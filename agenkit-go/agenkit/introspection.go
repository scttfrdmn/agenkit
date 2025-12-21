// Package agenkit provides introspection support for examining agent internal state.
//
// This module provides introspection capability - the ability for agents to examine
// their own internal state, memory, and capabilities. This is distinct from the
// Reflection pattern, which is about analyzing past performance.
//
// Key distinctions:
// - Introspection (this module): "What do I know?" - State examination
// - Reflection (pattern): "How did I do?" - Performance analysis
//
// References:
// - Issue #301: Add Introspection Capability to Agent Interface
// - ArXiv: Introspection of Thought Helps AI Agents (https://arxiv.org/abs/2507.08664)
// - Biswas & Talukdar: Building Agentic AI Systems
package agenkit

import (
	"fmt"
	"time"
)

// IntrospectionResult represents a snapshot of an agent's internal state.
//
// This provides a structured view into an agent's current state, including
// its capabilities, memory contents, and any agent-specific internal state.
//
// Design decisions:
// - Timestamp: When this snapshot was taken (UTC)
// - AgentName: Which agent was introspected
// - Capabilities: What the agent can do
// - MemoryState: Contents of agent's memory (nil if no memory)
// - InternalState: Agent-specific state information
// - Metadata: Extension point for additional information
//
// Usage:
//
//	result := agent.Introspect()
//	fmt.Printf("Agent: %s\n", result.AgentName)
//	fmt.Printf("Capabilities: %v\n", result.Capabilities)
//	if result.MemoryState != nil {
//	    fmt.Printf("Memory entries: %d\n", len(result.MemoryState))
//	}
//
// Introspection is useful for:
// - Debugging: Examine agent state during development
// - Monitoring: Track agent state in production
// - Coordination: Agents can inspect each other's capabilities
// - Testing: Verify agent state in tests
// - Explainability: Understand what an agent "knows"
type IntrospectionResult struct {
	// Timestamp when introspection was performed (UTC)
	Timestamp time.Time `json:"timestamp"`

	// AgentName is the name of the agent that was introspected
	AgentName string `json:"agent_name"`

	// Capabilities is the list of capability strings this agent supports
	Capabilities []string `json:"capabilities"`

	// MemoryState contains the agent's memory contents (nil if no memory)
	MemoryState map[string]interface{} `json:"memory_state,omitempty"`

	// InternalState contains agent-specific internal state
	InternalState map[string]interface{} `json:"internal_state"`

	// Metadata provides additional introspection information
	Metadata map[string]interface{} `json:"metadata"`
}

// NewIntrospectionResult creates a new introspection result with validation.
//
// This function validates the input parameters and returns an error if they
// are invalid. Use this for creating introspection results in agent implementations.
//
// Parameters:
//   - agentName: Name of the agent (cannot be empty)
//   - capabilities: List of capability strings (cannot be nil)
//   - memoryState: Memory contents (can be nil if no memory)
//   - internalState: Agent-specific state (cannot be nil)
//   - metadata: Additional metadata (can be nil, will be initialized)
//
// Returns:
//   - *IntrospectionResult: The created result
//   - error: Validation error if any parameter is invalid
func NewIntrospectionResult(
	agentName string,
	capabilities []string,
	memoryState map[string]interface{},
	internalState map[string]interface{},
	metadata map[string]interface{},
) (*IntrospectionResult, error) {
	result := &IntrospectionResult{
		Timestamp:     time.Now().UTC(),
		AgentName:     agentName,
		Capabilities:  capabilities,
		MemoryState:   memoryState,
		InternalState: internalState,
		Metadata:      metadata,
	}

	// Initialize maps if nil
	if result.Capabilities == nil {
		result.Capabilities = []string{}
	}
	if result.InternalState == nil {
		result.InternalState = make(map[string]interface{})
	}
	if result.Metadata == nil {
		result.Metadata = make(map[string]interface{})
	}

	// Validate
	if err := result.Validate(); err != nil {
		return nil, err
	}

	return result, nil
}

// Validate validates the introspection result.
//
// Returns an error if:
// - AgentName is empty
// - Capabilities is nil
// - InternalState is nil
// - MemoryState is not nil and not a map
func (r *IntrospectionResult) Validate() error {
	if r.AgentName == "" {
		return fmt.Errorf("agent_name cannot be empty")
	}

	if r.Capabilities == nil {
		return fmt.Errorf("capabilities cannot be nil (use empty slice instead)")
	}

	if r.InternalState == nil {
		return fmt.Errorf("internal_state cannot be nil (use empty map instead)")
	}

	return nil
}

// DefaultIntrospectionResult creates a basic introspection result for an agent.
//
// This is a helper function that creates an introspection result with default
// values for agents that don't have custom memory or internal state.
//
// Usage:
//
//	func (a *MyAgent) Introspect() *IntrospectionResult {
//	    return DefaultIntrospectionResult(a)
//	}
func DefaultIntrospectionResult(agent Agent) *IntrospectionResult {
	return &IntrospectionResult{
		Timestamp:     time.Now().UTC(),
		AgentName:     agent.Name(),
		Capabilities:  agent.Capabilities(),
		MemoryState:   nil,
		InternalState: make(map[string]interface{}),
		Metadata:      make(map[string]interface{}),
	}
}
