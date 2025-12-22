package patterns

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockReasoningAgent is a mock agent that returns predefined responses.
type mockReasoningAgent struct {
	name      string
	responses []string
	callCount int
}

func (m *mockReasoningAgent) Name() string {
	return m.name
}

func (m *mockReasoningAgent) Capabilities() []string {
	return []string{"reasoning"}
}

func (m *mockReasoningAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *mockReasoningAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
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

// mockReasoningTool is a mock tool for reasoning tests.
type mockReasoningTool struct {
	name        string
	description string
	response    string
	shouldFail  bool
	callCount   int
}

func (m *mockReasoningTool) Name() string {
	return m.name
}

func (m *mockReasoningTool) Description() string {
	return m.description
}

func (m *mockReasoningTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
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
// Constructor Tests
// ============================================================================

func TestNewReasoningWithToolsAgent(t *testing.T) {
	llm := &mockReasoningAgent{name: "test_llm", responses: []string{}}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}

	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	if agent.Name() != "reasoning_with_tools_test_llm" {
		t.Errorf("expected name 'reasoning_with_tools_test_llm', got %s", agent.Name())
	}

	if agent.maxReasoningSteps != 20 {
		t.Errorf("expected default maxReasoningSteps 20, got %d", agent.maxReasoningSteps)
	}

	if !agent.enableTrace {
		t.Error("expected default enableTrace true")
	}

	if agent.confidenceThreshold != 0.8 {
		t.Errorf("expected default confidenceThreshold 0.8, got %f", agent.confidenceThreshold)
	}
}

func TestNewReasoningWithToolsAgent_CustomConfig(t *testing.T) {
	llm := &mockReasoningAgent{name: "test_llm", responses: []string{}}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}

	config := &ReasoningWithToolsConfig{
		MaxReasoningSteps:   15,
		EnableTrace:         false,
		ConfidenceThreshold: 0.9,
		ToolUsePrompt:       "Custom prompt",
	}

	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, config)

	if agent.maxReasoningSteps != 15 {
		t.Errorf("expected maxReasoningSteps 15, got %d", agent.maxReasoningSteps)
	}

	if agent.confidenceThreshold != 0.9 {
		t.Errorf("expected confidenceThreshold 0.9, got %f", agent.confidenceThreshold)
	}

	if agent.toolUsePrompt != "Custom prompt" {
		t.Errorf("expected custom prompt, got %s", agent.toolUsePrompt)
	}
}

func TestReasoningWithToolsAgent_Capabilities(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}

	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)
	caps := agent.Capabilities()

	expectedCaps := []string{"reasoning", "tool-use", "interleaved-thinking"}
	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d", len(expectedCaps), len(caps))
	}

	for _, expected := range expectedCaps {
		found := false
		for _, cap := range caps {
			if cap == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("expected capability %s not found", expected)
		}
	}
}

// ============================================================================
// Tool Call Parsing Tests
// ============================================================================

func TestParseToolCall_Simple(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	text := `I need to calculate something.
TOOL_CALL: calculator
PARAMETERS: {"expression": "2 + 2"}
This should give me the answer.`

	toolName, parameters, remainingText := agent.parseToolCall(text)

	if toolName != "calculator" {
		t.Errorf("expected tool name 'calculator', got '%s'", toolName)
	}

	if parameters["expression"] != "2 + 2" {
		t.Errorf("expected expression '2 + 2', got '%v'", parameters["expression"])
	}

	if !strings.Contains(remainingText, "I need to calculate something.") {
		t.Error("expected remaining text to contain thinking before tool call")
	}
}

func TestParseToolCall_NoParameters(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "search", description: "Search", response: "results"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "TOOL_CALL: search"

	toolName, parameters, _ := agent.parseToolCall(text)

	if toolName != "search" {
		t.Errorf("expected tool name 'search', got '%s'", toolName)
	}

	if len(parameters) != 0 {
		t.Errorf("expected empty parameters, got %v", parameters)
	}
}

func TestParseToolCall_ComplexJSON(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "api", description: "API", response: "data"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := `TOOL_CALL: api
PARAMETERS: {"nested": {"key": "value"}, "array": [1, 2, 3]}`

	_, parameters, _ := agent.parseToolCall(text)

	if parameters["nested"] == nil {
		t.Error("expected nested object in parameters")
	}

	if parameters["array"] == nil {
		t.Error("expected array in parameters")
	}
}

func TestParseToolCall_NoToolCall(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "Just regular thinking, no tool call"

	toolName, parameters, remainingText := agent.parseToolCall(text)

	if toolName != "" {
		t.Errorf("expected empty tool name, got '%s'", toolName)
	}

	if parameters != nil {
		t.Errorf("expected nil parameters, got %v", parameters)
	}

	if remainingText != text {
		t.Error("expected remaining text to be unchanged")
	}
}

// ============================================================================
// Conclusion Detection Tests
// ============================================================================

func TestIsConclusion_FinalAnswer(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "FINAL ANSWER: The result is 42"
	if !agent.isConclusion(text) {
		t.Error("expected to detect FINAL ANSWER as conclusion")
	}
}

func TestIsConclusion_Conclusion(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "CONCLUSION: Based on the analysis, the answer is X"
	if !agent.isConclusion(text) {
		t.Error("expected to detect CONCLUSION as conclusion")
	}
}

func TestIsConclusion_Therefore(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "Therefore, the answer must be Y"
	if !agent.isConclusion(text) {
		t.Error("expected to detect Therefore as conclusion")
	}
}

func TestIsConclusion_TheAnswerIs(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "The answer is definitely 100"
	if !agent.isConclusion(text) {
		t.Error("expected to detect 'The answer is' as conclusion")
	}
}

func TestIsConclusion_NotConclusion(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "I'm still thinking about this problem"
	if agent.isConclusion(text) {
		t.Error("expected to NOT detect regular thinking as conclusion")
	}
}

// ============================================================================
// Answer Extraction Tests
// ============================================================================

func TestExtractAnswer_FinalAnswer(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "Some thinking... FINAL ANSWER: The result is 42"
	answer := agent.extractAnswer(text)

	if !strings.Contains(answer, "The result is 42") {
		t.Errorf("expected answer to contain 'The result is 42', got '%s'", answer)
	}
}

func TestExtractAnswer_Conclusion(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "CONCLUSION: Based on analysis, X is correct"
	answer := agent.extractAnswer(text)

	if !strings.Contains(answer, "Based on analysis, X is correct") {
		t.Errorf("expected answer to contain conclusion text, got '%s'", answer)
	}
}

func TestExtractAnswer_TheAnswerIs(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "After careful consideration, The answer is 100"
	answer := agent.extractAnswer(text)

	if !strings.Contains(answer, "100") {
		t.Errorf("expected answer to contain '100', got '%s'", answer)
	}
}

func TestExtractAnswer_NoMarker(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	tool := &mockReasoningTool{name: "test", description: "Test", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{tool}, nil)

	text := "Just some text without markers"
	answer := agent.extractAnswer(text)

	if answer != text {
		t.Error("expected answer to be the full text when no markers found")
	}
}

// ============================================================================
// Tool Management Tests
// ============================================================================

func TestGetTool(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	tool := agent.GetTool("calculator")
	if tool == nil {
		t.Error("expected to get calculator tool")
	}

	if tool.Name() != "calculator" {
		t.Errorf("expected tool name 'calculator', got '%s'", tool.Name())
	}
}

func TestGetTool_NotFound(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	tool := agent.GetTool("nonexistent")
	if tool != nil {
		t.Error("expected nil for nonexistent tool")
	}
}

func TestAddTool(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	search := &mockReasoningTool{name: "search", description: "Search", response: "results"}
	agent.AddTool(search)

	tool := agent.GetTool("search")
	if tool == nil {
		t.Error("expected to get search tool after adding")
	}
}

func TestRemoveTool(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	removed := agent.RemoveTool("calculator")
	if !removed {
		t.Error("expected RemoveTool to return true")
	}

	tool := agent.GetTool("calculator")
	if tool != nil {
		t.Error("expected calculator tool to be removed")
	}
}

func TestRemoveTool_NotFound(t *testing.T) {
	llm := &mockReasoningAgent{name: "test", responses: []string{}}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	removed := agent.RemoveTool("nonexistent")
	if removed {
		t.Error("expected RemoveTool to return false for nonexistent tool")
	}
}

// ============================================================================
// Integration Tests - Process Method
// ============================================================================

func TestProcess_DirectConclusion(t *testing.T) {
	llm := &mockReasoningAgent{
		name:      "test",
		responses: []string{"FINAL ANSWER: The result is 42"},
	}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "What is the answer?",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !strings.Contains(result.Content, "The result is 42") {
		t.Errorf("expected answer in result, got: %s", result.Content)
	}

	// Check metadata
	if result.Metadata == nil {
		t.Fatal("expected metadata")
	}

	if result.Metadata["reasoning_steps"] == nil {
		t.Error("expected reasoning_steps in metadata")
	}
}

func TestProcess_WithToolCall(t *testing.T) {
	llm := &mockReasoningAgent{
		name: "test",
		responses: []string{
			"I need to calculate: TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"2+2\"}",
			"FINAL ANSWER: The result is 4",
		},
	}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "4"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "What is 2+2?",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if calculator.callCount != 1 {
		t.Errorf("expected calculator called once, got %d", calculator.callCount)
	}

	if !strings.Contains(result.Content, "The result is 4") {
		t.Errorf("expected answer in result, got: %s", result.Content)
	}

	// Check trace
	if result.Metadata["tools_used"] != 1 {
		t.Errorf("expected 1 tool used, got %v", result.Metadata["tools_used"])
	}
}

func TestProcess_ToolCallFailure(t *testing.T) {
	llm := &mockReasoningAgent{
		name: "test",
		responses: []string{
			"Let me search: TOOL_CALL: search\nPARAMETERS: {\"query\": \"test\"}",
			"FINAL ANSWER: Continuing without search results",
		},
	}
	search := &mockReasoningTool{
		name:        "search",
		description: "Search",
		response:    "",
		shouldFail:  true,
	}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{search}, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Search for something",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should continue despite tool failure
	if !strings.Contains(result.Content, "Continuing without search results") {
		t.Error("expected agent to continue after tool failure")
	}
}

func TestProcess_UnknownTool(t *testing.T) {
	llm := &mockReasoningAgent{
		name: "test",
		responses: []string{
			"Let me use: TOOL_CALL: unknown_tool\nPARAMETERS: {}",
			"FINAL ANSWER: Proceeding without unknown tool",
		},
	}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Use unknown tool",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should continue with regular thinking
	if !strings.Contains(result.Content, "Proceeding without unknown tool") {
		t.Error("expected agent to continue when tool not found")
	}
}

func TestProcess_MaxStepsReached(t *testing.T) {
	// Create responses that never conclude
	responses := make([]string, 25)
	for i := range responses {
		responses[i] = fmt.Sprintf("Thinking step %d...", i)
	}

	llm := &mockReasoningAgent{
		name:      "test",
		responses: responses,
	}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}

	config := &ReasoningWithToolsConfig{
		MaxReasoningSteps: 5,
		EnableTrace:       true,
	}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, config)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Think forever",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should stop at max steps
	if result.Metadata["reasoning_steps"] == nil {
		t.Fatal("expected reasoning_steps in metadata")
	}
	steps := result.Metadata["reasoning_steps"].(int)
	if steps > 5 {
		t.Errorf("expected max 5 steps, got %d", steps)
	}
}

func TestProcess_MultipleToolCalls(t *testing.T) {
	llm := &mockReasoningAgent{
		name: "test",
		responses: []string{
			"First calculation: TOOL_CALL: calculator\nPARAMETERS: {\"expr\": \"2+2\"}",
			"Second calculation: TOOL_CALL: calculator\nPARAMETERS: {\"expr\": \"10*10\"}",
			"FINAL ANSWER: Results are 4 and 100",
		},
	}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "result"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Do multiple calculations",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if calculator.callCount != 2 {
		t.Errorf("expected calculator called twice, got %d", calculator.callCount)
	}

	toolsUsed := result.Metadata["tools_used"].(int)
	if toolsUsed != 2 {
		t.Errorf("expected 2 tools used in metadata, got %d", toolsUsed)
	}
}

func TestProcess_ContextCancellation(t *testing.T) {
	llm := &mockReasoningAgent{
		name:      "test",
		responses: []string{"Thinking...", "More thinking..."},
	}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	_, err := agent.Process(ctx, &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != context.Canceled {
		t.Errorf("expected context.Canceled error, got %v", err)
	}
}

func TestProcess_TraceDisabled(t *testing.T) {
	llm := &mockReasoningAgent{
		name:      "test",
		responses: []string{"FINAL ANSWER: Done"},
	}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "42"}

	config := &ReasoningWithToolsConfig{
		EnableTrace: false,
	}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, config)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Metadata should be empty when trace disabled
	if len(result.Metadata) > 0 {
		t.Error("expected empty metadata when trace disabled")
	}
}

// ============================================================================
// Reasoning Trace Tests
// ============================================================================

func TestProcess_ReasoningTrace(t *testing.T) {
	llm := &mockReasoningAgent{
		name: "test",
		responses: []string{
			"Step 1: Thinking about the problem",
			"Step 2: Using tool TOOL_CALL: calculator\nPARAMETERS: {\"expr\": \"2+2\"}",
			"Step 3: FINAL ANSWER: The result is 4",
		},
	}
	calculator := &mockReasoningTool{name: "calculator", description: "Calculate", response: "4"}
	agent := NewReasoningWithToolsAgent(llm, []agenkit.Tool{calculator}, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Calculate 2+2",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	trace := result.Metadata["reasoning_trace"].(map[string]interface{})
	if trace == nil {
		t.Fatal("expected reasoning_trace in metadata")
	}

	steps := trace["steps"].([]map[string]interface{})
	if len(steps) < 3 {
		t.Errorf("expected at least 3 steps in trace, got %d", len(steps))
	}

	// Check for thinking step
	foundThinking := false
	for _, step := range steps {
		if step["step_type"] == string(ReasoningStepThinking) {
			foundThinking = true
			break
		}
	}
	if !foundThinking {
		t.Error("expected at least one thinking step in trace")
	}

	// Check for tool call step
	foundToolCall := false
	for _, step := range steps {
		if step["step_type"] == string(ReasoningStepToolCall) {
			foundToolCall = true
			if step["tool_name"] != "calculator" {
				t.Errorf("expected tool_name 'calculator', got %v", step["tool_name"])
			}
			break
		}
	}
	if !foundToolCall {
		t.Error("expected tool call step in trace")
	}

	// Check for conclusion step
	foundConclusion := false
	for _, step := range steps {
		if step["step_type"] == string(ReasoningStepConclusion) {
			foundConclusion = true
			break
		}
	}
	if !foundConclusion {
		t.Error("expected conclusion step in trace")
	}
}
