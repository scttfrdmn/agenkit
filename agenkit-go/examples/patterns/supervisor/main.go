// Package main demonstrates the Supervisor pattern for hierarchical coordination.
//
// The Supervisor pattern uses a central planner to decompose tasks,
// delegate to specialist agents, and synthesize results. This enables
// complex multi-agent workflows with centralized orchestration.
//
// This example shows:
//   - Task decomposition and delegation
//   - Specialist agent coordination
//   - Result synthesis
//   - Software development workflow (code, test, review)
//
// Run with: go run supervisor_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// CoderAgent writes code
type CoderAgent struct{}

func (c *CoderAgent) Name() string {
	return "Coder"
}

func (c *CoderAgent) Capabilities() []string {
	return []string{"coding", "implementation"}
}

func (c *CoderAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}

func (c *CoderAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   💻 Coder implementing...")

	// Simulate code generation
	code := `func Add(a, b int) int {
    return a + b
}

func Multiply(a, b int) int {
    return a * b
}

func Calculate(operation string, a, b int) (int, error) {
    switch operation {
    case "add":
        return Add(a, b), nil
    case "multiply":
        return Multiply(a, b), nil
    default:
        return 0, fmt.Errorf("unknown operation: %s", operation)
    }
}`

	response := fmt.Sprintf("Code Implementation:\n\n```go\n%s\n```\n\nImplemented requested functionality.", code)

	result := agenkit.NewMessage("agent", response)
	result.WithMetadata("specialist", "coder").
		WithMetadata("lines_of_code", 15)

	fmt.Println("   ✓ Code generated")
	return result, nil
}

// TesterAgent writes and runs tests
type TesterAgent struct{}

func (t *TesterAgent) Name() string {
	return "Tester"
}

func (t *TesterAgent) Capabilities() []string {
	return []string{"testing", "quality-assurance"}
}

func (t *TesterAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    t.Name(),
		Capabilities: t.Capabilities(),
	}
}

func (t *TesterAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   🧪 Tester creating tests...")

	// Simulate test generation
	tests := `func TestAdd(t *testing.T) {
    result := Add(2, 3)
    if result != 5 {
        t.Errorf("Add(2, 3) = %d; want 5", result)
    }
}

func TestMultiply(t *testing.T) {
    result := Multiply(4, 5)
    if result != 20 {
        t.Errorf("Multiply(4, 5) = %d; want 20", result)
    }
}

func TestCalculate(t *testing.T) {
    tests := []struct{
        op   string
        a, b int
        want int
    }{
        {"add", 1, 2, 3},
        {"multiply", 3, 4, 12},
    }

    for _, tt := range tests {
        got, err := Calculate(tt.op, tt.a, tt.b)
        if err != nil {
            t.Errorf("Calculate(%s, %d, %d) error: %v", tt.op, tt.a, tt.b, err)
        }
        if got != tt.want {
            t.Errorf("Calculate(%s, %d, %d) = %d; want %d", tt.op, tt.a, tt.b, got, tt.want)
        }
    }
}`

	response := fmt.Sprintf("Test Suite:\n\n```go\n%s\n```\n\nAll tests passing ✓", tests)

	result := agenkit.NewMessage("agent", response)
	result.WithMetadata("specialist", "tester").
		WithMetadata("test_count", 3).
		WithMetadata("coverage", 100)

	fmt.Println("   ✓ Tests created and passed")
	return result, nil
}

// ReviewerAgent performs code review
type ReviewerAgent struct{}

func (r *ReviewerAgent) Name() string {
	return "Reviewer"
}

func (r *ReviewerAgent) Capabilities() []string {
	return []string{"review", "quality-check"}
}

func (r *ReviewerAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    r.Name(),
		Capabilities: r.Capabilities(),
	}
}

func (r *ReviewerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   👀 Reviewer analyzing...")

	review := `Code Review Report:

✅ APPROVED

Strengths:
- Clear function names and signatures
- Proper error handling in Calculate
- Good separation of concerns
- Comprehensive test coverage

Suggestions:
- Consider adding input validation
- Add documentation comments
- Consider edge cases (overflow)

Overall: Well-structured implementation with solid testing.
Ready for merge.`

	result := agenkit.NewMessage("agent", review)
	result.WithMetadata("specialist", "reviewer").
		WithMetadata("status", "approved").
		WithMetadata("issues_found", 0)

	fmt.Println("   ✓ Review completed")
	return result, nil
}

// SoftwarePlannerAgent orchestrates development workflow
type SoftwarePlannerAgent struct {
	agent agenkit.Agent
}

func NewSoftwarePlannerAgent() *SoftwarePlannerAgent {
	return &SoftwarePlannerAgent{
		agent: &MockLLMAgent{},
	}
}

func (s *SoftwarePlannerAgent) Name() string {
	return "SoftwarePlanner"
}

func (s *SoftwarePlannerAgent) Capabilities() []string {
	return []string{"planning", "synthesis", "coordination"}
}

func (s *SoftwarePlannerAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    s.Name(),
		Capabilities: s.Capabilities(),
	}
}

func (s *SoftwarePlannerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return s.agent.Process(ctx, message)
}

func (s *SoftwarePlannerAgent) Plan(ctx context.Context, message *agenkit.Message) ([]patterns.Subtask, error) {
	fmt.Println("\n🎯 Planner decomposing task...")

	// Parse the task and create subtasks
	subtasks := []patterns.Subtask{
		{
			Type:    "coder",
			Message: agenkit.NewMessage("user", "Implement calculator functions: Add, Multiply, Calculate"),
			Metadata: map[string]interface{}{
				"priority": "high",
				"phase":    "implementation",
			},
		},
		{
			Type:    "tester",
			Message: agenkit.NewMessage("user", "Create comprehensive tests for calculator functions"),
			Metadata: map[string]interface{}{
				"priority": "high",
				"phase":    "testing",
			},
		},
		{
			Type:    "reviewer",
			Message: agenkit.NewMessage("user", "Review code and tests for quality and correctness"),
			Metadata: map[string]interface{}{
				"priority": "medium",
				"phase":    "review",
			},
		},
	}

	fmt.Printf("   ✓ Created %d subtasks: code → test → review\n", len(subtasks))
	return subtasks, nil
}

func (s *SoftwarePlannerAgent) Synthesize(ctx context.Context, original *agenkit.Message, results map[string]*agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("\n📊 Planner synthesizing results...")

	var synthesis strings.Builder
	synthesis.WriteString("=== Software Development Summary ===\n\n")

	synthesis.WriteString("Task: ")
	synthesis.WriteString(original.Content)
	synthesis.WriteString("\n\n")

	// Organize results by phase
	phases := []struct {
		prefix string
		title  string
	}{
		{"coder_", "Implementation Phase"},
		{"tester_", "Testing Phase"},
		{"reviewer_", "Review Phase"},
	}

	for _, phase := range phases {
		synthesis.WriteString(fmt.Sprintf("%s:\n", phase.title))

		for key, result := range results {
			if strings.HasPrefix(key, phase.prefix) {
				// Extract key information
				if specialist, ok := result.Metadata["specialist"].(string); ok {
					synthesis.WriteString(fmt.Sprintf("  ✓ %s completed\n", specialist))
				}

				// Add phase-specific metrics
				switch phase.prefix {
				case "coder_":
					if loc, ok := result.Metadata["lines_of_code"].(int); ok {
						synthesis.WriteString(fmt.Sprintf("    Lines of code: %d\n", loc))
					}
				case "tester_":
					if tests, ok := result.Metadata["test_count"].(int); ok {
						synthesis.WriteString(fmt.Sprintf("    Tests created: %d\n", tests))
					}
					if coverage, ok := result.Metadata["coverage"].(int); ok {
						synthesis.WriteString(fmt.Sprintf("    Coverage: %d%%\n", coverage))
					}
				case "reviewer_":
					if status, ok := result.Metadata["status"].(string); ok {
						synthesis.WriteString(fmt.Sprintf("    Status: %s\n", status))
					}
				}
			}
		}
		synthesis.WriteString("\n")
	}

	synthesis.WriteString("Outcome: All phases completed successfully.\n")
	synthesis.WriteString("Status: Ready for deployment ✅")

	fmt.Println("   ✓ Results synthesized")

	return agenkit.NewMessage("agent", synthesis.String()), nil
}

// MockLLMAgent for basic agent behavior
type MockLLMAgent struct{}

func (m *MockLLMAgent) Name() string {
	return "MockLLM"
}

func (m *MockLLMAgent) Capabilities() []string {
	return []string{"llm"}
}

func (m *MockLLMAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockLLMAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "Processed by LLM"), nil
}

func main() {
	fmt.Println("=== Supervisor Pattern Demo ===")
	fmt.Println("Demonstrating hierarchical agent coordination")

	ctx := context.Background()

	// Example 1: Software development workflow
	fmt.Println("📊 Example 1: Software Development Workflow")
	fmt.Println(strings.Repeat("-", 50))

	// Create specialist agents
	specialists := map[string]agenkit.Agent{
		"coder":    &CoderAgent{},
		"tester":   &TesterAgent{},
		"reviewer": &ReviewerAgent{},
	}

	// Create planner
	planner := NewSoftwarePlannerAgent()

	// Create supervisor
	supervisor, err := patterns.NewSupervisorAgent(planner, specialists)
	if err != nil {
		log.Fatalf("Failed to create supervisor: %v", err)
	}

	fmt.Println("Supervisor configured with:")
	fmt.Println("  Planner: SoftwarePlanner")
	fmt.Println("  Specialists: Coder, Tester, Reviewer")

	// Execute development task
	task := agenkit.NewMessage("user",
		"Create a calculator module with Add, Multiply, and Calculate functions")

	fmt.Printf("\n📥 Task: %s\n", task.Content)

	result, err := supervisor.Process(ctx, task)
	if err != nil {
		log.Fatalf("Supervisor failed: %v", err)
	}

	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📤 Final Result:")
	fmt.Println(result.Content)

	// Display supervisor metadata
	if subtasks, ok := result.Metadata["supervisor_subtasks"].(int); ok {
		fmt.Printf("\nSupervisor Metrics:\n")
		fmt.Printf("  Subtasks: %d\n", subtasks)
	}
	if specialists, ok := result.Metadata["supervisor_specialists"].(int); ok {
		fmt.Printf("  Specialists: %d\n", specialists)
	}

	// Example 2: Simple planner (no decomposition)
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 2: Simple Task (No Decomposition)")
	fmt.Println(strings.Repeat("-", 50))

	simplePlanner := patterns.NewSimplePlanner(&MockLLMAgent{})

	simpleSupervisor, err := patterns.NewSupervisorAgent(
		simplePlanner,
		specialists,
	)
	if err != nil {
		log.Fatalf("Failed to create simple supervisor: %v", err)
	}

	simpleTask := agenkit.NewMessage("user", "Simple task that doesn't need decomposition")

	fmt.Printf("\n📥 Task: %s\n", simpleTask.Content)

	_, err = simpleSupervisor.Process(ctx, simpleTask)
	if err != nil {
		log.Fatalf("Simple supervisor failed: %v", err)
	}

	fmt.Printf("\n📤 Result: Task handled directly by planner (no specialists needed)\n")

	// Example 3: Validating specialist availability
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 3: Unknown Specialist Detection")
	fmt.Println(strings.Repeat("-", 50))

	// Create a planner that requests unknown specialist
	badPlanner := &BadPlannerAgent{}

	badSupervisor, err := patterns.NewSupervisorAgent(
		badPlanner,
		specialists,
	)
	if err != nil {
		log.Fatalf("Failed to create bad supervisor: %v", err)
	}

	fmt.Println("\nAttempting task with unknown specialist...")

	_, err = badSupervisor.Process(ctx, task)
	if err != nil {
		fmt.Printf("   ✓ Correctly detected unknown specialist: %v\n", err)
	}

	fmt.Println("\n✅ Supervisor pattern demo complete!")
}

// BadPlannerAgent for testing error handling
type BadPlannerAgent struct{}

func (b *BadPlannerAgent) Name() string {
	return "BadPlanner"
}

func (b *BadPlannerAgent) Capabilities() []string {
	return []string{"planning"}
}

func (b *BadPlannerAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    b.Name(),
		Capabilities: b.Capabilities(),
	}
}

func (b *BadPlannerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "Processed"), nil
}

func (b *BadPlannerAgent) Plan(ctx context.Context, message *agenkit.Message) ([]patterns.Subtask, error) {
	// Return subtask for non-existent specialist
	return []patterns.Subtask{
		{
			Type:    "unknown_specialist",
			Message: agenkit.NewMessage("user", "This should fail"),
		},
	}, nil
}

func (b *BadPlannerAgent) Synthesize(ctx context.Context, original *agenkit.Message, results map[string]*agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "Synthesized"), nil
}
