// Package patterns provides reusable agent composition patterns.
//
// Supervisor pattern implements hierarchical coordination where a central
// supervisor agent plans task decomposition, delegates to specialist agents,
// and synthesizes their results into a final response.
//
// Key concepts:
//   - Central planner/supervisor for coordination
//   - Specialist agents for domain-specific tasks
//   - Task decomposition and delegation
//   - Result synthesis from specialist outputs
//
// Performance characteristics:
//   - Time: O(planning + max(specialist) + synthesis)
//   - Memory: O(n specialists * message size)
//   - Hierarchical execution model
package patterns

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Subtask represents a decomposed task for a specialist agent.
type Subtask struct {
	// Type identifies which specialist should handle this subtask
	Type string
	// Message is the input for the specialist
	Message *agenkit.Message
	// Metadata contains additional task information
	Metadata map[string]interface{}
}

// PlannerAgent is responsible for task decomposition and result synthesis.
//
// The planner receives the initial message and breaks it down into subtasks
// for specialist agents. After specialists complete their work, the planner
// synthesizes their results into a final response.
type PlannerAgent interface {
	agenkit.Agent

	// Plan decomposes a message into subtasks for specialists
	Plan(ctx context.Context, message *agenkit.Message) ([]Subtask, error)

	// Synthesize combines specialist results into final response
	Synthesize(ctx context.Context, original *agenkit.Message, results map[string]*agenkit.Message) (*agenkit.Message, error)
}

// SupervisorAgent coordinates specialist agents through hierarchical planning.
//
// The supervisor uses a planner agent to decompose complex tasks into subtasks,
// delegates each subtask to an appropriate specialist, and synthesizes the
// specialist results into a coherent final response.
//
// Example use cases:
//   - Software development: planner coordinates coder, tester, reviewer
//   - Research: planner coordinates searcher, analyzer, writer
//   - Data processing: planner coordinates extractor, transformer, validator
//   - Customer service: planner coordinates billing, technical, account specialists
//
// The supervisor pattern is ideal when tasks have clear domain boundaries
// and benefit from specialized expertise.
type SupervisorAgent struct {
	name        string
	planner     PlannerAgent
	specialists map[string]agenkit.Agent
}

// NewSupervisorAgent creates a new supervisor agent.
//
// Parameters:
//   - planner: Agent responsible for planning and synthesis
//   - specialists: Map of specialist agents keyed by their domain/type
//
// The planner's Plan method should return subtasks with Type values that
// match keys in the specialists map.
func NewSupervisorAgent(planner PlannerAgent, specialists map[string]agenkit.Agent) (*SupervisorAgent, error) {
	if planner == nil {
		return nil, fmt.Errorf("planner is required")
	}
	if len(specialists) == 0 {
		return nil, fmt.Errorf("at least one specialist is required")
	}

	return &SupervisorAgent{
		name:        "SupervisorAgent",
		planner:     planner,
		specialists: specialists,
	}, nil
}

// Name returns the agent's identifier.
func (s *SupervisorAgent) Name() string {
	return s.name
}

// Capabilities returns the combined capabilities of planner and specialists.
func (s *SupervisorAgent) Capabilities() []string {
	capMap := make(map[string]bool)

	// Add planner capabilities
	for _, cap := range s.planner.Capabilities() {
		capMap[cap] = true
	}

	// Add specialist capabilities
	for _, specialist := range s.specialists {
		for _, cap := range specialist.Capabilities() {
			capMap[cap] = true
		}
	}

	capabilities := make([]string, 0, len(capMap))
	for cap := range capMap {
		capabilities = append(capabilities, cap)
	}
	capabilities = append(capabilities, "supervisor", "hierarchical", "coordination")

	return capabilities
}

// Process executes the supervisor pattern: plan, delegate, synthesize.
//
// The process follows these steps:
//  1. Planning: Planner decomposes the task into subtasks
//  2. Delegation: Each subtask is routed to appropriate specialist
//  3. Execution: Specialists process their assigned subtasks
//  4. Synthesis: Planner combines specialist results into final response
//
// If any subtask references an unknown specialist type, an error is returned.
// If any specialist fails, the error is returned immediately.
//
// The final message includes metadata about the planning and delegation process.
func (s *SupervisorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if message == nil {
		return nil, fmt.Errorf("message cannot be nil")
	}

	// Step 1: Plan - decompose task into subtasks
	subtasks, err := s.planner.Plan(ctx, message)
	if err != nil {
		return nil, fmt.Errorf("planning failed: %w", err)
	}

	if len(subtasks) == 0 {
		// No subtasks - let planner handle directly
		return s.planner.Process(ctx, message)
	}

	// Step 2: Validate specialist availability
	for i, subtask := range subtasks {
		if _, ok := s.specialists[subtask.Type]; !ok {
			availableTypes := make([]string, 0, len(s.specialists))
			for t := range s.specialists {
				availableTypes = append(availableTypes, t)
			}
			return nil, fmt.Errorf("subtask %d references unknown specialist type '%s' (available: %s)",
				i, subtask.Type, strings.Join(availableTypes, ", "))
		}
	}

	// Step 3: Execute subtasks with specialists
	results := make(map[string]*agenkit.Message)
	executionOrder := make([]map[string]interface{}, 0, len(subtasks))

	for i, subtask := range subtasks {
		// Check for context cancellation
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("supervisor cancelled at subtask %d: %w", i, ctx.Err())
		default:
		}

		specialist := s.specialists[subtask.Type]

		// Execute subtask
		result, err := specialist.Process(ctx, subtask.Message)
		if err != nil {
			return nil, fmt.Errorf("specialist '%s' failed on subtask %d: %w",
				subtask.Type, i, err)
		}

		// Store result keyed by specialist type and index for synthesis
		resultKey := fmt.Sprintf("%s_%d", subtask.Type, i)
		results[resultKey] = result

		// Track execution order
		executionOrder = append(executionOrder, map[string]interface{}{
			"index":      i,
			"type":       subtask.Type,
			"specialist": specialist.Name(),
		})
	}

	// Step 4: Synthesize - combine specialist results
	final, err := s.planner.Synthesize(ctx, message, results)
	if err != nil {
		return nil, fmt.Errorf("synthesis failed: %w", err)
	}

	// Add supervisor metadata
	if final.Metadata == nil {
		final.Metadata = make(map[string]interface{})
	}
	final.Metadata["supervisor_subtasks"] = len(subtasks)
	final.Metadata["supervisor_specialists"] = len(s.specialists)
	final.Metadata["execution_order"] = executionOrder

	return final, nil
}

// SimplePlanner provides a basic planner implementation for simple use cases.
//
// This planner uses an LLM agent to handle both planning and synthesis.
// For planning, it prompts the LLM to decompose the task. For synthesis,
// it prompts the LLM to combine results.
//
// For production use, consider implementing a custom PlannerAgent with
// domain-specific planning and synthesis logic.
type SimplePlanner struct {
	agent agenkit.Agent
}

// NewSimplePlanner creates a basic planner using an LLM agent.
func NewSimplePlanner(agent agenkit.Agent) *SimplePlanner {
	return &SimplePlanner{agent: agent}
}

// Name returns the planner's identifier.
func (p *SimplePlanner) Name() string {
	return "SimplePlanner"
}

// Capabilities returns the planner's capabilities.
func (p *SimplePlanner) Capabilities() []string {
	return append(p.agent.Capabilities(), "planning", "synthesis")
}

// Process handles direct message processing (delegates to underlying agent).
func (p *SimplePlanner) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return p.agent.Process(ctx, message)
}

// Plan uses the LLM to decompose tasks (simplified implementation).
//
// Note: This is a basic implementation. Production code should parse
// the LLM response and create proper Subtask structures.
func (p *SimplePlanner) Plan(ctx context.Context, message *agenkit.Message) ([]Subtask, error) {
	// In a real implementation, this would prompt the LLM to create a plan
	// and parse the response into Subtask structures.
	// For now, return empty to trigger direct processing.
	return []Subtask{}, nil
}

// Synthesize combines specialist results (simplified implementation).
func (p *SimplePlanner) Synthesize(ctx context.Context, original *agenkit.Message, results map[string]*agenkit.Message) (*agenkit.Message, error) {
	// Combine all results
	var combined strings.Builder
	combined.WriteString("Synthesis of specialist results:\n\n")

	for key, result := range results {
		combined.WriteString(fmt.Sprintf("Result from %s:\n%s\n\n", key, result.Content))
	}

	return agenkit.NewMessage("assistant", combined.String()), nil
}

// Introspect examines the planner's internal state.
func (p *SimplePlanner) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    p.Name(),
		Capabilities: p.Capabilities(),
	}
}
