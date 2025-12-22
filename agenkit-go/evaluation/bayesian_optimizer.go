// Package evaluation provides tools for evaluating and optimizing agent performance.
// Bayesian Optimization uses probabilistic models to efficiently find optimal
// hyperparameter configurations.
package evaluation

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"time"
)

// AcquisitionFunction specifies the acquisition function type for Bayesian optimization.
type AcquisitionFunction string

const (
	// AcquisitionEI represents Expected Improvement
	AcquisitionEI AcquisitionFunction = "ei"
	// AcquisitionUCB represents Upper Confidence Bound
	AcquisitionUCB AcquisitionFunction = "ucb"
	// AcquisitionPI represents Probability of Improvement
	AcquisitionPI AcquisitionFunction = "pi"
)

// ParameterType specifies the type of a hyperparameter.
type ParameterType string

const (
	// ParamTypeContinuous represents a continuous parameter (float)
	ParamTypeContinuous ParameterType = "continuous"
	// ParamTypeInteger represents an integer parameter
	ParamTypeInteger ParameterType = "integer"
	// ParamTypeDiscrete represents a discrete set of values
	ParamTypeDiscrete ParameterType = "discrete"
	// ParamTypeCategorical represents categorical values
	ParamTypeCategorical ParameterType = "categorical"
)

// ParameterSpec defines a parameter in the search space.
type ParameterSpec struct {
	Type   ParameterType
	Low    float64       // For continuous/integer
	High   float64       // For continuous/integer
	Values []interface{} // For discrete/categorical
}

// SearchSpace defines the hyperparameter search space.
type SearchSpace struct {
	Parameters map[string]ParameterSpec
}

// NewSearchSpace creates a new search space.
func NewSearchSpace() *SearchSpace {
	return &SearchSpace{
		Parameters: make(map[string]ParameterSpec),
	}
}

// AddContinuous adds a continuous parameter with range [low, high].
func (s *SearchSpace) AddContinuous(name string, low, high float64) {
	s.Parameters[name] = ParameterSpec{
		Type: ParamTypeContinuous,
		Low:  low,
		High: high,
	}
}

// AddInteger adds an integer parameter with range [low, high].
func (s *SearchSpace) AddInteger(name string, low, high int) {
	s.Parameters[name] = ParameterSpec{
		Type: ParamTypeInteger,
		Low:  float64(low),
		High: float64(high),
	}
}

// AddDiscrete adds a discrete parameter with specific values.
func (s *SearchSpace) AddDiscrete(name string, values []interface{}) {
	s.Parameters[name] = ParameterSpec{
		Type:   ParamTypeDiscrete,
		Values: values,
	}
}

// AddCategorical adds a categorical parameter with specific values.
func (s *SearchSpace) AddCategorical(name string, values []string) {
	interfaceValues := make([]interface{}, len(values))
	for i, v := range values {
		interfaceValues[i] = v
	}
	s.Parameters[name] = ParameterSpec{
		Type:   ParamTypeCategorical,
		Values: interfaceValues,
	}
}

// Sample generates a random configuration from the search space.
func (s *SearchSpace) Sample() map[string]interface{} {
	config := make(map[string]interface{})
	for name, spec := range s.Parameters {
		switch spec.Type {
		case ParamTypeContinuous:
			config[name] = spec.Low + rand.Float64()*(spec.High-spec.Low)
		case ParamTypeInteger:
			config[name] = int(spec.Low) + rand.Intn(int(spec.High-spec.Low+1))
		case ParamTypeDiscrete, ParamTypeCategorical:
			config[name] = spec.Values[rand.Intn(len(spec.Values))]
		}
	}
	return config
}

// OptimizationResult contains the results of an optimization run.
type OptimizationResult struct {
	BestConfig  map[string]interface{}
	BestScore   float64
	History     []OptimizationStep
	NIterations int
	StartTime   time.Time
	EndTime     time.Time
	Metadata    map[string]interface{}
}

// OptimizationStep represents a single evaluation in the optimization.
type OptimizationStep struct {
	Config map[string]interface{}
	Score  float64
}

// Duration returns the total optimization duration.
func (r *OptimizationResult) Duration() time.Duration {
	return r.EndTime.Sub(r.StartTime)
}

// GetImprovement returns the improvement from initial to best score.
func (r *OptimizationResult) GetImprovement() float64 {
	if len(r.History) == 0 {
		return 0.0
	}
	return r.BestScore - r.History[0].Score
}

// ObjectiveFunc evaluates a configuration and returns a score.
type ObjectiveFunc func(ctx context.Context, config map[string]interface{}) (float64, error)

// BayesianOptimizer implements Bayesian optimization for hyperparameter tuning.
//
// This implementation uses a simplified surrogate model based on local statistics
// rather than full Gaussian Process regression. It balances exploration and
// exploitation through acquisition functions.
//
// Algorithm:
//  1. Sample n_initial random configurations
//  2. Evaluate and build local statistics
//  3. Use acquisition function to select next config
//  4. Evaluate new config
//  5. Update statistics and repeat
type BayesianOptimizer struct {
	searchSpace *SearchSpace
	objective   ObjectiveFunc
	maximize    bool
	acquisition AcquisitionFunction
	nInitial    int
	xi          float64 // Exploration parameter for EI/PI
	kappa       float64 // Exploration parameter for UCB
	history     []OptimizationStep
	bestConfig  map[string]interface{}
	bestScore   float64
}

// BayesianOptimizerConfig contains configuration for BayesianOptimizer.
type BayesianOptimizerConfig struct {
	SearchSpace *SearchSpace
	Objective   ObjectiveFunc
	Maximize    bool
	Acquisition AcquisitionFunction
	NInitial    int
	Xi          float64 // Exploration parameter for EI and PI (default: 0.01)
	Kappa       float64 // Exploration parameter for UCB (default: 2.576)
}

// NewBayesianOptimizer creates a new Bayesian optimizer.
func NewBayesianOptimizer(config BayesianOptimizerConfig) (*BayesianOptimizer, error) {
	if config.SearchSpace == nil {
		return nil, fmt.Errorf("search space is required")
	}
	if config.Objective == nil {
		return nil, fmt.Errorf("objective function is required")
	}

	// Set defaults
	if config.NInitial == 0 {
		config.NInitial = 5
	}
	if config.Xi == 0.0 {
		config.Xi = 0.01
	}
	if config.Kappa == 0.0 {
		config.Kappa = 2.576 // 99% confidence interval
	}
	if config.Acquisition == "" {
		config.Acquisition = AcquisitionEI
	}

	return &BayesianOptimizer{
		searchSpace: config.SearchSpace,
		objective:   config.Objective,
		maximize:    config.Maximize,
		acquisition: config.Acquisition,
		nInitial:    config.NInitial,
		xi:          config.Xi,
		kappa:       config.Kappa,
		history:     make([]OptimizationStep, 0),
		bestScore:   math.Inf(-1),
	}, nil
}

// Optimize runs the Bayesian optimization process.
func (b *BayesianOptimizer) Optimize(ctx context.Context, nIterations int) (*OptimizationResult, error) {
	startTime := time.Now()

	// Phase 1: Random initialization
	for i := 0; i < min(b.nInitial, nIterations); i++ {
		config := b.searchSpace.Sample()
		score, err := b.objective(ctx, config)
		if err != nil {
			return nil, fmt.Errorf("evaluation failed at iteration %d: %w", i, err)
		}

		b.addObservation(config, score)
	}

	// Phase 2: Bayesian optimization with acquisition function
	for i := b.nInitial; i < nIterations; i++ {
		// Propose next configuration using acquisition function
		config := b.proposeNext()

		// Evaluate
		score, err := b.objective(ctx, config)
		if err != nil {
			return nil, fmt.Errorf("evaluation failed at iteration %d: %w", i, err)
		}

		b.addObservation(config, score)
	}

	endTime := time.Now()

	return &OptimizationResult{
		BestConfig:  b.bestConfig,
		BestScore:   b.bestScore,
		History:     b.history,
		NIterations: nIterations,
		StartTime:   startTime,
		EndTime:     endTime,
		Metadata: map[string]interface{}{
			"algorithm":   "bayesian_optimization",
			"acquisition": string(b.acquisition),
			"n_initial":   b.nInitial,
			"maximize":    b.maximize,
		},
	}, nil
}

// addObservation adds a new observation to the history.
func (b *BayesianOptimizer) addObservation(config map[string]interface{}, score float64) {
	step := OptimizationStep{
		Config: config,
		Score:  score,
	}
	b.history = append(b.history, step)

	// Update best
	if len(b.history) == 1 || (b.maximize && score > b.bestScore) || (!b.maximize && score < b.bestScore) {
		b.bestScore = score
		b.bestConfig = copyConfig(config)
	}
}

// proposeNext proposes the next configuration to evaluate using the acquisition function.
func (b *BayesianOptimizer) proposeNext() map[string]interface{} {
	nCandidates := 1000
	bestCandidate := b.searchSpace.Sample()
	bestAcqValue := math.Inf(-1)

	// Generate and evaluate random candidates
	for i := 0; i < nCandidates; i++ {
		candidate := b.searchSpace.Sample()
		acqValue := b.evaluateAcquisition(candidate)

		if acqValue > bestAcqValue {
			bestAcqValue = acqValue
			bestCandidate = candidate
		}
	}

	return bestCandidate
}

// evaluateAcquisition evaluates the acquisition function for a candidate.
func (b *BayesianOptimizer) evaluateAcquisition(config map[string]interface{}) float64 {
	// Use local statistics from history
	mu, sigma := b.estimatePerformance(config)

	switch b.acquisition {
	case AcquisitionEI:
		return b.expectedImprovement(mu, sigma)
	case AcquisitionUCB:
		return b.upperConfidenceBound(mu, sigma)
	case AcquisitionPI:
		return b.probabilityOfImprovement(mu, sigma)
	default:
		return mu
	}
}

// estimatePerformance estimates the mean and std of a configuration.
// This is a simplified version using local neighborhood statistics.
func (b *BayesianOptimizer) estimatePerformance(config map[string]interface{}) (float64, float64) {
	if len(b.history) == 0 {
		return 0.0, 1.0
	}

	// Find similar configurations in history
	var scores []float64
	for _, step := range b.history {
		similarity := b.configSimilarity(config, step.Config)
		if similarity > 0.5 { // Threshold for "similar"
			scores = append(scores, step.Score)
		}
	}

	// If no similar configs, use global statistics
	if len(scores) == 0 {
		for _, step := range b.history {
			scores = append(scores, step.Score)
		}
	}

	mu := mean(scores)
	sigma := stddev(scores, mu)

	// Ensure non-zero sigma
	if sigma < 1e-6 {
		sigma = 0.1
	}

	return mu, sigma
}

// configSimilarity computes similarity between two configurations (0-1).
func (b *BayesianOptimizer) configSimilarity(config1, config2 map[string]interface{}) float64 {
	if len(config1) == 0 || len(config2) == 0 {
		return 0.0
	}

	similaritySum := 0.0
	totalCount := 0

	for name, spec := range b.searchSpace.Parameters {
		v1, ok1 := config1[name]
		v2, ok2 := config2[name]
		if !ok1 || !ok2 {
			continue
		}

		totalCount++

		switch spec.Type {
		case ParamTypeContinuous, ParamTypeInteger:
			// Normalized distance
			val1 := toFloat64(v1)
			val2 := toFloat64(v2)
			range_ := spec.High - spec.Low
			if range_ > 0 {
				dist := math.Abs(val1-val2) / range_
				similaritySum += 1.0 - dist // Similarity = 1 - normalized distance
			} else {
				// Zero range - either identical or not
				if val1 == val2 {
					similaritySum += 1.0
				}
			}

		case ParamTypeDiscrete, ParamTypeCategorical:
			if v1 == v2 {
				similaritySum += 1.0
			}
		}
	}

	if totalCount == 0 {
		return 0.0
	}

	return similaritySum / float64(totalCount)
}

// expectedImprovement computes the Expected Improvement acquisition function.
func (b *BayesianOptimizer) expectedImprovement(mu, sigma float64) float64 {
	if len(b.history) == 0 {
		return 0.0
	}

	improvement := mu - b.bestScore - b.xi
	if sigma == 0.0 {
		return 0.0
	}

	z := improvement / sigma
	return improvement*normCDF(z) + sigma*normPDF(z)
}

// upperConfidenceBound computes the Upper Confidence Bound acquisition function.
func (b *BayesianOptimizer) upperConfidenceBound(mu, sigma float64) float64 {
	return mu + b.kappa*sigma
}

// probabilityOfImprovement computes the Probability of Improvement acquisition function.
func (b *BayesianOptimizer) probabilityOfImprovement(mu, sigma float64) float64 {
	if len(b.history) == 0 {
		return 0.0
	}

	if sigma == 0.0 {
		return 0.0
	}

	z := (mu - b.bestScore - b.xi) / sigma
	return normCDF(z)
}

// Helper functions

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func copyConfig(config map[string]interface{}) map[string]interface{} {
	copy := make(map[string]interface{})
	for k, v := range config {
		copy[k] = v
	}
	return copy
}

func toFloat64(v interface{}) float64 {
	switch val := v.(type) {
	case float64:
		return val
	case int:
		return float64(val)
	case float32:
		return float64(val)
	default:
		return 0.0
	}
}

func mean(values []float64) float64 {
	if len(values) == 0 {
		return 0.0
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func stddev(values []float64, mean float64) float64 {
	if len(values) <= 1 {
		return 1.0
	}
	variance := 0.0
	for _, v := range values {
		diff := v - mean
		variance += diff * diff
	}
	return math.Sqrt(variance / float64(len(values)-1))
}

func normCDF(x float64) float64 {
	// Approximation of standard normal CDF
	return 0.5 * (1.0 + math.Erf(x/math.Sqrt(2.0)))
}

func normPDF(x float64) float64 {
	// Standard normal PDF
	return math.Exp(-0.5*x*x) / math.Sqrt(2.0*math.Pi)
}
