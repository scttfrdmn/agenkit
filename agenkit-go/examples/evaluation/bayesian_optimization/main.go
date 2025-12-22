// Package main demonstrates Bayesian Optimization for hyperparameter tuning.
//
// Bayesian Optimization is a powerful technique for finding optimal hyperparameters
// efficiently. It uses a probabilistic surrogate model to guide the search, balancing
// exploration of unknown regions with exploitation of known good configurations.
//
// This example shows:
//   - Setting up a search space with different parameter types
//   - Defining an objective function (simulated agent performance)
//   - Running optimization with different acquisition functions
//   - Analyzing optimization results and convergence
//
// Run with: go run bayesian_optimization_example.go
package main

import (
	"context"
	"fmt"
	"log"
	"math"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

// simulateAgentPerformance simulates evaluating an agent with given hyperparameters.
// In a real scenario, this would train/run an agent and measure its performance.
func simulateAgentPerformance(config map[string]interface{}) float64 {
	// Extract hyperparameters
	learningRate := config["learning_rate"].(float64)
	batchSize := config["batch_size"].(int)
	optimizer := config["optimizer"].(string)
	momentum := config["momentum"].(float64)

	// Simulate performance based on hyperparameters
	// Optimal values: lr=0.01, batch_size=64, optimizer="adam", momentum=0.9
	score := 0.0

	// Learning rate contribution (optimal: 0.01)
	lrScore := 1.0 - math.Abs(math.Log10(learningRate)-math.Log10(0.01))
	score += math.Max(0, lrScore) * 30.0

	// Batch size contribution (optimal: 64)
	bsScore := 1.0 - math.Abs(float64(batchSize-64))/64.0
	score += math.Max(0, bsScore) * 25.0

	// Optimizer contribution
	optimizerScore := 0.0
	switch optimizer {
	case "adam":
		optimizerScore = 30.0
	case "sgd":
		optimizerScore = 20.0
	case "rmsprop":
		optimizerScore = 15.0
	}
	score += optimizerScore

	// Momentum contribution (optimal: 0.9)
	momentumScore := 1.0 - math.Abs(momentum-0.9)
	score += momentumScore * 15.0

	// Add some noise to simulate real-world variability
	// (In real optimization, noise comes from actual evaluation variability)
	return score
}

func main() {
	fmt.Println("Bayesian Optimization Example: Agent Hyperparameter Tuning")
	fmt.Println("===========================================================")

	// Step 1: Define the search space
	fmt.Println("Step 1: Defining Search Space")
	fmt.Println("------------------------------")

	space := evaluation.NewSearchSpace()

	// Continuous parameter: learning rate (log scale)
	space.AddContinuous("learning_rate", 0.0001, 0.1)
	fmt.Println("✓ Learning Rate: continuous [0.0001, 0.1]")

	// Integer parameter: batch size
	space.AddInteger("batch_size", 16, 128)
	fmt.Println("✓ Batch Size: integer [16, 128]")

	// Categorical parameter: optimizer
	space.AddCategorical("optimizer", []string{"adam", "sgd", "rmsprop"})
	fmt.Println("✓ Optimizer: categorical {adam, sgd, rmsprop}")

	// Discrete parameter: momentum values
	space.AddDiscrete("momentum", []interface{}{0.0, 0.5, 0.9, 0.95})
	fmt.Println("✓ Momentum: discrete {0.0, 0.5, 0.9, 0.95}")

	fmt.Println()

	// Step 2: Define the objective function
	fmt.Println("Step 2: Defining Objective Function")
	fmt.Println("------------------------------------")
	fmt.Println("Objective: Maximize agent performance score")
	fmt.Println("(simulates training and evaluating an agent)")

	objective := func(ctx context.Context, config map[string]interface{}) (float64, error) {
		score := simulateAgentPerformance(config)
		return score, nil
	}

	// Step 3: Run optimization with Expected Improvement (EI)
	fmt.Println("Step 3: Running Bayesian Optimization")
	fmt.Println("--------------------------------------")
	fmt.Println("Acquisition Function: Expected Improvement (EI)")
	fmt.Println("Initial Samples: 5 (random exploration)")
	fmt.Println("Total Iterations: 20")
	fmt.Println()

	optimizer, err := evaluation.NewBayesianOptimizer(evaluation.BayesianOptimizerConfig{
		SearchSpace: space,
		Objective:   objective,
		Maximize:    true,
		NInitial:    5,
		Acquisition: evaluation.AcquisitionEI,
		Xi:          0.01, // Exploration parameter
	})
	if err != nil {
		log.Fatalf("Failed to create optimizer: %v", err)
	}

	ctx := context.Background()
	result, err := optimizer.Optimize(ctx, 20)
	if err != nil {
		log.Fatalf("Optimization failed: %v", err)
	}

	// Step 4: Analyze results
	fmt.Println("Step 4: Optimization Results")
	fmt.Println("----------------------------")

	fmt.Printf("Duration: %v\n", result.Duration())
	fmt.Printf("Total Iterations: %d\n", result.NIterations)
	fmt.Printf("Best Score: %.2f\n\n", result.BestScore)

	fmt.Println("Best Configuration:")
	fmt.Printf("  Learning Rate: %.6f\n", result.BestConfig["learning_rate"])
	fmt.Printf("  Batch Size: %d\n", result.BestConfig["batch_size"])
	fmt.Printf("  Optimizer: %s\n", result.BestConfig["optimizer"])
	fmt.Printf("  Momentum: %.2f\n\n", result.BestConfig["momentum"])

	// Show convergence history
	fmt.Println("Convergence History:")
	fmt.Println(strings.Repeat("-", 70))
	fmt.Printf("%-10s %-15s %-15s\n", "Iteration", "Score", "Best So Far")
	fmt.Println(strings.Repeat("-", 70))

	bestSoFar := result.History[0].Score
	for i, step := range result.History {
		if step.Score > bestSoFar {
			bestSoFar = step.Score
		}
		fmt.Printf("%-10d %-15.2f %-15.2f", i+1, step.Score, bestSoFar)
		if step.Score == result.BestScore {
			fmt.Print(" ← Best")
		}
		fmt.Println()
	}
	fmt.Println()

	// Compare with random search
	fmt.Println("Step 5: Comparing with Random Search")
	fmt.Println("-------------------------------------")
	fmt.Println("Running 20 random evaluations for comparison...")

	randomBestScore := 0.0
	for i := 0; i < 20; i++ {
		config := space.Sample()
		score := simulateAgentPerformance(config)
		if score > randomBestScore {
			randomBestScore = score
		}
	}

	fmt.Printf("Random Search Best Score: %.2f\n", randomBestScore)
	fmt.Printf("Bayesian Optimization Best Score: %.2f\n", result.BestScore)
	improvement := result.BestScore - randomBestScore
	fmt.Printf("Improvement: %.2f points (%.1f%% better)\n\n",
		improvement, (improvement/randomBestScore)*100)

	// Compare different acquisition functions
	fmt.Println("Step 6: Comparing Acquisition Functions")
	fmt.Println("----------------------------------------")

	acquisitions := []struct {
		name string
		acq  evaluation.AcquisitionFunction
	}{
		{"Expected Improvement (EI)", evaluation.AcquisitionEI},
		{"Upper Confidence Bound (UCB)", evaluation.AcquisitionUCB},
		{"Probability of Improvement (PI)", evaluation.AcquisitionPI},
	}

	fmt.Printf("%-35s %-15s %-15s\n", "Acquisition Function", "Best Score", "Improvement")
	fmt.Println(strings.Repeat("-", 70))

	baselineScore := randomBestScore

	for _, acq := range acquisitions {
		opt, _ := evaluation.NewBayesianOptimizer(evaluation.BayesianOptimizerConfig{
			SearchSpace: space,
			Objective:   objective,
			Maximize:    true,
			NInitial:    5,
			Acquisition: acq.acq,
		})

		res, err := opt.Optimize(ctx, 20)
		if err != nil {
			log.Printf("Failed for %s: %v", acq.name, err)
			continue
		}

		improvement := res.BestScore - baselineScore
		fmt.Printf("%-35s %-15.2f +%.2f\n", acq.name, res.BestScore, improvement)
	}

	fmt.Println()

	// Summary and best practices
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("Summary: Bayesian Optimization")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("\nKey Benefits:")
	fmt.Println("1. Sample Efficient: Finds good configurations with fewer evaluations")
	fmt.Println("2. Balances Exploration & Exploitation: Systematically searches space")
	fmt.Println("3. Handles Mixed Parameter Types: Continuous, integer, categorical, discrete")
	fmt.Println("4. Guided Search: Uses past results to inform future trials")

	fmt.Println("\nWhen to Use:")
	fmt.Println("- Expensive objective functions (API calls, model training)")
	fmt.Println("- Limited evaluation budget")
	fmt.Println("- Mixed parameter types")
	fmt.Println("- Need reproducible optimization")

	fmt.Println("\nAcquisition Function Guide:")
	fmt.Println("- Expected Improvement (EI): Balanced, good default choice")
	fmt.Println("- Upper Confidence Bound (UCB): More exploration, use with uncertainty")
	fmt.Println("- Probability of Improvement (PI): More exploitation, refines solutions")

	fmt.Println("\nBest Practices:")
	fmt.Println("1. Start with 3-5 random samples to build initial surrogate model")
	fmt.Println("2. Use log scale for learning rates (transform externally)")
	fmt.Println("3. Run multiple trials for robust results")
	fmt.Println("4. Monitor convergence - stop if no improvement")
	fmt.Println("5. Consider parameter interactions in objective function")

	fmt.Println("\nReal-World Applications:")
	fmt.Println("- Agent LLM temperature and sampling parameters")
	fmt.Println("- RAG chunk size and overlap optimization")
	fmt.Println("- Tool selection strategy tuning")
	fmt.Println("- Prompt template hyperparameters")
	fmt.Println("- Multi-agent coordination parameters")
}
