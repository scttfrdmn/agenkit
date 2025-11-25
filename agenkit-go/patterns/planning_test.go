package patterns

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// planningMockLLMClient is a mock LLM client for planning tests.
type planningMockLLMClient struct {
	response string
	err      error
}

func (m *planningMockLLMClient) Chat(ctx context.Context, messages []*agenkit.Message) (*agenkit.Message, error) {
	if m.err != nil {
		return nil, m.err
	}
	return &agenkit.Message{
		Role:    "assistant",
		Content: m.response,
	}, nil
}

// mockStepExecutor is a mock step executor for testing.
type mockStepExecutor struct {
	err          error
	failOnStep   int
	executeCount int
}

func (m *mockStepExecutor) Execute(ctx context.Context, step PlanStep, context map[string]interface{}) (interface{}, error) {
	m.executeCount++
	if m.failOnStep >= 0 && step.StepNumber == m.failOnStep {
		return nil, errors.New("step execution failed")
	}
	if m.err != nil {
		return nil, m.err
	}
	return fmt.Sprintf("Completed: %s", step.Description), nil
}

// ============================================================================
// PlanStep Tests
// ============================================================================

func TestCreatePlanStep(t *testing.T) {
	step := CreatePlanStep("Do something", 0, []int{})

	if step.Description != "Do something" {
		t.Errorf("expected description 'Do something', got %s", step.Description)
	}

	if step.StepNumber != 0 {
		t.Errorf("expected step number 0, got %d", step.StepNumber)
	}

	if step.Status != StepStatusPending {
		t.Errorf("expected status pending, got %s", step.Status)
	}

	if len(step.Dependencies) != 0 {
		t.Errorf("expected 0 dependencies, got %d", len(step.Dependencies))
	}
}

func TestCreatePlanStep_WithDependencies(t *testing.T) {
	step := CreatePlanStep("Do something", 1, []int{0})

	if len(step.Dependencies) != 1 {
		t.Errorf("expected 1 dependency, got %d", len(step.Dependencies))
	}

	if step.Dependencies[0] != 0 {
		t.Errorf("expected dependency on step 0, got %d", step.Dependencies[0])
	}
}

func TestCanExecuteStep_NoDependencies(t *testing.T) {
	step := CreatePlanStep("Do something", 0, []int{})
	completed := []int{}

	if !CanExecuteStep(step, completed) {
		t.Error("expected step with no dependencies to be executable")
	}
}

func TestCanExecuteStep_WithSatisfiedDependencies(t *testing.T) {
	step := CreatePlanStep("Do something", 1, []int{0})
	completed := []int{0}

	if !CanExecuteStep(step, completed) {
		t.Error("expected step with satisfied dependencies to be executable")
	}
}

func TestCanExecuteStep_WithUnsatisfiedDependencies(t *testing.T) {
	step := CreatePlanStep("Do something", 2, []int{0, 1})
	completed := []int{0} // Only 0 is completed, but 1 is also required

	if CanExecuteStep(step, completed) {
		t.Error("expected step with unsatisfied dependencies to not be executable")
	}
}

// ============================================================================
// Plan Tests
// ============================================================================

func TestCreatePlan(t *testing.T) {
	steps := []PlanStep{
		CreatePlanStep("Step 1", 0, nil),
		CreatePlanStep("Step 2", 1, nil),
	}

	plan := CreatePlan("Test goal", steps)

	if plan.Goal != "Test goal" {
		t.Errorf("expected goal 'Test goal', got %s", plan.Goal)
	}

	if len(plan.Steps) != 2 {
		t.Errorf("expected 2 steps, got %d", len(plan.Steps))
	}
}

func TestGetNextSteps_AllPending(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		CreatePlanStep("Step 1", 0, nil),
		CreatePlanStep("Step 2", 1, nil),
	})

	nextSteps := GetNextSteps(plan)

	// All steps have no dependencies, so all should be next
	if len(nextSteps) != 2 {
		t.Errorf("expected 2 next steps, got %d", len(nextSteps))
	}
}

func TestGetNextSteps_WithDependencies(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		CreatePlanStep("Step 1", 0, nil),
		CreatePlanStep("Step 2", 1, []int{0}), // Depends on step 0
	})

	nextSteps := GetNextSteps(plan)

	// Only step 0 should be next (step 1 depends on it)
	if len(nextSteps) != 1 {
		t.Errorf("expected 1 next step, got %d", len(nextSteps))
	}

	if nextSteps[0].StepNumber != 0 {
		t.Errorf("expected step 0 to be next, got step %d", nextSteps[0].StepNumber)
	}
}

func TestGetNextSteps_AfterCompletion(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		{Description: "Step 1", StepNumber: 0, Status: StepStatusCompleted, Dependencies: []int{}},
		{Description: "Step 2", StepNumber: 1, Status: StepStatusPending, Dependencies: []int{0}},
	})

	nextSteps := GetNextSteps(plan)

	// Step 0 is complete, so step 1 should be next
	if len(nextSteps) != 1 {
		t.Errorf("expected 1 next step, got %d", len(nextSteps))
	}

	if nextSteps[0].StepNumber != 1 {
		t.Errorf("expected step 1 to be next, got step %d", nextSteps[0].StepNumber)
	}
}

func TestIsPlanComplete_AllCompleted(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		{Status: StepStatusCompleted},
		{Status: StepStatusCompleted},
	})

	if !IsPlanComplete(plan) {
		t.Error("expected plan to be complete")
	}
}

func TestIsPlanComplete_WithSkipped(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		{Status: StepStatusCompleted},
		{Status: StepStatusSkipped},
	})

	if !IsPlanComplete(plan) {
		t.Error("expected plan to be complete (skipped counts as complete)")
	}
}

func TestIsPlanComplete_NotComplete(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		{Status: StepStatusCompleted},
		{Status: StepStatusPending},
	})

	if IsPlanComplete(plan) {
		t.Error("expected plan to not be complete")
	}
}

func TestHasPlanFailures_WithFailures(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		{Status: StepStatusCompleted},
		{Status: StepStatusFailed},
	})

	if !HasPlanFailures(plan) {
		t.Error("expected plan to have failures")
	}
}

func TestHasPlanFailures_NoFailures(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		{Status: StepStatusCompleted},
		{Status: StepStatusPending},
	})

	if HasPlanFailures(plan) {
		t.Error("expected plan to have no failures")
	}
}

func TestGetPlanProgress_EmptyPlan(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{})

	progress := GetPlanProgress(plan)

	if progress != 0 {
		t.Errorf("expected 0%% progress, got %.0f%%", progress)
	}
}

func TestGetPlanProgress_PartiallyComplete(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		{Status: StepStatusCompleted},
		{Status: StepStatusPending},
		{Status: StepStatusPending},
		{Status: StepStatusPending},
	})

	progress := GetPlanProgress(plan)

	if progress != 25 {
		t.Errorf("expected 25%% progress, got %.0f%%", progress)
	}
}

func TestGetPlanProgress_AllComplete(t *testing.T) {
	plan := CreatePlan("Test", []PlanStep{
		{Status: StepStatusCompleted},
		{Status: StepStatusCompleted},
	})

	progress := GetPlanProgress(plan)

	if progress != 100 {
		t.Errorf("expected 100%% progress, got %.0f%%", progress)
	}
}

// ============================================================================
// DefaultStepExecutor Tests
// ============================================================================

func TestDefaultStepExecutor_Execute(t *testing.T) {
	executor := &DefaultStepExecutor{}
	step := CreatePlanStep("Test step", 0, nil)

	result, err := executor.Execute(context.Background(), step, make(map[string]interface{}))

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !strings.Contains(result.(string), "Completed: Test step") {
		t.Errorf("expected result to contain step description, got: %s", result)
	}
}

// ============================================================================
// PlanningAgent Tests
// ============================================================================

func TestNewPlanningAgent_DefaultConfig(t *testing.T) {
	llm := &planningMockLLMClient{response: "Goal: Test\nSteps:\n1. Do something"}
	agent := NewPlanningAgent(llm, nil, nil)

	if agent.Name() != "PlanningAgent" {
		t.Errorf("expected name 'PlanningAgent', got %s", agent.Name())
	}

	if agent.maxSteps != 10 {
		t.Errorf("expected maxSteps 10, got %d", agent.maxSteps)
	}

	if agent.allowReplanning {
		t.Error("expected replanning disabled by default")
	}
}

func TestNewPlanningAgent_WithConfig(t *testing.T) {
	llm := &planningMockLLMClient{response: "Goal: Test\nSteps:\n1. Do something"}
	executor := &DefaultStepExecutor{}

	agent := NewPlanningAgent(llm, executor, &PlanningAgentConfig{
		MaxSteps:        5,
		AllowReplanning: true,
		SystemPrompt:    "Custom prompt",
	})

	if agent.maxSteps != 5 {
		t.Errorf("expected maxSteps 5, got %d", agent.maxSteps)
	}

	if !agent.allowReplanning {
		t.Error("expected replanning enabled")
	}

	if agent.systemPrompt != "Custom prompt" {
		t.Error("expected custom system prompt")
	}
}

func TestPlanningAgent_Capabilities(t *testing.T) {
	llm := &planningMockLLMClient{response: "Goal: Test\nSteps:\n1. Do something"}
	agent := NewPlanningAgent(llm, nil, nil)

	caps := agent.Capabilities()

	expectedCaps := []string{"planning", "task_decomposition", "step_execution"}
	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d", len(expectedCaps), len(caps))
	}
}

func TestPlanningAgent_ParsePlan_Simple(t *testing.T) {
	llm := &planningMockLLMClient{}
	agent := NewPlanningAgent(llm, nil, nil)

	planText := `Goal: Organize team event
Steps:
1. Choose venue
2. Send invitations
3. Order catering`

	plan := agent.parsePlan(planText, "Default goal")

	if plan.Goal != "Organize team event" {
		t.Errorf("expected goal 'Organize team event', got %s", plan.Goal)
	}

	if len(plan.Steps) != 3 {
		t.Fatalf("expected 3 steps, got %d", len(plan.Steps))
	}

	if plan.Steps[0].Description != "Choose venue" {
		t.Errorf("expected first step 'Choose venue', got %s", plan.Steps[0].Description)
	}

	if plan.Steps[1].Description != "Send invitations" {
		t.Errorf("expected second step 'Send invitations', got %s", plan.Steps[1].Description)
	}

	if plan.Steps[2].Description != "Order catering" {
		t.Errorf("expected third step 'Order catering', got %s", plan.Steps[2].Description)
	}
}

func TestPlanningAgent_ParsePlan_WithParentheses(t *testing.T) {
	llm := &planningMockLLMClient{}
	agent := NewPlanningAgent(llm, nil, nil)

	planText := `Goal: Test
Steps:
1) First step
2) Second step`

	plan := agent.parsePlan(planText, "Default")

	if len(plan.Steps) != 2 {
		t.Fatalf("expected 2 steps, got %d", len(plan.Steps))
	}

	if plan.Steps[0].Description != "First step" {
		t.Errorf("expected 'First step', got %s", plan.Steps[0].Description)
	}
}

func TestPlanningAgent_ParsePlan_NoGoal(t *testing.T) {
	llm := &planningMockLLMClient{}
	agent := NewPlanningAgent(llm, nil, nil)

	planText := `Steps:
1. Do something`

	plan := agent.parsePlan(planText, "Default goal")

	// Should use default goal if no Goal: line found
	if plan.Goal != "Default goal" {
		t.Errorf("expected default goal, got %s", plan.Goal)
	}
}

func TestPlanningAgent_ParsePlan_MaxStepsLimit(t *testing.T) {
	llm := &planningMockLLMClient{}
	agent := NewPlanningAgent(llm, nil, &PlanningAgentConfig{MaxSteps: 2})

	planText := `Goal: Test
Steps:
1. Step 1
2. Step 2
3. Step 3
4. Step 4`

	plan := agent.parsePlan(planText, "Default")

	// Should only parse up to maxSteps
	if len(plan.Steps) != 2 {
		t.Errorf("expected 2 steps (maxSteps limit), got %d", len(plan.Steps))
	}
}

func TestPlanningAgent_Process_Success(t *testing.T) {
	llm := &planningMockLLMClient{
		response: `Goal: Test task
Steps:
1. First step
2. Second step`,
	}
	executor := &mockStepExecutor{
		failOnStep: -1, // Don't fail any steps
	}

	agent := NewPlanningAgent(llm, executor, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Do the task",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !strings.Contains(result.Content, "Task completed") {
		t.Error("expected result to contain 'Task completed'")
	}

	if !strings.Contains(result.Content, "Goal: Test task") {
		t.Error("expected result to contain goal")
	}

	if !strings.Contains(result.Content, "Steps completed: 2/2") {
		t.Errorf("expected result to show 2/2 steps completed, got: %s", result.Content)
	}

	// Check that executor was called twice
	if executor.executeCount != 2 {
		t.Errorf("expected executor called 2 times, got %d", executor.executeCount)
	}
}

func TestPlanningAgent_Process_LLMFailure(t *testing.T) {
	llm := &planningMockLLMClient{
		err: errors.New("LLM failed"),
	}

	agent := NewPlanningAgent(llm, nil, nil)

	_, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Do something",
	})

	if err == nil {
		t.Fatal("expected error when LLM fails")
	}

	if !strings.Contains(err.Error(), "failed to create plan") {
		t.Errorf("expected 'failed to create plan' error, got: %v", err)
	}
}

func TestPlanningAgent_Process_WithStepFailure(t *testing.T) {
	llm := &planningMockLLMClient{
		response: `Goal: Test
Steps:
1. Step 1
2. Step 2
3. Step 3`,
	}
	executor := &mockStepExecutor{
		failOnStep: 1, // Fail on step 1 (second step)
	}

	agent := NewPlanningAgent(llm, executor, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Do task",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should show partial completion
	if !strings.Contains(result.Content, "Steps completed: 2/3") {
		t.Errorf("expected 2/3 steps completed, got: %s", result.Content)
	}

	// Check the plan
	plan := agent.GetPlan()
	if plan == nil {
		t.Fatal("expected plan to be stored")
	}

	if plan.Steps[1].Status != StepStatusFailed {
		t.Errorf("expected step 1 to be failed, got status: %s", plan.Steps[1].Status)
	}
}

func TestPlanningAgent_GetPlan(t *testing.T) {
	llm := &planningMockLLMClient{
		response: `Goal: Test
Steps:
1. Step 1`,
	}

	agent := NewPlanningAgent(llm, nil, nil)

	// Before processing
	if agent.GetPlan() != nil {
		t.Error("expected nil plan before processing")
	}

	// After processing
	_, _ = agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	plan := agent.GetPlan()
	if plan == nil {
		t.Fatal("expected plan after processing")
	}

	if plan.Goal != "Test" {
		t.Errorf("expected goal 'Test', got %s", plan.Goal)
	}
}

func TestPlanningAgent_GetProgress(t *testing.T) {
	llm := &planningMockLLMClient{
		response: `Goal: Test
Steps:
1. Step 1
2. Step 2`,
	}

	agent := NewPlanningAgent(llm, nil, nil)

	// Before processing
	if agent.GetProgress() != 0 {
		t.Errorf("expected 0%% progress before processing, got %.0f%%", agent.GetProgress())
	}

	// After processing
	_, _ = agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	progress := agent.GetProgress()
	if progress != 100 {
		t.Errorf("expected 100%% progress after successful completion, got %.0f%%", progress)
	}
}

func TestPlanningAgent_WithReplanning(t *testing.T) {
	llm := &planningMockLLMClient{
		response: `Goal: Test
Steps:
1. Step 1
2. Step 2`,
	}
	executor := &mockStepExecutor{
		failOnStep: 0, // Fail on first step
	}

	agent := NewPlanningAgent(llm, executor, &PlanningAgentConfig{
		AllowReplanning: true,
	})

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Test",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// With replanning, failed steps should be skipped
	plan := agent.GetPlan()
	if plan.Steps[0].Status != StepStatusSkipped {
		t.Errorf("expected step 0 to be skipped after replanning, got status: %s", plan.Steps[0].Status)
	}

	// Should still show completion
	if !strings.Contains(result.Content, "Task completed") {
		t.Error("expected task to complete after replanning")
	}
}

// ============================================================================
// Integration Tests
// ============================================================================

func TestPlanningAgent_RealWorldScenario(t *testing.T) {
	llm := &planningMockLLMClient{
		response: `Goal: Organize team building event
Steps:
1. Choose date and book venue
2. Create guest list
3. Send invitations
4. Order catering
5. Prepare activities`,
	}

	agent := NewPlanningAgent(llm, nil, nil)

	result, err := agent.Process(context.Background(), &agenkit.Message{
		Role:    "user",
		Content: "Organize a team building event",
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !strings.Contains(result.Content, "Task completed") {
		t.Error("expected task completion")
	}

	plan := agent.GetPlan()
	if len(plan.Steps) != 5 {
		t.Errorf("expected 5 steps, got %d", len(plan.Steps))
	}

	// All steps should be completed
	for i, step := range plan.Steps {
		if step.Status != StepStatusCompleted {
			t.Errorf("expected step %d to be completed, got status: %s", i, step.Status)
		}
	}
}
