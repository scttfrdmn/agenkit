// Package agenkit provides core interfaces and types for the agenkit framework.
package agenkit

import (
	"context"
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
func NewMessage(role, content string) *Message {
	return &Message{
		Role:      role,
		Content:   content,
		Metadata:  make(map[string]interface{}),
		Timestamp: time.Now().UTC(),
	}
}

// WithMetadata adds metadata to the message and returns the message for chaining.
func (m *Message) WithMetadata(key string, value interface{}) *Message {
	m.Metadata[key] = value
	return m
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
