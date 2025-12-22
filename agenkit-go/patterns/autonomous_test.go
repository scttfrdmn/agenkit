package patterns

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ============================================================================
// Goal Tests
// ============================================================================

func TestCreateGoal(t *testing.T) {
	goal := CreateGoal("Test goal", 5)

	if goal.Description != "Test goal" {
		t.Errorf("expected description 'Test goal', got %s", goal.Description)
	}

	if goal.Priority != 5 {
		t.Errorf("expected priority 5, got %d", goal.Priority)
	}

	if goal.Status != GoalStatusActive {
		t.Errorf("expected status active, got %s", goal.Status)
	}

	if goal.Progress != 0.0 {
		t.Errorf("expected progress 0.0, got %f", goal.Progress)
	}
}

// ============================================================================
// AutonomousAgent Tests
// ============================================================================

func TestNewAutonomousAgent(t *testing.T) {
	agent := NewAutonomousAgent("Test objective", 10)

	if agent.Name() != "AutonomousAgent" {
		t.Errorf("expected name 'AutonomousAgent', got %s", agent.Name())
	}

	if agent.GetObjective() != "Test objective" {
		t.Errorf("expected objective 'Test objective', got %s", agent.GetObjective())
	}

	if agent.maxIterations != 10 {
		t.Errorf("expected max iterations 10, got %d", agent.maxIterations)
	}

	if agent.IsRunning() {
		t.Error("expected agent not running initially")
	}

	if agent.GetIterationCount() != 0 {
		t.Errorf("expected iteration count 0, got %d", agent.GetIterationCount())
	}
}

func TestNewAutonomousAgent_DefaultMaxIterations(t *testing.T) {
	agent := NewAutonomousAgent("Test", 0)

	if agent.maxIterations != 10 {
		t.Errorf("expected default max iterations 10, got %d", agent.maxIterations)
	}
}

func TestAutonomousAgent_Capabilities(t *testing.T) {
	agent := NewAutonomousAgent("Test", 5)
	caps := agent.Capabilities()

	expectedCaps := []string{"autonomous", "goal-directed", "self-organizing"}
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

func TestAutonomousAgent_Process(t *testing.T) {
	agent := NewAutonomousAgent("Test objective", 5)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !strings.Contains(result.Content, "Test objective") {
		t.Errorf("expected result to contain objective, got: %s", result.Content)
	}
}

func TestAutonomousAgent_AddGoal(t *testing.T) {
	agent := NewAutonomousAgent("Test", 5)

	goal1 := agent.AddGoal("Goal 1", 10)
	goal2 := agent.AddGoal("Goal 2", 5)

	if goal1.Description != "Goal 1" {
		t.Errorf("expected 'Goal 1', got %s", goal1.Description)
	}

	if goal1.Priority != 10 {
		t.Errorf("expected priority 10, got %d", goal1.Priority)
	}

	if goal2.Priority != 5 {
		t.Errorf("expected priority 5, got %d", goal2.Priority)
	}

	goals := agent.GetGoals()
	if len(goals) != 2 {
		t.Errorf("expected 2 goals, got %d", len(goals))
	}
}

func TestAutonomousAgent_Run_NoGoals(t *testing.T) {
	agent := NewAutonomousAgent("Test", 5)

	result, err := agent.Run(context.Background())

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Iterations != 0 {
		t.Errorf("expected 0 iterations with no goals, got %d", result.Iterations)
	}

	if result.GoalsCompleted != 0 {
		t.Errorf("expected 0 goals completed, got %d", result.GoalsCompleted)
	}
}

func TestAutonomousAgent_Run_SingleGoal(t *testing.T) {
	agent := NewAutonomousAgent("Test", 10)
	agent.AddGoal("Test goal", 1)

	result, err := agent.Run(context.Background())

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// With progress increment of 0.2 per iteration, needs 5 iterations to complete
	if result.Iterations != 5 {
		t.Errorf("expected 5 iterations to complete goal, got %d", result.Iterations)
	}

	if result.GoalsCompleted != 1 {
		t.Errorf("expected 1 goal completed, got %d", result.GoalsCompleted)
	}

	if len(result.Results) != 5 {
		t.Errorf("expected 5 results, got %d", len(result.Results))
	}
}

func TestAutonomousAgent_Run_MultipleGoals(t *testing.T) {
	agent := NewAutonomousAgent("Test", 20)
	agent.AddGoal("Low priority", 1)
	agent.AddGoal("High priority", 10)

	result, err := agent.Run(context.Background())

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should work on high priority goal first (5 iterations),
	// then low priority goal (5 iterations) = 10 total
	if result.Iterations != 10 {
		t.Errorf("expected 10 iterations, got %d", result.Iterations)
	}

	if result.GoalsCompleted != 2 {
		t.Errorf("expected 2 goals completed, got %d", result.GoalsCompleted)
	}
}

func TestAutonomousAgent_Run_MaxIterationsReached(t *testing.T) {
	agent := NewAutonomousAgent("Test", 3)
	agent.AddGoal("Test goal", 1)

	result, err := agent.Run(context.Background())

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Max iterations is 3, so should stop after 3
	if result.Iterations != 3 {
		t.Errorf("expected 3 iterations (max), got %d", result.Iterations)
	}

	// Goal needs 5 iterations to complete, so shouldn't be completed
	if result.GoalsCompleted != 0 {
		t.Errorf("expected 0 goals completed (not enough iterations), got %d", result.GoalsCompleted)
	}
}

func TestAutonomousAgent_Run_WithStopCondition(t *testing.T) {
	agent := NewAutonomousAgent("Test", 10)
	agent.AddGoal("Test goal", 1)

	iterationLimit := 0
	agent.SetStopCondition(func() bool {
		iterationLimit++
		return iterationLimit >= 2 // Stop after 2 iterations
	})

	result, err := agent.Run(context.Background())

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Iterations != 2 {
		t.Errorf("expected 2 iterations (stop condition), got %d", result.Iterations)
	}
}

func TestAutonomousAgent_Run_WithCustomWorker(t *testing.T) {
	agent := NewAutonomousAgent("Test", 5)
	agent.AddGoal("Test goal", 1)

	callCount := 0
	agent.SetWorker(func(ctx context.Context, goal *Goal) (string, error) {
		callCount++
		return "Custom work result", nil
	})

	result, err := agent.Run(context.Background())

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if callCount != 5 {
		t.Errorf("expected worker called 5 times, got %d", callCount)
	}

	if !strings.Contains(result.Results[0], "Custom work result") {
		t.Errorf("expected custom work result, got: %s", result.Results[0])
	}
}

func TestAutonomousAgent_Run_WorkerError(t *testing.T) {
	agent := NewAutonomousAgent("Test", 5)
	agent.AddGoal("Test goal", 1)

	agent.SetWorker(func(ctx context.Context, goal *Goal) (string, error) {
		return "", errors.New("worker failed")
	})

	_, err := agent.Run(context.Background())

	if err == nil {
		t.Fatal("expected error when worker fails")
	}

	if !strings.Contains(err.Error(), "work on goal failed") {
		t.Errorf("expected 'work on goal failed' error, got: %v", err)
	}
}

func TestAutonomousAgent_Run_ContextCancellation(t *testing.T) {
	agent := NewAutonomousAgent("Test", 100)
	agent.AddGoal("Test goal", 1)

	ctx, cancel := context.WithCancel(context.Background())

	// Cancel after first iteration
	agent.SetWorker(func(ctx context.Context, goal *Goal) (string, error) {
		cancel()
		return "work done", nil
	})

	_, err := agent.Run(ctx)

	if err != context.Canceled {
		t.Errorf("expected context.Canceled error, got %v", err)
	}
}

func TestAutonomousAgent_Stop(t *testing.T) {
	agent := NewAutonomousAgent("Test", 100)
	agent.AddGoal("Test goal", 1)

	// Set worker that stops agent after 2 iterations
	iterationCount := 0
	agent.SetWorker(func(ctx context.Context, goal *Goal) (string, error) {
		iterationCount++
		if iterationCount == 2 {
			agent.Stop()
		}
		return "work", nil
	})

	result, err := agent.Run(context.Background())

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Iterations != 2 {
		t.Errorf("expected 2 iterations before stop, got %d", result.Iterations)
	}

	if agent.IsRunning() {
		t.Error("expected agent not running after stop")
	}
}

func TestAutonomousAgent_GetProgress(t *testing.T) {
	agent := NewAutonomousAgent("Test", 10)

	// No goals
	if agent.GetProgress() != 0.0 {
		t.Errorf("expected 0%% progress with no goals, got %f", agent.GetProgress())
	}

	// Add goals
	goal1 := agent.AddGoal("Goal 1", 1)
	goal2 := agent.AddGoal("Goal 2", 1)

	// Set progress
	goal1.Progress = 0.5 // 50% complete
	goal2.Progress = 1.0 // 100% complete

	// Average: (0.5 + 1.0) / 2 = 0.75 = 75%
	progress := agent.GetProgress()
	if progress != 75.0 {
		t.Errorf("expected 75%% progress, got %f", progress)
	}
}

func TestAutonomousAgent_GetGoals(t *testing.T) {
	agent := NewAutonomousAgent("Test", 5)
	agent.AddGoal("Goal 1", 1)
	agent.AddGoal("Goal 2", 2)

	goals := agent.GetGoals()

	if len(goals) != 2 {
		t.Errorf("expected 2 goals, got %d", len(goals))
	}

	// Verify it's a copy (modifying returned goals shouldn't affect agent)
	goals[0].Description = "Modified"

	goals2 := agent.GetGoals()
	if goals2[0].Description == "Modified" {
		t.Error("GetGoals should return a copy, not original goals")
	}
}

func TestAutonomousAgent_GoalPrioritySelection(t *testing.T) {
	agent := NewAutonomousAgent("Test", 10)

	// Add goals in random priority order
	agent.AddGoal("Priority 3", 3)
	agent.AddGoal("Priority 10", 10) // This should be worked on first
	agent.AddGoal("Priority 5", 5)

	resultsOrder := make([]string, 0)
	agent.SetWorker(func(ctx context.Context, goal *Goal) (string, error) {
		resultsOrder = append(resultsOrder, goal.Description)
		return "work", nil
	})

	_, err := agent.Run(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// First 5 results should all be "Priority 10" (highest priority)
	for i := 0; i < 5; i++ {
		if resultsOrder[i] != "Priority 10" {
			t.Errorf("iteration %d: expected 'Priority 10', got '%s'", i, resultsOrder[i])
		}
	}

	// Next 5 should be "Priority 5"
	for i := 5; i < 10; i++ {
		if resultsOrder[i] != "Priority 5" {
			t.Errorf("iteration %d: expected 'Priority 5', got '%s'", i, resultsOrder[i])
		}
	}
}

func TestAutonomousAgent_GoalStatusTransitions(t *testing.T) {
	agent := NewAutonomousAgent("Test", 10)
	goal := agent.AddGoal("Test goal", 1)

	// Initially active
	if goal.Status != GoalStatusActive {
		t.Errorf("expected initial status active, got %s", goal.Status)
	}

	// Run to completion
	_, err := agent.Run(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should be completed
	if goal.Status != GoalStatusCompleted {
		t.Errorf("expected status completed, got %s", goal.Status)
	}

	// Progress should be >= 1.0
	if goal.Progress < 1.0 {
		t.Errorf("expected progress >= 1.0, got %f", goal.Progress)
	}
}

// ============================================================================
// Integration Tests
// ============================================================================

func TestAutonomousAgent_RealWorldScenario(t *testing.T) {
	agent := NewAutonomousAgent("Complete research project", 20)

	// Add goals with different priorities
	agent.AddGoal("Literature review", 10)
	agent.AddGoal("Data collection", 8)
	agent.AddGoal("Analysis", 5)
	agent.AddGoal("Write paper", 3)

	workLog := make([]string, 0)
	agent.SetWorker(func(ctx context.Context, goal *Goal) (string, error) {
		work := fmt.Sprintf("Working on: %s (progress: %.1f%%)", goal.Description, goal.Progress*100)
		workLog = append(workLog, work)
		return work, nil
	})

	result, err := agent.Run(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should complete all 4 goals (5 iterations each = 20 total)
	if result.GoalsCompleted != 4 {
		t.Errorf("expected 4 goals completed, got %d", result.GoalsCompleted)
	}

	if result.Iterations != 20 {
		t.Errorf("expected 20 iterations, got %d", result.Iterations)
	}

	// Check progress is 100%
	progress := agent.GetProgress()
	if progress != 100.0 {
		t.Errorf("expected 100%% progress, got %f", progress)
	}
}

func TestAutonomousAgent_WithTimeBasedStopCondition(t *testing.T) {
	agent := NewAutonomousAgent("Test", 100)
	agent.AddGoal("Long running goal", 1)

	startTime := time.Now()
	agent.SetStopCondition(func() bool {
		return time.Since(startTime) > 100*time.Millisecond
	})

	agent.SetWorker(func(ctx context.Context, goal *Goal) (string, error) {
		time.Sleep(10 * time.Millisecond)
		return "work", nil
	})

	result, err := agent.Run(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should stop due to time condition, not max iterations
	if result.Iterations >= 100 {
		t.Errorf("expected early stop due to time condition, got %d iterations", result.Iterations)
	}
}
