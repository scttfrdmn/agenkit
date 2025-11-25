// Package patterns provides implementation of common agent patterns.
// The Agents-as-Tools pattern enables agents to call other agents as tools,
// creating hierarchical multi-agent systems where specialized agents can be
// invoked by supervisor agents.
package patterns

import (
	"context"
	"fmt"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// OutputFormat specifies how agent output should be formatted.
type OutputFormat string

const (
	// OutputFormatString returns just the message content as a string
	OutputFormatString OutputFormat = "str"
	// OutputFormatDict returns a map with content and optionally metadata
	OutputFormatDict OutputFormat = "dict"
	// OutputFormatMessage returns the full Message object
	OutputFormatMessage OutputFormat = "message"
)

// AgentTool wraps an agent as a tool, enabling hierarchical agent delegation.
//
// Allows agents to call other agents as tools, enabling hierarchical
// delegation and specialization. Compatible with existing tool infrastructure.
//
// Performance Characteristics:
//   - Latency: Same as underlying agent
//   - Enables hierarchical composition
//   - Maintains full observability (traces preserved)
//
// Example:
//
//	specialist := &CodeSpecialistAgent{}
//	tool := patterns.NewAgentTool(patterns.AgentToolConfig{
//	    Agent:       specialist,
//	    Name:        "code_specialist",
//	    Description: "Expert in Python programming and code review",
//	    InputKey:    "task",
//	    OutputFormat: patterns.OutputFormatString,
//	})
//
//	result, err := tool.Execute(ctx, map[string]interface{}{
//	    "task": "Write a function to reverse a string",
//	})
type AgentTool struct {
	agent           agenkit.Agent
	name            string
	description     string
	inputKey        string
	outputFormat    OutputFormat
	includeMetadata bool
}

// AgentToolConfig contains configuration for creating an AgentTool.
type AgentToolConfig struct {
	Agent           agenkit.Agent
	Name            string
	Description     string
	InputKey        string
	OutputFormat    OutputFormat
	IncludeMetadata bool
}

// NewAgentTool creates a new AgentTool with the given configuration.
//
// Args:
//   - agent: The agent to wrap as a tool
//   - name: Tool name for identification and routing
//   - description: Description for LLM to understand when to use this tool
//   - inputKey: Parameter name for input (default: "query")
//   - outputFormat: How to format agent output (default: "str")
//   - includeMetadata: Whether to include agent metadata in output (default: false)
//
// Returns:
//   - AgentTool instance or error if validation fails
func NewAgentTool(config AgentToolConfig) (*AgentTool, error) {
	// Validate configuration
	if config.Agent == nil {
		return nil, fmt.Errorf("agent cannot be nil")
	}
	if config.Name == "" {
		return nil, fmt.Errorf("tool name cannot be empty")
	}
	if config.Description == "" {
		return nil, fmt.Errorf("tool description cannot be empty")
	}

	// Set defaults
	if config.InputKey == "" {
		config.InputKey = "query"
	}
	if config.OutputFormat == "" {
		config.OutputFormat = OutputFormatString
	}

	return &AgentTool{
		agent:           config.Agent,
		name:            config.Name,
		description:     config.Description,
		inputKey:        config.InputKey,
		outputFormat:    config.OutputFormat,
		includeMetadata: config.IncludeMetadata,
	}, nil
}

// Name returns the tool's name.
func (t *AgentTool) Name() string {
	return t.name
}

// Description returns the tool's description.
func (t *AgentTool) Description() string {
	return t.description
}

// Execute executes the wrapped agent.
//
// Args:
//   - ctx: Context for cancellation and timeouts
//   - params: Parameters passed to the tool. Must include inputKey.
//
// Returns:
//   - ToolResult containing agent output, formatted according to outputFormat
func (t *AgentTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	// Extract input
	query, ok := params[t.inputKey]
	if !ok {
		availableKeys := make([]string, 0, len(params))
		for k := range params {
			availableKeys = append(availableKeys, k)
		}
		return agenkit.NewToolError(fmt.Sprintf(
			"Missing required parameter '%s'. Available parameters: %v",
			t.inputKey, availableKeys,
		)), nil
	}

	// Create message
	message := agenkit.NewMessage("user", fmt.Sprintf("%v", query))

	// Call agent
	response, err := t.agent.Process(ctx, message)
	if err != nil {
		return agenkit.NewToolError(fmt.Sprintf(
			"Agent '%s' failed: %v",
			t.agent.Name(), err,
		)), nil
	}

	// Format output
	output := t.formatOutput(response)

	// Create tool result
	result := agenkit.NewToolResult(output)
	result.WithMetadata("agent_name", t.agent.Name())
	result.WithMetadata("tool_name", t.name)

	return result, nil
}

// formatOutput formats the agent response based on outputFormat.
func (t *AgentTool) formatOutput(response *agenkit.Message) interface{} {
	switch t.outputFormat {
	case OutputFormatString:
		return response.Content

	case OutputFormatDict:
		result := map[string]interface{}{
			"content": response.Content,
		}
		if t.includeMetadata {
			result["metadata"] = response.Metadata
		}
		return result

	case OutputFormatMessage:
		return response

	default:
		// Default to string content
		return response.Content
	}
}

// String returns a string representation of the AgentTool.
func (t *AgentTool) String() string {
	return fmt.Sprintf("AgentTool(name='%s', agent=%s)", t.name, t.agent.Name())
}

// GetAgent returns the underlying agent (useful for testing/inspection).
func (t *AgentTool) GetAgent() agenkit.Agent {
	return t.agent
}

// GetInputKey returns the input parameter key.
func (t *AgentTool) GetInputKey() string {
	return t.inputKey
}

// GetOutputFormat returns the output format setting.
func (t *AgentTool) GetOutputFormat() OutputFormat {
	return t.outputFormat
}

// AgentAsTool is a convenience function to wrap an agent as a tool.
//
// This is the primary API for creating agent tools. Use this function
// rather than instantiating AgentTool directly.
//
// Args:
//   - agent: The agent to wrap
//   - name: Tool name (used for routing and identification)
//   - description: Tool description (helps LLM decide when to use)
//   - inputKey: Parameter name for input (default: "query")
//   - outputFormat: Output format - "str", "dict", or "message" (default: "str")
//   - includeMetadata: Include agent metadata in output (default: false)
//
// Returns:
//   - AgentTool instance ready to be registered
//
// Example:
//
//	// Create specialists
//	codeAgent := &CodeSpecialistAgent{}
//	mathAgent := &MathSpecialistAgent{}
//
//	// Wrap as tools
//	codeTool, _ := patterns.AgentAsTool(
//	    codeAgent,
//	    "code_expert",
//	    "Expert programmer for code-related tasks",
//	    "query",
//	    patterns.OutputFormatString,
//	    false,
//	)
//
//	mathTool, _ := patterns.AgentAsTool(
//	    mathAgent,
//	    "math_expert",
//	    "Expert mathematician for math problems",
//	    "query",
//	    patterns.OutputFormatString,
//	    false,
//	)
//
// Best Practices:
//  1. Clear Names: Use descriptive, unique names (e.g., "python_expert" not "agent1")
//  2. Good Descriptions: Help LLM understand when to use the tool
//  3. Specialist Focus: Each agent should have clear domain expertise
//  4. Error Handling: Specialist agents should handle their own errors gracefully
//  5. Observability: Use tracing to understand delegation patterns
//
// Performance:
//   - Latency: Supervisor + Specialist(s)
//   - Cost: N× calls (supervisor + each specialist invocation)
//   - Benefit: Specialization often improves quality despite higher cost
func AgentAsTool(
	agent agenkit.Agent,
	name string,
	description string,
	inputKey string,
	outputFormat OutputFormat,
	includeMetadata bool,
) (*AgentTool, error) {
	return NewAgentTool(AgentToolConfig{
		Agent:           agent,
		Name:            name,
		Description:     description,
		InputKey:        inputKey,
		OutputFormat:    outputFormat,
		IncludeMetadata: includeMetadata,
	})
}

// AgentAsToolSimple is a simplified version that uses default values.
//
// Uses:
//   - inputKey: "query"
//   - outputFormat: OutputFormatString
//   - includeMetadata: false
//
// Example:
//
//	specialist := &CodeSpecialistAgent{}
//	tool, err := patterns.AgentAsToolSimple(
//	    specialist,
//	    "code_expert",
//	    "Expert programmer for code-related tasks",
//	)
func AgentAsToolSimple(agent agenkit.Agent, name string, description string) (*AgentTool, error) {
	return AgentAsTool(agent, name, description, "query", OutputFormatString, false)
}
