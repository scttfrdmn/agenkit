/**
 * @file optimizer_example.cpp
 * @brief Example demonstrating hyperparameter optimization for agents
 *
 * This example shows how to use the optimization framework to find the best
 * hyperparameters for an agent. It demonstrates:
 * - Defining a search space with multiple parameter types
 * - Creating an objective function based on agent performance
 * - Running random search optimization
 * - Analyzing optimization results
 */

#include "agenkit/evaluation/optimizer.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>
#include <iomanip>

using namespace agenkit::evaluation;
using namespace agenkit::core;
using namespace agenkit::adapters;

/**
 * Simple test cases for evaluating agent performance
 */
std::vector<std::pair<std::string, std::string>> get_test_cases() {
    return {
        {"What is 2+2?", "4"},
        {"What is the capital of France?", "Paris"},
        {"What color is the sky?", "blue"},
        {"How many days in a week?", "7"},
        {"What is water made of?", "H2O"}
    };
}

/**
 * Objective function that evaluates agent configuration
 *
 * In a real scenario, this would:
 * 1. Create an agent with the given config
 * 2. Run it on test cases
 * 3. Return a performance metric (accuracy, quality, etc.)
 *
 * For this example, we simulate with a simple formula
 */
double evaluate_agent_config(const std::map<std::string, std::any>& config) {
    // Extract parameters
    double temperature = std::any_cast<double>(config.at("temperature"));
    // max_tokens is discrete (stored as double) - need to cast to double
    double max_tokens = std::any_cast<double>(config.at("max_tokens"));
    // top_k is integer - stored as int
    int top_k = std::any_cast<int>(config.at("top_k"));

    // Simulate agent performance based on parameters
    // In reality, you would:
    //   1. Create agent with config
    //   2. Run test cases
    //   3. Calculate accuracy

    // Simple formula: optimal temperature=0.7, max_tokens=256, top_k=40
    double temp_score = 1.0 - std::abs(temperature - 0.7);
    double tokens_score = 1.0 - std::abs(max_tokens - 256.0) / 256.0;
    double topk_score = 1.0 - std::abs(top_k - 40.0) / 40.0;

    // Weighted average
    return 0.5 * temp_score + 0.3 * tokens_score + 0.2 * topk_score;
}

/**
 * Print configuration in a readable format
 */
void print_config(const std::map<std::string, std::any>& config, double score) {
    std::cout << "  temperature: " << std::any_cast<double>(config.at("temperature"));
    std::cout << ", max_tokens: " << static_cast<int>(std::any_cast<double>(config.at("max_tokens")));
    std::cout << ", top_k: " << std::any_cast<int>(config.at("top_k"));
    std::cout << " → score: " << std::fixed << std::setprecision(4) << score << std::endl;
}

int main() {
    std::cout << "=== Hyperparameter Optimization Example ===" << std::endl;
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

    // Step 2: Define objective function
    std::cout << "2. Objective: Maximize agent performance" << std::endl;
    std::cout << "   Target: temperature=0.7, max_tokens=256, top_k=40" << std::endl;
    std::cout << std::endl;

    // Step 3: Create optimizer
    std::cout << "3. Running random search optimization (50 iterations)..." << std::endl;
    RandomSearchOptimizer optimizer(
        evaluate_agent_config,
        search_space,
        true  // maximize
    );

    // Step 4: Run optimization
    auto result = optimizer.optimize(50).get();

    std::cout << "   Completed in " << std::fixed << std::setprecision(2)
              << result.duration_seconds() << " seconds" << std::endl;
    std::cout << std::endl;

    // Step 5: Show results
    std::cout << "4. Optimization Results:" << std::endl;
    std::cout << "   Best configuration found:" << std::endl;
    print_config(result.best_config, result.best_score);
    std::cout << std::endl;

    std::cout << "   Initial configuration (iteration 1):" << std::endl;
    if (!result.history.empty()) {
        print_config(result.history.front().config, result.history.front().score);
    }
    std::cout << std::endl;

    std::cout << "   Improvement: " << std::fixed << std::setprecision(1)
              << result.get_improvement() << "%" << std::endl;
    std::cout << std::endl;

    // Step 6: Show convergence
    std::cout << "5. Top 5 configurations found:" << std::endl;

    // Sort history by score
    auto sorted_history = result.history;
    std::sort(sorted_history.begin(), sorted_history.end(),
              [](const OptimizationStep& a, const OptimizationStep& b) {
                  return a.score > b.score;
              });

    for (size_t i = 0; i < std::min(size_t(5), sorted_history.size()); ++i) {
        std::cout << "   " << (i + 1) << ". ";
        print_config(sorted_history[i].config, sorted_history[i].score);
    }
    std::cout << std::endl;

    // Step 7: Validate best configuration
    std::cout << "6. Validating best configuration..." << std::endl;
    bool valid = search_space->validate(result.best_config);
    std::cout << "   Configuration is " << (valid ? "VALID" : "INVALID") << std::endl;
    std::cout << std::endl;

    // Step 8: Export results
    std::cout << "7. Exporting results to JSON..." << std::endl;
    auto json_result = result.to_json();
    std::cout << "   JSON size: " << json_result.dump().length() << " bytes" << std::endl;
    std::cout << "   Contains " << result.history.size() << " optimization steps" << std::endl;
    std::cout << std::endl;

    // Step 9: Usage recommendations
    std::cout << "8. Recommended next steps:" << std::endl;
    std::cout << "   - Use best configuration in production" << std::endl;
    std::cout << "   - Run A/B test comparing default vs optimized config" << std::endl;
    std::cout << "   - Consider Bayesian optimization for faster convergence" << std::endl;
    std::cout << "   - Monitor performance and re-optimize periodically" << std::endl;
    std::cout << std::endl;

    std::cout << "=== Example Complete ===" << std::endl;

    return 0;
}
