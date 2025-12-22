// Package main demonstrates the Reflection pattern for iterative refinement.
//
// The Reflection pattern enables agents to progressively improve their outputs
// through an iterative cycle of generation, critique, and refinement.
//
// This example shows:
//   - Setting up generator and critic agents
//   - Configuring reflection parameters (iterations, thresholds)
//   - Executing the reflection loop
//   - Analyzing reflection metadata (iterations, scores, stop reason)
//
// Run with: go run reflection_example.go
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// MockCodeGenerator simulates a code generation agent that improves over iterations
type MockCodeGenerator struct {
	iteration int
}

func (g *MockCodeGenerator) Name() string {
	return "CodeGenerator"
}

func (g *MockCodeGenerator) Capabilities() []string {
	return []string{"code-generation", "python"}
}

func (g *MockCodeGenerator) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    g.Name(),
		Capabilities: g.Capabilities(),
	}
}

func (g *MockCodeGenerator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	g.iteration++

	// Simulate progressive improvement in code quality
	var code string
	switch g.iteration {
	case 1:
		// Initial version - basic but works
		code = `def is_prime(n):
    for i in range(2, n):
        if n % i == 0:
            return False
    return True`

	case 2:
		// Improved version - better edge case handling
		code = `def is_prime(n):
    if n < 2:
        return False
    for i in range(2, n):
        if n % i == 0:
            return False
    return True`

	default:
		// Optimized version - efficient algorithm
		code = `def is_prime(n):
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
	}

	return agenkit.NewMessage("assistant", code), nil
}

// MockCodeCritic simulates a code review agent that provides quality scores
type MockCodeCritic struct{}

func (c *MockCodeCritic) Name() string {
	return "CodeCritic"
}

func (c *MockCodeCritic) Capabilities() []string {
	return []string{"code-review", "quality-assessment"}
}

func (c *MockCodeCritic) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}

func (c *MockCodeCritic) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	code := message.Content

	// Simulate critique based on code features
	var score float64
	var feedback string

	switch {
	case len(code) < 100:
		// Basic implementation
		score = 0.6
		feedback = "Basic implementation. Missing edge case handling (n < 2). Algorithm is inefficient for large numbers."

	case len(code) < 150:
		// Improved implementation
		score = 0.75
		feedback = "Good improvement! Edge cases handled. Still inefficient - checking all numbers up to n is slow. Consider optimizing to sqrt(n)."

	default:
		// Optimized implementation
		score = 0.95
		feedback = "Excellent implementation! Handles edge cases, uses sqrt optimization, and skips even numbers. Well done!"
	}

	critique := fmt.Sprintf(`{"score": %.2f, "feedback": "%s"}`, score, feedback)
	return agenkit.NewMessage("assistant", critique), nil
}

func main() {
	fmt.Println("Reflection Pattern Example: Iterative Code Refinement")
	fmt.Println("======================================================")

	// Create generator and critic agents
	generator := &MockCodeGenerator{}
	critic := &MockCodeCritic{}

	// Create reflection agent with configuration
	reflectionAgent, err := patterns.NewReflectionAgent(patterns.ReflectionConfig{
		Generator:            generator,
		Critic:               critic,
		MaxIterations:        5,                           // Allow up to 5 refinement iterations
		QualityThreshold:     0.9,                         // Stop when score >= 0.9
		ImprovementThreshold: 0.05,                        // Stop if improvement < 0.05
		CritiqueFormat:       patterns.CritiqueStructured, // Expect JSON critique
		Verbose:              true,                        // Include full history in output
	})
	if err != nil {
		log.Fatalf("Failed to create reflection agent: %v", err)
	}

	// Create user request
	request := agenkit.NewMessage("user", "Write a Python function to check if a number is prime")

	fmt.Printf("User Request: %s\n\n", request.Content)
	fmt.Println("Starting reflection loop...")
	fmt.Println("---")

	// Execute reflection loop
	ctx := context.Background()
	result, err := reflectionAgent.Process(ctx, request)
	if err != nil {
		log.Fatalf("Reflection failed: %v", err)
	}

	// Display results
	fmt.Println("\n=== Final Result ===")
	fmt.Printf("\n%s\n\n", result.Content)

	// Extract and display metadata
	fmt.Println("=== Reflection Metadata ===")
	fmt.Printf("Iterations: %v\n", result.Metadata["reflection_iterations"])
	fmt.Printf("Initial Score: %.2f\n", result.Metadata["initial_quality_score"])
	fmt.Printf("Final Score: %.2f\n", result.Metadata["final_quality_score"])
	fmt.Printf("Total Improvement: %.2f\n", result.Metadata["total_improvement"])
	fmt.Printf("Stop Reason: %s\n", result.Metadata["stop_reason"])

	// Display iteration history (if verbose)
	if history, ok := result.Metadata["reflection_history"].([]patterns.ReflectionStep); ok {
		fmt.Println("\n=== Iteration History ===")
		for _, step := range history {
			fmt.Printf("\nIteration %d:\n", step.Iteration)
			fmt.Printf("  Quality Score: %.2f\n", step.QualityScore)
			fmt.Printf("  Improvement: %.2f\n", step.Improvement)
			fmt.Printf("  Critique: %s\n", step.Critique)
		}
	}

	fmt.Println("\n=== Analysis ===")
	fmt.Println("The Reflection pattern demonstrates how agents can:")
	fmt.Println("1. Generate initial outputs")
	fmt.Println("2. Self-critique to identify weaknesses")
	fmt.Println("3. Iteratively refine until quality thresholds are met")
	fmt.Println("4. Automatically stop when improvements plateau")
	fmt.Println("\nThis approach is particularly useful for:")
	fmt.Println("- Code generation with quality requirements")
	fmt.Println("- Content creation needing multiple drafts")
	fmt.Println("- Problem-solving requiring iterative refinement")
	fmt.Println("- Any task where quality improvement justifies additional cost")
}
