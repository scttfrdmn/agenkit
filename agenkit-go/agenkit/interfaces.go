// Package agenkit provides core interfaces and types for the agenkit framework.
package agenkit

import (
	"context"
	"fmt"
	"time"
)

// Message represents a message exchanged between agents or tools.
type Message struct {
	Role      string                 `json:"role"`
	Content   string                 `json:"content"`
	Metadata  map[string]interface{} `json:"metadata"`
	Timestamp time.Time              `json:"timestamp"`
}

// NewMessage creates a new message with the given role and content.
// NOTE: This function does not validate the message. For production code,
// consider using NewValidatedMessage or calling Validate() explicitly.
func NewMessage(role, content string) *Message {
	return &Message{
		Role:      role,
		Content:   content,
		Metadata:  make(map[string]interface{}),
		Timestamp: time.Now().UTC(),
	}
}

// NewValidatedMessage creates a new message with automatic validation.
// This ensures the message meets security constraints before creation.
// Returns an error if the message is invalid.
func NewValidatedMessage(role, content string) (*Message, error) {
	m := NewMessage(role, content)
	if err := m.Validate(); err != nil {
		return nil, err
	}
	return m, nil
}

// WithMetadata adds metadata to the message and returns the message for chaining.
func (m *Message) WithMetadata(key string, value interface{}) *Message {
	m.Metadata[key] = value
	return m
}

// Validate validates the message according to security constraints.
func (m *Message) Validate() error {
	// Role validation
	if m.Role == "" {
		return fmt.Errorf("message role cannot be empty")
	}
	if len(m.Role) > 20 {
		return fmt.Errorf("message role exceeds maximum length of 20 characters (got %d)", len(m.Role))
	}

	// Validate role is one of the allowed values
	allowedRoles := map[string]bool{
		"user":      true,
		"assistant": true,
		"system":    true,
		"tool":      true,
		"agent":     true,
	}
	if !allowedRoles[m.Role] {
		return fmt.Errorf("invalid message role: %s. Must be one of: user, assistant, system, tool, agent", m.Role)
	}

	// Content validation - max 1MB
	contentSize := len(m.Content)
	maxContentSize := 1024 * 1024 // 1MB
	if contentSize > maxContentSize {
		return fmt.Errorf("message content exceeds maximum size of %d bytes (got %d bytes)", maxContentSize, contentSize)
	}

	// Metadata validation
	if m.Metadata != nil {
		// Max 100 keys
		if len(m.Metadata) > 100 {
			return fmt.Errorf("message metadata exceeds maximum of 100 keys (got %d)", len(m.Metadata))
		}

		// Validate each key and value
		maxKeyLength := 50
		maxValueSize := 10 * 1024 // 10KB

		for key, value := range m.Metadata {
			// Key length validation
			if len(key) > maxKeyLength {
				return fmt.Errorf("metadata key '%s...' exceeds maximum length of %d characters (got %d)",
					key[:min(20, len(key))], maxKeyLength, len(key))
			}

			// Value size validation
			valueStr := fmt.Sprintf("%v", value)
			valueSize := len(valueStr)
			if valueSize > maxValueSize {
				return fmt.Errorf("metadata value for key '%s' exceeds maximum size of %d bytes (got %d bytes)",
					key, maxValueSize, valueSize)
			}
		}
	}

	return nil
}

// min returns the minimum of two integers.
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// ToolResult represents the result of a tool execution.
type ToolResult struct {
	Success  bool                   `json:"success"`
	Data     interface{}            `json:"data,omitempty"`
	Error    string                 `json:"error,omitempty"`
	Metadata map[string]interface{} `json:"metadata"`
}

// NewToolResult creates a successful tool result.
func NewToolResult(data interface{}) *ToolResult {
	return &ToolResult{
		Success:  true,
		Data:     data,
		Metadata: make(map[string]interface{}),
	}
}

// NewToolError creates a tool result representing an error.
func NewToolError(err string) *ToolResult {
	return &ToolResult{
		Success:  false,
		Error:    err,
		Metadata: make(map[string]interface{}),
	}
}

// WithMetadata adds metadata to the tool result and returns it for chaining.
func (t *ToolResult) WithMetadata(key string, value interface{}) *ToolResult {
	t.Metadata[key] = value
	return t
}

// Agent is the core interface that all agents must implement.
// Agents process messages and optionally support streaming responses.
type Agent interface {
	// Name returns the unique identifier for this agent.
	Name() string

	// Process handles a message and returns a response.
	// This is the primary method for synchronous request-response interactions.
	Process(ctx context.Context, message *Message) (*Message, error)

	// Capabilities returns a list of capability identifiers this agent supports.
	// This is optional and can return an empty slice.
	Capabilities() []string

	// Introspect examines the agent's internal state, memory, and capabilities.
	//
	// This is introspection (examining "what I know"), not reflection
	// (analyzing "how I did"). Returns a snapshot of current internal state.
	//
	// Introspection is useful for:
	// - Debugging: Examine agent state during development
	// - Monitoring: Track agent state in production
	// - Coordination: Agents can inspect each other's capabilities
	// - Testing: Verify agent state in tests
	// - Explainability: Understand what an agent "knows"
	//
	// Default implementation can use DefaultIntrospectionResult helper:
	//
	//     func (a *MyAgent) Introspect() *IntrospectionResult {
	//         return DefaultIntrospectionResult(a)
	//     }
	//
	// Agents with memory or internal state should create custom results:
	//
	//     func (a *MyAgent) Introspect() *IntrospectionResult {
	//         result, _ := NewIntrospectionResult(
	//             a.Name(),
	//             a.Capabilities(),
	//             map[string]interface{}{
	//                 "short_term_count": len(a.memory.shortTerm),
	//                 "long_term_count": len(a.memory.longTerm),
	//             },
	//             map[string]interface{}{
	//                 "message_count": a.messageCount,
	//                 "has_memory": true,
	//             },
	//             nil,
	//         )
	//         return result
	//     }
	Introspect() *IntrospectionResult
}

// StreamingAgent extends Agent to support streaming responses.
// Agents that need to provide incremental responses (e.g., LLMs, long-running operations)
// should implement this interface.
type StreamingAgent interface {
	Agent

	// Stream handles a message and streams responses incrementally.
	// The returned channel will be closed when streaming is complete.
	// If an error occurs, it should be sent through the error channel and streaming should stop.
	Stream(ctx context.Context, message *Message) (<-chan *Message, <-chan error)
}

// Tool represents an executable capability that agents can use.
type Tool interface {
	// Name returns the unique identifier for this tool.
	Name() string

	// Description returns a human-readable description of what this tool does.
	Description() string

	// Execute runs the tool with the given parameters and returns a result.
	Execute(ctx context.Context, params map[string]interface{}) (*ToolResult, error)
}
