// Package main demonstrates the ReAct pattern for reasoning and acting.
//
// The ReAct (Reasoning + Acting) pattern enables agents to think through problems
// by interleaving reasoning steps with tool actions in an iterative loop.
//
// This example shows:
//   - Creating tools for agent use (calculator, search)
//   - Setting up a reasoning agent
//   - Executing the ReAct loop with thought/action/observation cycles
//   - Handling multi-step reasoning with multiple tools
//
// Run with: go run react_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strconv"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// CalculatorTool performs basic arithmetic calculations
type CalculatorTool struct{}

func (c *CalculatorTool) Name() string {
	return "calculator"
}

func (c *CalculatorTool) Description() string {
	return "Performs basic arithmetic calculations. Input should be an expression like '2+2' or '15% of 240'"
}

func (c *CalculatorTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	input, ok := params["input"].(string)
	if !ok {
		return nil, fmt.Errorf("input parameter is required")
	}

	fmt.Printf("   🧮 Calculator executing: %s\n", input)

	var result string
	switch {
	case strings.Contains(input, "+"):
		parts := strings.Split(input, "+")
		if len(parts) == 2 {
			a, _ := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64)
			b, _ := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
			result = fmt.Sprintf("%.2f", a+b)
		}
	case strings.Contains(input, "% of"):
		parts := strings.Split(input, "% of")
		if len(parts) == 2 {
			percent, _ := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64)
			value, _ := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
			result = fmt.Sprintf("%.2f", value*percent/100.0)
		}
	case strings.Contains(input, "*"):
		parts := strings.Split(input, "*")
		if len(parts) == 2 {
			a, _ := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64)
			b, _ := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
			result = fmt.Sprintf("%.2f", a*b)
		}
	default:
		result = "Error: Unsupported operation"
	}

	success := !strings.HasPrefix(result, "Error")
	return &agenkit.ToolResult{
		Data:    result,
		Success: success,
		Error:   "",
	}, nil
}

// SearchTool simulates searching for information
type SearchTool struct{}

func (s *SearchTool) Name() string {
	return "search"
}

func (s *SearchTool) Description() string {
	return "Searches for information on a given topic. Input should be a search query."
}

func (s *SearchTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	query, ok := params["input"].(string)
	if !ok {
		return nil, fmt.Errorf("input parameter is required")
	}

	fmt.Printf("   🔍 Search executing: %s\n", query)

	var result string
	queryLower := strings.ToLower(query)
	switch {
	case strings.Contains(queryLower, "go"):
		result = "Go is a statically typed, compiled programming language designed for simplicity and efficiency."
	case strings.Contains(queryLower, "agenkit"):
		result = "Agenkit is a cross-language AI agent framework supporting Python, Go, TypeScript, and Rust."
	case strings.Contains(queryLower, "react") || strings.Contains(queryLower, "reasoning"):
		result = "ReAct combines reasoning and acting by interleaving thought processes with tool actions."
	default:
		result = "No relevant information found for this query."
	}

	return &agenkit.ToolResult{
		Data:    result,
		Success: true,
		Error:   "",
	}, nil
}

// MockReasoningAgent simulates an LLM that reasons and decides on actions
type MockReasoningAgent struct {
	scenario string
	step     int
}

func (m *MockReasoningAgent) Name() string {
	return "MockReasoning"
}

func (m *MockReasoningAgent) Capabilities() []string {
	return []string{"reasoning", "planning"}
}

func (m *MockReasoningAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockReasoningAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content

	var response string

	switch m.scenario {
	case "calculator":
		if strings.Contains(content, "What is 15% of 240") {
			if strings.Contains(content, "Observation:") {
				response = "Thought: I have the calculation result\nFinal Answer: 15% of 240 is 36.00"
			} else {
				response = "Thought: I need to calculate 15% of 240\nAction: calculator\nAction Input: 15% of 240"
			}
		}

	case "search":
		if strings.Contains(content, "What is Go") {
			if strings.Contains(content, "Observation:") {
				response = "Thought: I found information about Go\nFinal Answer: Go is a statically typed, compiled programming language designed for simplicity and efficiency."
			} else {
				response = "Thought: I should search for information about Go\nAction: search\nAction Input: Go programming language"
			}
		}

	case "multi-step":
		if !strings.Contains(content, "Observation:") {
			response = "Thought: I should first search for what ReAct means\nAction: search\nAction Input: ReAct reasoning"
		} else if strings.Contains(content, "ReAct combines") {
			response = "Thought: Now I understand ReAct, let me calculate an example\nAction: calculator\nAction Input: 10 + 5"
		} else if strings.Contains(content, "15.00") {
			response = "Thought: I have both pieces of information\nFinal Answer: ReAct combines reasoning and acting. As an example, 10 + 5 = 15.00."
		}
	}

	m.step++
	return agenkit.NewMessage("assistant", response), nil
}

func main() {
	fmt.Println("🎭 ReAct Pattern Example")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println()

	// Example 1: Simple calculation with ReAct
	fmt.Println("📋 Example 1: Simple Calculation")
	fmt.Println(strings.Repeat("=", 60))

	reasoningAgent := &MockReasoningAgent{scenario: "calculator"}
	calculator := &CalculatorTool{}

	config := &patterns.ReActConfig{
		Agent:    reasoningAgent,
		Tools:    []agenkit.Tool{calculator},
		MaxSteps: 5,
		Verbose:  true,
	}

	reactAgent, err := patterns.NewReActAgent(config)
	if err != nil {
		log.Fatalf("Failed to create ReAct agent: %v", err)
	}

	fmt.Println("\n➡️  Query: What is 15% of 240?")
	message := agenkit.NewMessage("user", "What is 15% of 240?")
	result, err := reactAgent.Process(context.Background(), message)
	if err != nil {
		log.Fatalf("ReAct processing failed: %v", err)
	}

	fmt.Printf("\n✅ Result:\n%s\n", result.Content)

	// Example 2: Information search with ReAct
	fmt.Println("\n\n" + strings.Repeat("=", 60))
	fmt.Println("📋 Example 2: Information Search")
	fmt.Println(strings.Repeat("=", 60))

	reasoningAgent2 := &MockReasoningAgent{scenario: "search"}
	search := &SearchTool{}

	config2 := &patterns.ReActConfig{
		Agent:    reasoningAgent2,
		Tools:    []agenkit.Tool{search},
		MaxSteps: 5,
		Verbose:  true,
	}

	reactAgent2, err := patterns.NewReActAgent(config2)
	if err != nil {
		log.Fatalf("Failed to create ReAct agent: %v", err)
	}

	fmt.Println("\n➡️  Query: What is Go?")
	message2 := agenkit.NewMessage("user", "What is Go?")
	result2, err := reactAgent2.Process(context.Background(), message2)
	if err != nil {
		log.Fatalf("ReAct processing failed: %v", err)
	}

	fmt.Printf("\n✅ Result:\n%s\n", result2.Content)

	// Example 3: Multi-step reasoning with multiple tools
	fmt.Println("\n\n" + strings.Repeat("=", 60))
	fmt.Println("📋 Example 3: Multi-Step Reasoning")
	fmt.Println(strings.Repeat("=", 60))

	reasoningAgent3 := &MockReasoningAgent{scenario: "multi-step"}
	calculator3 := &CalculatorTool{}
	search3 := &SearchTool{}

	config3 := &patterns.ReActConfig{
		Agent:    reasoningAgent3,
		Tools:    []agenkit.Tool{calculator3, search3},
		MaxSteps: 10,
		Verbose:  true,
	}

	reactAgent3, err := patterns.NewReActAgent(config3)
	if err != nil {
		log.Fatalf("Failed to create ReAct agent: %v", err)
	}

	fmt.Println("\n➡️  Query: Explain ReAct and show a calculation example")
	message3 := agenkit.NewMessage("user", "Explain ReAct and show a calculation example")
	result3, err := reactAgent3.Process(context.Background(), message3)
	if err != nil {
		log.Fatalf("ReAct processing failed: %v", err)
	}

	fmt.Printf("\n✅ Result:\n%s\n", result3.Content)

	// Summary
	fmt.Println("\n\n" + strings.Repeat("=", 60))
	fmt.Println("✨ ReAct pattern examples complete!")
	fmt.Println("\n💡 Key takeaways:")
	fmt.Println("   - ReAct combines reasoning (thought) with acting (tool use)")
	fmt.Println("   - Agent iterates: Thought → Action → Observation → repeat")
	fmt.Println("   - Tools extend agent capabilities beyond pure language")
	fmt.Println("   - Transparent reasoning process visible in verbose mode")
	fmt.Println()
	fmt.Println("🎯 When to use ReAct:")
	fmt.Println("   - Tasks requiring external information or computation")
	fmt.Println("   - Problems needing step-by-step reasoning")
	fmt.Println("   - Situations where tool use must be justified")
	fmt.Println("   - Scenarios requiring transparent decision-making")
}
