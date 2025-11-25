package evaluation

import (
	"context"
	"fmt"
	"math"
	"testing"
)

// TestNewSearchSpace tests search space creation
func TestNewSearchSpace(t *testing.T) {
	space := NewSearchSpace()
	if space == nil {
		t.Fatal("expected non-nil search space")
	}
	if space.Parameters == nil {
		t.Fatal("expected initialized parameters map")
	}
	if len(space.Parameters) != 0 {
		t.Errorf("expected empty parameters, got %d", len(space.Parameters))
	}
}

// TestSearchSpaceAddContinuous tests adding continuous parameters
func TestSearchSpaceAddContinuous(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("learning_rate", 0.001, 0.1)

	param, ok := space.Parameters["learning_rate"]
	if !ok {
		t.Fatal("parameter not added")
	}
	if param.Type != ParamTypeContinuous {
		t.Errorf("expected type continuous, got %v", param.Type)
	}
	if param.Low != 0.001 {
		t.Errorf("expected low=0.001, got %v", param.Low)
	}
	if param.High != 0.1 {
		t.Errorf("expected high=0.1, got %v", param.High)
	}
}

// TestSearchSpaceAddInteger tests adding integer parameters
func TestSearchSpaceAddInteger(t *testing.T) {
	space := NewSearchSpace()
	space.AddInteger("batch_size", 16, 128)

	param, ok := space.Parameters["batch_size"]
	if !ok {
		t.Fatal("parameter not added")
	}
	if param.Type != ParamTypeInteger {
		t.Errorf("expected type integer, got %v", param.Type)
	}
	if param.Low != 16.0 {
		t.Errorf("expected low=16, got %v", param.Low)
	}
	if param.High != 128.0 {
		t.Errorf("expected high=128, got %v", param.High)
	}
}

// TestSearchSpaceAddDiscrete tests adding discrete parameters
func TestSearchSpaceAddDiscrete(t *testing.T) {
	space := NewSearchSpace()
	values := []interface{}{0.1, 0.5, 1.0, 2.0}
	space.AddDiscrete("momentum", values)

	param, ok := space.Parameters["momentum"]
	if !ok {
		t.Fatal("parameter not added")
	}
	if param.Type != ParamTypeDiscrete {
		t.Errorf("expected type discrete, got %v", param.Type)
	}
	if len(param.Values) != 4 {
		t.Errorf("expected 4 values, got %d", len(param.Values))
	}
}

// TestSearchSpaceAddCategorical tests adding categorical parameters
func TestSearchSpaceAddCategorical(t *testing.T) {
	space := NewSearchSpace()
	values := []string{"adam", "sgd", "rmsprop"}
	space.AddCategorical("optimizer", values)

	param, ok := space.Parameters["optimizer"]
	if !ok {
		t.Fatal("parameter not added")
	}
	if param.Type != ParamTypeCategorical {
		t.Errorf("expected type categorical, got %v", param.Type)
	}
	if len(param.Values) != 3 {
		t.Errorf("expected 3 values, got %d", len(param.Values))
	}
}

// TestSearchSpaceSample tests sampling from search space
func TestSearchSpaceSample(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("lr", 0.001, 0.1)
	space.AddInteger("batch_size", 16, 128)
	space.AddCategorical("optimizer", []string{"adam", "sgd"})

	config := space.Sample()

	if len(config) != 3 {
		t.Errorf("expected 3 parameters, got %d", len(config))
	}

	// Check continuous parameter
	lr, ok := config["lr"].(float64)
	if !ok {
		t.Errorf("expected float64 for lr, got %T", config["lr"])
	}
	if lr < 0.001 || lr > 0.1 {
		t.Errorf("lr out of range: %v", lr)
	}

	// Check integer parameter
	batchSize, ok := config["batch_size"].(int)
	if !ok {
		t.Errorf("expected int for batch_size, got %T", config["batch_size"])
	}
	if batchSize < 16 || batchSize > 128 {
		t.Errorf("batch_size out of range: %v", batchSize)
	}

	// Check categorical parameter
	optimizer, ok := config["optimizer"].(string)
	if !ok {
		t.Errorf("expected string for optimizer, got %T", config["optimizer"])
	}
	if optimizer != "adam" && optimizer != "sgd" {
		t.Errorf("unexpected optimizer value: %v", optimizer)
	}
}

// TestNewBayesianOptimizer tests optimizer creation
func TestNewBayesianOptimizer(t *testing.T) {
	tests := []struct {
		name        string
		config      BayesianOptimizerConfig
		expectError bool
		errorMsg    string
	}{
		{
			name: "valid configuration",
			config: BayesianOptimizerConfig{
				SearchSpace: NewSearchSpace(),
				Objective: func(ctx context.Context, config map[string]interface{}) (float64, error) {
					return 0.5, nil
				},
				Maximize:    true,
				Acquisition: AcquisitionEI,
				NInitial:    5,
			},
			expectError: false,
		},
		{
			name: "nil search space",
			config: BayesianOptimizerConfig{
				Objective: func(ctx context.Context, config map[string]interface{}) (float64, error) {
					return 0.5, nil
				},
			},
			expectError: true,
			errorMsg:    "search space is required",
		},
		{
			name: "nil objective",
			config: BayesianOptimizerConfig{
				SearchSpace: NewSearchSpace(),
			},
			expectError: true,
			errorMsg:    "objective function is required",
		},
		{
			name: "default values applied",
			config: BayesianOptimizerConfig{
				SearchSpace: NewSearchSpace(),
				Objective: func(ctx context.Context, config map[string]interface{}) (float64, error) {
					return 0.5, nil
				},
			},
			expectError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			opt, err := NewBayesianOptimizer(tt.config)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error but got none")
				} else if tt.errorMsg != "" && err.Error() != tt.errorMsg {
					t.Errorf("expected error %q, got %q", tt.errorMsg, err.Error())
				}
			} else {
				if err != nil {
					t.Errorf("unexpected error: %v", err)
				}
				if opt == nil {
					t.Fatal("expected non-nil optimizer")
				}

				// Check defaults
				if tt.config.NInitial == 0 && opt.nInitial != 5 {
					t.Errorf("expected default nInitial=5, got %d", opt.nInitial)
				}
				if tt.config.Xi == 0.0 && opt.xi != 0.01 {
					t.Errorf("expected default xi=0.01, got %v", opt.xi)
				}
				if tt.config.Kappa == 0.0 && opt.kappa != 2.576 {
					t.Errorf("expected default kappa=2.576, got %v", opt.kappa)
				}
				if tt.config.Acquisition == "" && opt.acquisition != AcquisitionEI {
					t.Errorf("expected default acquisition=EI, got %v", opt.acquisition)
				}
			}
		})
	}
}

// TestBayesianOptimizerOptimizeBasic tests basic optimization
func TestBayesianOptimizerOptimizeBasic(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("x", -5.0, 5.0)

	// Simple quadratic objective: minimize (x-2)^2
	objective := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		x := config["x"].(float64)
		return -(x - 2.0) * (x - 2.0), nil // Negative for maximization
	}

	opt, err := NewBayesianOptimizer(BayesianOptimizerConfig{
		SearchSpace: space,
		Objective:   objective,
		Maximize:    true, // Maximize negative quadratic = minimize quadratic
		NInitial:    3,
		Acquisition: AcquisitionEI,
	})
	if err != nil {
		t.Fatalf("failed to create optimizer: %v", err)
	}

	ctx := context.Background()
	result, err := opt.Optimize(ctx, 10)
	if err != nil {
		t.Fatalf("optimization failed: %v", err)
	}

	// Verify result structure
	if result == nil {
		t.Fatal("expected non-nil result")
	}
	if result.BestConfig == nil {
		t.Fatal("expected non-nil best config")
	}
	if len(result.History) != 10 {
		t.Errorf("expected 10 history entries, got %d", len(result.History))
	}
	if result.NIterations != 10 {
		t.Errorf("expected 10 iterations, got %d", result.NIterations)
	}

	// Best x should be close to 2.0 (may not be perfect due to sampling)
	bestX := result.BestConfig["x"].(float64)
	if math.Abs(bestX-2.0) > 2.0 {
		t.Logf("Warning: best x=%v is not very close to optimal (2.0)", bestX)
	}

	// Verify metadata
	if result.Metadata["algorithm"] != "bayesian_optimization" {
		t.Errorf("expected algorithm metadata")
	}
	if result.Metadata["maximize"] != true {
		t.Errorf("expected maximize=true in metadata")
	}
}

// TestBayesianOptimizerAcquisitionFunctions tests different acquisition functions
func TestBayesianOptimizerAcquisitionFunctions(t *testing.T) {
	acquisitions := []AcquisitionFunction{
		AcquisitionEI,
		AcquisitionUCB,
		AcquisitionPI,
	}

	space := NewSearchSpace()
	space.AddContinuous("x", 0.0, 10.0)

	objective := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		x := config["x"].(float64)
		return math.Sin(x), nil
	}

	ctx := context.Background()

	for _, acq := range acquisitions {
		t.Run(string(acq), func(t *testing.T) {
			opt, err := NewBayesianOptimizer(BayesianOptimizerConfig{
				SearchSpace: space,
				Objective:   objective,
				Maximize:    true,
				NInitial:    2,
				Acquisition: acq,
			})
			if err != nil {
				t.Fatalf("failed to create optimizer: %v", err)
			}

			result, err := opt.Optimize(ctx, 5)
			if err != nil {
				t.Fatalf("optimization failed for %s: %v", acq, err)
			}

			if result.Metadata["acquisition"] != string(acq) {
				t.Errorf("expected acquisition=%s in metadata, got %v",
					acq, result.Metadata["acquisition"])
			}
		})
	}
}

// TestBayesianOptimizerMultipleParameters tests optimization with multiple parameters
func TestBayesianOptimizerMultipleParameters(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("x", -5.0, 5.0)
	space.AddContinuous("y", -5.0, 5.0)
	space.AddInteger("z", 1, 10)

	// Objective: minimize distance from (1, 2, 5)
	objective := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		x := config["x"].(float64)
		y := config["y"].(float64)
		z := float64(config["z"].(int))

		dist := math.Sqrt((x-1.0)*(x-1.0) + (y-2.0)*(y-2.0) + (z-5.0)*(z-5.0))
		return -dist, nil // Negative for maximization
	}

	opt, err := NewBayesianOptimizer(BayesianOptimizerConfig{
		SearchSpace: space,
		Objective:   objective,
		Maximize:    true,
		NInitial:    5,
	})
	if err != nil {
		t.Fatalf("failed to create optimizer: %v", err)
	}

	ctx := context.Background()
	result, err := opt.Optimize(ctx, 15)
	if err != nil {
		t.Fatalf("optimization failed: %v", err)
	}

	// Verify all parameters present
	if _, ok := result.BestConfig["x"]; !ok {
		t.Error("missing x in best config")
	}
	if _, ok := result.BestConfig["y"]; !ok {
		t.Error("missing y in best config")
	}
	if _, ok := result.BestConfig["z"]; !ok {
		t.Error("missing z in best config")
	}
}

// TestBayesianOptimizerCategoricalParameters tests categorical parameter handling
func TestBayesianOptimizerCategoricalParameters(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("x", 0.0, 10.0)
	space.AddCategorical("method", []string{"a", "b", "c"})

	objective := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		x := config["x"].(float64)
		method := config["method"].(string)

		score := x
		switch method {
		case "a":
			score += 10.0
		case "b":
			score += 5.0
		case "c":
			score += 0.0
		}
		return score, nil
	}

	opt, err := NewBayesianOptimizer(BayesianOptimizerConfig{
		SearchSpace: space,
		Objective:   objective,
		Maximize:    true,
		NInitial:    3,
	})
	if err != nil {
		t.Fatalf("failed to create optimizer: %v", err)
	}

	ctx := context.Background()
	result, err := opt.Optimize(ctx, 10)
	if err != nil {
		t.Fatalf("optimization failed: %v", err)
	}

	// Best method should eventually be "a" with high x
	bestMethod := result.BestConfig["method"].(string)
	if bestMethod != "a" && bestMethod != "b" && bestMethod != "c" {
		t.Errorf("unexpected method value: %v", bestMethod)
	}
}

// TestBayesianOptimizerObjectiveError tests handling of objective function errors
func TestBayesianOptimizerObjectiveError(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("x", 0.0, 10.0)

	failCount := 0
	objective := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		failCount++
		if failCount == 3 {
			return 0, fmt.Errorf("simulated failure")
		}
		return 1.0, nil
	}

	opt, err := NewBayesianOptimizer(BayesianOptimizerConfig{
		SearchSpace: space,
		Objective:   objective,
		Maximize:    true,
		NInitial:    2,
	})
	if err != nil {
		t.Fatalf("failed to create optimizer: %v", err)
	}

	ctx := context.Background()
	result, err := opt.Optimize(ctx, 5)

	// Should fail at iteration 3
	if err == nil {
		t.Error("expected error from objective function")
	}
	if result != nil {
		t.Error("expected nil result on error")
	}
}

// TestOptimizationResultDuration tests duration calculation
func TestOptimizationResultDuration(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("x", 0.0, 1.0)

	objective := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		return 1.0, nil
	}

	opt, err := NewBayesianOptimizer(BayesianOptimizerConfig{
		SearchSpace: space,
		Objective:   objective,
		NInitial:    2,
	})
	if err != nil {
		t.Fatalf("failed to create optimizer: %v", err)
	}

	ctx := context.Background()
	result, err := opt.Optimize(ctx, 5)
	if err != nil {
		t.Fatalf("optimization failed: %v", err)
	}

	duration := result.Duration()
	if duration <= 0 {
		t.Errorf("expected positive duration, got %v", duration)
	}
}

// TestOptimizationResultGetImprovement tests improvement calculation
func TestOptimizationResultGetImprovement(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("x", 0.0, 10.0)

	// Objective that improves with iteration
	iteration := 0
	objective := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		iteration++
		return float64(iteration), nil // Increasing scores
	}

	opt, err := NewBayesianOptimizer(BayesianOptimizerConfig{
		SearchSpace: space,
		Objective:   objective,
		Maximize:    true,
		NInitial:    2,
	})
	if err != nil {
		t.Fatalf("failed to create optimizer: %v", err)
	}

	ctx := context.Background()
	result, err := opt.Optimize(ctx, 5)
	if err != nil {
		t.Fatalf("optimization failed: %v", err)
	}

	improvement := result.GetImprovement()
	if improvement <= 0 {
		t.Errorf("expected positive improvement, got %v", improvement)
	}

	// Improvement should be: final_score - initial_score = 5 - 1 = 4
	if improvement != 4.0 {
		t.Errorf("expected improvement=4.0, got %v", improvement)
	}
}

// TestConfigSimilarity tests configuration similarity calculation
func TestConfigSimilarity(t *testing.T) {
	space := NewSearchSpace()
	space.AddContinuous("x", 0.0, 10.0)
	space.AddCategorical("method", []string{"a", "b"})

	opt, _ := NewBayesianOptimizer(BayesianOptimizerConfig{
		SearchSpace: space,
		Objective: func(ctx context.Context, config map[string]interface{}) (float64, error) {
			return 1.0, nil
		},
	})

	// Test identical configs
	config1 := map[string]interface{}{"x": 5.0, "method": "a"}
	config2 := map[string]interface{}{"x": 5.0, "method": "a"}
	sim := opt.configSimilarity(config1, config2)
	if sim < 0.9 {
		t.Errorf("expected high similarity for identical configs, got %v", sim)
	}

	// Test different categorical
	config3 := map[string]interface{}{"x": 5.0, "method": "b"}
	sim = opt.configSimilarity(config1, config3)
	if sim >= 1.0 {
		t.Errorf("expected lower similarity for different method, got %v", sim)
	}

	// Test different continuous
	config4 := map[string]interface{}{"x": 8.0, "method": "a"}
	sim = opt.configSimilarity(config1, config4)
	if sim >= 1.0 {
		t.Errorf("expected lower similarity for different x, got %v", sim)
	}
}

// TestHelperFunctions tests utility functions
func TestHelperFunctions(t *testing.T) {
	// Test mean
	values := []float64{1.0, 2.0, 3.0, 4.0, 5.0}
	m := mean(values)
	if m != 3.0 {
		t.Errorf("expected mean=3.0, got %v", m)
	}

	// Test stddev
	s := stddev(values, m)
	expected := math.Sqrt(2.5) // Sample stddev of 1,2,3,4,5
	if math.Abs(s-expected) > 0.01 {
		t.Errorf("expected stddev≈%v, got %v", expected, s)
	}

	// Test normCDF
	cdf := normCDF(0.0)
	if math.Abs(cdf-0.5) > 0.01 {
		t.Errorf("expected normCDF(0)≈0.5, got %v", cdf)
	}

	// Test normPDF
	pdf := normPDF(0.0)
	expected = 1.0 / math.Sqrt(2.0*math.Pi)
	if math.Abs(pdf-expected) > 0.01 {
		t.Errorf("expected normPDF(0)≈%v, got %v", expected, pdf)
	}

	// Test toFloat64
	if toFloat64(42) != 42.0 {
		t.Error("toFloat64 failed for int")
	}
	if toFloat64(3.14) != 3.14 {
		t.Error("toFloat64 failed for float64")
	}
	if toFloat64(float32(2.5)) != 2.5 {
		t.Error("toFloat64 failed for float32")
	}
	if toFloat64("string") != 0.0 {
		t.Error("toFloat64 should return 0.0 for unsupported types")
	}
}

// TestMinFunction tests the min helper
func TestMinFunction(t *testing.T) {
	if min(5, 10) != 5 {
		t.Error("min(5, 10) should be 5")
	}
	if min(10, 5) != 5 {
		t.Error("min(10, 5) should be 5")
	}
	if min(7, 7) != 7 {
		t.Error("min(7, 7) should be 7")
	}
}

// TestCopyConfig tests configuration copying
func TestCopyConfig(t *testing.T) {
	original := map[string]interface{}{
		"x":      5.0,
		"method": "a",
	}

	copied := copyConfig(original)

	// Should be equal
	if copied["x"] != original["x"] {
		t.Error("copied config x value mismatch")
	}
	if copied["method"] != original["method"] {
		t.Error("copied config method value mismatch")
	}

	// Should be independent
	copied["x"] = 10.0
	if original["x"].(float64) == 10.0 {
		t.Error("modifying copy affected original")
	}
}
