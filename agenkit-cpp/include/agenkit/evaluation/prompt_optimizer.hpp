/**
 * @file prompt_optimizer.hpp
 * @brief Prompt optimization through systematic variation and testing
 *
 * This module provides automated prompt engineering using three strategies:
 * 1. Grid Search - Exhaustive evaluation of all combinations
 * 2. Random Search - Sampling random combinations
 * 3. Genetic Algorithm - Evolutionary optimization
 *
 * Example:
 * @code
 * auto optimizer = PromptOptimizer(
 *     "You are a {role}. {instructions}",
 *     {{"role", {"assistant", "advisor"}},
 *      {"instructions", {"Be brief.", "Be detailed."}}},
 *     [](const std::string& prompt) -> double {
 *         // Create agent, evaluate, return score
 *         return evaluate_agent_with_prompt(prompt);
 *     }
 * );
 *
 * auto result = optimizer.optimize_grid().get();
 * std::cout << "Best prompt: " << result.best_prompt << std::endl;
 * @endcode
 */

#pragma once

#include <string>
#include <map>
#include <vector>
#include <functional>
#include <future>
#include <chrono>

namespace agenkit {
namespace evaluation {

/**
 * @brief Optimization strategies for prompt engineering
 */
enum class OptimizationStrategy {
    GRID,     ///< Exhaustive grid search (all combinations)
    RANDOM,   ///< Random sampling of configurations
    GENETIC   ///< Genetic algorithm (evolutionary)
};

/**
 * @brief Results from prompt optimization
 */
struct PromptOptimizationResult {
    std::string best_prompt;                          ///< Best prompt found
    std::map<std::string, std::string> best_config;   ///< Best variable configuration
    std::map<std::string, double> best_scores;        ///< Best metric scores

    /// Complete history: (prompt, config, scores)
    std::vector<std::tuple<
        std::string,
        std::map<std::string, std::string>,
        std::map<std::string, double>
    >> history;

    int n_evaluated;                                   ///< Number of prompts evaluated
    OptimizationStrategy strategy;                     ///< Strategy used
    std::chrono::system_clock::time_point start_time;  ///< Start timestamp
    std::chrono::system_clock::time_point end_time;    ///< End timestamp

    /**
     * @brief Calculate optimization duration in seconds
     * @return Duration in seconds
     */
    double duration_seconds() const;
};

/**
 * @brief Prompt optimization through systematic variation
 *
 * The PromptOptimizer automatically finds better prompts by:
 * 1. Defining a template with {variable} placeholders
 * 2. Providing variations for each variable
 * 3. Systematically testing combinations
 * 4. Selecting the best performing prompt
 *
 * Three optimization strategies are available:
 * - **Grid Search**: Evaluates all possible combinations (exhaustive)
 * - **Random Search**: Samples N random combinations (faster)
 * - **Genetic Algorithm**: Evolves prompts over generations (adaptive)
 *
 * Thread Safety:
 * - Not thread-safe for concurrent optimize() calls on same instance
 * - Safe to use different instances concurrently
 *
 * Example Usage:
 * @code
 * // Define template
 * std::string template_str = "You are a {role}. {style}";
 *
 * // Define variations
 * std::map<std::string, std::vector<std::string>> variations = {
 *     {"role", {"assistant", "advisor", "guide"}},
 *     {"style", {"Be concise.", "Be detailed.", "Be friendly."}}
 * };
 *
 * // Objective function: evaluate prompt and return score
 * auto objective = [](const std::string& prompt) -> double {
 *     auto agent = create_agent(prompt);
 *     return evaluate_performance(agent);  // Higher is better
 * };
 *
 * // Create optimizer
 * PromptOptimizer optimizer(template_str, variations, objective);
 *
 * // Run grid search (9 combinations)
 * auto grid_result = optimizer.optimize_grid().get();
 *
 * // Run random search (sample 5)
 * auto random_result = optimizer.optimize_random(5).get();
 *
 * // Run genetic algorithm
 * auto genetic_result = optimizer.optimize_genetic(
 *     10,   // population_size
 *     5,    // n_generations
 *     0.2   // mutation_rate
 * ).get();
 * @endcode
 */
class PromptOptimizer {
public:
    /// Function that evaluates a prompt and returns a score (higher is better by default)
    using ObjectiveFunction = std::function<double(const std::string& prompt)>;

    /**
     * @brief Construct prompt optimizer
     *
     * @param template_str Prompt template with {variable} placeholders
     *                     Example: "You are a {role}. {instructions}"
     * @param variations Map of variable names to possible values
     *                   Example: {{"role", {"assistant", "advisor"}}}
     * @param objective Function that evaluates a prompt and returns score
     * @param maximize Whether to maximize (true) or minimize (false) the objective
     *
     * @throws std::invalid_argument if template or variations are empty
     */
    explicit PromptOptimizer(
        std::string template_str,
        std::map<std::string, std::vector<std::string>> variations,
        ObjectiveFunction objective,
        bool maximize = true
    );

    /**
     * @brief Grid search: Evaluate all possible combinations
     *
     * Exhaustively tests every combination of variables. This guarantees
     * finding the global optimum but can be expensive for large search spaces.
     *
     * Complexity: O(n^k) where n is avg values per variable, k is num variables
     *
     * Example: 3 variables with 4 values each = 4^3 = 64 evaluations
     *
     * @return Future with PromptOptimizationResult
     */
    std::future<PromptOptimizationResult> optimize_grid();

    /**
     * @brief Random search: Sample random combinations
     *
     * Tests N randomly sampled combinations. Much faster than grid search
     * for large spaces, often finds near-optimal solutions.
     *
     * Complexity: O(n_samples)
     *
     * @param n_samples Number of random configurations to sample (default: 20)
     * @return Future with PromptOptimizationResult
     */
    std::future<PromptOptimizationResult> optimize_random(size_t n_samples = 20);

    /**
     * @brief Genetic algorithm: Evolve prompts through selection and mutation
     *
     * Uses evolutionary principles:
     * 1. Initialize random population
     * 2. Evaluate fitness (objective score)
     * 3. Select fit individuals (tournament selection)
     * 4. Mutate (randomly change variables)
     * 5. Repeat for N generations
     *
     * Good for large search spaces with smooth fitness landscapes.
     *
     * Complexity: O(population_size * n_generations)
     *
     * @param population_size Number of prompts per generation (default: 10)
     * @param n_generations Number of evolution cycles (default: 5)
     * @param mutation_rate Probability of mutating each variable (default: 0.2)
     * @return Future with PromptOptimizationResult
     */
    std::future<PromptOptimizationResult> optimize_genetic(
        size_t population_size = 10,
        size_t n_generations = 5,
        double mutation_rate = 0.2
    );

    /**
     * @brief Get number of possible configurations
     *
     * Useful for deciding whether grid search is feasible.
     * If > 100, consider random or genetic instead.
     *
     * @return Total number of unique prompt configurations
     */
    size_t get_search_space_size() const;

    /**
     * @brief Get the prompt template
     * @return Template string with {variable} placeholders
     */
    const std::string& get_template() const { return template_; }

    /**
     * @brief Get the variable variations
     * @return Map of variable names to possible values
     */
    const std::map<std::string, std::vector<std::string>>& get_variations() const {
        return variations_;
    }

private:
    /**
     * @brief Fill template with configuration values
     * @param config Variable assignments
     * @return Completed prompt string
     */
    std::string fill_template(const std::map<std::string, std::string>& config) const;

    /**
     * @brief Generate all possible configurations (Cartesian product)
     * @return Vector of all configurations
     */
    std::vector<std::map<std::string, std::string>> generate_all_configs() const;

    /**
     * @brief Sample one random configuration
     * @return Random configuration
     */
    std::map<std::string, std::string> sample_config() const;

    /**
     * @brief Evaluate a prompt using the objective function
     * @param prompt Prompt to evaluate
     * @return Objective score (higher is better if maximize=true)
     */
    double evaluate_prompt(const std::string& prompt) const;

    /**
     * @brief Mutate a configuration by randomly changing variables
     * @param config Configuration to mutate
     * @param mutation_rate Probability of changing each variable
     * @return Mutated configuration
     */
    std::map<std::string, std::string> mutate_config(
        const std::map<std::string, std::string>& config,
        double mutation_rate
    ) const;

    std::string template_;                                        ///< Prompt template
    std::map<std::string, std::vector<std::string>> variations_;  ///< Variable options
    ObjectiveFunction objective_;                                 ///< Evaluation function
    bool maximize_;                                               ///< Maximize or minimize
};

}  // namespace evaluation
}  // namespace agenkit
