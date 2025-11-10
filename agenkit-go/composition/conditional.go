package composition

import (
	"context"
	"fmt"

	"github.com/agenkit/agenkit-go/agenkit"
)

// Condition is a function that determines whether to use an agent.
type Condition func(message *agenkit.Message) bool

// ConditionalRoute represents a condition-agent pair.
type ConditionalRoute struct {
	Condition Condition
	Agent     agenkit.Agent
}

// ConditionalAgent routes messages to different agents based on conditions.
type ConditionalAgent struct {
	name          string
	routes        []ConditionalRoute
	defaultAgent  agenkit.Agent
}

// Verify that ConditionalAgent implements Agent interface.
var _ agenkit.Agent = (*ConditionalAgent)(nil)

// NewConditionalAgent creates a new conditional agent.
func NewConditionalAgent(name string, defaultAgent agenkit.Agent) *ConditionalAgent {
	return &ConditionalAgent{
		name:         name,
		routes:       make([]ConditionalRoute, 0),
		defaultAgent: defaultAgent,
	}
}

// AddRoute adds a conditional route.
func (c *ConditionalAgent) AddRoute(condition Condition, agent agenkit.Agent) {
	c.routes = append(c.routes, ConditionalRoute{
		Condition: condition,
		Agent:     agent,
	})
}

// Name returns the name of the conditional agent.
func (c *ConditionalAgent) Name() string {
	return c.name
}

// Capabilities returns combined capabilities of all agents.
func (c *ConditionalAgent) Capabilities() []string {
	capsSet := make(map[string]bool)

	// Add default agent capabilities
	if c.defaultAgent != nil {
		for _, cap := range c.defaultAgent.Capabilities() {
			capsSet[cap] = true
		}
	}

	// Add route agent capabilities
	for _, route := range c.routes {
		for _, cap := range route.Agent.Capabilities() {
			capsSet[cap] = true
		}
	}

	caps := make([]string, 0, len(capsSet))
	for cap := range capsSet {
		caps = append(caps, cap)
	}
	caps = append(caps, "conditional")
	return caps
}

// Process routes the message to the first agent whose condition is met.
func (c *ConditionalAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Check context cancellation
	select {
	case <-ctx.Done():
		return nil, fmt.Errorf("conditional routing cancelled: %w", ctx.Err())
	default:
	}

	// Try each route in order
	for i, route := range c.routes {
		if route.Condition(message) {
			result, err := route.Agent.Process(ctx, message)
			if err != nil {
				return nil, fmt.Errorf("route %d (%s) failed: %w", i+1, route.Agent.Name(), err)
			}

			// Add metadata about routing decision
			result.Metadata["conditional_agent_used"] = route.Agent.Name()
			result.Metadata["conditional_route"] = i + 1
			return result, nil
		}
	}

	// No condition matched, use default agent
	if c.defaultAgent == nil {
		return nil, fmt.Errorf("no condition matched and no default agent configured")
	}

	result, err := c.defaultAgent.Process(ctx, message)
	if err != nil {
		return nil, fmt.Errorf("default agent (%s) failed: %w", c.defaultAgent.Name(), err)
	}

	// Add metadata about using default
	result.Metadata["conditional_agent_used"] = c.defaultAgent.Name()
	result.Metadata["conditional_route"] = "default"
	return result, nil
}

// GetRoutes returns the conditional routes.
func (c *ConditionalAgent) GetRoutes() []ConditionalRoute {
	return c.routes
}

// GetDefaultAgent returns the default agent.
func (c *ConditionalAgent) GetDefaultAgent() agenkit.Agent {
	return c.defaultAgent
}

// Common condition helpers

// ContentContains returns a condition that checks if message content contains a substring.
func ContentContains(substr string) Condition {
	return func(message *agenkit.Message) bool {
		return len(message.Content) >= len(substr) && findSubstring(message.Content, substr)
	}
}

// RoleEquals returns a condition that checks if message role equals the given role.
func RoleEquals(role string) Condition {
	return func(message *agenkit.Message) bool {
		return message.Role == role
	}
}

// MetadataHasKey returns a condition that checks if metadata contains a key.
func MetadataHasKey(key string) Condition {
	return func(message *agenkit.Message) bool {
		_, exists := message.Metadata[key]
		return exists
	}
}

// MetadataEquals returns a condition that checks if metadata key equals value.
func MetadataEquals(key string, value interface{}) Condition {
	return func(message *agenkit.Message) bool {
		val, exists := message.Metadata[key]
		return exists && val == value
	}
}

// And combines multiple conditions with AND logic.
func And(conditions ...Condition) Condition {
	return func(message *agenkit.Message) bool {
		for _, cond := range conditions {
			if !cond(message) {
				return false
			}
		}
		return true
	}
}

// Or combines multiple conditions with OR logic.
func Or(conditions ...Condition) Condition {
	return func(message *agenkit.Message) bool {
		for _, cond := range conditions {
			if cond(message) {
				return true
			}
		}
		return false
	}
}

// Not negates a condition.
func Not(condition Condition) Condition {
	return func(message *agenkit.Message) bool {
		return !condition(message)
	}
}

// Helper function to find substring
func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
