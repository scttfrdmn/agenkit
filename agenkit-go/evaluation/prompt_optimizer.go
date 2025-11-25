// Package evaluation provides the Prompt Optimization Framework.
//
// Automatically improve prompts through systematic variation and testing
// using grid search, random search, or genetic algorithms.
//
// Example:
//
//	template := `You are a {role}.
//	{instructions}`
//
//	variations := map[string][]string{
//	    "role":         {"helpful assistant", "expert advisor"},
//	    "instructions": {"Be concise.", "Be detailed."},
//	}
//
//	optimizer := evaluation.NewPromptOptimizer(
//	    template,
//	    variations,
//	    func(prompt string) agenkit.Agent { return MyAgent{SystemPrompt: prompt} },
//	    []string{"accuracy"},
//	    nil,
//	)
//
//	result, _ := optimizer.Optimize(ctx, testCases, "grid", nil)
package evaluation

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// OptimizationStrategy represents prompt optimization strategies.
type OptimizationStrategy string

const (
	// StrategyGrid exhaustive grid search
	StrategyGrid OptimizationStrategy = "grid"
	// StrategyRandom random sampling
	StrategyRandom OptimizationStrategy = "random"
	// StrategyGenetic genetic algorithm
	StrategyGenetic OptimizationStrategy = "genetic"
)

// PromptOptimizationResult contains results from prompt optimization.
type PromptOptimizationResult struct {
	// BestPrompt is the best prompt found
	BestPrompt string
	// BestConfig is the best variable configuration
	BestConfig map[string]string
	// BestScores contains best metric scores
	BestScores map[string]float64
	// History contains all (prompt, config, scores) tuples
	History []PromptEvaluation
	// NEvaluated is the number of prompts evaluated
	NEvaluated int
	// Strategy used
	Strategy string
	// StartTime in milliseconds
	StartTime int64
	// EndTime in milliseconds
	EndTime int64
}

// PromptEvaluation represents a single prompt evaluation.
type PromptEvaluation struct {
	Prompt string
	Config map[string]string
	Scores map[string]float64
}

// DurationSeconds returns the duration in seconds.
func (r *PromptOptimizationResult) DurationSeconds() float64 {
	return float64(r.EndTime-r.StartTime) / 1000.0
}

// ToDict converts result to dictionary.
func (r *PromptOptimizationResult) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"best_prompt":      r.BestPrompt,
		"best_config":      r.BestConfig,
		"best_scores":      r.BestScores,
		"n_evaluated":      r.NEvaluated,
		"strategy":         r.Strategy,
		"duration_seconds": r.DurationSeconds(),
		"start_time":       r.StartTime,
		"end_time":         r.EndTime,
	}
}

// AgentFactory is a function that creates an agent from a prompt string.
type AgentFactory func(prompt string) agenkit.Agent

// PromptOptimizer optimizes prompts through systematic variation.
//
// Supports multiple optimization strategies:
// - Grid search: Exhaustive evaluation of all combinations
// - Random search: Random sampling of combinations
// - Genetic algorithm: Evolutionary optimization
type PromptOptimizer struct {
	template        string
	variations      map[string][]string
	agentFactory    AgentFactory
	metrics         []string
	objectiveMetric string
	maximize        bool
	history         []PromptEvaluation
}

// NewPromptOptimizer creates a new prompt optimizer.
//
// Args:
//
//	template: Prompt template with {variable} placeholders
//	variations: Map of variable names to possible values
//	agentFactory: Function that creates agent from prompt string
//	metrics: List of metrics to evaluate
//	objectiveMetric: Primary metric for optimization (nil = first metric)
//	maximize: Whether to maximize (true) or minimize (false) objective
func NewPromptOptimizer(
	template string,
	variations map[string][]string,
	agentFactory AgentFactory,
	metrics []string,
	objectiveMetric *string,
) *PromptOptimizer {
	objMetric := metrics[0]
	if objectiveMetric != nil {
		objMetric = *objectiveMetric
	}

	return &PromptOptimizer{
		template:        template,
		variations:      variations,
		agentFactory:    agentFactory,
		metrics:         metrics,
		objectiveMetric: objMetric,
		maximize:        true,
		history:         make([]PromptEvaluation, 0),
	}
}

// SetMaximize sets whether to maximize (true) or minimize (false) the objective.
func (p *PromptOptimizer) SetMaximize(maximize bool) {
	p.maximize = maximize
}

// fillTemplate fills template with configuration values.
func (p *PromptOptimizer) fillTemplate(config map[string]string) string {
	result := p.template
	for key, value := range config {
		placeholder := "{" + key + "}"
		result = strings.ReplaceAll(result, placeholder, value)
	}
	return result
}

// generateAllConfigs generates all possible configurations (Cartesian product).
func (p *PromptOptimizer) generateAllConfigs() []map[string]string {
	keys := make([]string, 0, len(p.variations))
	valueLists := make([][]string, 0, len(p.variations))

	for key, values := range p.variations {
		keys = append(keys, key)
		valueLists = append(valueLists, values)
	}

	return p.cartesianProduct(keys, valueLists, 0, make(map[string]string))
}

// cartesianProduct generates Cartesian product recursively.
func (p *PromptOptimizer) cartesianProduct(
	keys []string,
	valueLists [][]string,
	index int,
	current map[string]string,
) []map[string]string {
	if index == len(keys) {
		// Base case: copy current config
		config := make(map[string]string)
		for k, v := range current {
			config[k] = v
		}
		return []map[string]string{config}
	}

	results := make([]map[string]string, 0)
	for _, value := range valueLists[index] {
		current[keys[index]] = value
		configs := p.cartesianProduct(keys, valueLists, index+1, current)
		results = append(results, configs...)
	}

	return results
}

// sampleConfig samples a random configuration.
func (p *PromptOptimizer) sampleConfig() map[string]string {
	config := make(map[string]string)
	for key, values := range p.variations {
		config[key] = values[rand.Intn(len(values))]
	}
	return config
}

// evaluatePrompt evaluates a prompt on test cases.
func (p *PromptOptimizer) evaluatePrompt(
	ctx context.Context,
	prompt string,
	testCases []map[string]interface{},
) (map[string]float64, error) {
	// Create agent with prompt
	agent := p.agentFactory(prompt)

	// Create evaluator
	// Note: This is a simplified evaluation - in production, you'd use
	// the full evaluation framework with custom metrics
	scores := make(map[string]float64)

	// For now, just run the agent on test cases and collect basic metrics
	// This would be replaced with proper metric evaluation
	totalLatency := 0.0
	successCount := 0

	for _, testCase := range testCases {
		input, ok := testCase["input"].(string)
		if !ok {
			continue
		}

		startTime := time.Now()
		_, err := agent.Process(ctx, &agenkit.Message{
			Role:    "user",
			Content: input,
		})
		latency := time.Since(startTime).Milliseconds()

		totalLatency += float64(latency)
		if err == nil {
			successCount++
		}
	}

	// Calculate metrics
	if len(testCases) > 0 {
		scores["accuracy"] = float64(successCount) / float64(len(testCases))
		scores["latency_ms"] = totalLatency / float64(len(testCases))
	}

	return scores, nil
}

// getObjectiveScore gets objective score from metric scores.
func (p *PromptOptimizer) getObjectiveScore(scores map[string]float64) float64 {
	score, ok := scores[p.objectiveMetric]
	if !ok {
		return 0.0
	}

	// Invert if minimizing (e.g., latency)
	if !p.maximize {
		score = -score
	}

	return score
}

// OptimizeGrid performs grid search by evaluating all possible combinations.
func (p *PromptOptimizer) OptimizeGrid(
	ctx context.Context,
	testCases []map[string]interface{},
) (*PromptOptimizationResult, error) {
	startTime := time.Now().UnixMilli()
	p.history = make([]PromptEvaluation, 0)

	// Generate all configs
	configs := p.generateAllConfigs()

	bestPrompt := ""
	bestConfig := make(map[string]string)
	bestScores := make(map[string]float64)
	bestObjective := -1e9

	// Evaluate each configuration
	for _, config := range configs {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		prompt := p.fillTemplate(config)
		scores, err := p.evaluatePrompt(ctx, prompt, testCases)
		if err != nil {
			return nil, fmt.Errorf("evaluation failed: %w", err)
		}

		objectiveScore := p.getObjectiveScore(scores)

		// Copy config and scores
		configCopy := make(map[string]string)
		for k, v := range config {
			configCopy[k] = v
		}
		scoresCopy := make(map[string]float64)
		for k, v := range scores {
			scoresCopy[k] = v
		}

		p.history = append(p.history, PromptEvaluation{
			Prompt: prompt,
			Config: configCopy,
			Scores: scoresCopy,
		})

		if objectiveScore > bestObjective {
			bestObjective = objectiveScore
			bestPrompt = prompt
			bestConfig = configCopy
			bestScores = scoresCopy
		}
	}

	endTime := time.Now().UnixMilli()

	return &PromptOptimizationResult{
		BestPrompt: bestPrompt,
		BestConfig: bestConfig,
		BestScores: bestScores,
		History:    p.history,
		NEvaluated: len(configs),
		Strategy:   string(StrategyGrid),
		StartTime:  startTime,
		EndTime:    endTime,
	}, nil
}

// OptimizeRandom performs random search by sampling random combinations.
func (p *PromptOptimizer) OptimizeRandom(
	ctx context.Context,
	testCases []map[string]interface{},
	nSamples int,
) (*PromptOptimizationResult, error) {
	startTime := time.Now().UnixMilli()
	p.history = make([]PromptEvaluation, 0)

	bestPrompt := ""
	bestConfig := make(map[string]string)
	bestScores := make(map[string]float64)
	bestObjective := -1e9

	// Sample and evaluate random configurations
	for i := 0; i < nSamples; i++ {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		config := p.sampleConfig()
		prompt := p.fillTemplate(config)
		scores, err := p.evaluatePrompt(ctx, prompt, testCases)
		if err != nil {
			return nil, fmt.Errorf("evaluation failed: %w", err)
		}

		objectiveScore := p.getObjectiveScore(scores)

		// Copy config and scores
		configCopy := make(map[string]string)
		for k, v := range config {
			configCopy[k] = v
		}
		scoresCopy := make(map[string]float64)
		for k, v := range scores {
			scoresCopy[k] = v
		}

		p.history = append(p.history, PromptEvaluation{
			Prompt: prompt,
			Config: configCopy,
			Scores: scoresCopy,
		})

		if objectiveScore > bestObjective {
			bestObjective = objectiveScore
			bestPrompt = prompt
			bestConfig = configCopy
			bestScores = scoresCopy
		}
	}

	endTime := time.Now().UnixMilli()

	return &PromptOptimizationResult{
		BestPrompt: bestPrompt,
		BestConfig: bestConfig,
		BestScores: bestScores,
		History:    p.history,
		NEvaluated: nSamples,
		Strategy:   string(StrategyRandom),
		StartTime:  startTime,
		EndTime:    endTime,
	}, nil
}

// OptimizeGenetic performs genetic algorithm optimization.
func (p *PromptOptimizer) OptimizeGenetic(
	ctx context.Context,
	testCases []map[string]interface{},
	populationSize int,
	nGenerations int,
	mutationRate float64,
) (*PromptOptimizationResult, error) {
	startTime := time.Now().UnixMilli()
	p.history = make([]PromptEvaluation, 0)

	// Initialize population with random configurations
	population := make([]map[string]string, populationSize)
	fitnessScores := make([]float64, populationSize)

	for i := 0; i < populationSize; i++ {
		population[i] = p.sampleConfig()
	}

	// Evaluate initial population
	for i, config := range population {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		prompt := p.fillTemplate(config)
		scores, err := p.evaluatePrompt(ctx, prompt, testCases)
		if err != nil {
			return nil, fmt.Errorf("evaluation failed: %w", err)
		}

		objectiveScore := p.getObjectiveScore(scores)
		fitnessScores[i] = objectiveScore

		// Copy config and scores
		configCopy := make(map[string]string)
		for k, v := range config {
			configCopy[k] = v
		}
		scoresCopy := make(map[string]float64)
		for k, v := range scores {
			scoresCopy[k] = v
		}

		p.history = append(p.history, PromptEvaluation{
			Prompt: prompt,
			Config: configCopy,
			Scores: scoresCopy,
		})
	}

	// Evolution loop
	for gen := 0; gen < nGenerations; gen++ {
		// Selection: Tournament selection
		newPopulation := make([]map[string]string, populationSize)
		for i := 0; i < populationSize; i++ {
			// Select 2 random individuals
			idx1 := rand.Intn(populationSize)
			idx2 := rand.Intn(populationSize)
			for idx2 == idx1 {
				idx2 = rand.Intn(populationSize)
			}

			// Choose fitter one
			winnerIdx := idx1
			if fitnessScores[idx2] > fitnessScores[idx1] {
				winnerIdx = idx2
			}

			// Copy winner
			newPopulation[i] = make(map[string]string)
			for k, v := range population[winnerIdx] {
				newPopulation[i][k] = v
			}
		}

		// Mutation
		for _, config := range newPopulation {
			for key := range config {
				if rand.Float64() < mutationRate {
					values := p.variations[key]
					config[key] = values[rand.Intn(len(values))]
				}
			}
		}

		// Evaluate new population
		population = newPopulation
		fitnessScores = make([]float64, populationSize)

		for i, config := range population {
			// Check context cancellation
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			default:
			}

			prompt := p.fillTemplate(config)
			scores, err := p.evaluatePrompt(ctx, prompt, testCases)
			if err != nil {
				return nil, fmt.Errorf("evaluation failed: %w", err)
			}

			objectiveScore := p.getObjectiveScore(scores)
			fitnessScores[i] = objectiveScore

			// Copy config and scores
			configCopy := make(map[string]string)
			for k, v := range config {
				configCopy[k] = v
			}
			scoresCopy := make(map[string]float64)
			for k, v := range scores {
				scoresCopy[k] = v
			}

			p.history = append(p.history, PromptEvaluation{
				Prompt: prompt,
				Config: configCopy,
				Scores: scoresCopy,
			})
		}
	}

	// Find best from all history
	bestIdx := 0
	bestObjective := p.getObjectiveScore(p.history[0].Scores)
	for i := 1; i < len(p.history); i++ {
		objScore := p.getObjectiveScore(p.history[i].Scores)
		if objScore > bestObjective {
			bestObjective = objScore
			bestIdx = i
		}
	}

	bestEval := p.history[bestIdx]
	endTime := time.Now().UnixMilli()

	return &PromptOptimizationResult{
		BestPrompt: bestEval.Prompt,
		BestConfig: bestEval.Config,
		BestScores: bestEval.Scores,
		History:    p.history,
		NEvaluated: len(p.history),
		Strategy:   string(StrategyGenetic),
		StartTime:  startTime,
		EndTime:    endTime,
	}, nil
}

// Optimize runs prompt optimization with the specified strategy.
//
// Args:
//
//	ctx: Context for cancellation
//	testCases: Test cases for evaluation
//	strategy: Optimization strategy ("grid", "random", "genetic")
//	options: Strategy-specific options (nSamples, populationSize, etc.)
func (p *PromptOptimizer) Optimize(
	ctx context.Context,
	testCases []map[string]interface{},
	strategy string,
	options map[string]interface{},
) (*PromptOptimizationResult, error) {
	if options == nil {
		options = make(map[string]interface{})
	}

	switch OptimizationStrategy(strategy) {
	case StrategyGrid:
		return p.OptimizeGrid(ctx, testCases)

	case StrategyRandom:
		nSamples := 20
		if val, ok := options["nSamples"].(int); ok {
			nSamples = val
		} else if val, ok := options["n_samples"].(int); ok {
			nSamples = val
		}
		return p.OptimizeRandom(ctx, testCases, nSamples)

	case StrategyGenetic:
		populationSize := 10
		if val, ok := options["populationSize"].(int); ok {
			populationSize = val
		} else if val, ok := options["population_size"].(int); ok {
			populationSize = val
		}

		nGenerations := 5
		if val, ok := options["nGenerations"].(int); ok {
			nGenerations = val
		} else if val, ok := options["n_generations"].(int); ok {
			nGenerations = val
		}

		mutationRate := 0.2
		if val, ok := options["mutationRate"].(float64); ok {
			mutationRate = val
		} else if val, ok := options["mutation_rate"].(float64); ok {
			mutationRate = val
		}

		return p.OptimizeGenetic(ctx, testCases, populationSize, nGenerations, mutationRate)

	default:
		return nil, fmt.Errorf("unknown strategy: %s", strategy)
	}
}
