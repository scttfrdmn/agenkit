// Package patterns provides the Autonomous Agent pattern.
//
// An agent that operates independently with minimal human intervention:
//   - Sets its own goals based on high-level objectives
//   - Makes decisions about actions to take
//   - Monitors progress and adapts strategy
//   - Continues until objective is met or stopped
//
// This pattern is useful for:
//   - Long-running tasks
//   - Self-directed research
//   - Continuous improvement systems
//   - Automated workflows
//
// Key concepts:
//   - Objective: High-level goal the agent is working towards
//   - Goals: Specific sub-tasks the agent pursues
//   - Iterations: Number of work cycles completed
//   - Stop Condition: Optional function to halt execution early
//
// Example:
//
//	agent := patterns.NewAutonomousAgent("Research and summarize AI trends", 10)
//	agent.AddGoal("Search for recent AI papers", 10)
//	agent.AddGoal("Identify key trends", 5)
//	agent.AddGoal("Write summary report", 1)
//
//	result, _ := agent.Run(ctx)
//	// Agent operates independently until complete
package patterns

import (
	"context"
	"fmt"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// GoalStatus represents the status of a goal.
type GoalStatus string

const (
	// GoalStatusActive indicates an active goal
	GoalStatusActive GoalStatus = "active"
	// GoalStatusCompleted indicates a completed goal
	GoalStatusCompleted GoalStatus = "completed"
	// GoalStatusAbandoned indicates an abandoned goal
	GoalStatusAbandoned GoalStatus = "abandoned"
)

// Goal represents a goal the autonomous agent is pursuing.
type Goal struct {
	// Description of the goal
	Description string
	// Priority (higher = more important)
	Priority int
	// Status of the goal
	Status GoalStatus
	// Progress from 0.0 to 1.0
	Progress float64
	// CreatedAt timestamp
	CreatedAt time.Time
}

// CreateGoal creates a new goal.
func CreateGoal(description string, priority int) *Goal {
	return &Goal{
		Description: description,
		Priority:    priority,
		Status:      GoalStatusActive,
		Progress:    0.0,
		CreatedAt:   time.Now(),
	}
}

// AutonomousResult represents the result of running an autonomous agent.
type AutonomousResult struct {
	// Objective being pursued
	Objective string
	// Iterations completed
	Iterations int
	// GoalsCompleted count
	GoalsCompleted int
	// Results from each iteration
	Results []string
}

// StopCondition is a function that determines if the agent should stop.
type StopCondition func() bool

// GoalWorker is a function that performs work on a goal.
type GoalWorker func(ctx context.Context, goal *Goal) (string, error)

// AutonomousAgent operates autonomously toward objectives.
//
// The autonomous agent:
//   - Manages multiple goals with different priorities
//   - Works on the highest priority active goal each iteration
//   - Updates progress and marks goals as completed
//   - Runs until max iterations, all goals complete, or stop condition met
//
// Example:
//
//	agent := NewAutonomousAgent("Complete research project", 10)
//	agent.AddGoal("Literature review", 10)
//	agent.AddGoal("Data collection", 8)
//	agent.AddGoal("Analysis", 5)
//	agent.AddGoal("Write paper", 3)
//
//	// Set custom work function
//	agent.SetWorker(func(ctx context.Context, goal *Goal) (string, error) {
//	    return fmt.Sprintf("Worked on: %s", goal.Description), nil
//	})
//
//	result, _ := agent.Run(context.Background())
type AutonomousAgent struct {
	name           string
	objective      string
	maxIterations  int
	stopCondition  StopCondition
	goals          []*Goal
	iterationCount int
	isRunning      bool
	worker         GoalWorker
}

// NewAutonomousAgent creates a new autonomous agent.
func NewAutonomousAgent(objective string, maxIterations int) *AutonomousAgent {
	if maxIterations <= 0 {
		maxIterations = 10
	}

	return &AutonomousAgent{
		name:           "AutonomousAgent",
		objective:      objective,
		maxIterations:  maxIterations,
		goals:          make([]*Goal, 0),
		iterationCount: 0,
		isRunning:      false,
		worker:         defaultWorker,
	}
}

// defaultWorker is the default work function.
func defaultWorker(ctx context.Context, goal *Goal) (string, error) {
	return fmt.Sprintf("Progress on: %s", goal.Description), nil
}

// Name returns the agent name.
func (a *AutonomousAgent) Name() string {
	return a.name
}

// Capabilities returns the agent capabilities.
func (a *AutonomousAgent) Capabilities() []string {
	return []string{"autonomous", "goal-directed", "self-organizing"}
}

// Process processes a message (autonomous agents don't need messages).
func (a *AutonomousAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{
		Role:    "assistant",
		Content: fmt.Sprintf("Autonomous agent working on: %s", a.objective),
	}, nil
}

// AddGoal adds a goal for the agent to pursue.
func (a *AutonomousAgent) AddGoal(description string, priority int) *Goal {
	goal := CreateGoal(description, priority)
	a.goals = append(a.goals, goal)
	return goal
}

// SetStopCondition sets the stop condition function.
func (a *AutonomousAgent) SetStopCondition(condition StopCondition) {
	a.stopCondition = condition
}

// SetWorker sets the worker function for processing goals.
func (a *AutonomousAgent) SetWorker(worker GoalWorker) {
	a.worker = worker
}

// Run runs the autonomous agent.
//
// Executes work iterations until:
//   - Max iterations reached
//   - All goals completed
//   - Stop condition met
//   - Agent manually stopped
//   - Context cancelled
func (a *AutonomousAgent) Run(ctx context.Context) (*AutonomousResult, error) {
	a.isRunning = true
	results := make([]string, 0)

	for a.iterationCount < a.maxIterations && a.isRunning {
		// Check context cancellation
		select {
		case <-ctx.Done():
			a.isRunning = false
			return nil, ctx.Err()
		default:
		}

		// Get active goals
		activeGoals := a.getActiveGoals()
		if len(activeGoals) == 0 {
			break
		}

		a.iterationCount++

		// Check stop condition (after increment to match TypeScript behavior)
		if a.stopCondition != nil && a.stopCondition() {
			break
		}

		// Work on highest priority goal
		goal := a.selectHighestPriorityGoal(activeGoals)
		result, err := a.worker(ctx, goal)
		if err != nil {
			return nil, fmt.Errorf("work on goal failed: %w", err)
		}

		results = append(results, result)

		// Update progress
		goal.Progress += 0.2
		if goal.Progress >= 1.0 {
			goal.Status = GoalStatusCompleted
		}
	}

	a.isRunning = false

	return &AutonomousResult{
		Objective:      a.objective,
		Iterations:     a.iterationCount,
		GoalsCompleted: a.countCompletedGoals(),
		Results:        results,
	}, nil
}

// getActiveGoals returns all active goals.
func (a *AutonomousAgent) getActiveGoals() []*Goal {
	active := make([]*Goal, 0)
	for _, goal := range a.goals {
		if goal.Status == GoalStatusActive {
			active = append(active, goal)
		}
	}
	return active
}

// selectHighestPriorityGoal selects the goal with highest priority.
func (a *AutonomousAgent) selectHighestPriorityGoal(goals []*Goal) *Goal {
	if len(goals) == 0 {
		return nil
	}

	highestPriority := goals[0]
	for _, goal := range goals[1:] {
		if goal.Priority > highestPriority.Priority {
			highestPriority = goal
		}
	}

	return highestPriority
}

// countCompletedGoals counts completed goals.
func (a *AutonomousAgent) countCompletedGoals() int {
	count := 0
	for _, goal := range a.goals {
		if goal.Status == GoalStatusCompleted {
			count++
		}
	}
	return count
}

// Stop stops the autonomous agent.
func (a *AutonomousAgent) Stop() {
	a.isRunning = false
}

// GetProgress returns overall progress as a percentage (0-100).
func (a *AutonomousAgent) GetProgress() float64 {
	if len(a.goals) == 0 {
		return 0.0
	}

	totalProgress := 0.0
	for _, goal := range a.goals {
		totalProgress += goal.Progress
	}

	return (totalProgress / float64(len(a.goals))) * 100.0
}

// GetGoals returns a copy of all goals.
func (a *AutonomousAgent) GetGoals() []*Goal {
	goalsCopy := make([]*Goal, len(a.goals))
	for i, goal := range a.goals {
		goalCopy := *goal
		goalsCopy[i] = &goalCopy
	}
	return goalsCopy
}

// GetObjective returns the agent's objective.
func (a *AutonomousAgent) GetObjective() string {
	return a.objective
}

// GetIterationCount returns the current iteration count.
func (a *AutonomousAgent) GetIterationCount() int {
	return a.iterationCount
}

// IsRunning returns whether the agent is currently running.
func (a *AutonomousAgent) IsRunning() bool {
	return a.isRunning
}
