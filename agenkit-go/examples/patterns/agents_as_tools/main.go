// Package main demonstrates the Agents-as-Tools pattern for hierarchical delegation.
//
// The Agents-as-Tools pattern enables agents to call other agents as tools,
// creating hierarchical multi-agent systems where specialized agents can be
// invoked by supervisor agents.
//
// This example shows:
//   - Creating specialist agents with domain expertise
//   - Wrapping agents as tools
//   - Using agents as tools in a supervisor pattern
//   - Handling different output formats
//
// Run with: go run agents_as_tools_example.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// CodeSpecialistAgent is a mock agent specialized in code-related tasks
type CodeSpecialistAgent struct {
	name string
}

func (c *CodeSpecialistAgent) Name() string {
	return c.name
}

func (c *CodeSpecialistAgent) Capabilities() []string {
	return []string{"programming", "code-review", "debugging", "python", "go"}
}

func (c *CodeSpecialistAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}

func (c *CodeSpecialistAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	query := strings.ToLower(message.Content)

	var response string
	switch {
	case strings.Contains(query, "fibonacci"):
		response = `def fibonacci(n):
    """Calculate the nth Fibonacci number using dynamic programming."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Example usage:
# print(fibonacci(10))  # Output: 55`

	case strings.Contains(query, "prime"):
		response = `def is_prime(n):
    """Check if a number is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True`

	case strings.Contains(query, "sort"):
		response = `def quicksort(arr):
    """Sort an array using quicksort algorithm."""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)`

	default:
		response = "I'm a code specialist. I can help with programming tasks like algorithms, data structures, and code implementation."
	}

	return agenkit.NewMessage("assistant", response), nil
}

// DataSpecialistAgent is a mock agent specialized in data analysis
type DataSpecialistAgent struct {
	name string
}

func (d *DataSpecialistAgent) Name() string {
	return d.name
}

func (d *DataSpecialistAgent) Capabilities() []string {
	return []string{"data-analysis", "sql", "statistics", "visualization"}
}

func (d *DataSpecialistAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    d.Name(),
		Capabilities: d.Capabilities(),
	}
}

func (d *DataSpecialistAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	query := strings.ToLower(message.Content)

	var response string
	switch {
	case strings.Contains(query, "sql") || strings.Contains(query, "database"):
		response = `SELECT
    customer_id,
    COUNT(*) as total_orders,
    SUM(amount) as total_spent,
    AVG(amount) as avg_order_value
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY customer_id
HAVING COUNT(*) >= 5
ORDER BY total_spent DESC
LIMIT 10;`

	case strings.Contains(query, "average") || strings.Contains(query, "mean"):
		response = "To calculate the mean: sum(values) / len(values)\nFor example: [1,2,3,4,5] → mean = 15/5 = 3.0"

	case strings.Contains(query, "visualiz"):
		response = `import matplotlib.pyplot as plt
import pandas as pd

# Create visualization
df.plot(kind='bar', x='category', y='value', figsize=(10,6))
plt.title('Category Distribution')
plt.xlabel('Category')
plt.ylabel('Value')
plt.show()`

	default:
		response = "I'm a data specialist. I can help with SQL queries, statistical analysis, and data visualization."
	}

	return agenkit.NewMessage("assistant", response), nil
}

// SupervisorAgent simulates a supervisor that delegates to specialists
type SupervisorAgent struct {
	tools map[string]*patterns.AgentTool
}

func NewSupervisorAgent() *SupervisorAgent {
	return &SupervisorAgent{
		tools: make(map[string]*patterns.AgentTool),
	}
}

func (s *SupervisorAgent) RegisterTool(tool *patterns.AgentTool) {
	s.tools[tool.Name()] = tool
}

func (s *SupervisorAgent) Name() string {
	return "SupervisorAgent"
}

func (s *SupervisorAgent) Capabilities() []string {
	return []string{"delegation", "routing", "coordination"}
}

func (s *SupervisorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	query := strings.ToLower(message.Content)

	// Simple routing logic
	var toolName string
	switch {
	case strings.Contains(query, "code") || strings.Contains(query, "function") ||
		strings.Contains(query, "algorithm") || strings.Contains(query, "program"):
		toolName = "code_expert"

	case strings.Contains(query, "data") || strings.Contains(query, "sql") ||
		strings.Contains(query, "analyze") || strings.Contains(query, "query"):
		toolName = "data_expert"

	default:
		return agenkit.NewMessage("assistant",
			"I'm not sure which specialist to route this to. I can help with:\n"+
				"- Code and programming (use code_expert)\n"+
				"- Data analysis and SQL (use data_expert)"), nil
	}

	// Get the appropriate tool
	tool, ok := s.tools[toolName]
	if !ok {
		return nil, fmt.Errorf("tool %s not found", toolName)
	}

	fmt.Printf("  🔀 Supervisor routing to: %s\n", toolName)

	// Delegate to the specialist
	result, err := tool.Execute(ctx, map[string]interface{}{
		"query": message.Content,
	})
	if err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf("tool execution failed: %s", result.Error)
	}

	// Return the specialist's response
	response := fmt.Sprintf("[Delegated to %s]\n\n%s", toolName, result.Data)
	return agenkit.NewMessage("assistant", response), nil
}

func main() {
	fmt.Println("Agents-as-Tools Pattern Example: Hierarchical Delegation")
	fmt.Println("========================================================")

	// Create specialist agents
	codeAgent := &CodeSpecialistAgent{name: "CodeSpecialist"}
	dataAgent := &DataSpecialistAgent{name: "DataSpecialist"}

	fmt.Println("Created specialist agents:")
	fmt.Printf("  - %s: %v\n", codeAgent.Name(), codeAgent.Capabilities())
	fmt.Printf("  - %s: %v\n\n", dataAgent.Name(), dataAgent.Capabilities())

	// Wrap specialists as tools
	codeTool, err := patterns.AgentAsToolSimple(
		codeAgent,
		"code_expert",
		"Expert programmer for code-related tasks, algorithms, and implementations",
	)
	if err != nil {
		log.Fatalf("Failed to create code tool: %v", err)
	}

	dataTool, err := patterns.AgentAsToolSimple(
		dataAgent,
		"data_expert",
		"Expert data analyst for SQL queries, statistics, and visualization",
	)
	if err != nil {
		log.Fatalf("Failed to create data tool: %v", err)
	}

	fmt.Println("Wrapped specialists as tools:")
	fmt.Printf("  - %s\n", codeTool)
	fmt.Printf("  - %s\n\n", dataTool)

	// Create supervisor and register tools
	supervisor := NewSupervisorAgent()
	supervisor.RegisterTool(codeTool)
	supervisor.RegisterTool(dataTool)

	fmt.Println("Supervisor registered with specialist tools")
	fmt.Println("=" + strings.Repeat("=", 70))

	// Test cases demonstrating delegation
	testCases := []struct {
		description string
		query       string
	}{
		{
			description: "Code Task → Routes to Code Specialist",
			query:       "Write a function to calculate Fibonacci numbers",
		},
		{
			description: "Data Task → Routes to Data Specialist",
			query:       "Write a SQL query to analyze customer orders",
		},
		{
			description: "Code Task → Routes to Code Specialist",
			query:       "Implement a prime number checker",
		},
		{
			description: "Data Task → Routes to Data Specialist",
			query:       "Show me how to visualize data with Python",
		},
	}

	ctx := context.Background()

	for i, tc := range testCases {
		fmt.Printf("\n\nTest Case %d: %s\n", i+1, tc.description)
		fmt.Println(strings.Repeat("-", 70))
		fmt.Printf("Query: %s\n\n", tc.query)

		message := agenkit.NewMessage("user", tc.query)
		result, err := supervisor.Process(ctx, message)
		if err != nil {
			log.Printf("Error: %v", err)
			continue
		}

		fmt.Printf("Response:\n%s\n", result.Content)
	}

	// Demonstrate direct tool usage (without supervisor)
	fmt.Println("\n\n" + strings.Repeat("=", 70))
	fmt.Println("\nDirect Tool Usage (bypassing supervisor):")
	fmt.Println(strings.Repeat("-", 70))

	directResult, err := codeTool.Execute(ctx, map[string]interface{}{
		"query": "Implement quicksort",
	})
	if err != nil {
		log.Fatalf("Direct tool execution failed: %v", err)
	}

	fmt.Printf("Direct call to code_expert:\n%s\n", directResult.Data)

	// Summary
	fmt.Println("\n\n" + strings.Repeat("=", 70))
	fmt.Println("Summary")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("\nThe Agents-as-Tools pattern enables:")
	fmt.Println("1. Hierarchical multi-agent systems")
	fmt.Println("2. Supervisor agents that delegate to specialists")
	fmt.Println("3. Domain-specific routing and specialization")
	fmt.Println("4. Reusable agent components")
	fmt.Println("\nBest Practices:")
	fmt.Println("- Give agents clear, focused specializations")
	fmt.Println("- Use descriptive tool names and descriptions")
	fmt.Println("- Implement intelligent routing in supervisors")
	fmt.Println("- Maintain observability through metadata")
	fmt.Println("\nUse Cases:")
	fmt.Println("- Multi-domain problem solving")
	fmt.Println("- Complex task decomposition")
	fmt.Println("- Agent specialization and expertise")
	fmt.Println("- Scalable agent architectures")
}
