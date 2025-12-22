package evaluation

import (
	"context"
	"fmt"
	"testing"
	"time"
)

// Mock objective function for testing
func mockObjectiveFunc(ctx context.Context, config map[string]interface{}) (float64, error) {
	// Simple quadratic function: minimize (x-5)^2 + (y-3)^2
	x := toFloat64(config["x"])
	y := toFloat64(config["y"])

	dx := x - 5.0
	dy := y - 3.0
	score := dx*dx + dy*dy
	return score, nil
}

func TestNewRandomSearchOptimizer(t *testing.T) {
	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)
	searchSpace.AddContinuous("y", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		mockObjectiveFunc,
		searchSpace,
		false, // Minimize
	)

	if optimizer == nil {
		t.Fatal("Expected optimizer to be created")
	}

	if optimizer.searchSpace != searchSpace {
		t.Error("Expected search space to be set")
	}

	if optimizer.maximize {
		t.Error("Expected maximize to be false")
	}
}

func TestRandomSearchOptimizeMinimization(t *testing.T) {
	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)
	searchSpace.AddContinuous("y", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		mockObjectiveFunc,
		searchSpace,
		false, // Minimize
	)

	ctx := context.Background()
	nIterations := 50

	result, err := optimizer.Optimize(ctx, nIterations)
	if err != nil {
		t.Fatalf("Optimize failed: %v", err)
	}

	if result == nil {
		t.Fatal("Expected non-nil result")
	}

	// Check basic result properties
	if result.BestConfig == nil {
		t.Error("Expected best config to be set")
	}

	if len(result.History) != nIterations {
		t.Errorf("Expected %d history entries, got %d", nIterations, len(result.History))
	}

	// Since we're minimizing (x-5)^2 + (y-3)^2, optimal is x=5, y=3, score=0
	// With random search, we should get reasonably close
	if result.BestScore > 10.0 {
		t.Errorf("Expected best score < 10.0, got %.2f", result.BestScore)
	}

	// Check metadata
	if result.Metadata["algorithm"] != "random_search" {
		t.Errorf("Expected algorithm 'random_search', got %v", result.Metadata["algorithm"])
	}

	if result.Metadata["maximize"] != false {
		t.Error("Expected maximize to be false in metadata")
	}
}

func TestRandomSearchOptimizeMaximization(t *testing.T) {
	// Objective that should be maximized
	maximizeObj := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		x := toFloat64(config["x"])
		y := toFloat64(config["y"])

		// Maximize: higher when x and y are closer to 10
		dx := x - 10.0
		dy := y - 10.0
		score := -(dx*dx + dy*dy)
		return score, nil
	}

	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)
	searchSpace.AddContinuous("y", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		maximizeObj,
		searchSpace,
		true, // Maximize
	)

	ctx := context.Background()
	nIterations := 50

	result, err := optimizer.Optimize(ctx, nIterations)
	if err != nil {
		t.Fatalf("Optimize failed: %v", err)
	}

	// Best score should be close to 0 (which is max when x=10, y=10)
	if result.BestScore < -10.0 {
		t.Errorf("Expected best score > -10.0, got %.2f", result.BestScore)
	}

	if !optimizer.maximize {
		t.Error("Expected maximize to be true")
	}
}

func TestRandomSearchOptimizeWithDiscreteParams(t *testing.T) {
	discreteObj := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		n := int(toFloat64(config["n"]))
		// Score is just the value itself
		return float64(n), nil
	}

	searchSpace := NewSearchSpace()
	searchSpace.AddDiscrete("n", []interface{}{1, 5, 10, 20, 50})

	optimizer := NewRandomSearchOptimizer(
		discreteObj,
		searchSpace,
		true, // Maximize
	)

	ctx := context.Background()
	result, err := optimizer.Optimize(ctx, 20)
	if err != nil {
		t.Fatalf("Optimize failed: %v", err)
	}

	// Best should be 50 (or close to it with reasonable probability)
	if result.BestScore < 5.0 {
		t.Errorf("Expected best score >= 5.0, got %.2f", result.BestScore)
	}
}

func TestRandomSearchOptimizeWithCategorical(t *testing.T) {
	categoricalObj := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		model := config["model"].(string)
		// Assign scores to different models
		scores := map[string]float64{
			"model-a": 0.6,
			"model-b": 0.8,
			"model-c": 0.7,
		}
		return scores[model], nil
	}

	searchSpace := NewSearchSpace()
	searchSpace.AddCategorical("model", []string{"model-a", "model-b", "model-c"})

	optimizer := NewRandomSearchOptimizer(
		categoricalObj,
		searchSpace,
		true, // Maximize
	)

	ctx := context.Background()
	result, err := optimizer.Optimize(ctx, 15)
	if err != nil {
		t.Fatalf("Optimize failed: %v", err)
	}

	// Best should be model-b with score 0.8
	if result.BestScore < 0.6 {
		t.Errorf("Expected best score >= 0.6, got %.2f", result.BestScore)
	}
}

func TestRandomSearchOptimizeContextCancellation(t *testing.T) {
	slowObj := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		select {
		case <-ctx.Done():
			return 0, ctx.Err()
		case <-time.After(100 * time.Millisecond):
			return 0.5, nil
		}
	}

	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		slowObj,
		searchSpace,
		true,
	)

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	_, err := optimizer.Optimize(ctx, 10)
	if err == nil {
		t.Error("Expected error from cancelled context")
	}

	if err != context.Canceled {
		t.Errorf("Expected context.Canceled, got %v", err)
	}
}

func TestRandomSearchOptimizeObjectiveError(t *testing.T) {
	errorObj := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		return 0, fmt.Errorf("evaluation failed")
	}

	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		errorObj,
		searchSpace,
		true,
	)

	ctx := context.Background()
	_, err := optimizer.Optimize(ctx, 5)
	if err == nil {
		t.Error("Expected error from failing objective function")
	}
}

func TestRandomSearchOptimizeHistory(t *testing.T) {
	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		mockObjectiveFunc,
		searchSpace,
		false,
	)

	ctx := context.Background()
	nIterations := 10

	result, err := optimizer.Optimize(ctx, nIterations)
	if err != nil {
		t.Fatalf("Optimize failed: %v", err)
	}

	// Check history structure
	if len(result.History) != nIterations {
		t.Errorf("Expected %d history entries, got %d", nIterations, len(result.History))
	}

	for i, step := range result.History {
		if step.Config == nil {
			t.Errorf("Expected config to be set in step %d", i)
		}
		// Score should be recorded (could be 0, checked config above)
	}
}

func TestRandomSearchOptimizeDuration(t *testing.T) {
	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		mockObjectiveFunc,
		searchSpace,
		false,
	)

	ctx := context.Background()
	result, err := optimizer.Optimize(ctx, 5)
	if err != nil {
		t.Fatalf("Optimize failed: %v", err)
	}

	duration := result.Duration()
	if duration == 0 {
		t.Error("Expected non-zero duration")
	}

	// Should complete reasonably quickly
	if duration > 1*time.Second {
		t.Errorf("Expected duration < 1s, got %v", duration)
	}
}

func TestRandomSearchOptimizeImprovement(t *testing.T) {
	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		mockObjectiveFunc,
		searchSpace,
		false, // Minimize
	)

	ctx := context.Background()
	result, err := optimizer.Optimize(ctx, 20)
	if err != nil {
		t.Fatalf("Optimize failed: %v", err)
	}

	improvement := result.GetImprovement()

	// For minimization, improvement should be positive (we improved by reducing the score)
	// The first score should be worse than the best score
	if len(result.History) > 0 {
		firstScore := result.History[0].Score
		if firstScore < result.BestScore {
			// First was better, so improvement should be negative
			if improvement > 0 {
				t.Errorf("Expected negative improvement when first score was better")
			}
		}
	}
}

func TestGetHistory(t *testing.T) {
	searchSpace := NewSearchSpace()
	searchSpace.AddContinuous("x", 0.0, 10.0)

	optimizer := NewRandomSearchOptimizer(
		mockObjectiveFunc,
		searchSpace,
		false,
	)

	// Initially empty
	if len(optimizer.GetHistory()) != 0 {
		t.Error("Expected empty history before optimization")
	}

	ctx := context.Background()
	_, err := optimizer.Optimize(ctx, 5)
	if err != nil {
		t.Fatalf("Optimize failed: %v", err)
	}

	// Should have history now
	history := optimizer.GetHistory()
	if len(history) != 5 {
		t.Errorf("Expected 5 history entries, got %d", len(history))
	}
}
