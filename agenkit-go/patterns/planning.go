// Package patterns provides the Planning pattern for task decomposition.
//
// This module provides the Planning pattern, which breaks complex tasks into
// manageable steps and executes them in order.
//
// Key features:
//   - LLM-powered task decomposition
//   - Step dependency tracking
//   - Automatic plan execution
//   - Progress tracking
//   - Optional replanning on failures
//
// Example:
//
//	// Create a planning agent
//	agent := patterns.NewPlanningAgent(llmClient, executor, &patterns.PlanningAgentConfig{
//	    MaxSteps: 10,
//	    AllowReplanning: true,
//	})
//
//	// Process a complex task
//	result, _ := agent.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "Organize a team event",
//	})
//	// Agent will create a plan with steps like:
//	// 1. Choose date and venue
//	// 2. Create invitation list
//	// 3. Send invitations
//	// 4. Arrange catering
package patterns

import (
	"context"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

// StepStatus represents the status of a plan step.
type StepStatus string

const (
	// StepStatusPending indicates step not yet started
	StepStatusPending StepStatus = "pending"
	// StepStatusInProgress indicates step currently executing
	StepStatusInProgress StepStatus = "in_progress"
	// StepStatusCompleted indicates step completed successfully
	StepStatusCompleted StepStatus = "completed"
	// StepStatusFailed indicates step failed with error
	StepStatusFailed StepStatus = "failed"
	// StepStatusSkipped indicates step was skipped
	StepStatusSkipped StepStatus = "skipped"
)

// PlanStep represents a single step in a plan.
type PlanStep struct {
	// Description of what this step should accomplish
	Description string
	// Dependencies are step indices that must complete before this step
	Dependencies []int
	// Status is the current status of the step
	Status StepStatus
	// Result from executing the step (if completed)
	Result interface{}
	// Error message if step failed
	Error string
	// StepNumber is the position in the plan (0-indexed)
	StepNumber int
	// Metadata contains additional step metadata
	Metadata map[string]interface{}
	// Timestamp when the step was created
	Timestamp time.Time
}

// CreatePlanStep creates a new plan step.
func CreatePlanStep(description string, stepNumber int, dependencies []int) PlanStep {
	if dependencies == nil {
		dependencies = []int{}
	}

	return PlanStep{
		Description:  description,
		Dependencies: dependencies,
		Status:       StepStatusPending,
		StepNumber:   stepNumber,
		Timestamp:    time.Now(),
	}
}

// CanExecuteStep checks if a step's dependencies are met.
func CanExecuteStep(step PlanStep, completedSteps []int) bool {
	for _, dep := range step.Dependencies {
		found := false
		for _, completed := range completedSteps {
			if dep == completed {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

// Plan represents a plan consisting of multiple steps.
type Plan struct {
	// Goal is the overall goal the plan aims to achieve
	Goal string
	// Steps is the list of steps in the plan
	Steps []PlanStep
	// CreatedAt is when the plan was created
	CreatedAt time.Time
	// Metadata contains additional plan metadata
	Metadata map[string]interface{}
}

// CreatePlan creates a new plan.
func CreatePlan(goal string, steps []PlanStep) Plan {
	if steps == nil {
		steps = []PlanStep{}
	}

	return Plan{
		Goal:      goal,
		Steps:     steps,
		CreatedAt: time.Now(),
	}
}

// GetNextSteps returns all steps that can be executed now.
func GetNextSteps(plan Plan) []PlanStep {
	// Get completed step indices
	completedIndices := []int{}
	for i, step := range plan.Steps {
		if step.Status == StepStatusCompleted {
			completedIndices = append(completedIndices, i)
		}
	}

	// Find pending steps with satisfied dependencies
	nextSteps := []PlanStep{}
	for _, step := range plan.Steps {
		if step.Status == StepStatusPending && CanExecuteStep(step, completedIndices) {
			nextSteps = append(nextSteps, step)
		}
	}

	return nextSteps
}

// IsPlanComplete checks if all steps are completed or skipped.
func IsPlanComplete(plan Plan) bool {
	for _, step := range plan.Steps {
		if step.Status != StepStatusCompleted && step.Status != StepStatusSkipped {
			return false
		}
	}
	return true
}

// HasPlanFailures checks if any steps failed.
func HasPlanFailures(plan Plan) bool {
	for _, step := range plan.Steps {
		if step.Status == StepStatusFailed {
			return true
		}
	}
	return false
}

// GetPlanProgress returns completion progress as a percentage.
func GetPlanProgress(plan Plan) float64 {
	if len(plan.Steps) == 0 {
		return 0
	}

	completed := 0
	for _, step := range plan.Steps {
		if step.Status == StepStatusCompleted || step.Status == StepStatusSkipped {
			completed++
		}
	}

	return float64(completed) / float64(len(plan.Steps)) * 100
}

// StepExecutor is the protocol for executing individual plan steps.
type StepExecutor interface {
	// Execute executes a plan step
	Execute(ctx context.Context, step PlanStep, context map[string]interface{}) (interface{}, error)
}

// DefaultStepExecutor is a default step executor that returns mock results.
type DefaultStepExecutor struct{}

// Execute implements StepExecutor.
func (d *DefaultStepExecutor) Execute(ctx context.Context, step PlanStep, context map[string]interface{}) (interface{}, error) {
	// Mock execution - just return success
	return fmt.Sprintf("Completed: %s", step.Description), nil
}

// PlanningAgentConfig configures a PlanningAgent.
type PlanningAgentConfig struct {
	// MaxSteps is the maximum steps in a plan
	MaxSteps int
	// AllowReplanning enables replanning on failures
	AllowReplanning bool
	// SystemPrompt is an optional system prompt
	SystemPrompt string
	// EnableErrorTracking opts into recording each executed step's
	// success/failure via evaluation.ErrorTracker, exposed on the result
	// message's Metadata["error_tracker"] (default: false, opt-in; see #653).
	EnableErrorTracking bool
}

// PlanningAgent creates and executes plans for complex tasks.
//
// The PlanningAgent uses an LLM to create a plan by breaking down
// complex tasks into manageable steps, then executes each step
// sequentially or in parallel (if dependencies allow).
//
// Use this when:
//   - Tasks require multiple coordinated steps
//   - Order of operations matters
//   - You need dynamic replanning on failures
//
// Example:
//
//	agent := NewPlanningAgent(llmClient, executor, &PlanningAgentConfig{
//	    MaxSteps: 10,
//	    AllowReplanning: true,
//	})
//
//	result, _ := agent.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "Organize a team event",
//	})
type PlanningAgent struct {
	name                string
	llm                 any
	executor            StepExecutor
	maxSteps            int
	allowReplanning     bool
	systemPrompt        string
	currentPlan         *Plan
	enableErrorTracking bool
	// ErrorTracker records each executed step's success/failure when
	// EnableErrorTracking is set on the config. The zero value is a disabled
	// tracker (RecordStep is a no-op), so it is always safe to read.
	ErrorTracker *evaluation.ErrorTracker
}

// NewPlanningAgent creates a new planning agent.
//
// llmClient may implement any of the three contracts in llmclient.go: Complete
// (every shipped adapter), Process (any agent), or the deprecated Chat. It is not
// validated here because this constructor returns no error; an unrecognized client
// surfaces as a named error from Process (#805).
func NewPlanningAgent(llmClient any, stepExecutor StepExecutor, config *PlanningAgentConfig) *PlanningAgent {
	if config == nil {
		config = &PlanningAgentConfig{}
	}

	if config.MaxSteps == 0 {
		config.MaxSteps = 10
	}

	agent := &PlanningAgent{
		name:                "PlanningAgent",
		llm:                 llmClient,
		executor:            stepExecutor,
		maxSteps:            config.MaxSteps,
		allowReplanning:     config.AllowReplanning,
		enableErrorTracking: config.EnableErrorTracking,
		ErrorTracker:        &evaluation.ErrorTracker{Enabled: config.EnableErrorTracking},
	}

	if config.SystemPrompt != "" {
		agent.systemPrompt = config.SystemPrompt
	} else {
		agent.systemPrompt = agent.defaultSystemPrompt()
	}

	if agent.executor == nil {
		agent.executor = &DefaultStepExecutor{}
	}

	return agent
}

func (p *PlanningAgent) defaultSystemPrompt() string {
	return fmt.Sprintf(`You are a planning agent that breaks down complex tasks into steps.

For each task, create a plan with specific, actionable steps.

Format your plan as:
Goal: [overall goal]
Steps:
1. [first step]
2. [second step]
...

Maximum %d steps.

Guidelines:
- Make steps concrete and actionable
- Consider dependencies between steps
- Keep steps focused and achievable
- Include verification steps when appropriate`, p.maxSteps)
}

// Name returns the agent name.
func (p *PlanningAgent) Name() string {
	return p.name
}

// Capabilities returns the agent capabilities.
func (p *PlanningAgent) Capabilities() []string {
	return []string{"planning", "task_decomposition", "step_execution"}
}

// Introspect reports the current plan, if any, as the agent's working state.
func (p *PlanningAgent) Introspect() *agenkit.IntrospectionResult {
	internal := map[string]interface{}{
		"max_steps":        p.maxSteps,
		"allow_replanning": p.allowReplanning,
		"has_plan":         p.currentPlan != nil,
	}
	if p.currentPlan != nil {
		completed := 0
		for _, step := range p.currentPlan.Steps {
			if step.Status == StepStatusCompleted {
				completed++
			}
		}
		internal["plan_goal"] = p.currentPlan.Goal
		internal["plan_step_count"] = len(p.currentPlan.Steps)
		internal["plan_steps_completed"] = completed
	}

	result, _ := agenkit.NewIntrospectionResult(
		p.Name(),
		p.Capabilities(),
		nil,
		internal,
		nil,
	)
	return result
}

// Process processes a task by creating and executing a plan.
func (p *PlanningAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	p.ErrorTracker.Reset() // Reset for new task (no-op when disabled)

	// Create plan
	plan, err := p.createPlan(ctx, message.ContentString())
	if err != nil {
		return nil, fmt.Errorf("failed to create plan: %w", err)
	}

	p.currentPlan = &plan

	// Execute plan
	result, err := p.executePlan(ctx, &plan)
	if err != nil {
		return nil, fmt.Errorf("failed to execute plan: %w", err)
	}

	completed := 0
	for _, step := range plan.Steps {
		if step.Status == StepStatusCompleted {
			completed++
		}
	}

	var metadata map[string]interface{}
	if p.enableErrorTracking {
		metadata = map[string]interface{}{"error_tracker": p.ErrorTracker}
	}

	return &agenkit.Message{
		Role:     "assistant",
		Content:  fmt.Sprintf("Task completed.\n\nGoal: %s\n\nSteps completed: %d/%d\n\nResult: %s", plan.Goal, completed, len(plan.Steps), result),
		Metadata: metadata,
	}, nil
}

func (p *PlanningAgent) createPlan(ctx context.Context, task string) (Plan, error) {
	// Ask LLM to create a plan
	messages := []*agenkit.Message{
		{Role: "system", Content: p.systemPrompt},
		{Role: "user", Content: fmt.Sprintf("Create a plan for: %s", task)},
	}

	response, err := completeMessages(ctx, p.llm, messages)
	if err != nil {
		return Plan{}, fmt.Errorf("LLM completion failed: %w", err)
	}

	// Parse the plan
	plan := p.parsePlan(response.ContentString(), task)

	return plan, nil
}

func (p *PlanningAgent) parsePlan(planText string, goal string) Plan {
	lines := strings.Split(strings.TrimSpace(planText), "\n")

	// Extract goal
	planGoal := goal
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "Goal:") {
			planGoal = strings.TrimSpace(strings.TrimPrefix(trimmed, "Goal:"))
			break
		}
	}

	// Extract steps
	steps := []PlanStep{}
	inStepsSection := false
	stepNumber := 0

	// Regex for matching step numbers
	stepRegex := regexp.MustCompile(`^(\d+)[.)]`)

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		if strings.HasPrefix(trimmed, "Steps:") {
			inStepsSection = true
			continue
		}

		if inStepsSection && trimmed != "" {
			// Remove leading numbers and dots
			stepText := trimmed

			// Try to match and remove step number prefix
			matches := stepRegex.FindStringSubmatch(stepText)
			if len(matches) > 0 {
				stepText = strings.TrimSpace(stepRegex.ReplaceAllString(stepText, ""))
			}

			// Also try "Step N:" format
			if strings.HasPrefix(stepText, fmt.Sprintf("Step %d:", stepNumber+1)) {
				stepText = strings.TrimSpace(strings.TrimPrefix(stepText, fmt.Sprintf("Step %d:", stepNumber+1)))
			}

			if stepText != "" && len(steps) < p.maxSteps {
				steps = append(steps, CreatePlanStep(stepText, stepNumber, nil))
				stepNumber++
			}
		}
	}

	return CreatePlan(planGoal, steps)
}

func (p *PlanningAgent) executePlan(ctx context.Context, plan *Plan) (string, error) {
	context := make(map[string]interface{})
	results := []string{}

	for !IsPlanComplete(*plan) {
		// Get next executable steps
		nextSteps := GetNextSteps(*plan)

		if len(nextSteps) == 0 {
			// No steps can execute (all blocked or completed)
			if HasPlanFailures(*plan) && p.allowReplanning {
				// Try to replan around failures
				if err := p.replan(ctx, plan); err != nil {
					return "", fmt.Errorf("replanning failed: %w", err)
				}
				continue
			}
			break
		}

		// Execute next steps (for now, sequentially)
		for _, step := range nextSteps {
			// Find the step in the plan and update its status
			for i := range plan.Steps {
				if plan.Steps[i].StepNumber == step.StepNumber {
					plan.Steps[i].Status = StepStatusInProgress

					result, err := p.executor.Execute(ctx, step, context)
					if err != nil {
						plan.Steps[i].Error = err.Error()
						plan.Steps[i].Status = StepStatusFailed
						p.ErrorTracker.RecordStep(false,
							evaluation.WithStepName(step.Description),
							evaluation.WithStepError(err.Error()),
						)
						results = append(results, fmt.Sprintf("Step %d: %s ✗ (%s)", step.StepNumber+1, step.Description, err.Error()))
					} else {
						plan.Steps[i].Result = result
						plan.Steps[i].Status = StepStatusCompleted
						p.ErrorTracker.RecordStep(true, evaluation.WithStepName(step.Description))

						// Add result to context for future steps
						context[fmt.Sprintf("step_%d_result", step.StepNumber)] = result
						results = append(results, fmt.Sprintf("Step %d: %s ✓", step.StepNumber+1, step.Description))
					}
					break
				}
			}
		}
	}

	// Generate summary
	summary := strings.Join(results, "\n")

	if IsPlanComplete(*plan) {
		summary += fmt.Sprintf("\n\nPlan completed successfully (%.0f%%)", GetPlanProgress(*plan))
	} else if HasPlanFailures(*plan) {
		summary += fmt.Sprintf("\n\nPlan failed (%.0f%% complete)", GetPlanProgress(*plan))
	} else {
		summary += fmt.Sprintf("\n\nPlan partially completed (%.0f%%)", GetPlanProgress(*plan))
	}

	return summary, nil
}

func (p *PlanningAgent) replan(ctx context.Context, failedPlan *Plan) error {
	// Get failed steps
	failedSteps := []PlanStep{}
	for _, step := range failedPlan.Steps {
		if step.Status == StepStatusFailed {
			failedSteps = append(failedSteps, step)
		}
	}

	if len(failedSteps) == 0 {
		return nil
	}

	// Ask LLM to create alternative steps
	failedDescriptions := []string{}
	for _, step := range failedSteps {
		failedDescriptions = append(failedDescriptions, fmt.Sprintf("- %s (Error: %s)", step.Description, step.Error))
	}

	messages := []*agenkit.Message{
		{Role: "system", Content: p.systemPrompt},
		{Role: "user", Content: fmt.Sprintf("The following steps failed:\n%s\n\nCreate alternative steps to accomplish the goal: %s", strings.Join(failedDescriptions, "\n"), failedPlan.Goal)},
	}

	_, err := completeMessages(ctx, p.llm, messages)
	if err != nil {
		return fmt.Errorf("replanning LLM call failed: %w", err)
	}

	// For simplicity, mark failed steps as skipped
	for i := range failedPlan.Steps {
		if failedPlan.Steps[i].Status == StepStatusFailed {
			failedPlan.Steps[i].Status = StepStatusSkipped
		}
	}

	return nil
}

// GetPlan returns the current plan.
func (p *PlanningAgent) GetPlan() *Plan {
	return p.currentPlan
}

// GetProgress returns current plan progress as a percentage.
func (p *PlanningAgent) GetProgress() float64 {
	if p.currentPlan != nil {
		return GetPlanProgress(*p.currentPlan)
	}
	return 0
}
