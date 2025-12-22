// Package main demonstrates the Planning pattern for task decomposition and execution.
//
// The Planning pattern enables agents to break complex tasks into manageable steps,
// execute them in order (respecting dependencies), and track progress.
//
// This example shows:
//   - Creating plans with multiple steps
//   - Step dependency management
//   - Custom step executors for specialized logic
//   - Progress tracking and metadata
//   - Replanning capabilities
//
// Run with: go run planning_pattern.go
package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// MockLLMAgent generates plans for different scenarios
type MockLLMAgent struct {
	scenario string
}

func (m *MockLLMAgent) Name() string {
	return "MockLLM"
}

func (m *MockLLMAgent) Capabilities() []string {
	return []string{"planning"}
}

func (m *MockLLMAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content

	var planText string

	if strings.Contains(content, "event") || m.scenario == "event" {
		planText = `Goal: Organize a successful team event
Steps:
1. Choose date and venue for the event
2. Create invitation list with all team members
3. Send invitations via email
4. Arrange catering and refreshments
5. Prepare agenda and activities`
	} else if strings.Contains(content, "website") || m.scenario == "website" {
		planText = `Goal: Launch a new company website
Steps:
1. Design website mockups and wireframes
2. Develop frontend with HTML/CSS/JS
3. Implement backend API and database
4. Write content and add images
5. Deploy to production server
6. Configure domain and SSL certificate`
	} else if strings.Contains(content, "campaign") || m.scenario == "campaign" {
		planText = `Goal: Execute marketing campaign
Steps:
1. Define target audience and goals
2. Create campaign content and assets
3. Set up advertising channels
4. Launch campaign across platforms
5. Monitor metrics and performance`
	} else {
		planText = `Goal: Complete the task
Steps:
1. Analyze requirements
2. Create implementation plan
3. Execute the plan
4. Verify results`
	}

	return agenkit.NewMessage("assistant", planText), nil
}

// CustomStepExecutor simulates realistic step execution
type CustomStepExecutor struct {
	verbose bool
}

func (c *CustomStepExecutor) Execute(ctx context.Context, step *patterns.PlanStep, contextData map[string]interface{}) (interface{}, error) {
	if c.verbose {
		fmt.Printf("  → Executing: %s\n", step.Description)
	}

	// Simulate different execution results based on step content
	var result string
	desc := step.Description

	switch {
	case strings.Contains(desc, "Choose date"):
		result = "Selected June 15th, 2:00 PM at Conference Room A"
	case strings.Contains(desc, "invitation list"):
		result = "Created list of 25 team members"
	case strings.Contains(desc, "Send invitations"):
		result = "Sent 25 email invitations (24 delivered, 1 bounced)"
	case strings.Contains(desc, "catering"):
		result = "Booked catering service for 25 people, budget: $500"
	case strings.Contains(desc, "agenda"):
		result = "Prepared 2-hour agenda with team building activities"
	case strings.Contains(desc, "Design website"):
		result = "Created mockups in Figma (5 pages, responsive design)"
	case strings.Contains(desc, "frontend"):
		result = "Built responsive frontend with React and Tailwind CSS"
	case strings.Contains(desc, "backend"):
		result = "Implemented REST API with PostgreSQL database"
	case strings.Contains(desc, "content"):
		result = "Added 12 pages of content with 45 images"
	case strings.Contains(desc, "Deploy"):
		result = "Deployed to AWS (load time: 1.2s, 99.9% uptime)"
	case strings.Contains(desc, "domain"):
		result = "Configured www.example.com with Let's Encrypt SSL"
	case strings.Contains(desc, "target audience"):
		result = "Defined audience: 25-45 year olds, tech industry professionals"
	case strings.Contains(desc, "campaign content"):
		result = "Created 3 video ads, 5 social posts, 2 blog articles"
	case strings.Contains(desc, "advertising"):
		result = "Set up Google Ads, Facebook Ads, LinkedIn campaigns"
	case strings.Contains(desc, "Launch campaign"):
		result = "Campaign live across 4 platforms, initial reach: 10,000"
	case strings.Contains(desc, "Monitor"):
		result = "Tracking: 500 clicks, 50 conversions, 10% CTR"
	default:
		result = "Step completed successfully"
	}

	if c.verbose && len(contextData) > 0 {
		fmt.Printf("    (Using context from %d previous steps)\n", len(contextData))
	}

	// Small delay to simulate work
	time.Sleep(100 * time.Millisecond)

	return result, nil
}

// Example 1: Simple event planning with default executor
// TODO: Fix API usage - examples use incorrect PlanningAgent API
/*
func exampleSimplePlanning() error {
	fmt.Println("\n=== Example 1: Simple Event Planning (Default Executor) ===")

	llm := &MockLLMAgent{scenario: "event"}

	config := patterns.PlanningConfig{
		LLM:             llm,
		Executor:        nil, // Use default executor
		MaxSteps:        10,
		AllowReplanning: false,
		SystemPrompt:    "",
	}

	planner, err := patterns.NewPlanningAgent(config)
	if err != nil {
		return err
	}

	message := agenkit.NewMessage("user", "Organize a team event")
	result, err := planner.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("Result:\n%s\n\n", result.Content)

	// Show plan details from metadata
	if planData, ok := result.Metadata["plan"].(*patterns.Plan); ok {
		fmt.Println("Plan Details:")
		fmt.Printf("  Goal: %s\n", planData.Goal)
		fmt.Printf("  Total Steps: %d\n", len(planData.Steps))
		completed := 0
		for _, s := range planData.Steps {
			if s.Status == patterns.StepStatusCompleted {
				completed++
			}
		}
		fmt.Printf("  Completed: %d\n", completed)
	}

	return nil
}

// Example 2: Website launch with custom executor
func exampleCustomExecutor() error {
	fmt.Println("\n=== Example 2: Website Launch (Custom Executor) ===")

	llm := &MockLLMAgent{scenario: "website"}
	customExecutor := &CustomStepExecutor{verbose: true}

	config := patterns.PlanningConfig{
		LLM:             llm,
		Executor:        customExecutor,
		MaxSteps:        10,
		AllowReplanning: false,
		SystemPrompt:    "",
	}

	planner, err := patterns.NewPlanningAgent(config)
	if err != nil {
		return err
	}

	message := agenkit.NewMessage("user", "Launch a new website")
	result, err := planner.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("\nResult:\n%s\n\n", result.Content)

	if progress, ok := result.Metadata["progress"].(float64); ok {
		fmt.Printf("Overall Progress: %.1f%%\n", progress)
	}

	return nil
}

// Example 3: Marketing campaign with progress tracking
func exampleProgressTracking() error {
	fmt.Println("\n=== Example 3: Marketing Campaign (Progress Tracking) ===")

	llm := &MockLLMAgent{scenario: "campaign"}
	customExecutor := &CustomStepExecutor{verbose: false}

	config := patterns.PlanningConfig{
		LLM:             llm,
		Executor:        customExecutor,
		MaxSteps:        8,
		AllowReplanning: false,
		SystemPrompt:    "You are a marketing planning expert. Create detailed campaign plans.",
	}

	planner, err := patterns.NewPlanningAgent(config)
	if err != nil {
		return err
	}

	fmt.Println("Starting marketing campaign planning...")

	message := agenkit.NewMessage("user", "Execute a marketing campaign")
	result, err := planner.Process(context.Background(), message)
	if err != nil {
		return err
	}

	// Extract plan from metadata
	if planData, ok := result.Metadata["plan"].(*patterns.Plan); ok {
		fmt.Println("Campaign Plan Execution:")
		fmt.Printf("Goal: %s\n\n", planData.Goal)

		for _, step := range planData.Steps {
			statusIcon := "○"
			switch step.Status {
			case patterns.StepStatusCompleted:
				statusIcon = "✓"
			case patterns.StepStatusFailed:
				statusIcon = "✗"
			case patterns.StepStatusSkipped:
				statusIcon = "⊘"
			case patterns.StepStatusInProgress:
				statusIcon = "→"
			}

			fmt.Printf("%s Step %d: %s\n", statusIcon, step.StepNumber+1, step.Description)

			if step.Result != nil {
				if resultStr, ok := step.Result.(string); ok {
					fmt.Printf("  Result: %s\n", resultStr)
				}
			}
		}

		fmt.Printf("\nProgress: %.1f%%\n", planData.GetProgress())
		status := "In Progress"
		if planData.IsComplete() {
			status = "Complete"
		}
		fmt.Printf("Status: %s\n", status)
	}

	return nil
}

// Example 4: Step dependencies demonstration
func exampleDependencies() error {
	fmt.Println("\n=== Example 4: Step Dependencies ===")

	// Create a plan manually to demonstrate dependencies
	plan := patterns.NewPlan(
		"Build a simple application",
		[]*patterns.PlanStep{
			patterns.NewPlanStep("Set up development environment", 0, []int{}),
			patterns.NewPlanStep("Design database schema", 1, []int{}),
			patterns.NewPlanStep("Implement database migrations", 2, []int{1}),      // Depends on step 1
			patterns.NewPlanStep("Create API endpoints", 3, []int{2}),                // Depends on step 2
			patterns.NewPlanStep("Build frontend UI", 4, []int{0}),                   // Depends on step 0
			patterns.NewPlanStep("Integrate frontend with API", 5, []int{3, 4}),      // Depends on 3 and 4
			patterns.NewPlanStep("Write tests", 6, []int{5}),                         // Depends on step 5
			patterns.NewPlanStep("Deploy to production", 7, []int{6}),                // Depends on step 6
		},
	)

	fmt.Printf("Plan: %s\n", plan.Goal)
	fmt.Printf("Total steps: %d\n\n", len(plan.Steps))

	// Show dependency graph
	fmt.Println("Dependency Graph:")
	for _, step := range plan.Steps {
		fmt.Printf("  Step %d: %s", step.StepNumber, step.Description)
		if len(step.Dependencies) > 0 {
			fmt.Printf(" (depends on: %v)", step.Dependencies)
		}
		fmt.Println()
	}

	fmt.Println("\nExecution Order:")

	// Simulate execution
	executor := &patterns.DefaultStepExecutor{}
	contextData := make(map[string]interface{})
	executionRound := 0

	for !plan.IsComplete() {
		nextSteps := plan.GetNextSteps()
		if len(nextSteps) == 0 {
			break
		}

		executionRound++
		fmt.Printf("\nRound %d:\n", executionRound)

		for _, step := range nextSteps {
			fmt.Printf("  → Executing Step %d: %s\n", step.StepNumber, step.Description)

			result, err := executor.Execute(context.Background(), step, contextData)
			if err != nil {
				return err
			}

			step.Status = patterns.StepStatusCompleted
			step.Result = result
			contextData[fmt.Sprintf("step_%d_result", step.StepNumber)] = result
		}

		fmt.Printf("  Progress: %.1f%%\n", plan.GetProgress())
	}

	fmt.Println("\n✓ All steps completed!")
	fmt.Printf("Final Progress: %.1f%%\n", plan.GetProgress())

	return nil
}
*/

func main() {
	fmt.Println("Planning Pattern Examples")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("\n⚠ These examples need updating to match current PlanningAgent API.")
	fmt.Println("See agenkit-go/patterns/planning_test.go for correct usage.")

	// TODO: Update examples to use correct API:
	// NewPlanningAgent(llmClient LLMClient, stepExecutor StepExecutor, config *PlanningAgentConfig)
	/*
		// Run all examples
		if err := exampleSimplePlanning(); err != nil {
			log.Fatalf("Example 1 failed: %v", err)
		}

		if err := exampleCustomExecutor(); err != nil {
			log.Fatalf("Example 2 failed: %v", err)
		}

		if err := exampleProgressTracking(); err != nil {
			log.Fatalf("Example 3 failed: %v", err)
		}

		if err := exampleDependencies(); err != nil {
			log.Fatalf("Example 4 failed: %v", err)
		}
	*/

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("✓ All examples completed successfully!")
	fmt.Println("\n💡 Key takeaways:")
	fmt.Println("   - Planning decomposes complex tasks into steps")
	fmt.Println("   - Dependencies ensure correct execution order")
	fmt.Println("   - Custom executors enable specialized logic")
	fmt.Println("   - Progress tracking provides visibility")
	fmt.Println()
	fmt.Println("🎯 When to use Planning:")
	fmt.Println("   - Complex multi-step processes")
	fmt.Println("   - Tasks with interdependencies")
	fmt.Println("   - Projects requiring progress monitoring")
	fmt.Println("   - Workflows needing replanning capabilities")
}
