// Package patterns provides implementation of common agent patterns.
// The Reflection pattern enables agents to review and improve their own outputs
// through an iterative cycle of generation, critique, and refinement.
package patterns

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// StopReason indicates why the reflection loop stopped.
type StopReason string

const (
	// StopQualityThreshold indicates quality threshold was met
	StopQualityThreshold StopReason = "quality_threshold_met"
	// StopMinimalImprovement indicates improvements became minimal
	StopMinimalImprovement StopReason = "minimal_improvement"
	// StopMaxIterations indicates maximum iterations reached
	StopMaxIterations StopReason = "max_iterations"
	// StopPerfectScore indicates perfect score (1.0) achieved
	StopPerfectScore StopReason = "perfect_score"
)

// CritiqueFormat specifies the expected format from the critic agent.
type CritiqueFormat string

const (
	// CritiqueStructured expects JSON format: {"score": 0.8, "feedback": "..."}
	CritiqueStructured CritiqueFormat = "structured"
	// CritiqueFreeForm expects free text with score extracted
	CritiqueFreeForm CritiqueFormat = "free_form"
)

// ReflectionStep represents a single iteration in the reflection loop.
type ReflectionStep struct {
	Iteration    int       `json:"iteration"`
	Output       string    `json:"output"`
	Critique     string    `json:"critique"`
	QualityScore float64   `json:"quality_score"`
	Improvement  float64   `json:"improvement"`
	Timestamp    time.Time `json:"timestamp"`
}

// CritiqueResponse represents structured critique from the critic agent.
type CritiqueResponse struct {
	Score    float64 `json:"score"`
	Feedback string  `json:"feedback"`
}

// ReflectionAgent implements the Reflection pattern for iterative refinement.
// It coordinates between a generator agent and a critic agent to progressively
// improve outputs through self-critique.
//
// The reflection loop:
//  1. Generator creates initial output
//  2. Critic evaluates output, provides score and feedback
//  3. Generator refines output based on feedback
//  4. Repeat until quality threshold, minimal improvement, or max iterations
//
// Performance Characteristics:
//   - Latency: N × (generator + critic), where N = number of iterations
//   - Quality: Generally improves with iterations
//   - Cost: N × (generator cost + critic cost)
//   - Best for: Tasks where quality improvement justifies additional cost
type ReflectionAgent struct {
	generator            agenkit.Agent
	critic               agenkit.Agent
	maxIterations        int
	qualityThreshold     float64
	improvementThreshold float64
	critiqueFormat       CritiqueFormat
	verbose              bool
	history              []ReflectionStep
}

// ReflectionConfig contains configuration for a ReflectionAgent.
type ReflectionConfig struct {
	Generator            agenkit.Agent
	Critic               agenkit.Agent
	MaxIterations        int
	QualityThreshold     float64
	ImprovementThreshold float64
	CritiqueFormat       CritiqueFormat
	Verbose              bool
}

// NewReflectionAgent creates a new ReflectionAgent with the given configuration.
func NewReflectionAgent(config ReflectionConfig) (*ReflectionAgent, error) {
	// Validate configuration
	if config.Generator == nil {
		return nil, fmt.Errorf("generator agent is required")
	}
	if config.Critic == nil {
		return nil, fmt.Errorf("critic agent is required")
	}
	if config.MaxIterations < 1 {
		return nil, fmt.Errorf("max_iterations must be at least 1, got %d", config.MaxIterations)
	}
	if config.QualityThreshold < 0.0 || config.QualityThreshold > 1.0 {
		return nil, fmt.Errorf("quality_threshold must be between 0.0 and 1.0, got %f", config.QualityThreshold)
	}
	if config.ImprovementThreshold < 0.0 || config.ImprovementThreshold > 1.0 {
		return nil, fmt.Errorf("improvement_threshold must be between 0.0 and 1.0, got %f", config.ImprovementThreshold)
	}

	// Set defaults
	if config.MaxIterations == 0 {
		config.MaxIterations = 5
	}
	if config.QualityThreshold == 0.0 {
		config.QualityThreshold = 0.9
	}
	if config.ImprovementThreshold == 0.0 {
		config.ImprovementThreshold = 0.05
	}
	if config.CritiqueFormat == "" {
		config.CritiqueFormat = CritiqueStructured
	}

	return &ReflectionAgent{
		generator:            config.Generator,
		critic:               config.Critic,
		maxIterations:        config.MaxIterations,
		qualityThreshold:     config.QualityThreshold,
		improvementThreshold: config.ImprovementThreshold,
		critiqueFormat:       config.CritiqueFormat,
		verbose:              config.Verbose,
		history:              make([]ReflectionStep, 0),
	}, nil
}

// Name returns the agent's name.
func (r *ReflectionAgent) Name() string {
	return "ReflectionAgent"
}

// Capabilities returns the combined capabilities of generator and critic.
func (r *ReflectionAgent) Capabilities() []string {
	caps := make(map[string]bool)

	// Add generator capabilities
	for _, cap := range r.generator.Capabilities() {
		caps[cap] = true
	}

	// Add critic capabilities
	for _, cap := range r.critic.Capabilities() {
		caps[cap] = true
	}

	// Add reflection-specific capabilities
	caps["reflection"] = true
	caps["self-critique"] = true

	// Convert to slice
	result := make([]string, 0, len(caps))
	for cap := range caps {
		result = append(result, cap)
	}

	return result
}

// Process executes the reflection loop.
//
// Args:
//
//	ctx: Context for cancellation and timeouts
//	message: User's request/task
//
// Returns:
//
//	Message containing refined output with reflection metadata
//
// Metadata Structure:
//   - reflection_iterations: Number of iterations performed
//   - final_quality_score: Final quality score achieved
//   - stop_reason: Why the loop stopped
//   - reflection_history: List of ReflectionStep (if verbose=true)
//   - initial_quality_score: Quality score of first output
//   - total_improvement: Improvement from first to final
func (r *ReflectionAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Reset history for new task
	r.history = make([]ReflectionStep, 0)

	// Initial generation
	output, err := r.generator.Process(ctx, message)
	if err != nil {
		return nil, fmt.Errorf("initial generation failed: %w", err)
	}

	previousScore := 0.0

	// Reflection loop
	for iteration := 1; iteration <= r.maxIterations; iteration++ {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		// Critique current output
		critiqueMsg := r.buildCritiquePrompt(message.Content, output.Content)
		critiqueResponse, err := r.critic.Process(ctx, critiqueMsg)
		if err != nil {
			return nil, fmt.Errorf("critique failed at iteration %d: %w", iteration, err)
		}

		// Parse critique (score + feedback)
		score, feedback, err := r.parseCritique(critiqueResponse.Content)
		if err != nil {
			return nil, fmt.Errorf("failed to parse critique at iteration %d: %w", iteration, err)
		}

		improvement := score - previousScore

		// Record step
		step := ReflectionStep{
			Iteration:    iteration,
			Output:       output.Content,
			Critique:     feedback,
			QualityScore: score,
			Improvement:  improvement,
			Timestamp:    time.Now().UTC(),
		}
		r.history = append(r.history, step)

		// Check stopping conditions
		stopReason, shouldStop := r.checkStopConditions(score, improvement)

		if shouldStop {
			return r.formatResult(output, stopReason), nil
		}

		// Refine based on critique
		refineMsg := r.buildRefinementPrompt(message.Content, output.Content, feedback, iteration)
		output, err = r.generator.Process(ctx, refineMsg)
		if err != nil {
			return nil, fmt.Errorf("refinement failed at iteration %d: %w", iteration, err)
		}

		previousScore = score
	}

	// Max iterations reached
	return r.formatResult(output, StopMaxIterations), nil
}

// buildCritiquePrompt creates a prompt for the critic agent.
func (r *ReflectionAgent) buildCritiquePrompt(originalQuery, currentOutput string) *agenkit.Message {
	var prompt string

	if r.critiqueFormat == CritiqueStructured {
		prompt = fmt.Sprintf(`Please evaluate the following output and provide structured feedback.

Original Request:
%s

Current Output:
%s

Provide your evaluation in this JSON format:
{
  "score": <float between 0.0 and 1.0>,
  "feedback": "<specific feedback on what could be improved>"
}

Focus on:
- Correctness: Does it solve the problem?
- Quality: Is it well-structured and clear?
- Completeness: Does it address all aspects?
- Potential Issues: Are there bugs or edge cases?`, originalQuery, currentOutput)
	} else {
		prompt = fmt.Sprintf(`Please evaluate the following output on a scale of 0.0 to 1.0.

Original Request:
%s

Current Output:
%s

Provide:
1. A score (0.0-1.0) indicating quality
2. Specific feedback on what could be improved

Your evaluation:`, originalQuery, currentOutput)
	}

	return agenkit.NewMessage("user", prompt)
}

// buildRefinementPrompt creates a prompt for the generator to refine output.
func (r *ReflectionAgent) buildRefinementPrompt(originalQuery, currentOutput, critique string, iteration int) *agenkit.Message {
	prompt := fmt.Sprintf(`Please refine your previous output based on the following critique.

Original Request:
%s

Your Previous Output (Iteration %d):
%s

Critique:
%s

Please provide an improved version that addresses the critique while maintaining what was already good.

Refined Output:`, originalQuery, iteration, currentOutput, critique)

	return agenkit.NewMessage("user", prompt)
}

// parseCritique parses the critic's response into score and feedback.
func (r *ReflectionAgent) parseCritique(critiqueContent string) (float64, string, error) {
	if r.critiqueFormat == CritiqueStructured {
		return r.parseStructuredCritique(critiqueContent)
	}
	return r.parseFreeFormCritique(critiqueContent)
}

// parseStructuredCritique parses JSON-formatted critique.
func (r *ReflectionAgent) parseStructuredCritique(content string) (float64, string, error) {
	// Handle markdown code blocks
	content = strings.TrimSpace(content)
	if strings.HasPrefix(content, "```") {
		lines := strings.Split(content, "\n")
		var jsonLines []string
		for _, line := range lines {
			if line != "" && !strings.HasPrefix(line, "```") {
				jsonLines = append(jsonLines, line)
			}
		}
		content = strings.Join(jsonLines, "\n")
	}

	var critique CritiqueResponse
	if err := json.Unmarshal([]byte(content), &critique); err != nil {
		// Fallback to free-form parsing
		return r.parseFreeFormCritique(content)
	}

	// Clamp score to valid range
	score := critique.Score
	if score < 0.0 {
		score = 0.0
	}
	if score > 1.0 {
		score = 1.0
	}

	feedback := critique.Feedback
	if feedback == "" {
		feedback = content
	}

	return score, feedback, nil
}

// parseFreeFormCritique extracts score from free-form text.
func (r *ReflectionAgent) parseFreeFormCritique(content string) (float64, string, error) {
	score := 0.5 // Default if no score found

	// Try to find score patterns
	patterns := []string{
		`score[:\s]+([0-9]*\.?[0-9]+)`,  // "Score: 0.8"
		`rating[:\s]+([0-9]*\.?[0-9]+)`, // "Rating: 8"
		`([0-9]+)/10`,                   // "8/10"
		`([0-9]*\.?[0-9]+)/1\.?0`,       // "0.8/1.0"
	}

	for _, pattern := range patterns {
		re := regexp.MustCompile(`(?i)` + pattern)
		matches := re.FindStringSubmatch(content)
		if len(matches) > 1 {
			value, err := strconv.ParseFloat(matches[1], 64)
			if err == nil {
				// Normalize to 0.0-1.0 range
				if value > 1.0 {
					value = value / 10.0 // Assume 0-10 scale
				}
				score = value
				if score < 0.0 {
					score = 0.0
				}
				if score > 1.0 {
					score = 1.0
				}
				break
			}
		}
	}

	return score, content, nil
}

// checkStopConditions determines if the reflection loop should stop.
func (r *ReflectionAgent) checkStopConditions(score, improvement float64) (StopReason, bool) {
	// Perfect score
	if score >= 1.0 {
		return StopPerfectScore, true
	}

	// Quality threshold met
	if score >= r.qualityThreshold {
		return StopQualityThreshold, true
	}

	// Minimal improvement (skip on first iteration)
	if len(r.history) > 1 && improvement < r.improvementThreshold {
		return StopMinimalImprovement, true
	}

	// Continue iterating
	return StopMaxIterations, false // Placeholder, will be overridden if needed
}

// formatResult formats the final result with metadata.
func (r *ReflectionAgent) formatResult(output *agenkit.Message, stopReason StopReason) *agenkit.Message {
	// Gather metadata
	metadata := make(map[string]interface{})
	for k, v := range output.Metadata {
		metadata[k] = v
	}

	metadata["reflection_iterations"] = len(r.history)
	metadata["stop_reason"] = string(stopReason)

	if len(r.history) > 0 {
		metadata["final_quality_score"] = r.history[len(r.history)-1].QualityScore
		metadata["initial_quality_score"] = r.history[0].QualityScore
		metadata["total_improvement"] = r.history[len(r.history)-1].QualityScore - r.history[0].QualityScore
	} else {
		metadata["final_quality_score"] = 0.0
	}

	// Include history if verbose
	if r.verbose {
		metadata["reflection_history"] = r.history
	}

	result := &agenkit.Message{
		Role:      output.Role,
		Content:   output.Content,
		Metadata:  metadata,
		Timestamp: time.Now().UTC(),
	}

	return result
}

// GetHistory returns the reflection history from the last execution.
func (r *ReflectionAgent) GetHistory() []ReflectionStep {
	history := make([]ReflectionStep, len(r.history))
	copy(history, r.history)
	return history
}

// ClearHistory clears the reflection history.
func (r *ReflectionAgent) ClearHistory() {
	r.history = make([]ReflectionStep, 0)
}
