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

// Pre-compiled regex patterns for critique parsing (performance optimization).
// Compiling regexes at package level avoids repeated compilation in hot loops.
var (
	scorePatternScore   = regexp.MustCompile(`(?i)score[:\s]+([0-9]*\.?[0-9]+)`)
	scorePatternRating  = regexp.MustCompile(`(?i)rating[:\s]+([0-9]*\.?[0-9]+)`)
	scorePatternOutOf10 = regexp.MustCompile(`(?i)([0-9]+)/10`)
	scorePatternOutOf1  = regexp.MustCompile(`(?i)([0-9]*\.?[0-9]+)/1\.?0`)

	scorePatterns = []*regexp.Regexp{
		scorePatternScore,
		scorePatternRating,
		scorePatternOutOf10,
		scorePatternOutOf1,
	}
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
	// Reset history for new task (pre-allocate with capacity to avoid reallocations)
	r.history = make([]ReflectionStep, 0, r.maxIterations)

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
		critiqueMsg := r.buildCritiquePrompt(message.ContentString(), output.ContentString())
		critiqueResponse, err := r.critic.Process(ctx, critiqueMsg)
		if err != nil {
			return nil, fmt.Errorf("critique failed at iteration %d: %w", iteration, err)
		}

		// Parse critique (score + feedback)
		score, feedback, err := r.parseCritique(critiqueResponse.ContentString())
		if err != nil {
			return nil, fmt.Errorf("failed to parse critique at iteration %d: %w", iteration, err)
		}

		improvement := score - previousScore

		// Record step (skip timestamp if not verbose to avoid syscall)
		step := ReflectionStep{
			Iteration:    iteration,
			Output:       output.ContentString(),
			Critique:     feedback,
			QualityScore: score,
			Improvement:  improvement,
		}
		if r.verbose {
			step.Timestamp = time.Now().UTC()
		}
		r.history = append(r.history, step)

		// Check stopping conditions
		stopReason, shouldStop := r.checkStopConditions(score, improvement)

		if shouldStop {
			return r.formatResult(output, stopReason), nil
		}

		// Refine based on critique
		refineMsg := r.buildRefinementPrompt(message.ContentString(), output.ContentString(), feedback, iteration)
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
// Optimized to use strings.Builder instead of fmt.Sprintf to reduce allocations.
func (r *ReflectionAgent) buildCritiquePrompt(originalQuery, currentOutput string) *agenkit.Message {
	var b strings.Builder
	b.Grow(256 + len(originalQuery) + len(currentOutput)) // Pre-allocate reasonable size

	if r.critiqueFormat == CritiqueStructured {
		b.WriteString("Please evaluate the following output and provide structured feedback.\n\nOriginal Request:\n")
		b.WriteString(originalQuery)
		b.WriteString("\n\nCurrent Output:\n")
		b.WriteString(currentOutput)
		b.WriteString("\n\nProvide your evaluation in this JSON format:\n{\n  \"score\": <float between 0.0 and 1.0>,\n  \"feedback\": \"<specific feedback on what could be improved>\"\n}\n\nFocus on:\n- Correctness: Does it solve the problem?\n- Quality: Is it well-structured and clear?\n- Completeness: Does it address all aspects?\n- Potential Issues: Are there bugs or edge cases?")
	} else {
		b.WriteString("Please evaluate the following output on a scale of 0.0 to 1.0.\n\nOriginal Request:\n")
		b.WriteString(originalQuery)
		b.WriteString("\n\nCurrent Output:\n")
		b.WriteString(currentOutput)
		b.WriteString("\n\nProvide:\n1. A score (0.0-1.0) indicating quality\n2. Specific feedback on what could be improved\n\nYour evaluation:")
	}

	return agenkit.NewMessage("user", b.String())
}

// buildRefinementPrompt creates a prompt for the generator to refine output.
// Optimized to use strings.Builder instead of fmt.Sprintf to reduce allocations.
func (r *ReflectionAgent) buildRefinementPrompt(originalQuery, currentOutput, critique string, iteration int) *agenkit.Message {
	var b strings.Builder
	b.Grow(256 + len(originalQuery) + len(currentOutput) + len(critique))

	b.WriteString("Please refine your previous output based on the following critique.\n\nOriginal Request:\n")
	b.WriteString(originalQuery)
	b.WriteString("\n\nYour Previous Output (Iteration ")
	b.WriteString(strconv.Itoa(iteration))
	b.WriteString("):\n")
	b.WriteString(currentOutput)
	b.WriteString("\n\nCritique:\n")
	b.WriteString(critique)
	b.WriteString("\n\nPlease provide an improved version that addresses the critique while maintaining what was already good.\n\nRefined Output:")

	return agenkit.NewMessage("user", b.String())
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
	content = strings.TrimSpace(content)

	// Fast path: if content doesn't look like JSON, skip expensive parsing
	if !strings.Contains(content, "{") || !strings.Contains(content, "}") {
		return r.parseFreeFormCritique(content)
	}

	// Handle markdown code blocks only if present
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

	// Use pre-compiled regex patterns (package-level variables)
	for _, pattern := range scorePatterns {
		matches := pattern.FindStringSubmatch(content)
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
	// Reuse or create metadata map (optimization: avoid copying if possible)
	metadata := output.Metadata
	if metadata == nil {
		metadata = make(map[string]interface{}, 8)
	} else {
		// Make a copy if metadata exists to avoid modifying original
		newMetadata := make(map[string]interface{}, len(metadata)+8)
		for k, v := range metadata {
			newMetadata[k] = v
		}
		metadata = newMetadata
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
		Content:   output.ContentString(),
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
	r.history = make([]ReflectionStep, 0, r.maxIterations)
}
