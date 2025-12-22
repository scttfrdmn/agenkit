package patterns

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockReActAgent is a mock agent that returns predefined responses.
type mockReActAgent struct {
	name      string
	responses []string
	callCount int
}

func (m *mockReActAgent) Name() string {
	return m.name
}

func (m *mockReActAgent) Capabilities() []string {
	return []string{"test"}
}

func (m *mockReActAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *mockReActAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.callCount >= len(m.responses) {
		return nil, fmt.Errorf("no more mock responses available")
	}
	response := m.responses[m.callCount]
	m.callCount++
	return &agenkit.Message{
		Role:    "assistant",
		Content: response,
	}, nil
}

// mockTool is a mock tool for testing.
type mockTool struct {
	name        string
	description string
	response    string
	shouldFail  bool
	callCount   int
}

func (m *mockTool) Name() string {
	return m.name
}

func (m *mockTool) Description() string {
	return m.description
}

func (m *mockTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	m.callCount++

	if m.shouldFail {
		return nil, fmt.Errorf("tool execution failed")
	}

	return &agenkit.ToolResult{
		Data:    m.response,
		Success: true,
	}, nil
}

// ============================================================================
// Configuration Validation Tests
// ============================================================================

func TestReActAgent_NilConfig(t *testing.T) {
	_, err := NewReActAgent(nil)
	if err == nil {
		t.Error("expected error for nil config, got nil")
	}
}

func TestReActAgent_NilAgent(t *testing.T) {
	tool := &mockTool{name: "test", description: "Test tool", response: "result"}
	_, err := NewReActAgent(&ReActConfig{
		Agent: nil,
		Tools: []agenkit.Tool{tool},
	})
	if err == nil || !strings.Contains(err.Error(), "agent is required") {
		t.Errorf("expected 'agent is required' error, got %v", err)
	}
}

func TestReActAgent_EmptyTools(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{}}
	_, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{},
	})
	if err == nil || !strings.Contains(err.Error(), "at least one tool is required") {
		t.Errorf("expected 'at least one tool is required' error, got %v", err)
	}
}

func TestReActAgent_DefaultMaxSteps(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{"Final Answer: Done"}}
	tool := &mockTool{name: "test_tool", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if reactAgent.maxSteps != 10 {
		t.Errorf("expected default maxSteps 10, got %d", reactAgent.maxSteps)
	}
}

func TestReActAgent_CustomMaxSteps(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{"Final Answer: Done"}}
	tool := &mockTool{name: "test_tool", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent:    agent,
		Tools:    []agenkit.Tool{tool},
		MaxSteps: 5,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if reactAgent.maxSteps != 5 {
		t.Errorf("expected maxSteps 5, got %d", reactAgent.maxSteps)
	}
}

func TestReActAgent_DefaultVerbose(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{"Final Answer: Done"}}
	tool := &mockTool{name: "test_tool", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !reactAgent.verbose {
		t.Error("expected default verbose true, got false")
	}
}

func TestReActAgent_ExplicitVerbose(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{"Final Answer: Done"}}
	tool := &mockTool{name: "test_tool", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent:    agent,
		Tools:    []agenkit.Tool{tool},
		Verbose:  false,
		MaxSteps: 5,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if reactAgent.verbose {
		t.Error("expected verbose false, got true")
	}
}

// ============================================================================
// Basic ReAct Loop Tests
// ============================================================================

func TestReActAgent_SingleStepFinalAnswer(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: I can answer directly\nFinal Answer: The answer is 42",
		},
	}
	tool := &mockTool{name: "calculator", description: "Does math", response: "42"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "What is the answer?",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(result.Content, "The answer is 42") {
		t.Errorf("expected result to contain 'The answer is 42', got %s", result.Content)
	}
	if result.Metadata["stop_reason"] != string(StopReasonFinalAnswer) {
		t.Errorf("expected stop_reason final_answer, got %v", result.Metadata["stop_reason"])
	}
	if result.Metadata["steps"] != 1 {
		t.Errorf("expected 1 step, got %v", result.Metadata["steps"])
	}
}

func TestReActAgent_MultiStepReasoning(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: I need to search for information\nAction: search\nAction Input: weather",
			"Thought: I now have the answer\nFinal Answer: It is sunny",
		},
	}
	searchTool := &mockTool{name: "search", description: "Search for info", response: "The weather is sunny"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{searchTool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "What is the weather?",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(result.Content, "It is sunny") {
		t.Errorf("expected result to contain 'It is sunny', got %s", result.Content)
	}
	if result.Metadata["stop_reason"] != string(StopReasonFinalAnswer) {
		t.Errorf("expected stop_reason final_answer, got %v", result.Metadata["stop_reason"])
	}
	if result.Metadata["steps"] != 2 {
		t.Errorf("expected 2 steps, got %v", result.Metadata["steps"])
	}
}

func TestReActAgent_MultipleToolCalls(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: First search\nAction: search\nAction Input: population",
			"Thought: Now calculate\nAction: calculator\nAction Input: 1000 * 2",
			"Thought: I have the answer\nFinal Answer: Population is 2000",
		},
	}
	searchTool := &mockTool{name: "search", description: "Search", response: "1000"}
	calcTool := &mockTool{name: "calculator", description: "Calculate", response: "2000"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{searchTool, calcTool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "What is the population?",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(result.Content, "Population is 2000") {
		t.Errorf("expected result to contain 'Population is 2000', got %s", result.Content)
	}
	if result.Metadata["steps"] != 3 {
		t.Errorf("expected 3 steps, got %v", result.Metadata["steps"])
	}
	if searchTool.callCount != 1 {
		t.Errorf("expected search tool called 1 time, got %d", searchTool.callCount)
	}
	if calcTool.callCount != 1 {
		t.Errorf("expected calculator tool called 1 time, got %d", calcTool.callCount)
	}
}

// ============================================================================
// Error Handling Tests
// ============================================================================

func TestReActAgent_UnknownTool(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: Try unknown tool\nAction: unknown\nAction Input: test",
			"Thought: I'll answer anyway\nFinal Answer: Done",
		},
	}
	tool := &mockTool{name: "known", description: "Known tool", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Should continue and complete
	if result.Metadata["stop_reason"] != string(StopReasonFinalAnswer) {
		t.Errorf("expected stop_reason final_answer, got %v", result.Metadata["stop_reason"])
	}
	// Should have recorded the error observation
	steps := reactAgent.GetSteps()
	if len(steps) != 2 {
		t.Errorf("expected 2 steps, got %d", len(steps))
	}
	if !strings.Contains(steps[0].Observation, "not found") {
		t.Errorf("expected error observation, got %s", steps[0].Observation)
	}
}

func TestReActAgent_ToolExecutionFails(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: Use failing tool\nAction: failing\nAction Input: test",
		},
	}
	tool := &mockTool{name: "failing", description: "Fails", response: "", shouldFail: true}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Metadata["stop_reason"] != string(StopReasonToolError) {
		t.Errorf("expected stop_reason tool_error, got %v", result.Metadata["stop_reason"])
	}
	if !strings.Contains(result.Content, "Unable to complete task") {
		t.Errorf("expected error message in content, got %s", result.Content)
	}
}

func TestReActAgent_InvalidAction(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: I don't know what to do",
		},
	}
	tool := &mockTool{name: "test", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Metadata["stop_reason"] != string(StopReasonInvalidAction) {
		t.Errorf("expected stop_reason invalid_action, got %v", result.Metadata["stop_reason"])
	}
}

func TestReActAgent_MaxStepsReached(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: Step 1\nAction: search\nAction Input: test",
			"Thought: Step 2\nAction: search\nAction Input: test",
			"Thought: Step 3\nAction: search\nAction Input: test",
		},
	}
	tool := &mockTool{name: "search", description: "Search", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent:    agent,
		Tools:    []agenkit.Tool{tool},
		MaxSteps: 3,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Metadata["stop_reason"] != string(StopReasonMaxSteps) {
		t.Errorf("expected stop_reason max_steps, got %v", result.Metadata["stop_reason"])
	}
	if result.Metadata["steps"] != 3 {
		t.Errorf("expected 3 steps, got %v", result.Metadata["steps"])
	}
}

// ============================================================================
// Verbose Mode Tests
// ============================================================================

func TestReActAgent_VerboseMode(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: Need info\nAction: search\nAction Input: test",
			"Thought: Got it\nFinal Answer: Result found",
		},
	}
	tool := &mockTool{name: "search", description: "Search", response: "data"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent:   agent,
		Tools:   []agenkit.Tool{tool},
		Verbose: true,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Verbose should include full trace
	if !strings.Contains(result.Content, "Thought:") {
		t.Error("expected verbose output to contain 'Thought:'")
	}
	if !strings.Contains(result.Content, "Action:") {
		t.Error("expected verbose output to contain 'Action:'")
	}
	if !strings.Contains(result.Content, "Observation:") {
		t.Error("expected verbose output to contain 'Observation:'")
	}
	if !strings.Contains(result.Content, "---") {
		t.Error("expected verbose output to contain separator '---'")
	}
}

func TestReActAgent_NonVerboseMode(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: Need info\nAction: search\nAction Input: test",
			"Thought: Got it\nFinal Answer: Result found",
		},
	}
	tool := &mockTool{name: "search", description: "Search", response: "data"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent:    agent,
		Tools:    []agenkit.Tool{tool},
		Verbose:  false,
		MaxSteps: 10,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	result, err := reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Non-verbose should only have final answer
	if strings.Contains(result.Content, "Thought:") {
		t.Error("expected non-verbose output to not contain 'Thought:'")
	}
	if strings.Contains(result.Content, "Action:") {
		t.Error("expected non-verbose output to not contain 'Action:'")
	}
	if result.Content != "Result found" {
		t.Errorf("expected only final answer, got %s", result.Content)
	}
}

// ============================================================================
// GetSteps Tests
// ============================================================================

func TestReActAgent_GetSteps(t *testing.T) {
	agent := &mockReActAgent{
		name: "test",
		responses: []string{
			"Thought: Step 1\nAction: search\nAction Input: test",
			"Thought: Step 2\nFinal Answer: Done",
		},
	}
	tool := &mockTool{name: "search", description: "Search", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = reactAgent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	steps := reactAgent.GetSteps()
	if len(steps) != 2 {
		t.Errorf("expected 2 steps, got %d", len(steps))
	}
	if steps[0].Thought != "Step 1" {
		t.Errorf("expected first thought 'Step 1', got %s", steps[0].Thought)
	}
	if steps[0].Action != "search" {
		t.Errorf("expected first action 'search', got %s", steps[0].Action)
	}
	if steps[1].IsFinal != true {
		t.Error("expected second step to be final")
	}
}

// ============================================================================
// Name and Capabilities Tests
// ============================================================================

func TestReActAgent_Name(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{}}
	tool := &mockTool{name: "test", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if reactAgent.Name() != "ReActAgent" {
		t.Errorf("expected name 'ReActAgent', got %s", reactAgent.Name())
	}
}

func TestReActAgent_Capabilities(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{}}
	tool := &mockTool{name: "test", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	capabilities := reactAgent.Capabilities()
	expected := []string{"reasoning", "tool-use", "react"}
	if len(capabilities) != len(expected) {
		t.Errorf("expected %d capabilities, got %d", len(expected), len(capabilities))
	}
	for i, cap := range expected {
		if capabilities[i] != cap {
			t.Errorf("expected capability %s, got %s", cap, capabilities[i])
		}
	}
}

// ============================================================================
// Parsing Tests
// ============================================================================

func TestParseResponse_FullFormat(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{}}
	tool := &mockTool{name: "test", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	response := "Thought: I need to search\nAction: search\nAction Input: test query"
	parsed := reactAgent.parseResponse(response)

	if parsed.Thought != "I need to search" {
		t.Errorf("expected thought 'I need to search', got %s", parsed.Thought)
	}
	if parsed.Action != "search" {
		t.Errorf("expected action 'search', got %s", parsed.Action)
	}
	if parsed.ActionInput != "test query" {
		t.Errorf("expected action input 'test query', got %s", parsed.ActionInput)
	}
	if parsed.IsFinal {
		t.Error("expected IsFinal false")
	}
}

func TestParseResponse_FinalAnswer(t *testing.T) {
	agent := &mockReActAgent{name: "test", responses: []string{}}
	tool := &mockTool{name: "test", description: "Test", response: "result"}
	reactAgent, err := NewReActAgent(&ReActConfig{
		Agent: agent,
		Tools: []agenkit.Tool{tool},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	response := "Thought: I know the answer\nFinal Answer: 42"
	parsed := reactAgent.parseResponse(response)

	if parsed.Thought != "I know the answer" {
		t.Errorf("expected thought 'I know the answer', got %s", parsed.Thought)
	}
	if parsed.Observation != "42" {
		t.Errorf("expected observation '42', got %s", parsed.Observation)
	}
	if !parsed.IsFinal {
		t.Error("expected IsFinal true")
	}
}
