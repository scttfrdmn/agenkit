// Package tools provides tool calling capabilities for agents.
package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/agenkit/agenkit-go/agenkit"
)

// ToolRegistry manages available tools for an agent.
type ToolRegistry struct {
	tools map[string]agenkit.Tool
}

// NewToolRegistry creates a new tool registry.
func NewToolRegistry() *ToolRegistry {
	return &ToolRegistry{
		tools: make(map[string]agenkit.Tool),
	}
}

// Register adds a tool to the registry.
func (r *ToolRegistry) Register(tool agenkit.Tool) error {
	if tool == nil {
		return fmt.Errorf("tool cannot be nil")
	}
	if tool.Name() == "" {
		return fmt.Errorf("tool name cannot be empty")
	}
	if _, exists := r.tools[tool.Name()]; exists {
		return fmt.Errorf("tool '%s' is already registered", tool.Name())
	}
	r.tools[tool.Name()] = tool
	return nil
}

// Get retrieves a tool by name.
func (r *ToolRegistry) Get(name string) (agenkit.Tool, bool) {
	tool, exists := r.tools[name]
	return tool, exists
}

// List returns all registered tool names.
func (r *ToolRegistry) List() []string {
	names := make([]string, 0, len(r.tools))
	for name := range r.tools {
		names = append(names, name)
	}
	return names
}

// GetToolDescriptions returns a formatted description of all available tools.
func (r *ToolRegistry) GetToolDescriptions() string {
	if len(r.tools) == 0 {
		return "No tools available."
	}

	var sb strings.Builder
	sb.WriteString("Available tools:\n")
	for _, name := range r.List() {
		tool := r.tools[name]
		sb.WriteString(fmt.Sprintf("- %s: %s\n", name, tool.Description()))
	}
	return sb.String()
}

// ToolCall represents a request to execute a tool.
type ToolCall struct {
	ToolName   string                 `json:"tool_name"`
	Parameters map[string]interface{} `json:"parameters"`
}

// ToolAgent wraps an agent with tool calling capabilities.
type ToolAgent struct {
	agent    agenkit.Agent
	registry *ToolRegistry
}

// Verify that ToolAgent implements Agent interface.
var _ agenkit.Agent = (*ToolAgent)(nil)

// NewToolAgent creates a new tool-enabled agent.
func NewToolAgent(agent agenkit.Agent, registry *ToolRegistry) *ToolAgent {
	return &ToolAgent{
		agent:    agent,
		registry: registry,
	}
}

// Name returns the name of the underlying agent.
func (t *ToolAgent) Name() string {
	return t.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent plus tool support.
func (t *ToolAgent) Capabilities() []string {
	caps := t.agent.Capabilities()
	return append(caps, "tool_calling")
}

// Process handles a message with tool calling support.
// If the message contains tool calls in metadata, it executes them and returns results.
// Otherwise, it passes the message to the underlying agent.
func (t *ToolAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Check if message contains tool calls
	toolCallsData, hasToolCalls := message.Metadata["tool_calls"]
	if !hasToolCalls {
		// No tool calls - pass through to underlying agent
		return t.agent.Process(ctx, message)
	}

	// Parse tool calls
	toolCalls, err := t.parseToolCalls(toolCallsData)
	if err != nil {
		return nil, fmt.Errorf("failed to parse tool calls: %w", err)
	}

	// Execute tool calls
	results := make([]*agenkit.ToolResult, len(toolCalls))
	for i, call := range toolCalls {
		result, err := t.executeTool(ctx, call)
		if err != nil {
			results[i] = agenkit.NewToolError(err.Error())
		} else {
			results[i] = result
		}
	}

	// Create response with tool results
	response := agenkit.NewMessage("agent", t.formatToolResults(results))
	response.Metadata["tool_results"] = results
	return response, nil
}

// parseToolCalls converts metadata to ToolCall structures.
func (t *ToolAgent) parseToolCalls(data interface{}) ([]*ToolCall, error) {
	// Convert to JSON and back for type safety
	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal tool calls: %w", err)
	}

	var calls []*ToolCall
	if err := json.Unmarshal(jsonData, &calls); err != nil {
		return nil, fmt.Errorf("failed to unmarshal tool calls: %w", err)
	}

	return calls, nil
}

// executeTool executes a single tool call.
func (t *ToolAgent) executeTool(ctx context.Context, call *ToolCall) (*agenkit.ToolResult, error) {
	tool, exists := t.registry.Get(call.ToolName)
	if !exists {
		return nil, fmt.Errorf("tool '%s' not found", call.ToolName)
	}

	return tool.Execute(ctx, call.Parameters)
}

// formatToolResults formats tool results into a readable message.
func (t *ToolAgent) formatToolResults(results []*agenkit.ToolResult) string {
	var sb strings.Builder
	sb.WriteString("Tool execution results:\n")
	for i, result := range results {
		if result.Success {
			sb.WriteString(fmt.Sprintf("%d. Success: %v\n", i+1, result.Data))
		} else {
			sb.WriteString(fmt.Sprintf("%d. Error: %s\n", i+1, result.Error))
		}
	}
	return sb.String()
}

// GetRegistry returns the tool registry for this agent.
func (t *ToolAgent) GetRegistry() *ToolRegistry {
	return t.registry
}
