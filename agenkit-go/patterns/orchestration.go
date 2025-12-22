// Package patterns provides core orchestration patterns for agenkit.
//
// Patterns are reusable ways to compose agents:
//   - Sequential: Execute agents one after another (pipeline)
//   - Parallel: Execute agents concurrently (fan-out)
//   - Router: Route to one agent based on condition (dispatch)
//
// Design principles:
//   - Simple, obvious implementations
//   - No magic, no surprises
//   - Composable (patterns can contain patterns)
//   - Observable (hooks for monitoring)
package patterns

import (
	"context"
	"fmt"
	"sync"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// AgentHook is called before/after agent execution
type AgentHook func(agent agenkit.Agent, message *agenkit.Message)

// Aggregator combines parallel results into a single message
type Aggregator func(messages []*agenkit.Message) *agenkit.Message

// Router returns a handler key for routing a message
type Router func(message *agenkit.Message) string

// SequentialPattern executes agents sequentially - output of one becomes input of next.
//
// This is the simplest and most common pattern: agent1 → agent2 → agent3
//
// Performance characteristics:
//   - No overhead vs calling agents directly
//   - Agents execute in order (no parallelism)
//   - Short-circuits on error (stops at first failure)
//
// Example:
//
//	pipeline := NewSequentialPattern([]agenkit.Agent{agent1, agent2, agent3}, nil)
//	result, err := pipeline.Process(ctx, message)
type SequentialPattern struct {
	agents      []agenkit.Agent
	name        string
	beforeAgent AgentHook
	afterAgent  AgentHook
}

// SequentialPatternConfig configures a sequential pattern
type SequentialPatternConfig struct {
	Name        string
	BeforeAgent AgentHook
	AfterAgent  AgentHook
}

// NewSequentialPattern creates a new sequential execution pattern
func NewSequentialPattern(agents []agenkit.Agent, config *SequentialPatternConfig) (*SequentialPattern, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("sequential pattern requires at least one agent")
	}

	name := "sequential"
	var beforeAgent, afterAgent AgentHook

	if config != nil {
		if config.Name != "" {
			name = config.Name
		}
		beforeAgent = config.BeforeAgent
		afterAgent = config.AfterAgent
	}

	return &SequentialPattern{
		agents:      agents,
		name:        name,
		beforeAgent: beforeAgent,
		afterAgent:  afterAgent,
	}, nil
}

// Name returns the pattern name
func (s *SequentialPattern) Name() string {
	return s.name
}

// Capabilities returns combined capabilities of all agents
func (s *SequentialPattern) Capabilities() []string {
	capsMap := make(map[string]struct{})
	for _, agent := range s.agents {
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

// Introspect returns introspection information about the pattern
func (s *SequentialPattern) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    s.Name(),
		Capabilities: s.Capabilities(),
	}
}

// Process executes agents sequentially
func (s *SequentialPattern) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	current := message

	for _, agent := range s.agents {
		// Hook: before agent
		if s.beforeAgent != nil {
			s.beforeAgent(agent, current)
		}

		// Process
		result, err := agent.Process(ctx, current)
		if err != nil {
			return nil, err
		}
		current = result

		// Hook: after agent
		if s.afterAgent != nil {
			s.afterAgent(agent, current)
		}
	}

	return current, nil
}

// Unwrap returns the underlying agents list
func (s *SequentialPattern) Unwrap() []agenkit.Agent {
	agents := make([]agenkit.Agent, len(s.agents))
	copy(agents, s.agents)
	return agents
}

// ParallelPattern executes agents in parallel and aggregates results.
//
// All agents receive the same input, execute concurrently, results are combined.
//
// Performance characteristics:
//   - True parallelism (uses goroutines)
//   - Bounded by slowest agent
//   - Memory: O(n) where n = number of agents
//
// Example:
//
//	aggregator := func(messages []agenkit.Message) agenkit.Message {
//	    // Combine results
//	    return agenkit.Message{Role: "assistant", Content: combined}
//	}
//	parallel := NewParallelPattern([]agenkit.Agent{agent1, agent2}, aggregator, nil)
//	result, err := parallel.Process(ctx, message)
type ParallelPattern struct {
	agents      []agenkit.Agent
	aggregator  Aggregator
	name        string
	beforeAgent AgentHook
	afterAgent  AgentHook
}

// ParallelPatternConfig configures a parallel pattern
type ParallelPatternConfig struct {
	Name        string
	BeforeAgent AgentHook
	AfterAgent  AgentHook
}

// NewParallelPattern creates a new parallel execution pattern
func NewParallelPattern(agents []agenkit.Agent, aggregator Aggregator, config *ParallelPatternConfig) (*ParallelPattern, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("parallel pattern requires at least one agent")
	}

	if aggregator == nil {
		return nil, fmt.Errorf("parallel pattern requires an aggregator function")
	}

	name := "parallel"
	var beforeAgent, afterAgent AgentHook

	if config != nil {
		if config.Name != "" {
			name = config.Name
		}
		beforeAgent = config.BeforeAgent
		afterAgent = config.AfterAgent
	}

	return &ParallelPattern{
		agents:      agents,
		aggregator:  aggregator,
		name:        name,
		beforeAgent: beforeAgent,
		afterAgent:  afterAgent,
	}, nil
}

// Name returns the pattern name
func (p *ParallelPattern) Name() string {
	return p.name
}

// Capabilities returns combined capabilities of all agents
func (p *ParallelPattern) Capabilities() []string {
	capsMap := make(map[string]struct{})
	for _, agent := range p.agents {
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

// Introspect returns introspection information about the pattern
func (p *ParallelPattern) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    p.Name(),
		Capabilities: p.Capabilities(),
	}
}

// Process executes agents in parallel and aggregates results
func (p *ParallelPattern) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Create channels for results and errors
	results := make([]*agenkit.Message, len(p.agents))
	errors := make([]error, len(p.agents))
	var wg sync.WaitGroup

	// Execute all agents in parallel
	for i, agent := range p.agents {
		wg.Add(1)
		go func(index int, ag agenkit.Agent) {
			defer wg.Done()

			// Hook: before agent
			if p.beforeAgent != nil {
				p.beforeAgent(ag, message)
			}

			// Process
			result, err := ag.Process(ctx, message)
			if err != nil {
				errors[index] = err
				return
			}
			results[index] = result

			// Hook: after agent
			if p.afterAgent != nil {
				p.afterAgent(ag, result)
			}
		}(i, agent)
	}

	// Wait for all agents to complete
	wg.Wait()

	// Check for errors
	for i, err := range errors {
		if err != nil {
			return nil, fmt.Errorf("agent %d failed: %w", i, err)
		}
	}

	// Aggregate results
	return p.aggregator(results), nil
}

// Unwrap returns the underlying agents list
func (p *ParallelPattern) Unwrap() []agenkit.Agent {
	agents := make([]agenkit.Agent, len(p.agents))
	copy(agents, p.agents)
	return agents
}

// RouterPattern routes messages to one agent based on a routing function.
//
// The router function examines the message and returns a key to select which agent handles it.
//
// Performance characteristics:
//   - O(1) routing decision
//   - Only one agent executes per request
//   - No overhead vs calling agents directly
//
// Example:
//
//	router := func(msg agenkit.Message) string {
//	    if strings.Contains(msg.Content, "code") {
//	        return "code_agent"
//	    }
//	    return "general_agent"
//	}
//	handlers := map[string]agenkit.Agent{
//	    "code_agent": codeAgent,
//	    "general_agent": generalAgent,
//	}
//	routerPattern := NewRouterPattern(router, handlers, nil)
//	result, err := routerPattern.Process(ctx, message)
type RouterPattern struct {
	router         Router
	handlers       map[string]agenkit.Agent
	defaultHandler agenkit.Agent
	name           string
}

// RouterPatternConfig configures a router pattern
type RouterPatternConfig struct {
	Name           string
	DefaultHandler agenkit.Agent
}

// NewRouterPattern creates a new router pattern
func NewRouterPattern(router Router, handlers map[string]agenkit.Agent, config *RouterPatternConfig) (*RouterPattern, error) {
	if router == nil {
		return nil, fmt.Errorf("router pattern requires a router function")
	}

	if len(handlers) == 0 {
		return nil, fmt.Errorf("router pattern requires at least one handler")
	}

	name := "router"
	var defaultHandler agenkit.Agent

	if config != nil {
		if config.Name != "" {
			name = config.Name
		}
		defaultHandler = config.DefaultHandler
	}

	return &RouterPattern{
		router:         router,
		handlers:       handlers,
		defaultHandler: defaultHandler,
		name:           name,
	}, nil
}

// Name returns the pattern name
func (r *RouterPattern) Name() string {
	return r.name
}

// Capabilities returns combined capabilities of all handlers
func (r *RouterPattern) Capabilities() []string {
	capsMap := make(map[string]struct{})
	for _, handler := range r.handlers {
		for _, cap := range handler.Capabilities() {
			capsMap[cap] = struct{}{}
		}
	}
	if r.defaultHandler != nil {
		for _, cap := range r.defaultHandler.Capabilities() {
			capsMap[cap] = struct{}{}
		}
	}

	caps := make([]string, 0, len(capsMap))
	for cap := range capsMap {
		caps = append(caps, cap)
	}
	return caps
}

// Introspect returns introspection information about the pattern
func (r *RouterPattern) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    r.Name(),
		Capabilities: r.Capabilities(),
	}
}

// Process routes the message to the appropriate handler
func (r *RouterPattern) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Get handler key from router
	key := r.router(message)

	// Find handler
	handler, ok := r.handlers[key]
	if !ok {
		// Try default handler
		if r.defaultHandler != nil {
			return r.defaultHandler.Process(ctx, message)
		}
		return nil, fmt.Errorf("router returned unknown key '%s' and no default handler is configured", key)
	}

	// Process with selected handler
	return handler.Process(ctx, message)
}

// Unwrap returns the handlers map
func (r *RouterPattern) Unwrap() map[string]agenkit.Agent {
	handlers := make(map[string]agenkit.Agent, len(r.handlers))
	for k, v := range r.handlers {
		handlers[k] = v
	}
	return handlers
}
