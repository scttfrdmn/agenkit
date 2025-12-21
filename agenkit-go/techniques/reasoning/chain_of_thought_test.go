package reasoning

import (
	"context"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Test basic Chain-of-Thought functionality
func TestChainOfThoughtBasic(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. First, analyze the problem.\n2. Then, calculate.\n3. The answer is 42.",
	})

	cot := NewChainOfThought(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the answer?")

	response, err := cot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Check response content
	if !strings.Contains(response.Content, "42") {
		t.Errorf("Expected answer to contain '42', got: %s", response.Content)
	}

	// Check metadata
	if response.Metadata["technique"] != "chain_of_thought" {
		t.Errorf("Expected technique='chain_of_thought', got: %v", response.Metadata["technique"])
	}

	// Check reasoning steps
	steps, ok := response.Metadata["reasoning_steps"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_steps to be []string, got: %T", response.Metadata["reasoning_steps"])
	}

	if len(steps) != 3 {
		t.Errorf("Expected 3 reasoning steps, got: %d", len(steps))
	}

	numSteps, ok := response.Metadata["num_steps"].(int)
	if !ok || numSteps != 3 {
		t.Errorf("Expected num_steps=3, got: %v", response.Metadata["num_steps"])
	}
}

// Test name and capabilities
func TestChainOfThoughtNameAndCapabilities(t *testing.T) {
	mockAgent := NewMockAgent([]string{"response"})
	cot := NewChainOfThought(mockAgent)

	if cot.Name() != "chain_of_thought" {
		t.Errorf("Expected name='chain_of_thought', got: %s", cot.Name())
	}

	caps := cot.Capabilities()
	expectedCaps := []string{"reasoning", "step_by_step", "chain_of_thought", "explainable_ai"}

	for _, expected := range expectedCaps {
		found := false
		for _, cap := range caps {
			if cap == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected capability '%s' not found in: %v", expected, caps)
		}
	}
}

// Test numbered step parsing
func TestChainOfThoughtNumberedSteps(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. First step\n2. Second step\n3. Third step\n4. Fourth step",
	})

	cot := NewChainOfThought(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := cot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	steps, ok := response.Metadata["reasoning_steps"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_steps to be []string")
	}

	if len(steps) != 4 {
		t.Errorf("Expected 4 steps, got: %d", len(steps))
	}

	if steps[0] != "First step" {
		t.Errorf("Expected first step='First step', got: %s", steps[0])
	}
}

// Test numbered steps with parentheses
func TestChainOfThoughtNumberedStepsParentheses(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1) First step\n2) Second step\n3) Third step",
	})

	cot := NewChainOfThought(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := cot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	steps, ok := response.Metadata["reasoning_steps"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_steps to be []string")
	}

	if len(steps) != 3 {
		t.Errorf("Expected 3 steps, got: %d", len(steps))
	}
}

// Test bullet point parsing
func TestChainOfThoughtBulletPoints(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"- First step\n- Second step\n- Third step",
	})

	cot := NewChainOfThought(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := cot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	steps, ok := response.Metadata["reasoning_steps"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_steps to be []string")
	}

	if len(steps) != 3 {
		t.Errorf("Expected 3 steps, got: %d", len(steps))
	}

	if steps[0] != "First step" {
		t.Errorf("Expected first step='First step', got: %s", steps[0])
	}
}

// Test custom prompt template
func TestChainOfThoughtCustomTemplate(t *testing.T) {
	capturedPrompt := ""
	customAgent := &CustomCaptureAgent{
		promptCaptured: &capturedPrompt,
		response:       "1. Answer",
	}

	cot := NewChainOfThought(
		customAgent,
		WithPromptTemplate("Solve carefully:\n{query}"),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test query")

	_, err := cot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if capturedPrompt != "Solve carefully:\nTest query" {
		t.Errorf("Expected prompt='Solve carefully:\\nTest query', got: %s", capturedPrompt)
	}
}

// Test max steps limiting
func TestChainOfThoughtMaxSteps(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. First\n2. Second\n3. Third\n4. Fourth\n5. Fifth\n6. Sixth",
	})

	maxSteps := 3
	cot := NewChainOfThought(
		mockAgent,
		WithMaxSteps(maxSteps),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := cot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	steps, ok := response.Metadata["reasoning_steps"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_steps to be []string")
	}

	if len(steps) != maxSteps {
		t.Errorf("Expected %d steps, got: %d", maxSteps, len(steps))
	}

	numSteps, ok := response.Metadata["num_steps"].(int)
	if !ok || numSteps != maxSteps {
		t.Errorf("Expected num_steps=%d, got: %v", maxSteps, response.Metadata["num_steps"])
	}
}

// Test parse steps disabled
func TestChainOfThoughtParseStepsDisabled(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. First\n2. Second\n3. Third",
	})

	cot := NewChainOfThought(
		mockAgent,
		WithParseSteps(false),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := cot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if _, exists := response.Metadata["reasoning_steps"]; exists {
		t.Error("Expected reasoning_steps to not be present when parseSteps=false")
	}

	if _, exists := response.Metadata["num_steps"]; exists {
		t.Error("Expected num_steps to not be present when parseSteps=false")
	}

	if response.Metadata["technique"] != "chain_of_thought" {
		t.Errorf("Expected technique to still be present")
	}
}

// Test error on missing {query} placeholder
func TestChainOfThoughtMissingPlaceholder(t *testing.T) {
	mockAgent := NewMockAgent([]string{"response"})

	cot := NewChainOfThought(
		mockAgent,
		WithPromptTemplate("This template has no placeholder"),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	_, err := cot.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected error for missing {query} placeholder")
	}

	if !strings.Contains(err.Error(), "placeholder") {
		t.Errorf("Expected error message about placeholder, got: %v", err)
	}
}

// Test empty response
func TestChainOfThoughtEmptyResponse(t *testing.T) {
	mockAgent := NewMockAgent([]string{""})

	cot := NewChainOfThought(mockAgent)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Test")

	response, err := cot.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	steps, ok := response.Metadata["reasoning_steps"].([]string)
	if !ok {
		t.Fatalf("Expected reasoning_steps to be []string")
	}

	if len(steps) != 0 {
		t.Errorf("Expected 0 steps for empty response, got: %d", len(steps))
	}
}

// CustomCaptureAgent captures the prompt for testing
type CustomCaptureAgent struct {
	promptCaptured *string
	response       string
}

func (a *CustomCaptureAgent) Name() string {
	return "custom_capture"
}

func (a *CustomCaptureAgent) Capabilities() []string {
	return []string{"testing"}
}

func (a *CustomCaptureAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	*a.promptCaptured = message.Content
	return agenkit.NewMessage("assistant", a.response), nil
}

func (a *CustomCaptureAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}
