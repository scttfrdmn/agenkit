package tools

import (
	"context"
	"errors"
	"testing"

	"github.com/agenkit/agenkit-go/agenkit"
)

// MockTool is a test tool that returns predefined results.
type MockTool struct {
	name        string
	description string
	result      *agenkit.ToolResult
	err         error
	callCount   int
	lastParams  map[string]interface{}
}

func (m *MockTool) Name() string {
	return m.name
}

func (m *MockTool) Description() string {
	return m.description
}

func (m *MockTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	m.callCount++
	m.lastParams = params
	if m.err != nil {
		return nil, m.err
	}
	return m.result, nil
}

// MockAgent is a test agent that echoes messages.
type MockAgent struct {
	processFunc func(context.Context, *agenkit.Message) (*agenkit.Message, error)
}

func (m *MockAgent) Name() string {
	return "mock-agent"
}

func (m *MockAgent) Capabilities() []string {
	return []string{"test"}
}

func (m *MockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.processFunc != nil {
		return m.processFunc(ctx, message)
	}
	return agenkit.NewMessage("agent", "echo: "+message.Content), nil
}

func TestToolRegistryRegister(t *testing.T) {
	registry := NewToolRegistry()

	tool := &MockTool{name: "test-tool", description: "Test tool"}
	err := registry.Register(tool)
	if err != nil {
		t.Fatalf("Failed to register tool: %v", err)
	}

	// Verify tool is registered
	retrieved, exists := registry.Get("test-tool")
	if !exists {
		t.Fatal("Tool not found in registry")
	}
	if retrieved.Name() != "test-tool" {
		t.Errorf("Expected tool name 'test-tool', got '%s'", retrieved.Name())
	}
}

func TestToolRegistryRegisterDuplicate(t *testing.T) {
	registry := NewToolRegistry()

	tool1 := &MockTool{name: "tool", description: "Tool 1"}
	tool2 := &MockTool{name: "tool", description: "Tool 2"}

	registry.Register(tool1)
	err := registry.Register(tool2)
	if err == nil {
		t.Fatal("Expected error when registering duplicate tool")
	}
}

func TestToolRegistryRegisterNil(t *testing.T) {
	registry := NewToolRegistry()

	err := registry.Register(nil)
	if err == nil {
		t.Fatal("Expected error when registering nil tool")
	}
}

func TestToolRegistryRegisterEmptyName(t *testing.T) {
	registry := NewToolRegistry()

	tool := &MockTool{name: "", description: "No name"}
	err := registry.Register(tool)
	if err == nil {
		t.Fatal("Expected error when registering tool with empty name")
	}
}

func TestToolRegistryGet(t *testing.T) {
	registry := NewToolRegistry()

	tool := &MockTool{name: "test-tool", description: "Test tool"}
	registry.Register(tool)

	// Get existing tool
	retrieved, exists := registry.Get("test-tool")
	if !exists {
		t.Fatal("Tool should exist")
	}
	if retrieved.Name() != "test-tool" {
		t.Errorf("Expected name 'test-tool', got '%s'", retrieved.Name())
	}

	// Get non-existing tool
	_, exists = registry.Get("non-existent")
	if exists {
		t.Fatal("Non-existent tool should not exist")
	}
}

func TestToolRegistryList(t *testing.T) {
	registry := NewToolRegistry()

	// Empty registry
	names := registry.List()
	if len(names) != 0 {
		t.Errorf("Expected 0 tools, got %d", len(names))
	}

	// Add tools
	registry.Register(&MockTool{name: "tool1", description: "Tool 1"})
	registry.Register(&MockTool{name: "tool2", description: "Tool 2"})
	registry.Register(&MockTool{name: "tool3", description: "Tool 3"})

	names = registry.List()
	if len(names) != 3 {
		t.Errorf("Expected 3 tools, got %d", len(names))
	}

	// Verify all tool names are present
	nameSet := make(map[string]bool)
	for _, name := range names {
		nameSet[name] = true
	}
	for _, expected := range []string{"tool1", "tool2", "tool3"} {
		if !nameSet[expected] {
			t.Errorf("Expected tool '%s' in list", expected)
		}
	}
}

func TestToolRegistryGetToolDescriptions(t *testing.T) {
	registry := NewToolRegistry()

	// Empty registry
	desc := registry.GetToolDescriptions()
	if desc != "No tools available." {
		t.Errorf("Unexpected description for empty registry: %s", desc)
	}

	// Add tools
	registry.Register(&MockTool{name: "tool1", description: "Does thing 1"})
	registry.Register(&MockTool{name: "tool2", description: "Does thing 2"})

	desc = registry.GetToolDescriptions()
	if desc == "No tools available." {
		t.Error("Expected tool descriptions, got empty message")
	}
}

func TestToolAgentPassthrough(t *testing.T) {
	ctx := context.Background()

	agent := &MockAgent{}
	registry := NewToolRegistry()
	toolAgent := NewToolAgent(agent, registry)

	// Send message without tool calls - should pass through
	msg := agenkit.NewMessage("user", "hello")
	response, err := toolAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if response.Content != "echo: hello" {
		t.Errorf("Expected 'echo: hello', got '%s'", response.Content)
	}
}

func TestToolAgentExecuteTool(t *testing.T) {
	ctx := context.Background()

	agent := &MockAgent{}
	registry := NewToolRegistry()

	// Register a calculator tool
	calcTool := &MockTool{
		name:        "calculator",
		description: "Performs calculations",
		result:      agenkit.NewToolResult(42),
	}
	registry.Register(calcTool)

	toolAgent := NewToolAgent(agent, registry)

	// Create message with tool call
	msg := agenkit.NewMessage("user", "calculate 20+22")
	msg.Metadata["tool_calls"] = []map[string]interface{}{
		{
			"tool_name":  "calculator",
			"parameters": map[string]interface{}{"expression": "20+22"},
		},
	}

	response, err := toolAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify tool was called
	if calcTool.callCount != 1 {
		t.Errorf("Expected tool to be called once, got %d calls", calcTool.callCount)
	}

	// Verify response contains tool results
	toolResults, ok := response.Metadata["tool_results"]
	if !ok {
		t.Fatal("Expected tool_results in response metadata")
	}

	results := toolResults.([]*agenkit.ToolResult)
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if !results[0].Success {
		t.Error("Expected successful result")
	}
	if results[0].Data != 42 {
		t.Errorf("Expected result data 42, got %v", results[0].Data)
	}
}

func TestToolAgentExecuteMultipleTools(t *testing.T) {
	ctx := context.Background()

	agent := &MockAgent{}
	registry := NewToolRegistry()

	// Register multiple tools
	tool1 := &MockTool{name: "tool1", result: agenkit.NewToolResult("result1")}
	tool2 := &MockTool{name: "tool2", result: agenkit.NewToolResult("result2")}
	registry.Register(tool1)
	registry.Register(tool2)

	toolAgent := NewToolAgent(agent, registry)

	// Create message with multiple tool calls
	msg := agenkit.NewMessage("user", "use tools")
	msg.Metadata["tool_calls"] = []map[string]interface{}{
		{"tool_name": "tool1", "parameters": map[string]interface{}{"param": "value1"}},
		{"tool_name": "tool2", "parameters": map[string]interface{}{"param": "value2"}},
	}

	response, err := toolAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify both tools were called
	if tool1.callCount != 1 {
		t.Errorf("Expected tool1 to be called once, got %d calls", tool1.callCount)
	}
	if tool2.callCount != 1 {
		t.Errorf("Expected tool2 to be called once, got %d calls", tool2.callCount)
	}

	// Verify results
	results := response.Metadata["tool_results"].([]*agenkit.ToolResult)
	if len(results) != 2 {
		t.Fatalf("Expected 2 results, got %d", len(results))
	}
	if results[0].Data != "result1" {
		t.Errorf("Expected result1, got %v", results[0].Data)
	}
	if results[1].Data != "result2" {
		t.Errorf("Expected result2, got %v", results[1].Data)
	}
}

func TestToolAgentToolNotFound(t *testing.T) {
	ctx := context.Background()

	agent := &MockAgent{}
	registry := NewToolRegistry()
	toolAgent := NewToolAgent(agent, registry)

	// Create message with non-existent tool call
	msg := agenkit.NewMessage("user", "use non-existent tool")
	msg.Metadata["tool_calls"] = []map[string]interface{}{
		{"tool_name": "non-existent", "parameters": map[string]interface{}{}},
	}

	response, err := toolAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify error result
	results := response.Metadata["tool_results"].([]*agenkit.ToolResult)
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Success {
		t.Error("Expected failed result for non-existent tool")
	}
	if results[0].Error == "" {
		t.Error("Expected error message for non-existent tool")
	}
}

func TestToolAgentToolExecutionError(t *testing.T) {
	ctx := context.Background()

	agent := &MockAgent{}
	registry := NewToolRegistry()

	// Register tool that returns error
	errorTool := &MockTool{
		name: "error-tool",
		err:  errors.New("tool execution failed"),
	}
	registry.Register(errorTool)

	toolAgent := NewToolAgent(agent, registry)

	// Create message with tool call
	msg := agenkit.NewMessage("user", "use error tool")
	msg.Metadata["tool_calls"] = []map[string]interface{}{
		{"tool_name": "error-tool", "parameters": map[string]interface{}{}},
	}

	response, err := toolAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify error result
	results := response.Metadata["tool_results"].([]*agenkit.ToolResult)
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Success {
		t.Error("Expected failed result for error tool")
	}
	if results[0].Error == "" {
		t.Error("Expected error message")
	}
}

func TestToolAgentInvalidToolCallsFormat(t *testing.T) {
	ctx := context.Background()

	agent := &MockAgent{}
	registry := NewToolRegistry()
	toolAgent := NewToolAgent(agent, registry)

	// Create message with invalid tool calls format
	msg := agenkit.NewMessage("user", "invalid format")
	msg.Metadata["tool_calls"] = "not an array"

	_, err := toolAgent.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected error for invalid tool calls format")
	}
}

func TestToolAgentName(t *testing.T) {
	agent := &MockAgent{}
	registry := NewToolRegistry()
	toolAgent := NewToolAgent(agent, registry)

	if toolAgent.Name() != "mock-agent" {
		t.Errorf("Expected name 'mock-agent', got '%s'", toolAgent.Name())
	}
}

func TestToolAgentCapabilities(t *testing.T) {
	agent := &MockAgent{}
	registry := NewToolRegistry()
	toolAgent := NewToolAgent(agent, registry)

	caps := toolAgent.Capabilities()

	// Should include underlying agent capabilities plus tool_calling
	found := false
	for _, cap := range caps {
		if cap == "tool_calling" {
			found = true
			break
		}
	}
	if !found {
		t.Error("Expected 'tool_calling' in capabilities")
	}
}

func TestToolAgentGetRegistry(t *testing.T) {
	agent := &MockAgent{}
	registry := NewToolRegistry()
	toolAgent := NewToolAgent(agent, registry)

	retrieved := toolAgent.GetRegistry()
	if retrieved != registry {
		t.Error("GetRegistry should return the same registry instance")
	}
}

func TestToolAgentImplementsInterface(t *testing.T) {
	agent := &MockAgent{}
	registry := NewToolRegistry()
	toolAgent := NewToolAgent(agent, registry)

	// Verify it implements Agent interface
	var _ agenkit.Agent = toolAgent
}
