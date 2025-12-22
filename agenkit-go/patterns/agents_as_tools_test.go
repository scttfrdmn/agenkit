package patterns

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestNewAgentTool tests AgentTool creation
func TestNewAgentTool(t *testing.T) {
	tests := []struct {
		name        string
		config      AgentToolConfig
		expectError bool
		errorMsg    string
	}{
		{
			name: "valid configuration",
			config: AgentToolConfig{
				Agent:        NewMockAgent("test", []string{"response"}),
				Name:         "test_tool",
				Description:  "A test tool",
				InputKey:     "query",
				OutputFormat: OutputFormatString,
			},
			expectError: false,
		},
		{
			name: "nil agent",
			config: AgentToolConfig{
				Name:        "test_tool",
				Description: "A test tool",
			},
			expectError: true,
			errorMsg:    "agent cannot be nil",
		},
		{
			name: "empty name",
			config: AgentToolConfig{
				Agent:       NewMockAgent("test", []string{"response"}),
				Name:        "",
				Description: "A test tool",
			},
			expectError: true,
			errorMsg:    "tool name cannot be empty",
		},
		{
			name: "empty description",
			config: AgentToolConfig{
				Agent:       NewMockAgent("test", []string{"response"}),
				Name:        "test_tool",
				Description: "",
			},
			expectError: true,
			errorMsg:    "tool description cannot be empty",
		},
		{
			name: "default input key",
			config: AgentToolConfig{
				Agent:       NewMockAgent("test", []string{"response"}),
				Name:        "test_tool",
				Description: "A test tool",
				// InputKey not specified - should default to "query"
			},
			expectError: false,
		},
		{
			name: "default output format",
			config: AgentToolConfig{
				Agent:       NewMockAgent("test", []string{"response"}),
				Name:        "test_tool",
				Description: "A test tool",
				// OutputFormat not specified - should default to OutputFormatString
			},
			expectError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tool, err := NewAgentTool(tt.config)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error but got none")
				} else if !strings.Contains(err.Error(), tt.errorMsg) {
					t.Errorf("expected error containing %q, got %q", tt.errorMsg, err.Error())
				}
			} else {
				if err != nil {
					t.Errorf("unexpected error: %v", err)
				}
				if tool == nil {
					t.Errorf("expected tool but got nil")
				}

				// Verify defaults
				if tt.config.InputKey == "" && tool.GetInputKey() != "query" {
					t.Errorf("expected default input key 'query', got %q", tool.GetInputKey())
				}
				if tt.config.OutputFormat == "" && tool.GetOutputFormat() != OutputFormatString {
					t.Errorf("expected default output format 'str', got %q", tool.GetOutputFormat())
				}
			}
		})
	}
}

// TestAgentToolName tests the Name method
func TestAgentToolName(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:       agent,
		Name:        "my_tool",
		Description: "Test description",
	})

	if tool.Name() != "my_tool" {
		t.Errorf("expected name 'my_tool', got %q", tool.Name())
	}
}

// TestAgentToolDescription tests the Description method
func TestAgentToolDescription(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:       agent,
		Name:        "my_tool",
		Description: "This is a test tool",
	})

	if tool.Description() != "This is a test tool" {
		t.Errorf("expected description 'This is a test tool', got %q", tool.Description())
	}
}

// TestAgentToolExecute tests basic execution
func TestAgentToolExecute(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"Hello from agent"})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:        agent,
		Name:         "test_tool",
		Description:  "Test tool",
		InputKey:     "query",
		OutputFormat: OutputFormatString,
	})

	ctx := context.Background()
	params := map[string]interface{}{
		"query": "Test input",
	}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !result.Success {
		t.Errorf("expected success=true, got %v", result.Success)
	}

	if result.Data != "Hello from agent" {
		t.Errorf("expected data 'Hello from agent', got %v", result.Data)
	}

	// Check metadata
	if result.Metadata["agent_name"] != "test_agent" {
		t.Errorf("expected agent_name metadata, got %v", result.Metadata["agent_name"])
	}
	if result.Metadata["tool_name"] != "test_tool" {
		t.Errorf("expected tool_name metadata, got %v", result.Metadata["tool_name"])
	}
}

// TestAgentToolExecuteMissingParameter tests handling of missing parameters
func TestAgentToolExecuteMissingParameter(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"response"})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:       agent,
		Name:        "test_tool",
		Description: "Test tool",
		InputKey:    "required_param",
	})

	ctx := context.Background()
	params := map[string]interface{}{
		"wrong_param": "value",
	}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Success {
		t.Errorf("expected success=false for missing parameter")
	}

	if !strings.Contains(result.Error, "Missing required parameter 'required_param'") {
		t.Errorf("expected error about missing parameter, got %q", result.Error)
	}
}

// TestAgentToolExecuteAgentError tests handling of agent errors
func TestAgentToolExecuteAgentError(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{})
	agent.processFunc = func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
		return nil, fmt.Errorf("agent processing failed")
	}

	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:       agent,
		Name:        "test_tool",
		Description: "Test tool",
	})

	ctx := context.Background()
	params := map[string]interface{}{
		"query": "test",
	}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Success {
		t.Errorf("expected success=false when agent fails")
	}

	if !strings.Contains(result.Error, "Agent 'test_agent' failed") {
		t.Errorf("expected error message about agent failure, got %q", result.Error)
	}
}

// TestAgentToolOutputFormatString tests string output format
func TestAgentToolOutputFormatString(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"test response"})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:        agent,
		Name:         "test_tool",
		Description:  "Test tool",
		OutputFormat: OutputFormatString,
	})

	ctx := context.Background()
	params := map[string]interface{}{"query": "test"}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should be string
	str, ok := result.Data.(string)
	if !ok {
		t.Errorf("expected string output, got %T", result.Data)
	}

	if str != "test response" {
		t.Errorf("expected 'test response', got %q", str)
	}
}

// TestAgentToolOutputFormatDict tests dict output format
func TestAgentToolOutputFormatDict(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"test response"})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:        agent,
		Name:         "test_tool",
		Description:  "Test tool",
		OutputFormat: OutputFormatDict,
	})

	ctx := context.Background()
	params := map[string]interface{}{"query": "test"}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should be map
	dict, ok := result.Data.(map[string]interface{})
	if !ok {
		t.Errorf("expected map output, got %T", result.Data)
	}

	if dict["content"] != "test response" {
		t.Errorf("expected content 'test response', got %v", dict["content"])
	}

	// Metadata should not be included by default
	if _, hasMetadata := dict["metadata"]; hasMetadata {
		t.Errorf("did not expect metadata in output")
	}
}

// TestAgentToolOutputFormatDictWithMetadata tests dict format with metadata
func TestAgentToolOutputFormatDictWithMetadata(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"test response"})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:           agent,
		Name:            "test_tool",
		Description:     "Test tool",
		OutputFormat:    OutputFormatDict,
		IncludeMetadata: true,
	})

	ctx := context.Background()
	params := map[string]interface{}{"query": "test"}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	dict, ok := result.Data.(map[string]interface{})
	if !ok {
		t.Errorf("expected map output, got %T", result.Data)
	}

	// Metadata should be included
	if _, hasMetadata := dict["metadata"]; !hasMetadata {
		t.Errorf("expected metadata in output")
	}
}

// TestAgentToolOutputFormatMessage tests message output format
func TestAgentToolOutputFormatMessage(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"test response"})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:        agent,
		Name:         "test_tool",
		Description:  "Test tool",
		OutputFormat: OutputFormatMessage,
	})

	ctx := context.Background()
	params := map[string]interface{}{"query": "test"}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should be Message
	msg, ok := result.Data.(*agenkit.Message)
	if !ok {
		t.Errorf("expected *Message output, got %T", result.Data)
	}

	if msg.Content != "test response" {
		t.Errorf("expected content 'test response', got %q", msg.Content)
	}
}

// TestAgentToolCustomInputKey tests custom input key
func TestAgentToolCustomInputKey(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"response"})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:       agent,
		Name:        "test_tool",
		Description: "Test tool",
		InputKey:    "custom_input",
	})

	ctx := context.Background()
	params := map[string]interface{}{
		"custom_input": "test value",
	}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !result.Success {
		t.Errorf("expected success with custom input key")
	}
}

// TestAgentToolString tests String method
func TestAgentToolString(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:       agent,
		Name:        "my_tool",
		Description: "Test",
	})

	str := tool.String()
	expected := "AgentTool(name='my_tool', agent=test_agent)"

	if str != expected {
		t.Errorf("expected %q, got %q", expected, str)
	}
}

// TestAgentToolGetAgent tests GetAgent accessor
func TestAgentToolGetAgent(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{})
	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:       agent,
		Name:        "test_tool",
		Description: "Test",
	})

	retrieved := tool.GetAgent()
	if retrieved != agent {
		t.Errorf("GetAgent() returned different agent")
	}
}

// TestAgentAsTool tests the convenience function
func TestAgentAsTool(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"response"})

	tool, err := AgentAsTool(
		agent,
		"test_tool",
		"Test tool",
		"query",
		OutputFormatString,
		false,
	)

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if tool.Name() != "test_tool" {
		t.Errorf("expected name 'test_tool', got %q", tool.Name())
	}

	if tool.GetInputKey() != "query" {
		t.Errorf("expected input key 'query', got %q", tool.GetInputKey())
	}

	if tool.GetOutputFormat() != OutputFormatString {
		t.Errorf("expected output format 'str', got %q", tool.GetOutputFormat())
	}
}

// TestAgentAsToolSimple tests the simplified convenience function
func TestAgentAsToolSimple(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{"response"})

	tool, err := AgentAsToolSimple(agent, "test_tool", "Test tool")

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should use defaults
	if tool.GetInputKey() != "query" {
		t.Errorf("expected default input key 'query', got %q", tool.GetInputKey())
	}

	if tool.GetOutputFormat() != OutputFormatString {
		t.Errorf("expected default output format 'str', got %q", tool.GetOutputFormat())
	}
}

// TestAgentToolContextCancellation tests context cancellation handling
func TestAgentToolContextCancellation(t *testing.T) {
	agent := NewMockAgent("test_agent", []string{})
	agent.processFunc = func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
			return agenkit.NewMessage("assistant", "response"), nil
		}
	}

	tool, _ := NewAgentTool(AgentToolConfig{
		Agent:       agent,
		Name:        "test_tool",
		Description: "Test",
	})

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	params := map[string]interface{}{"query": "test"}

	result, err := tool.Execute(ctx, params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should capture cancellation as tool error
	if result.Success {
		t.Errorf("expected failure due to context cancellation")
	}
}

// TestAgentToolIntegration tests integration scenario
func TestAgentToolIntegration(t *testing.T) {
	// Create specialist agents
	codeAgent := NewMockAgent("code_specialist", []string{"def hello(): print('hello')"})
	mathAgent := NewMockAgent("math_specialist", []string{"42"})

	// Wrap as tools
	codeTool, _ := AgentAsToolSimple(codeAgent, "code_expert", "Expert in programming")
	mathTool, _ := AgentAsToolSimple(mathAgent, "math_expert", "Expert in mathematics")

	ctx := context.Background()

	// Use code tool
	codeResult, err := codeTool.Execute(ctx, map[string]interface{}{
		"query": "Write a hello function",
	})
	if err != nil {
		t.Fatalf("code tool error: %v", err)
	}

	if !codeResult.Success {
		t.Errorf("code tool should succeed")
	}

	if !strings.Contains(codeResult.Data.(string), "def hello()") {
		t.Errorf("expected code output, got %v", codeResult.Data)
	}

	// Use math tool
	mathResult, err := mathTool.Execute(ctx, map[string]interface{}{
		"query": "What is the answer?",
	})
	if err != nil {
		t.Fatalf("math tool error: %v", err)
	}

	if !mathResult.Success {
		t.Errorf("math tool should succeed")
	}

	if mathResult.Data != "42" {
		t.Errorf("expected '42', got %v", mathResult.Data)
	}
}
