// Package main demonstrates the Autonomous pattern for self-directed agents.
//
// The Autonomous pattern enables goal-directed agents that operate independently
// with minimal human intervention, managing their own objectives and execution.
//
// This example shows:
//   - Creating autonomous agents with objectives and goals
//   - Priority-based goal selection
//   - Custom worker functions for goal execution
//   - Stop conditions and manual termination
//   - Progress tracking and lifecycle management
//
// Run with: go run autonomous_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync/atomic"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// Example 1: Basic autonomous agent
func exampleBasic() error {
	fmt.Println("\n=== Example 1: Basic Autonomous Agent ===")

	agent := patterns.NewAutonomousAgent("Complete research project", 10)

	fmt.Printf("Objective: %s\n", agent.GetObjective())
	fmt.Printf("Max iterations: %d\n\n", 10) // maxIterations is not exposed via getter

	agent.AddGoal("Literature review", 10)
	agent.AddGoal("Data collection", 8)
	agent.AddGoal("Analysis", 5)
	agent.AddGoal("Write paper", 3)

	fmt.Printf("Goals added: %d\n", len(agent.GetGoals()))
	for _, goal := range agent.GetGoals() {
		fmt.Printf("  - %s (priority: %d)\n", goal.Description, goal.Priority)
	}

	fmt.Println("\nRunning agent...")
	result, err := agent.Run(context.Background())
	if err != nil {
		return err
	}

	fmt.Println("Result:")
	fmt.Printf("  Objective: %s\n", result.Objective)
	fmt.Printf("  Iterations: %d\n", result.Iterations)
	fmt.Printf("  Goals completed: %d/%d\n", result.GoalsCompleted, len(agent.GetGoals()))
	fmt.Printf("\nProgress: %.1f%%\n", agent.GetProgress())

	return nil
}

// Example 2: Custom worker function
func exampleCustomWorker() error {
	fmt.Println("\n=== Example 2: Custom Worker Function ===")

	agent := patterns.NewAutonomousAgent("Build web application", 15)

	agent.AddGoal("Design database schema", 10)
	agent.AddGoal("Create API endpoints", 8)
	agent.AddGoal("Build frontend", 6)
	agent.AddGoal("Write tests", 4)
	agent.AddGoal("Deploy to production", 2)

	// Custom worker that simulates detailed work
	agent.SetWorker(func(ctx context.Context, goal *patterns.Goal) (string, error) {
		var workDone string
		switch {
		case strings.Contains(goal.Description, "database"):
			workDone = "Defined tables, relationships, and indexes"
		case strings.Contains(goal.Description, "API"):
			workDone = "Implemented REST endpoints with validation"
		case strings.Contains(goal.Description, "frontend"):
			workDone = "Created React components and routing"
		case strings.Contains(goal.Description, "tests"):
			workDone = "Wrote unit and integration tests"
		case strings.Contains(goal.Description, "Deploy"):
			workDone = "Configured CI/CD and deployed to AWS"
		default:
			workDone = "Made progress on task"
		}

		return fmt.Sprintf("%s: %s", goal.Description, workDone), nil
	})

	fmt.Println("Running agent with custom worker...")
	result, err := agent.Run(context.Background())
	if err != nil {
		return err
	}

	fmt.Println("Work completed:")
	for i, work := range result.Results {
		fmt.Printf("  %d. %s\n", i+1, work)
	}

	fmt.Printf("\nFinal progress: %.1f%%\n", agent.GetProgress())

	return nil
}

// Example 3: Priority-based goal selection
func examplePriority() error {
	fmt.Println("\n=== Example 3: Priority-Based Goal Selection ===")

	agent := patterns.NewAutonomousAgent("Incident response", 12)

	agent.AddGoal("Document findings", 2)
	agent.AddGoal("Notify stakeholders", 5)
	agent.AddGoal("Fix critical bug", 10) // Highest priority
	agent.AddGoal("Write post-mortem", 1)

	fmt.Println("Goals (with priorities):")
	for _, goal := range agent.GetGoals() {
		fmt.Printf("  - %s [priority: %d]\n", goal.Description, goal.Priority)
	}

	fmt.Println("\nAgent will work on highest priority goals first...")

	result, err := agent.Run(context.Background())
	if err != nil {
		return err
	}

	fmt.Printf("Goals completed: %d\n", result.GoalsCompleted)
	fmt.Println("\nFirst 3 iterations (should prioritize 'Fix critical bug'):")
	for i, work := range result.Results {
		if i >= 3 {
			break
		}
		fmt.Printf("  %d. %s\n", i+1, work)
	}

	return nil
}

// Example 4: Stop condition
func exampleStopCondition() error {
	fmt.Println("\n=== Example 4: Stop Condition ===")

	agent := patterns.NewAutonomousAgent("Long-running task", 100)
	agent.AddGoal("Process data", 10)

	var processedItems int32
	target := int32(50)

	// Stop after processing 50 items
	agent.SetStopCondition(func() bool {
		return atomic.LoadInt32(&processedItems) >= target
	})

	agent.SetWorker(func(ctx context.Context, goal *patterns.Goal) (string, error) {
		count := atomic.AddInt32(&processedItems, 10)
		return fmt.Sprintf("%s: Processed %d items", goal.Description, count), nil
	})

	fmt.Println("Target: Process 50 items")
	fmt.Println("Max iterations: 100")
	fmt.Println("\nRunning with stop condition...")

	result, err := agent.Run(context.Background())
	if err != nil {
		return err
	}

	fmt.Printf("Stopped after %d iterations (target reached)\n", result.Iterations)
	fmt.Println("Well before max_iterations=100!")

	return nil
}

// Example 5: Manual stop
func exampleManualStop() error {
	fmt.Println("\n=== Example 5: Manual Stop ===")

	agent := patterns.NewAutonomousAgent("Continuous monitoring", 1000)
	agent.AddGoal("Monitor system health", 10)

	// Spawn goroutine to stop agent after 200ms
	go func() {
		time.Sleep(200 * time.Millisecond)
		fmt.Println("  [External trigger] Stopping agent...")
		agent.Stop()
	}()

	fmt.Println("Starting continuous monitoring...")
	fmt.Println("(will be stopped externally after 200ms)")

	result, err := agent.Run(context.Background())
	if err != nil {
		return err
	}

	fmt.Printf("\nAgent stopped after %d iterations\n", result.Iterations)
	fmt.Println("(manually stopped before reaching max_iterations=1000)")

	return nil
}

// Example 6: Progress tracking
func exampleProgressTracking() error {
	fmt.Println("\n=== Example 6: Progress Tracking ===")

	agent := patterns.NewAutonomousAgent("Software release", 20)

	agent.AddGoal("Code freeze", 10)
	agent.AddGoal("QA testing", 8)
	agent.AddGoal("Documentation", 5)
	agent.AddGoal("Release notes", 3)

	fmt.Println("Tracking progress during execution:")

	// Run agent
	result, err := agent.Run(context.Background())
	if err != nil {
		return err
	}

	fmt.Printf("Phase 1: %.1f%% complete\n", agent.GetProgress())
	fmt.Printf("  Iterations: %d\n", result.Iterations)
	fmt.Printf("  Goals completed: %d/%d\n", result.GoalsCompleted, len(agent.GetGoals()))

	fmt.Println("\n✓ Release complete!")

	return nil
}

// Example 7: Goal lifecycle
func exampleGoalLifecycle() error {
	fmt.Println("\n=== Example 7: Goal Lifecycle ===")

	agent := patterns.NewAutonomousAgent("Study project lifecycle", 6)

	goal := agent.AddGoal("Learn Go", 10)

	fmt.Println("New goal created:")
	fmt.Printf("  Description: %s\n", goal.Description)
	fmt.Printf("  Priority: %d\n", goal.Priority)
	fmt.Printf("  Status: %s\n", goal.Status)
	fmt.Printf("  Progress: %.0f%%\n", goal.Progress*100)
	fmt.Printf("  Created at: %s\n\n", goal.CreatedAt.Format(time.RFC3339))

	fmt.Println("Running agent...")
	result, err := agent.Run(context.Background())
	if err != nil {
		return err
	}

	fmt.Printf("After %d iterations:\n", result.Iterations)
	finalGoal := agent.GetGoals()[0]
	fmt.Printf("  Status: %s\n", finalGoal.Status)
	fmt.Printf("  Progress: %.0f%%\n\n", finalGoal.Progress*100)

	return nil
}

// Example 8: Multiple goals with different completion times
func exampleGoalCompletionTimes() error {
	fmt.Println("\n=== Example 8: Goal Completion Times ===")

	agent := patterns.NewAutonomousAgent("Varied task durations", 30)

	agent.AddGoal("Quick task (1 iteration)", 10)
	agent.AddGoal("Medium task (5 iterations)", 8)
	agent.AddGoal("Long task (15 iterations)", 5)

	fmt.Println("Goals with different estimated durations:")
	for _, goal := range agent.GetGoals() {
		fmt.Printf("  - %s\n", goal.Description)
	}

	fmt.Println("\nRunning agent...")
	result, err := agent.Run(context.Background())
	if err != nil {
		return err
	}

	fmt.Println("Results:")
	fmt.Printf("  Total iterations: %d\n", result.Iterations)
	fmt.Printf("  Goals completed: %d\n", result.GoalsCompleted)

	fmt.Println("\nFinal goal states:")
	for _, goal := range agent.GetGoals() {
		statusIcon := "○"
		switch goal.Status {
		case patterns.GoalStatusCompleted:
			statusIcon = "✓"
		case patterns.GoalStatusActive:
			statusIcon = "○"
		case patterns.GoalStatusAbandoned:
			statusIcon = "✗"
		}
		fmt.Printf("  %s %s - %.0f%% complete\n",
			statusIcon,
			goal.Description,
			goal.Progress*100)
	}

	return nil
}

func main() {
	fmt.Println("Autonomous Agent Pattern Examples")
	fmt.Println(strings.Repeat("=", 60))

	// Run all examples
	if err := exampleBasic(); err != nil {
		log.Fatalf("Example 1 failed: %v", err)
	}

	if err := exampleCustomWorker(); err != nil {
		log.Fatalf("Example 2 failed: %v", err)
	}

	if err := examplePriority(); err != nil {
		log.Fatalf("Example 3 failed: %v", err)
	}

	if err := exampleStopCondition(); err != nil {
		log.Fatalf("Example 4 failed: %v", err)
	}

	if err := exampleManualStop(); err != nil {
		log.Fatalf("Example 5 failed: %v", err)
	}

	if err := exampleProgressTracking(); err != nil {
		log.Fatalf("Example 6 failed: %v", err)
	}

	if err := exampleGoalLifecycle(); err != nil {
		log.Fatalf("Example 7 failed: %v", err)
	}

	if err := exampleGoalCompletionTimes(); err != nil {
		log.Fatalf("Example 8 failed: %v", err)
	}

	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("✓ All examples completed successfully!")
	fmt.Println("\n💡 Key takeaways:")
	fmt.Println("   - Autonomous agents self-direct toward objectives")
	fmt.Println("   - Priority-based goal selection focuses effort")
	fmt.Println("   - Stop conditions enable adaptive termination")
	fmt.Println("   - Custom workers provide domain-specific logic")
	fmt.Println()
	fmt.Println("🎯 When to use Autonomous:")
	fmt.Println("   - Long-running goal-directed tasks")
	fmt.Println("   - Agents requiring minimal human supervision")
	fmt.Println("   - Systems with dynamic objectives")
	fmt.Println("   - Scenarios needing adaptive behavior")
}
