// Plan-and-Solve Prompting Technique
//
// Explicitly separates planning (devising a solution strategy) from solving
// (executing the strategy). Creates more structured reasoning than pure CoT
// by forcing an upfront planning phase.
//
// This technique is particularly effective for complex problems that benefit
// from strategic planning before execution.
//
// Reference: "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning"
// Lei Wang et al., 2023 - https://arxiv.org/abs/2305.04091

package reasoning

import (
	"context"
	"fmt"
	"regexp"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// PlanStep represents a single step in a plan
type PlanStep struct {
	Description         string
	Order               int
	Dependencies        []int
	EstimatedComplexity int // 1-5 scale
	Result              string
	Executed            bool
}

// Plan represents a complete solution plan
type Plan struct {
	Steps           []*PlanStep
	Problem         string
	Strategy        string
	Validated       bool
	ValidationNotes string
}

// PlannerFunc is a custom function to create plans
type PlannerFunc func(ctx context.Context, problem string) (*Plan, error)

// SolverFunc is a custom function to execute plan steps
type SolverFunc func(ctx context.Context, step *PlanStep, previousResults []string) (string, error)

// PlanAndSolveConfig configures the Plan-and-Solve agent
type PlanAndSolveConfig struct {
	Planner          PlannerFunc
	Solver           SolverFunc
	ValidatePlan     bool
	AllowReplanning  bool
}

// PlanAndSolveAgent implements the Plan-and-Solve technique
type PlanAndSolveAgent struct {
	agent           agenkit.Agent
	planner         PlannerFunc
	solver          SolverFunc
	validatePlan    bool
	allowReplanning bool
}

// NewPlanAndSolveAgent creates a new Plan-and-Solve agent
func NewPlanAndSolveAgent(agent agenkit.Agent, config PlanAndSolveConfig) *PlanAndSolveAgent {
	return &PlanAndSolveAgent{
		agent:           agent,
		planner:         config.Planner,
		solver:          config.Solver,
		validatePlan:    config.ValidatePlan,
		allowReplanning: config.AllowReplanning,
	}
}

// Name returns the agent name
func (a *PlanAndSolveAgent) Name() string {
	return "plan_and_solve"
}

// Capabilities returns agent capabilities
func (a *PlanAndSolveAgent) Capabilities() []string {
	return []string{
		"reasoning",
		"planning",
		"plan_and_solve",
		"strategic_thinking",
		"step_by_step_execution",
	}
}

// llmCall calls the underlying LLM with a prompt
func (a *PlanAndSolveAgent) llmCall(ctx context.Context, prompt string) (string, error) {
	message := &agenkit.Message{
		Role:    "user",
		Content: prompt,
	}

	response, err := a.agent.Process(ctx, message)
	if err != nil {
		return "", err
	}

	return response.Content, nil
}

// CreatePlan creates a solution plan for the problem
func (a *PlanAndSolveAgent) CreatePlan(ctx context.Context, problem string) (*Plan, error) {
	if a.planner != nil {
		return a.planner(ctx, problem)
	}

	// Use LLM to create plan
	prompt := fmt.Sprintf(`Create a detailed step-by-step plan to solve this problem.
List each step on a separate line, numbered 1, 2, 3, etc.
Focus on WHAT needs to be done, not HOW to do it yet.

Problem: %s

Solution Plan:`, problem)

	response, err := a.llmCall(ctx, prompt)
	if err != nil {
		return nil, err
	}

	// Parse plan from response
	steps := make([]*PlanStep, 0)
	lines := strings.Split(strings.TrimSpace(response), "\n")

	// Regex to remove numbering (1., 1), etc.)
	numberPattern := regexp.MustCompile(`^\d+[\.\)]\s*`)

	for i, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		cleaned := numberPattern.ReplaceAllString(line, "")
		if cleaned != "" {
			steps = append(steps, &PlanStep{
				Description:         cleaned,
				Order:               i,
				EstimatedComplexity: 1,
				Executed:            false,
			})
		}
	}

	return &Plan{
		Steps:   steps,
		Problem: problem,
	}, nil
}

// Validate validates that a plan is complete and feasible
func (a *PlanAndSolveAgent) Validate(ctx context.Context, plan *Plan) (*Plan, error) {
	prompt := fmt.Sprintf(`Review this solution plan for completeness and feasibility.
Is this plan sufficient to solve the problem? Are there any missing steps or issues?

Problem: %s

Plan:
%s

Validation (answer "VALID" or describe issues):`, plan.Problem, a.formatPlan(plan))

	response, err := a.llmCall(ctx, prompt)
	if err != nil {
		return plan, err
	}

	// Check if plan is valid
	responseUpper := strings.ToUpper(response)
	isValid := strings.Contains(responseUpper, "VALID") || strings.Contains(responseUpper, "YES")

	plan.Validated = isValid
	plan.ValidationNotes = strings.TrimSpace(response)

	return plan, nil
}

// formatPlan formats a plan for display
func (a *PlanAndSolveAgent) formatPlan(plan *Plan) string {
	lines := make([]string, 0, len(plan.Steps))
	for i, step := range plan.Steps {
		status := "○"
		if step.Executed {
			status = "✓"
		}
		lines = append(lines, fmt.Sprintf("%d. [%s] %s", i+1, status, step.Description))
	}
	return strings.Join(lines, "\n")
}

// ExecuteStep executes a single plan step
func (a *PlanAndSolveAgent) ExecuteStep(ctx context.Context, step *PlanStep, previousResults []string) (string, error) {
	if a.solver != nil {
		return a.solver(ctx, step, previousResults)
	}

	// Use LLM to execute step
	var prompt string

	if len(previousResults) > 0 {
		contextLines := make([]string, 0, len(previousResults))
		for i, result := range previousResults {
			contextLines = append(contextLines, fmt.Sprintf("Previous step %d result: %s", i+1, result))
		}
		context := strings.Join(contextLines, "\n")

		prompt = fmt.Sprintf(`Execute this step of the plan, using previous results as context.

Previous Results:
%s

Current Step: %s

Execution Result:`, context, step.Description)
	} else {
		prompt = fmt.Sprintf(`Execute this step of the plan:

Step: %s

Execution Result:`, step.Description)
	}

	result, err := a.llmCall(ctx, prompt)
	if err != nil {
		return "", err
	}

	return strings.TrimSpace(result), nil
}

// ExecutePlan executes all steps in the plan sequentially
func (a *PlanAndSolveAgent) ExecutePlan(ctx context.Context, plan *Plan) ([]string, error) {
	results := make([]string, 0, len(plan.Steps))

	for _, step := range plan.Steps {
		result, err := a.ExecuteStep(ctx, step, results)
		if err != nil {
			return results, err
		}

		step.Result = result
		step.Executed = true
		results = append(results, result)
	}

	return results, nil
}

// Process processes a message with Plan-and-Solve prompting
func (a *PlanAndSolveAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	problem := message.Content

	// Phase 1: Create plan
	plan, err := a.CreatePlan(ctx, problem)
	if err != nil {
		return nil, err
	}

	// Phase 2: Validate plan (if enabled)
	if a.validatePlan {
		plan, err = a.Validate(ctx, plan)
		if err != nil {
			return nil, err
		}

		// If validation failed and replanning is allowed
		if !plan.Validated && a.allowReplanning {
			improvedPrompt := fmt.Sprintf(`The previous plan had issues. Create an improved plan.

Problem: %s

Previous Plan Issues:
%s

Improved Plan:`, problem, plan.ValidationNotes)

			_, _ = a.llmCall(ctx, improvedPrompt)
			plan, err = a.CreatePlan(ctx, problem)
			if err != nil {
				return nil, err
			}
			plan, err = a.Validate(ctx, plan)
			if err != nil {
				return nil, err
			}
		}
	}

	// Phase 3: Execute plan
	executionResults, err := a.ExecutePlan(ctx, plan)
	if err != nil {
		return nil, err
	}

	// Final solution is the last step's result
	finalSolution := ""
	if len(executionResults) > 0 {
		finalSolution = executionResults[len(executionResults)-1]
	}

	// Build metadata
	planSteps := make([]string, len(plan.Steps))
	for i, step := range plan.Steps {
		planSteps[i] = step.Description
	}

	metadata := map[string]interface{}{
		"technique":         "plan_and_solve",
		"plan_steps":        planSteps,
		"execution_steps":   executionResults,
		"num_steps":         len(plan.Steps),
		"validated":         plan.Validated,
		"validation_notes":  plan.ValidationNotes,
		"allow_replanning":  a.allowReplanning,
	}

	return &agenkit.Message{
		Role:     "assistant",
		Content:  finalSolution,
		Metadata: metadata,
	}, nil
}
