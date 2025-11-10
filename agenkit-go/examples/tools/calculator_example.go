/*
Tools Usage Example - Calculator

WHY USE TOOLS?
--------------
1. Accuracy: LLMs hallucinate math, tools compute correctly
2. Determinism: Same input → same output (essential for critical ops)
3. External Data: Access databases, APIs, filesystems, web
4. Complex Operations: Leverage existing libraries (math, data processing)
5. Auditability: Tool calls are explicit and loggable
6. Cost Efficiency: Don't waste tokens on computable results

WHEN TO USE TOOLS:
- Mathematical calculations (arithmetic, statistics, algebra)
- Data retrieval (databases, APIs, search engines)
- File system operations (read, write, list)
- Date/time operations (parsing, formatting, arithmetic)
- Structured data processing (JSON, XML, CSV)
- External integrations (Slack, email, CRM)

WHEN NOT TO USE TOOLS:
- Creative tasks (writing, brainstorming)
- Subjective judgments (quality, sentiment)
- Tasks LLMs excel at (summarization, translation)
- Simple transformations (upper/lowercase, trim)

TRADE-OFFS:
- Accuracy/Reliability vs Flexibility
- Determinism vs Creativity
- Integration overhead vs correctness

Run with: go run agenkit-go/examples/tools/calculator_example.go
*/

package main

import (
	"context"
	"fmt"
	"math"
	"strings"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/tools"
)

// AddTool adds numbers accurately
type AddTool struct{}

func (t *AddTool) Name() string { return "add" }
func (t *AddTool) Description() string { return "Add two or more numbers together" }

func (t *AddTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	numbersIface, ok := params["numbers"]
	if !ok {
		return agenkit.NewToolError("missing 'numbers' parameter"), nil
	}

	// Convert interface{} to []float64
	var numbers []float64
	switch v := numbersIface.(type) {
	case []interface{}:
		for _, n := range v {
			switch num := n.(type) {
			case float64:
				numbers = append(numbers, num)
			case int:
				numbers = append(numbers, float64(num))
			}
		}
	case []float64:
		numbers = v
	}

	if len(numbers) < 2 {
		return agenkit.NewToolError("need at least 2 numbers to add"), nil
	}

	sum := 0.0
	for _, n := range numbers {
		sum += n
	}

	return agenkit.NewToolResult(map[string]interface{}{
		"operation": "addition",
		"inputs":    numbers,
		"result":    sum,
	}), nil
}

// MultiplyTool multiplies numbers accurately
type MultiplyTool struct{}

func (t *MultiplyTool) Name() string { return "multiply" }
func (t *MultiplyTool) Description() string { return "Multiply two or more numbers together" }

func (t *MultiplyTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	numbersIface, ok := params["numbers"]
	if !ok {
		return agenkit.NewToolError("missing 'numbers' parameter"), nil
	}

	var numbers []float64
	switch v := numbersIface.(type) {
	case []interface{}:
		for _, n := range v {
			switch num := n.(type) {
			case float64:
				numbers = append(numbers, num)
			case int:
				numbers = append(numbers, float64(num))
			}
		}
	case []float64:
		numbers = v
	}

	product := 1.0
	for _, n := range numbers {
		product *= n
	}

	return agenkit.NewToolResult(map[string]interface{}{
		"operation": "multiplication",
		"inputs":    numbers,
		"result":    product,
	}), nil
}

// PowerTool computes exponentiation
type PowerTool struct{}

func (t *PowerTool) Name() string { return "power" }
func (t *PowerTool) Description() string { return "Compute base^exponent" }

func (t *PowerTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	base, ok := params["base"].(float64)
	if !ok {
		if i, ok := params["base"].(int); ok {
			base = float64(i)
		} else {
			return agenkit.NewToolError("missing or invalid 'base' parameter"), nil
		}
	}

	exponent, ok := params["exponent"].(float64)
	if !ok {
		if i, ok := params["exponent"].(int); ok {
			exponent = float64(i)
		} else {
			return agenkit.NewToolError("missing or invalid 'exponent' parameter"), nil
		}
	}

	result := math.Pow(base, exponent)

	return agenkit.NewToolResult(map[string]interface{}{
		"operation": "power",
		"base":      base,
		"exponent":  exponent,
		"result":    result,
	}), nil
}

// SqrtTool computes square root
type SqrtTool struct{}

func (t *SqrtTool) Name() string { return "sqrt" }
func (t *SqrtTool) Description() string { return "Compute square root of a number" }

func (t *SqrtTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	number, ok := params["number"].(float64)
	if !ok {
		if i, ok := params["number"].(int); ok {
			number = float64(i)
		} else {
			return agenkit.NewToolError("missing or invalid 'number' parameter"), nil
		}
	}

	if number < 0 {
		return agenkit.NewToolError("cannot compute square root of negative number"), nil
	}

	result := math.Sqrt(number)

	return agenkit.NewToolResult(map[string]interface{}{
		"operation": "sqrt",
		"input":     number,
		"result":    result,
	}), nil
}

// SimpleAgent that uses tools through direct execution
type SimpleAgent struct {
	name     string
	registry *tools.ToolRegistry
}

func NewSimpleAgent(name string, registry *tools.ToolRegistry) *SimpleAgent {
	return &SimpleAgent{name: name, registry: registry}
}

func (a *SimpleAgent) Name() string { return a.name }
func (a *SimpleAgent) Capabilities() []string { return []string{"math", "calculator"} }

func (a *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simple parsing to extract tool calls from natural language
	content := strings.ToLower(message.Content)

	var result *agenkit.ToolResult
	var err error

	if strings.Contains(content, "add") || strings.Contains(content, "sum") {
		// Example: "add 5 10 15"
		numbers := extractNumbers(content)
		if len(numbers) >= 2 {
			tool, _ := a.registry.Get("add")
			result, err = tool.Execute(ctx, map[string]interface{}{"numbers": numbers})
		}
	} else if strings.Contains(content, "multiply") {
		numbers := extractNumbers(content)
		if len(numbers) >= 2 {
			tool, _ := a.registry.Get("multiply")
			result, err = tool.Execute(ctx, map[string]interface{}{"numbers": numbers})
		}
	} else if strings.Contains(content, "power") || strings.Contains(content, "^") {
		numbers := extractNumbers(content)
		if len(numbers) >= 2 {
			tool, _ := a.registry.Get("power")
			result, err = tool.Execute(ctx, map[string]interface{}{
				"base":     numbers[0],
				"exponent": numbers[1],
			})
		}
	} else if strings.Contains(content, "sqrt") || strings.Contains(content, "square root") {
		numbers := extractNumbers(content)
		if len(numbers) >= 1 {
			tool, _ := a.registry.Get("sqrt")
			result, err = tool.Execute(ctx, map[string]interface{}{"number": numbers[0]})
		}
	}

	if err != nil {
		return nil, err
	}

	if result == nil || !result.Success {
		errorMsg := "Could not parse request"
		if result != nil {
			errorMsg = result.Error
		}
		return agenkit.NewMessage("agent", fmt.Sprintf("Error: %s", errorMsg)), nil
	}

	// Format response
	data := result.Data.(map[string]interface{})
	response := fmt.Sprintf("Result: %v", data["result"])

	return agenkit.NewMessage("agent", response).
		WithMetadata("tool_result", data), nil
}

// Helper function to extract numbers from text
func extractNumbers(text string) []float64 {
	var numbers []float64
	words := strings.Fields(text)

	for _, word := range words {
		var num float64
		_, err := fmt.Sscanf(word, "%f", &num)
		if err == nil {
			numbers = append(numbers, num)
		}
	}

	return numbers
}

// Example 1: Basic arithmetic with tools
func example1BasicMath() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Basic Arithmetic")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: LLMs hallucinate math, tools compute correctly")

	// Create registry and register tools
	registry := tools.NewToolRegistry()
	registry.Register(&AddTool{})
	registry.Register(&MultiplyTool{})

	agent := NewSimpleAgent("calculator", registry)

	tests := []string{
		"add 123 456 789",
		"multiply 17 23",
	}

	ctx := context.Background()

	for _, test := range tests {
		fmt.Printf("\nQuery: %s\n", test)
		result, _ := agent.Process(ctx, agenkit.NewMessage("user", test))
		fmt.Printf("Result: %s\n", result.Content)

		// Show the actual tool data
		if toolResult, ok := result.Metadata["tool_result"].(map[string]interface{}); ok {
			fmt.Printf("  Verification: %v of %v\n", toolResult["operation"], toolResult["inputs"])
		}
	}

	fmt.Println("\nWHY USE TOOLS FOR MATH?")
	fmt.Println("  - LLM might say: '123 + 456 + 789 ≈ 1,350' (wrong!)")
	fmt.Println("  - Tool computes: 123 + 456 + 789 = 1,368 (correct)")
	fmt.Println("  - Deterministic, auditable, accurate")
}

// Example 2: Mathematical functions
func example2MathFunctions() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Mathematical Functions")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: Complex calculations require precision")

	// Create registry with math tools
	registry := tools.NewToolRegistry()
	registry.Register(&PowerTool{})
	registry.Register(&SqrtTool{})

	agent := NewSimpleAgent("math-agent", registry)

	tests := []string{
		"power 2 8",         // 2^8
		"sqrt 144",          // √144
	}

	ctx := context.Background()

	for _, test := range tests {
		fmt.Printf("\nQuery: %s\n", test)
		result, _ := agent.Process(ctx, agenkit.NewMessage("user", test))
		fmt.Printf("Result: %s\n", result.Content)
	}

	fmt.Println("\nWHY TOOLS FOR MATH FUNCTIONS?")
	fmt.Println("  - Exact algorithms (not approximations)")
	fmt.Println("  - Handle edge cases (negative numbers, zero)")
	fmt.Println("  - Consistent with mathematical standards")
}

// Example 3: Tool accuracy vs LLM approximation
func example3Accuracy() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 3: Tool Accuracy")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nComparing tool accuracy with LLM estimation")

	// Create registry
	registry := tools.NewToolRegistry()
	registry.Register(&MultiplyTool{})

	agent := NewSimpleAgent("precise-calculator", registry)

	// Complex calculation
	query := "multiply 17 23 11 13 19"
	fmt.Printf("\nQuery: %s\n", query)

	ctx := context.Background()
	result, _ := agent.Process(ctx, agenkit.NewMessage("user", query))

	toolResult := result.Metadata["tool_result"].(map[string]interface{})
	actual := toolResult["result"].(float64)

	fmt.Printf("Tool result: %.0f\n", actual)
	fmt.Println("\nWhat an LLM might say:")
	fmt.Println("  'That's approximately 1,000,000'")
	fmt.Printf("  (Actually: %.0f)\n", actual)

	llmGuess := 1000000.0
	errorPct := math.Abs(llmGuess-actual) / actual * 100
	fmt.Printf("  Error: %.0f (%.1f%%)\n", math.Abs(llmGuess-actual), errorPct)

	fmt.Println("\nCRITICAL USE CASES REQUIRING TOOLS:")
	fmt.Println("  - Financial calculations (no room for approximation)")
	fmt.Println("  - Scientific computing (precision matters)")
	fmt.Println("  - Legal/compliance (must be exact)")
	fmt.Println("  - Engineering (safety-critical calculations)")
}

func main() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("TOOLS USAGE EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nTools extend agents with deterministic, accurate operations.")
	fmt.Println("Use them when precision matters more than creativity.")

	// Run examples
	example1BasicMath()
	example2MathFunctions()
	example3Accuracy()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. When to use tools:
   - Math: LLMs hallucinate, tools compute correctly
   - External data: Databases, APIs, filesystems
   - Determinism: Need same input → same output
   - Auditability: Tool calls are explicit
   - Cost: Don't waste tokens on calculations

2. Tool design principles:
   - Single responsibility (one tool, one job)
   - Clear description (self-documenting)
   - Proper error handling (ToolResult with success flag)
   - Type safety (validate parameters)

3. Common tool categories:
   - Computation: Math, statistics, data analysis
   - Retrieval: Database queries, API calls, search
   - Transformation: Data format conversion, parsing
   - Integration: External services (Slack, email, CRM)
   - System: File I/O, process management

4. Tool vs LLM decision matrix:
   - Accuracy matters? → Tool
   - Creative task? → LLM
   - External data needed? → Tool
   - Subjective judgment? → LLM
   - Must be deterministic? → Tool
   - Natural language generation? → LLM

5. Best practices:
   - Register tools before agent processes messages
   - Validate all parameters in Execute()
   - Return ToolResult with success flag
   - Include operation details in result data
   - Handle edge cases (empty input, invalid values)

REAL-WORLD TOOL EXAMPLES:
✓ Calculator: Arithmetic, statistics, conversions
✓ Search: Web search, database queries, vector search
✓ Weather: Current conditions, forecasts
✓ Calendar: Schedule meetings, check availability
✓ Database: CRUD operations, queries
✓ Files: Read, write, list, search
✓ APIs: REST calls, GraphQL queries

TRADE-OFF SUMMARY:
✓ Pros: Accurate, deterministic, auditable, cost-efficient
✗ Cons: Development overhead, maintenance, inflexible
→ Choose when: Correctness > flexibility

Next steps:
- See ToolAgent in tools/tool_agent.go for full integration
- Implement custom tools for your domain
- Combine tools with composition patterns
	`)
}
