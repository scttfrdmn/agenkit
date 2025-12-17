/**
 * @file bayesian_optimizer_example.cpp
 * @brief Example demonstrating Bayesian optimization for hyperparameter tuning
 *
 * This example shows how to use Bayesian optimization to find the best
 * hyperparameters for an agent more efficiently than random search.
 * It demonstrates:
 * - Setting up search space with multiple parameter types
 * - Comparing different acquisition functions (EI, UCB, PI)
 * - Analyzing convergence and efficiency
 * - Best practices for hyperparameter optimization
 */

#include "agenkit/evaluation/bayesian_optimizer.hpp"
#include "agenkit/evaluation/optimizer.hpp"  // For RandomSearchOptimizer comparison
#include <iostream>
#include <iomanip>
#include <cmath>

using namespace agenkit::evaluation;

/**
 * Simulated agent performance objective
 *
 * In reality, this would:
 * 1. Create an agent with the given hyperparameters
 * 2. Run it on test cases
 * 3. Return accuracy or quality score
 *
 * For this example, we use a known function with optimal parameters:
 * - temperature = 0.7
 * - max_tokens = 512
 * - top_k = 40
 */
double evaluate_agent_config(const std::map<std::string, std::any>& config) {
    double temperature = std::any_cast<double>(config.at("temperature"));
    double max_tokens = std::any_cast<double>(config.at("max_tokens"));
    int top_k = std::any_cast<int>(config.at("top_k"));

    // Simulate performance with known optima
    double temp_score = 1.0 - std::abs(temperature - 0.7);
    double tokens_score = 1.0 - std::abs(max_tokens - 512.0) / 512.0;
    double topk_score = 1.0 - std::abs(top_k - 40.0) / 40.0;

    // Weighted combination
    return 0.5 * temp_score + 0.3 * tokens_score + 0.2 * topk_score;
}

/**
 * Print configuration in readable format
 */
void print_config(const std::map<std::string, std::any>& config, double score) {
    std::cout << "  temperature: " << std::fixed << std::setprecision(3)
              << std::any_cast<double>(config.at("temperature"));
    std::cout << ", max_tokens: " << static_cast<int>(std::any_cast<double>(config.at("max_tokens")));
    std::cout << ", top_k: " << std::any_cast<int>(config.at("top_k"));
    std::cout << " → score: " << std::setprecision(4) << score << std::endl;
}

/**
 * Demonstrate basic Bayesian optimization
 */
void demonstrate_basic_optimization() {
    std::cout << "=== Basic Bayesian Optimization ===" << std::endl;
    std::cout << std::endl;

    // Step 1: Define search space
    std::cout << "1. Defining search space:" << std::endl;
    std::cout << "   - temperature: continuous [0.0, 1.0]" << std::endl;
    std::cout << "   - max_tokens: discrete {128, 256, 512, 1024}" << std::endl;
    std::cout << "   - top_k: integer [1, 100]" << std::endl;
    std::cout << std::endl;

    auto search_space = std::make_shared<SearchSpace>();
    search_space->add_continuous("temperature", 0.0, 1.0);
    search_space->add_discrete("max_tokens", {128.0, 256.0, 512.0, 1024.0});
    search_space->add_integer("top_k", 1, 100);

    // Step 2: Create optimizer
    std::cout << "2. Creating Bayesian optimizer:" << std::endl;
    std::cout << "   - Acquisition: Expected Improvement (EI)" << std::endl;
    std::cout << "   - Initial samples: 5 (random exploration)" << std::endl;
    std::cout << "   - Total iterations: 40" << std::endl;
    std::cout << std::endl;

    BayesianOptimizer optimizer(
        evaluate_agent_config,
        search_space,
        true,                      // maximize
        AcquisitionFunction::EI,   // Expected Improvement
        5,                         // n_initial
        0.01,                      // xi
        2.576                      // kappa
    );

    // Step 3: Run optimization
    std::cout << "3. Running Bayesian optimization..." << std::endl;
    auto result = optimizer.optimize(40).get();

    std::cout << "   Completed in " << std::fixed << std::setprecision(2)
              << result.duration_seconds() << " seconds" << std::endl;
    std::cout << std::endl;

    // Step 4: Show results
    std::cout << "4. Optimization Results:" << std::endl;
    std::cout << "   Best configuration found:" << std::endl;
    print_config(result.best_config, result.best_score);
    std::cout << std::endl;

    std::cout << "   Target configuration (optimal):" << std::endl;
    std::cout << "   temperature: 0.700, max_tokens: 512, top_k: 40 → score: 1.0000" << std::endl;
    std::cout << std::endl;

    // Show convergence
    std::cout << "   Convergence:" << std::endl;
    std::cout << "   Initial (iteration 1): score = " << std::setprecision(4)
              << result.history[0].score << std::endl;
    std::cout << "   Final (iteration 40): score = " << result.best_score << std::endl;
    std::cout << "   Improvement: " << std::setprecision(1)
              << ((result.best_score - result.history[0].score) / result.history[0].score * 100)
              << "%" << std::endl;
    std::cout << std::endl;
}

/**
 * Compare different acquisition functions
 */
void compare_acquisition_functions() {
    std::cout << "=== Comparing Acquisition Functions ===" << std::endl;
    std::cout << std::endl;

    auto search_space = std::make_shared<SearchSpace>();
    search_space->add_continuous("temperature", 0.0, 1.0);
    search_space->add_discrete("max_tokens", {128.0, 256.0, 512.0, 1024.0});
    search_space->add_integer("top_k", 1, 100);

    std::vector<std::pair<AcquisitionFunction, std::string>> acquisitions = {
        {AcquisitionFunction::EI, "Expected Improvement (EI)"},
        {AcquisitionFunction::UCB, "Upper Confidence Bound (UCB)"},
        {AcquisitionFunction::PI, "Probability of Improvement (PI)"}
    };

    std::cout << "Running each acquisition function for 30 iterations..." << std::endl;
    std::cout << std::endl;

    for (const auto& [acq_func, acq_name] : acquisitions) {
        BayesianOptimizer optimizer(
            evaluate_agent_config,
            search_space,
            true,
            acq_func,
            5
        );

        auto result = optimizer.optimize(30).get();

        std::cout << acq_name << ":" << std::endl;
        std::cout << "  Best score: " << std::setprecision(4) << result.best_score << std::endl;
        std::cout << "  Best config: ";
        print_config(result.best_config, result.best_score);
        std::cout << std::endl;
    }

    std::cout << "Note: Results may vary due to random sampling." << std::endl;
    std::cout << "- EI: Good balance of exploration/exploitation" << std::endl;
    std::cout << "- UCB: More exploratory, good for large search spaces" << std::endl;
    std::cout << "- PI: More exploitative, good for fine-tuning" << std::endl;
    std::cout << std::endl;
}

/**
 * Compare Bayesian optimization vs Random search
 */
void compare_with_random_search() {
    std::cout << "=== Bayesian vs Random Search ===" << std::endl;
    std::cout << std::endl;

    auto search_space = std::make_shared<SearchSpace>();
    search_space->add_continuous("temperature", 0.0, 1.0);
    search_space->add_discrete("max_tokens", {128.0, 256.0, 512.0, 1024.0});
    search_space->add_integer("top_k", 1, 100);

    constexpr size_t n_iterations = 40;

    // Run Bayesian optimization
    std::cout << "Running Bayesian optimization (" << n_iterations << " iterations)..." << std::endl;
    BayesianOptimizer bayes_opt(
        evaluate_agent_config,
        search_space,
        true,
        AcquisitionFunction::EI,
        5
    );
    auto bayes_result = bayes_opt.optimize(n_iterations).get();

    // Run Random search
    std::cout << "Running Random search (" << n_iterations << " iterations)..." << std::endl;
    RandomSearchOptimizer random_opt(
        evaluate_agent_config,
        search_space,
        true
    );
    auto random_result = random_opt.optimize(n_iterations).get();

    std::cout << std::endl;
    std::cout << "Results Comparison:" << std::endl;
    std::cout << "─────────────────────────────────────────────────" << std::endl;
    std::cout << std::setw(30) << "Method" << std::setw(15) << "Best Score" << std::endl;
    std::cout << "─────────────────────────────────────────────────" << std::endl;
    std::cout << std::setw(30) << "Bayesian Optimization"
              << std::setw(15) << std::setprecision(4) << bayes_result.best_score << std::endl;
    std::cout << std::setw(30) << "Random Search"
              << std::setw(15) << random_result.best_score << std::endl;
    std::cout << "─────────────────────────────────────────────────" << std::endl;
    std::cout << std::endl;

    double improvement = ((bayes_result.best_score - random_result.best_score) /
                          random_result.best_score) * 100.0;
    if (improvement > 0) {
        std::cout << "Bayesian optimization found a " << std::setprecision(1)
                  << improvement << "% better solution!" << std::endl;
    } else {
        std::cout << "Results are similar (both found good solutions)." << std::endl;
    }
    std::cout << std::endl;

    std::cout << "Key Advantages of Bayesian Optimization:" << std::endl;
    std::cout << "  • More sample-efficient (needs fewer evaluations)" << std::endl;
    std::cout << "  • Intelligent exploration guided by surrogate model" << std::endl;
    std::cout << "  • Better for expensive objective functions" << std::endl;
    std::cout << "  • Adapts search strategy based on observations" << std::endl;
    std::cout << std::endl;
}

/**
 * Demonstrate effect of initial samples
 */
void demonstrate_initial_samples() {
    std::cout << "=== Effect of Initial Samples ===" << std::endl;
    std::cout << std::endl;

    auto search_space = std::make_shared<SearchSpace>();
    search_space->add_continuous("temperature", 0.0, 1.0);
    search_space->add_discrete("max_tokens", {128.0, 256.0, 512.0, 1024.0});
    search_space->add_integer("top_k", 1, 100);

    std::vector<size_t> n_initial_values = {3, 5, 10, 15};

    std::cout << "Testing different numbers of initial random samples:" << std::endl;
    std::cout << std::endl;

    for (size_t n_init : n_initial_values) {
        BayesianOptimizer optimizer(
            evaluate_agent_config,
            search_space,
            true,
            AcquisitionFunction::EI,
            n_init
        );

        auto result = optimizer.optimize(30).get();

        std::cout << "  n_initial = " << std::setw(2) << n_init
                  << ": best score = " << std::setprecision(4) << result.best_score << std::endl;
    }

    std::cout << std::endl;
    std::cout << "Guidelines:" << std::endl;
    std::cout << "  • Too few initial samples: May miss good regions" << std::endl;
    std::cout << "  • Too many initial samples: Wastes evaluations on random search" << std::endl;
    std::cout << "  • Typical: 5-10 initial samples for most problems" << std::endl;
    std::cout << "  • Rule of thumb: n_initial ≈ 2 * n_parameters" << std::endl;
    std::cout << std::endl;
}

int main() {
    std::cout << "=== Bayesian Optimization Example ===" << std::endl;
    std::cout << std::endl;

    // Demonstrate basic usage
    demonstrate_basic_optimization();

    // Compare acquisition functions
    compare_acquisition_functions();

    // Compare with random search
    compare_with_random_search();

    // Show effect of initial samples
    demonstrate_initial_samples();

    // Best practices
    std::cout << "=== Best Practices ===" << std::endl;
    std::cout << std::endl;
    std::cout << "1. Search Space Design:" << std::endl;
    std::cout << "   • Start with wide ranges, narrow based on results" << std::endl;
    std::cout << "   • Use log scale for parameters spanning orders of magnitude" << std::endl;
    std::cout << "   • Normalize parameters to similar scales when possible" << std::endl;
    std::cout << std::endl;

    std::cout << "2. Acquisition Function Selection:" << std::endl;
    std::cout << "   • EI: Default choice, good balance" << std::endl;
    std::cout << "   • UCB: Large search spaces, early exploration" << std::endl;
    std::cout << "   • PI: Fine-tuning around known good regions" << std::endl;
    std::cout << std::endl;

    std::cout << "3. Computational Budget:" << std::endl;
    std::cout << "   • Cheap evaluations (< 1s): 50-100 iterations" << std::endl;
    std::cout << "   • Moderate (1-10s): 30-50 iterations" << std::endl;
    std::cout << "   • Expensive (> 10s): 20-30 iterations" << std::endl;
    std::cout << std::endl;

    std::cout << "4. When to Use Bayesian Optimization:" << std::endl;
    std::cout << "   ✓ Expensive objective function (minutes per evaluation)" << std::endl;
    std::cout << "   ✓ Continuous or mixed parameter spaces" << std::endl;
    std::cout << "   ✓ Limited evaluation budget" << std::endl;
    std::cout << "   ✗ Very high dimensional (> 20 parameters)" << std::endl;
    std::cout << "   ✗ Cheap evaluations where random search suffices" << std::endl;
    std::cout << std::endl;

    std::cout << "=== Example Complete ===" << std::endl;

    return 0;
}
