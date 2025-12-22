// Package main demonstrates the Reasoning with Tools pattern.
//
// The Reasoning with Tools pattern enables interleaved reasoning and tool usage,
// where tools are called DURING the thinking process, not just after reasoning
// completes. This is inspired by Claude 4 and o3's extended thinking capabilities.
//
// This example shows:
//   - Basic reasoning with tool calls during thought process
//   - Multiple tool usage in a single reasoning session
//   - Extended thinking with multiple reasoning steps
//   - Sequential tool chaining with reasoning between calls
//   - Max steps limit to prevent infinite loops
//
// Run with: go run reasoning_with_tools_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// MockReasoningLLM simulates an LLM that performs reasoning and tool calls
type MockReasoningLLM struct {
	responses []string
	current   int
	mu        sync.Mutex
}

func NewMockReasoningLLM(responses []string) *MockReasoningLLM {
	return &MockReasoningLLM{
		responses: responses,
		current:   0,
	}
}

func (m *MockReasoningLLM) Name() string {
	return "mock-reasoning-llm"
}

func (m *MockReasoningLLM) Capabilities() []string {
	return []string{"reasoning", "tool-calling"}
}

func (m *MockReasoningLLM) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockReasoningLLM) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	var response string
	if m.current < len(m.responses) {
		response = m.responses[m.current]
		m.current++
	} else {
		response = "CONCLUSION: Done thinking"
	}

	return agenkit.NewMessage("assistant", response), nil
}

// CalculatorTool for mathematical operations
type CalculatorTool struct{}

func (c *CalculatorTool) Name() string {
	return "calculator"
}

func (c *CalculatorTool) Description() string {
	return "Performs mathematical calculations"
}

func (c *CalculatorTool) Execute(ctx context.Context, parameters map[string]interface{}) (*agenkit.ToolResult, error) {
	expression, ok := parameters["expression"].(string)
	if !ok {
		return nil, fmt.Errorf("missing expression parameter")
	}

	// Simple eval for demo
	var result string
	switch expression {
	case "2 + 2":
		result = "4"
	case "10 * 5":
		result = "50"
	case "100 / 4":
		result = "25"
	case "15 + 30":
		result = "45"
	default:
		result = "42"
	}

	return &agenkit.ToolResult{
		Data:    result,
		Success: true,
	}, nil
}

// SearchTool for looking up information
type SearchTool struct{}

func (s *SearchTool) Name() string {
	return "search"
}

func (s *SearchTool) Description() string {
	return "Searches for information"
}

func (s *SearchTool) Execute(ctx context.Context, parameters map[string]interface{}) (*agenkit.ToolResult, error) {
	query, ok := parameters["query"].(string)
	if !ok {
		return nil, fmt.Errorf("missing query parameter")
	}

	result := fmt.Sprintf("Search results for: %s", query)
	return &agenkit.ToolResult{
		Data:    result,
		Success: true,
	}, nil
}

// Example 1: Basic reasoning with tool
func exampleBasicReasoning() error {
	fmt.Println("\n--- Scenario 1: Basic Interleaved Reasoning ---")

	llm := NewMockReasoningLLM([]string{
		"Let me think about this problem... I need to calculate 2 + 2.",
		"TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"2 + 2\"}",
		"The calculator returned 4. CONCLUSION: The answer is 4",
	})

	tools := []agenkit.Tool{&CalculatorTool{}}
	config := patterns.ReasoningWithToolsConfig{
		MaxReasoningSteps: 10,
		EnableTrace:       true,
	}

	agent := patterns.NewReasoningWithToolsAgent(llm, tools, &config)

	message := agenkit.NewMessage("user", "What is 2 + 2?")
	result, err := agent.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Println("Question: What is 2 + 2?")
	fmt.Printf("Answer: %s\n", result.Content)
	fmt.Println("✓ Tool was called DURING reasoning, not after")

	return nil
}

// Example 2: Multiple tools
func exampleMultipleTools() error {
	fmt.Println("--- Scenario 2: Multiple Tool Usage ---")

	llm := NewMockReasoningLLM([]string{
		"I need to search first.",
		"TOOL_CALL: search\nPARAMETERS: {\"query\": \"Go programming\"}",
		"Good, now let me calculate something.",
		"TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"15 + 30\"}",
		"CONCLUSION: Search found info, calculation gives 45",
	})

	tools := []agenkit.Tool{&CalculatorTool{}, &SearchTool{}}
	config := patterns.ReasoningWithToolsConfig{
		MaxReasoningSteps: 10,
		EnableTrace:       true,
	}

	agent := patterns.NewReasoningWithToolsAgent(llm, tools, &config)

	message := agenkit.NewMessage("user", "Search for Go and calculate 15 + 30")
	result, err := agent.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Println("Question: Search for Go and calculate 15 + 30")
	fmt.Println("Tools used: search, calculator")
	fmt.Printf("Answer: %s\n", result.Content)
	fmt.Println("✓ Multiple tools orchestrated through reasoning")

	return nil
}

// Example 3: Extended thinking
func exampleExtendedThinking() error {
	fmt.Println("--- Scenario 3: Extended Thinking Process ---")

	llm := NewMockReasoningLLM([]string{
		"This is a complex problem. Let me break it down.",
		"First, I need to calculate 10 * 5.",
		"TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"10 * 5\"}",
		"Good, that's 50. Now I need to think about the next step.",
		"Let me verify with another calculation.",
		"TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"100 / 4\"}",
		"Perfect, that confirms my hypothesis.",
		"CONCLUSION: The results are 50 and 25",
	})

	tools := []agenkit.Tool{&CalculatorTool{}}
	config := patterns.ReasoningWithToolsConfig{
		MaxReasoningSteps: 15,
		EnableTrace:       true,
	}

	agent := patterns.NewReasoningWithToolsAgent(llm, tools, &config)

	message := agenkit.NewMessage("user", "Calculate 10 * 5 and 100 / 4")
	result, err := agent.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Println("Question: Calculate 10 * 5 and 100 / 4")
	fmt.Println("Steps taken: Multiple reasoning steps with tool calls")
	fmt.Printf("Answer: %s\n", result.Content)

	if _, ok := result.Metadata["reasoning_trace"]; ok {
		fmt.Println("✓ Reasoning trace captured:")
		fmt.Println("  - Thinking steps")
		fmt.Println("  - Tool calls with parameters")
		fmt.Println("  - Tool results")
		fmt.Println("  - Full observability")
	}

	return nil
}

// Example 4: Tool chaining
func exampleToolChaining() error {
	fmt.Println("--- Scenario 4: Sequential Tool Usage ---")

	llm := NewMockReasoningLLM([]string{
		"Step 1: Search for information.",
		"TOOL_CALL: search\nPARAMETERS: {\"query\": \"population\"}",
		"Step 2: Calculate based on results.",
		"TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"10 * 5\"}",
		"Step 3: Final analysis.",
		"CONCLUSION: Population is 50 million",
	})

	tools := []agenkit.Tool{&CalculatorTool{}, &SearchTool{}}
	config := patterns.ReasoningWithToolsConfig{
		MaxReasoningSteps: 10,
		EnableTrace:       true,
	}

	agent := patterns.NewReasoningWithToolsAgent(llm, tools, &config)

	message := agenkit.NewMessage("user", "Find population and calculate")
	_, err := agent.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Println("Question: Find population and calculate")
	fmt.Println("Process:")
	fmt.Println("  1. Reasoning → Search tool")
	fmt.Println("  2. Reasoning → Calculator tool")
	fmt.Println("  3. Reasoning → Conclusion")
	fmt.Println("✓ Tools used sequentially with reasoning between each")

	return nil
}

// Example 5: Max steps limit
func exampleMaxStepsLimit() error {
	fmt.Println("--- Scenario 5: Max Steps Limit ---")

	var responses []string
	for i := 1; i <= 15; i++ {
		responses = append(responses, fmt.Sprintf("Thinking step %d...", i))
	}
	responses = append(responses, "CONCLUSION: Done")

	llm := NewMockReasoningLLM(responses)
	tools := []agenkit.Tool{}
	config := patterns.ReasoningWithToolsConfig{
		MaxReasoningSteps: 5, // Max 5 steps
		EnableTrace:       false,
	}

	agent := patterns.NewReasoningWithToolsAgent(llm, tools, &config)

	message := agenkit.NewMessage("user", "Think deeply")
	result, err := agent.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Println("Question: Think deeply")
	fmt.Println("Max reasoning steps: 5")
	fmt.Printf("Answer: %s\n", result.Content)
	fmt.Println("✓ Reasoning terminated at max steps to prevent infinite loops")

	return nil
}

func main() {
	fmt.Println("=== Reasoning with Tools Pattern Examples ===")

	// Run all examples
	if err := exampleBasicReasoning(); err != nil {
		log.Fatalf("Example 1 failed: %v", err)
	}

	if err := exampleMultipleTools(); err != nil {
		log.Fatalf("Example 2 failed: %v", err)
	}

	if err := exampleExtendedThinking(); err != nil {
		log.Fatalf("Example 3 failed: %v", err)
	}

	if err := exampleToolChaining(); err != nil {
		log.Fatalf("Example 4 failed: %v", err)
	}

	if err := exampleMaxStepsLimit(); err != nil {
		log.Fatalf("Example 5 failed: %v", err)
	}

	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("=== All Reasoning with Tools Examples Complete! ===")
	fmt.Println("\nKey Takeaways:")
	fmt.Println("1. Tools called DURING reasoning, not just after")
	fmt.Println("2. Multiple reasoning steps before and after tool use")
	fmt.Println("3. Full observability with reasoning traces")
	fmt.Println("4. Support for multiple tools in one reasoning session")
	fmt.Println("5. Sequential tool chaining with reasoning between")
	fmt.Println("6. Max steps limit prevents infinite loops")
	fmt.Println("7. Suitable for complex, multi-step problem solving")
	fmt.Println("\nInspired by:")
	fmt.Println("- Claude 4's extended thinking")
	fmt.Println("- o3's reasoning capabilities")
	fmt.Println("- Chain-of-thought prompting")
	fmt.Println()
	fmt.Println("🎯 When to use Reasoning with Tools:")
	fmt.Println("   - Complex problems requiring deep analysis")
	fmt.Println("   - Tasks needing both computation and reasoning")
	fmt.Println("   - Scenarios requiring transparent decision-making")
	fmt.Println("   - Multi-step problems with tool dependencies")
}
