// Package evaluation provides the Automated Optimization Framework.
//
// This module provides intelligent optimization of agent configurations, prompts,
// and hyperparameters using Bayesian optimization, genetic algorithms, and other
// search strategies.
//
// Interfaces:
//   - Optimizer: Base interface for optimization algorithms
//
// Implementations:
//   - RandomSearchOptimizer: Baseline random search
//   - BayesianOptimizer: Bayesian optimization (in bayesian_optimizer.go)
//
// Example:
//
//	searchSpace := evaluation.NewSearchSpace()
//	searchSpace.AddContinuous("temperature", 0.0, 1.0)
//	searchSpace.AddContinuous("top_p", 0.0, 1.0)
//
//	optimizer := evaluation.NewRandomSearchOptimizer(
//	    objectiveFunc,
//	    searchSpace,
//	    true, // maximize
//	)
//
//	result, err := optimizer.Optimize(ctx, 50)
//	fmt.Printf("Best config: %v\n", result.BestConfig)
//	fmt.Printf("Best score: %.3f\n", result.BestScore)
package evaluation

import (
	"context"
	"fmt"
	"time"
)

// Optimizer is the base interface for optimization algorithms.
//
// Implementations should provide intelligent search over configuration spaces
// using various strategies (random search, Bayesian optimization, genetic algorithms, etc.).
type Optimizer interface {
	// Optimize runs the optimization process.
	//
	// Args:
	//   ctx: Context for cancellation
	//   nIterations: Number of iterations to run
	//
	// Returns:
	//   OptimizationResult with best configuration and history
	Optimize(ctx context.Context, nIterations int) (*OptimizationResult, error)
}

// RandomSearchOptimizer implements baseline random search optimization.
//
// Randomly samples configurations from the search space and evaluates them.
// Useful as a baseline for comparison with more sophisticated algorithms.
//
// Example:
//
//	optimizer := evaluation.NewRandomSearchOptimizer(
//	    objectiveFunc,
//	    searchSpace,
//	    true, // maximize
//	)
//	result, err := optimizer.Optimize(ctx, 20)
type RandomSearchOptimizer struct {
	objective   ObjectiveFunc
	searchSpace *SearchSpace
	maximize    bool
	history     []OptimizationStep
}

// NewRandomSearchOptimizer creates a new random search optimizer.
//
// Args:
//
//	objective: Function to evaluate configurations
//	searchSpace: SearchSpace defining parameter space
//	maximize: Whether to maximize (true) or minimize (false) objective
//
// Returns:
//
//	RandomSearchOptimizer instance
func NewRandomSearchOptimizer(
	objective ObjectiveFunc,
	searchSpace *SearchSpace,
	maximize bool,
) *RandomSearchOptimizer {
	return &RandomSearchOptimizer{
		objective:   objective,
		searchSpace: searchSpace,
		maximize:    maximize,
		history:     make([]OptimizationStep, 0),
	}
}

// Optimize runs random search optimization.
//
// Randomly samples nIterations configurations from the search space,
// evaluates each, and tracks the best configuration found.
//
// Args:
//
//	ctx: Context for cancellation
//	nIterations: Number of configurations to sample and evaluate
//
// Returns:
//
//	OptimizationResult with best config, score, and history
//	error if optimization fails
func (r *RandomSearchOptimizer) Optimize(ctx context.Context, nIterations int) (*OptimizationResult, error) {
	startTime := time.Now()
	r.history = make([]OptimizationStep, 0, nIterations)

	var bestConfig map[string]interface{}
	var bestScore float64
	if r.maximize {
		bestScore = -1e9 // Start with very low score for maximization
	} else {
		bestScore = 1e9 // Start with very high score for minimization
	}

	for i := 0; i < nIterations; i++ {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		// Sample random configuration
		config := r.searchSpace.Sample()

		// Evaluate
		score, err := r.objective(ctx, config)
		if err != nil {
			return nil, fmt.Errorf("failed to evaluate config: %w", err)
		}

		// Record step
		r.history = append(r.history, OptimizationStep{
			Config: copyConfig(config),
			Score:  score,
		})

		// Update best
		isBetter := (r.maximize && score > bestScore) || (!r.maximize && score < bestScore)
		if isBetter || bestConfig == nil {
			bestScore = score
			bestConfig = copyConfig(config)
		}
	}

	endTime := time.Now()

	if bestConfig == nil {
		// Fallback: use a random sample if nothing was evaluated
		bestConfig = r.searchSpace.Sample()
	}

	return &OptimizationResult{
		BestConfig:  bestConfig,
		BestScore:   bestScore,
		History:     r.history,
		NIterations: nIterations,
		StartTime:   startTime,
		EndTime:     endTime,
		Metadata: map[string]interface{}{
			"algorithm": "random_search",
			"maximize":  r.maximize,
		},
	}, nil
}

// GetHistory returns the optimization history.
func (r *RandomSearchOptimizer) GetHistory() []OptimizationStep {
	return r.history
}
