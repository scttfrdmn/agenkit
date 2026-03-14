package reasoning

import (
	"context"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestPlanAndSolveBasic tests basic plan-and-solve functionality
func TestPlanAndSolveBasic(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		// Planning response
		"1. Gather ingredients\n2. Preheat oven\n3. Mix ingredients\n4. Bake",
		// Validation response
		"VALID: Plan is complete",
		// Execution responses
		"Gathered: flour, sugar, eggs",
		"Preheated oven to 350°F",
		"Mixed all ingredients thoroughly",
		"Baked for 30 minutes",
	})

	config := PlanAndSolveConfig{
		ValidatePlan: true,
	}

	agent := NewPlanAndSolveAgent(mockAgent, config)

	message := &agenkit.Message{
		Role:    "user",
		Content: "How do I bake a cake?",
	}

	response, err := agent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if response.ContentString() == "" {
		t.Error("Expected non-empty response content")
	}

	// Check metadata
	if response.Metadata == nil {
		t.Fatal("Expected metadata to be set")
	}

	if response.Metadata["technique"] != "plan_and_solve" {
		t.Errorf("Expected technique=plan_and_solve, got %v", response.Metadata["technique"])
	}
}

// TestPlanAndSolvePlanningPhase tests the planning phase
func TestPlanAndSolvePlanningPhase(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Step one\n2. Step two\n3. Step three",
	})

	agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{
		ValidatePlan: false,
	})

	plan, err := agent.CreatePlan(context.Background(), "Test problem")
	if err != nil {
		t.Fatalf("CreatePlan failed: %v", err)
	}

	if len(plan.Steps) != 3 {
		t.Errorf("Expected 3 steps, got %d", len(plan.Steps))
	}

	if plan.Problem != "Test problem" {
		t.Errorf("Expected problem='Test problem', got '%s'", plan.Problem)
	}

	if plan.Steps[0].Description != "Step one" {
		t.Errorf("Expected 'Step one', got '%s'", plan.Steps[0].Description)
	}
}

// TestPlanAndSolveValidation tests plan validation
func TestPlanAndSolveValidation(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"VALID: The plan is complete and feasible",
	})

	agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{})

	plan := &Plan{
		Problem: "Test problem",
		Steps: []*PlanStep{
			{Description: "Step 1", Order: 0},
			{Description: "Step 2", Order: 1},
		},
	}

	validatedPlan, err := agent.Validate(context.Background(), plan)
	if err != nil {
		t.Fatalf("Validate failed: %v", err)
	}

	if !validatedPlan.Validated {
		t.Error("Expected plan to be validated")
	}

	if validatedPlan.ValidationNotes == "" {
		t.Error("Expected validation notes to be set")
	}
}

// TestPlanAndSolveNoValidation tests skipping validation
func TestPlanAndSolveNoValidation(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Step",
		"Result",
	})

	config := PlanAndSolveConfig{
		ValidatePlan: false,
	}

	agent := NewPlanAndSolveAgent(mockAgent, config)

	message := &agenkit.Message{
		Role:    "user",
		Content: "Simple problem",
	}

	_, err := agent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Validation should not have been called, so callCount should be 2 (plan + execute)
	// not 3 (plan + validate + execute)
	mockAgent.mu.Lock()
	callCount := mockAgent.callCount
	mockAgent.mu.Unlock()
	if callCount != 2 {
		t.Errorf("Expected 2 LLM calls (no validation), got %d", callCount)
	}
}

// TestPlanAndSolveExecutionPhase tests step execution
func TestPlanAndSolveExecutionPhase(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"Executed step 1 successfully",
	})

	agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{})

	step := &PlanStep{
		Description: "Do something",
		Order:       0,
	}

	result, err := agent.ExecuteStep(context.Background(), step, []string{})
	if err != nil {
		t.Fatalf("ExecuteStep failed: %v", err)
	}

	if !strings.Contains(result, "Executed") {
		t.Errorf("Expected 'Executed' in result, got '%s'", result)
	}
}

// TestPlanAndSolveCustomPlanner tests custom planner function
func TestPlanAndSolveCustomPlanner(t *testing.T) {
	customPlanner := func(ctx context.Context, problem string) (*Plan, error) {
		return &Plan{
			Problem: problem,
			Steps: []*PlanStep{
				{Description: "Custom step 1", Order: 0},
				{Description: "Custom step 2", Order: 1},
			},
			Strategy: "Custom strategy",
		}, nil
	}

	mockAgent := NewMockAgent([]string{
		"Step 1 result",
		"Step 2 result",
	})

	config := PlanAndSolveConfig{
		Planner:      customPlanner,
		ValidatePlan: false,
	}

	agent := NewPlanAndSolveAgent(mockAgent, config)

	message := &agenkit.Message{
		Role:    "user",
		Content: "Test problem",
	}

	response, err := agent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Check that custom planner was used (it should have 2 custom steps)
	planSteps, ok := response.Metadata["plan_steps"].([]string)
	if !ok {
		t.Fatal("Expected plan_steps to be []string")
	}
	if len(planSteps) != 2 {
		t.Errorf("Expected 2 steps from custom planner, got %d", len(planSteps))
	}
	if planSteps[0] != "Custom step 1" {
		t.Errorf("Expected 'Custom step 1', got '%s'", planSteps[0])
	}
}

// TestPlanAndSolveCustomSolver tests custom solver function
func TestPlanAndSolveCustomSolver(t *testing.T) {
	customSolver := func(ctx context.Context, step *PlanStep, previousResults []string) (string, error) {
		return "Custom solution for: " + step.Description, nil
	}

	mockAgent := NewMockAgent([]string{
		"1. Test step",
	})

	config := PlanAndSolveConfig{
		Solver:       customSolver,
		ValidatePlan: false,
	}

	agent := NewPlanAndSolveAgent(mockAgent, config)

	message := &agenkit.Message{
		Role:    "user",
		Content: "Test problem",
	}

	response, err := agent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if !strings.Contains(response.ContentString(), "Custom solution") {
		t.Errorf("Expected custom solver output, got '%s'", response.ContentString())
	}
}

// TestPlanAndSolveName tests agent name
func TestPlanAndSolveName(t *testing.T) {
	mockAgent := NewMockAgent([]string{})
	agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{})

	if agent.Name() != "plan_and_solve" {
		t.Errorf("Expected name 'plan_and_solve', got '%s'", agent.Name())
	}
}

// TestPlanAndSolveCapabilities tests agent capabilities
func TestPlanAndSolveCapabilities(t *testing.T) {
	mockAgent := NewMockAgent([]string{})
	agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{})

	capabilities := agent.Capabilities()

	expectedCaps := []string{"reasoning", "planning", "plan_and_solve", "strategic_thinking", "step_by_step_execution"}
	for _, expected := range expectedCaps {
		found := false
		for _, cap := range capabilities {
			if cap == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected capability '%s' not found", expected)
		}
	}
}

// TestPlanAndSolveEmptyPlan tests handling empty plans
func TestPlanAndSolveEmptyPlan(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"", // Empty response
	})

	agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{
		ValidatePlan: false,
	})

	plan, err := agent.CreatePlan(context.Background(), "Problem")
	if err != nil {
		t.Fatalf("CreatePlan failed: %v", err)
	}

	if len(plan.Steps) != 0 {
		t.Errorf("Expected 0 steps for empty response, got %d", len(plan.Steps))
	}
}

// TestPlanAndSolveSingleStep tests plans with single step
func TestPlanAndSolveSingleStep(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Only step",
		"Step result",
	})

	agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{
		ValidatePlan: false,
	})

	message := &agenkit.Message{
		Role:    "user",
		Content: "Simple task",
	}

	response, err := agent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	numSteps := response.Metadata["num_steps"]
	if numSteps != 1 {
		t.Errorf("Expected 1 step, got %v", numSteps)
	}
}

// TestPlanAndSolveNumberingFormats tests different step numbering formats
func TestPlanAndSolveNumberingFormats(t *testing.T) {
	testCases := []struct {
		name     string
		response string
		expected int
	}{
		{
			name:     "Period format",
			response: "1. Step one\n2. Step two\n3. Step three",
			expected: 3,
		},
		{
			name:     "Parenthesis format",
			response: "1) Step one\n2) Step two",
			expected: 2,
		},
		{
			name:     "Mixed with empty lines",
			response: "1. Step one\n\n2. Step two\n\n",
			expected: 2,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			mockAgent := NewMockAgent([]string{tc.response})
			agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{})

			plan, err := agent.CreatePlan(context.Background(), "Problem")
			if err != nil {
				t.Fatalf("CreatePlan failed: %v", err)
			}

			if len(plan.Steps) != tc.expected {
				t.Errorf("Expected %d steps, got %d", tc.expected, len(plan.Steps))
			}
		})
	}
}

// TestPlanAndSolveMetadata tests metadata tracking
func TestPlanAndSolveMetadata(t *testing.T) {
	mockAgent := NewMockAgent([]string{
		"1. Step 1\n2. Step 2",
		"VALID",
		"Result 1",
		"Result 2",
	})

	agent := NewPlanAndSolveAgent(mockAgent, PlanAndSolveConfig{
		ValidatePlan: true,
	})

	message := &agenkit.Message{
		Role:    "user",
		Content: "Test",
	}

	response, err := agent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Check metadata fields
	requiredFields := []string{"technique", "plan_steps", "validated"}
	for _, field := range requiredFields {
		if _, exists := response.Metadata[field]; !exists {
			t.Errorf("Expected metadata field '%s' not found", field)
		}
	}

	if response.Metadata["technique"] != "plan_and_solve" {
		t.Error("Expected technique='plan_and_solve'")
	}

	if response.Metadata["validated"] != true {
		t.Error("Expected validated=true")
	}
}

// TestPlanAndSolveStepDependencies tests step dependency tracking
func TestPlanAndSolveStepDependencies(t *testing.T) {
	plan := &Plan{
		Problem: "Test",
		Steps: []*PlanStep{
			{Description: "Step 1", Order: 0, Dependencies: []int{}},
			{Description: "Step 2", Order: 1, Dependencies: []int{0}},
			{Description: "Step 3", Order: 2, Dependencies: []int{0, 1}},
		},
	}

	// Verify step 2 depends on step 1
	if len(plan.Steps[1].Dependencies) != 1 || plan.Steps[1].Dependencies[0] != 0 {
		t.Error("Step 2 should depend on step 0")
	}

	// Verify step 3 depends on steps 1 and 2
	if len(plan.Steps[2].Dependencies) != 2 {
		t.Error("Step 3 should depend on 2 previous steps")
	}
}

// TestPlanAndSolveExecutionTracking tests execution state tracking
func TestPlanAndSolveExecutionTracking(t *testing.T) {
	step := &PlanStep{
		Description: "Test step",
		Order:       0,
		Executed:    false,
	}

	if step.Executed {
		t.Error("Step should not be executed initially")
	}

	step.Executed = true
	step.Result = "Test result"

	if !step.Executed {
		t.Error("Step should be marked as executed")
	}

	if step.Result != "Test result" {
		t.Errorf("Expected result 'Test result', got '%s'", step.Result)
	}
}
