/**
 * @file optimizer.hpp
 * @brief Automated optimization framework for agent configurations
 *
 * This module provides intelligent optimization of agent configurations, prompts,
 * and hyperparameters using various search strategies:
 * - Random search (baseline)
 * - Bayesian optimization (in bayesian_optimizer.hpp)
 * - Genetic algorithms (in prompt_optimizer.hpp)
 *
 * Key components:
 * - SearchSpace: Defines parameter search space (continuous, discrete, integer, categorical)
 * - OptimizationResult: Results from optimization run with history
 * - Optimizer: Base class for optimization algorithms
 * - RandomSearchOptimizer: Baseline random search implementation
 *
 * Key use cases:
 * - Optimize LLM hyperparameters (temperature, top_p, max_tokens)
 * - Find best prompt templates automatically
 * - Tune agent configurations for specific tasks
 * - Compare different optimization strategies
 *
 * @example
 * @code
 * // Define search space
 * auto space = std::make_shared<SearchSpace>();
 * space->add_continuous("temperature", 0.0, 1.0);
 * space->add_discrete("max_tokens", {128.0, 256.0, 512.0});
 *
 * // Define objective function
 * auto objective = [](const std::map<std::string, std::any>& config) -> double {
 *     // Create agent with config, evaluate on test cases
 *     return accuracy_score;
 * };
 *
 * // Run optimization
 * auto optimizer = RandomSearchOptimizer(objective, space, true);
 * auto result = optimizer.optimize(50).get();
 *
 * std::cout << "Best score: " << result.best_score << std::endl;
 * std::cout << "Best config: " << result.best_config << std::endl;
 * @endcode
 */

#ifndef AGENKIT_EVALUATION_OPTIMIZER_HPP
#define AGENKIT_EVALUATION_OPTIMIZER_HPP

#include <string>
#include <vector>
#include <map>
#include <any>
#include <memory>
#include <functional>
#include <future>
#include <random>
#include <chrono>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace evaluation {

/**
 * @brief Parameter type enumeration for search space
 *
 * Defines the type of parameter and how it should be sampled.
 */
enum class ParameterType {
    Continuous,    ///< Continuous float in range [low, high]
    Discrete,      ///< Discrete values from a list
    Integer,       ///< Integer in range [low, high]
    Categorical    ///< Categorical string values from a list
};

/**
 * @brief Parameter specification for search space
 *
 * Defines a single parameter with its type, bounds, and possible values.
 */
struct ParameterSpec {
    ParameterType type;              ///< Parameter type
    double low;                      ///< Lower bound (for continuous/integer)
    double high;                     ///< Upper bound (for continuous/integer)
    std::vector<std::any> values;    ///< Discrete/categorical values

    /**
     * @brief Create continuous parameter spec
     */
    ParameterSpec(double low_val, double high_val)
        : type(ParameterType::Continuous)
        , low(low_val)
        , high(high_val)
    {}

    /**
     * @brief Create discrete/categorical parameter spec
     */
    explicit ParameterSpec(std::vector<std::any> vals, ParameterType param_type = ParameterType::Discrete)
        : type(param_type)
        , low(0.0)
        , high(0.0)
        , values(std::move(vals))
    {}

    /**
     * @brief Default constructor
     */
    ParameterSpec()
        : type(ParameterType::Continuous)
        , low(0.0)
        , high(0.0)
    {}
};

/**
 * @brief Search space definition for optimization
 *
 * Defines the hyperparameter search space with support for:
 * - Continuous parameters: float in range [low, high]
 * - Discrete parameters: specific float/int values
 * - Integer parameters: integer in range [low, high]
 * - Categorical parameters: specific string values
 *
 * @details
 * SearchSpace is thread-safe for sampling operations when using separate
 * random number generators per thread.
 *
 * @example
 * @code
 * auto space = std::make_shared<SearchSpace>();
 * space->add_continuous("temperature", 0.0, 1.0);
 * space->add_discrete("max_tokens", {128.0, 256.0, 512.0, 1024.0});
 * space->add_integer("top_k", 1, 100);
 * space->add_categorical("model", {"gpt-4", "claude-3", "gemini-pro"});
 *
 * // Sample random configuration
 * auto config = space->sample();
 *
 * // Validate configuration
 * bool valid = space->validate(config);
 * @endcode
 */
class SearchSpace {
public:
    /**
     * @brief Create a new search space
     */
    SearchSpace();

    /**
     * @brief Add continuous parameter with range [low, high]
     * @param name Parameter name
     * @param low Lower bound (inclusive)
     * @param high Upper bound (inclusive)
     */
    void add_continuous(const std::string& name, double low, double high);

    /**
     * @brief Add discrete parameter with specific numeric values
     * @param name Parameter name
     * @param values List of possible values
     */
    void add_discrete(const std::string& name, const std::vector<double>& values);

    /**
     * @brief Add integer parameter with range [low, high]
     * @param name Parameter name
     * @param low Lower bound (inclusive)
     * @param high Upper bound (inclusive)
     */
    void add_integer(const std::string& name, int low, int high);

    /**
     * @brief Add categorical parameter with specific string values
     * @param name Parameter name
     * @param values List of possible string values
     */
    void add_categorical(const std::string& name, const std::vector<std::string>& values);

    /**
     * @brief Sample random configuration from search space
     * @return Random configuration as map of parameter name -> value
     *
     * Uses internal random number generator. Thread-safe if each thread
     * uses a separate SearchSpace instance.
     */
    std::map<std::string, std::any> sample();

    /**
     * @brief Validate that configuration is within search space
     * @param config Configuration to validate
     * @return true if valid, false otherwise
     *
     * Checks that all parameters are within bounds and that no unknown
     * parameters are present.
     */
    bool validate(const std::map<std::string, std::any>& config) const;

    /**
     * @brief Get parameter specifications
     * @return Map of parameter name -> ParameterSpec
     */
    const std::map<std::string, ParameterSpec>& parameters() const { return parameters_; }

private:
    std::map<std::string, ParameterSpec> parameters_;
    std::mt19937 rng_;  ///< Random number generator for sampling
};

/**
 * @brief Single optimization step (config + score)
 *
 * Records one evaluation during optimization.
 */
struct OptimizationStep {
    std::map<std::string, std::any> config;  ///< Configuration tested
    double score;                             ///< Objective score achieved

    /**
     * @brief Serialize to JSON
     */
    nlohmann::json to_json() const;
};

/**
 * @brief Results from optimization run
 *
 * Contains the best configuration found, complete history of evaluations,
 * and metadata about the optimization process.
 *
 * @example
 * @code
 * auto result = optimizer.optimize(50).get();
 * std::cout << "Best score: " << result.best_score << std::endl;
 * std::cout << "Improvement: " << result.get_improvement() << "%" << std::endl;
 * std::cout << "Duration: " << result.duration_seconds() << "s" << std::endl;
 * @endcode
 */
struct OptimizationResult {
    std::map<std::string, std::any> best_config;  ///< Best configuration found
    double best_score;                             ///< Best objective score
    std::vector<OptimizationStep> history;         ///< Complete evaluation history
    int n_iterations;                              ///< Number of iterations performed
    std::chrono::system_clock::time_point start_time;  ///< Start timestamp
    std::chrono::system_clock::time_point end_time;    ///< End timestamp
    nlohmann::json metadata;                       ///< Additional metadata

    /**
     * @brief Calculate optimization duration in seconds
     * @return Duration in seconds
     */
    double duration_seconds() const;

    /**
     * @brief Calculate improvement from initial to best score
     * @return Percentage improvement
     *
     * Returns 0.0 if no history or initial score is 0.
     */
    double get_improvement() const;

    /**
     * @brief Serialize to JSON
     * @return JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     * @param j JSON object
     * @return OptimizationResult instance
     */
    static OptimizationResult from_json(const nlohmann::json& j);
};

/**
 * @brief Objective function type
 *
 * Takes a configuration and returns a score to maximize or minimize.
 * Should return higher scores for better configurations when maximizing.
 */
using ObjectiveFunc = std::function<double(const std::map<std::string, std::any>&)>;

/**
 * @brief Base class for optimization algorithms
 *
 * Provides interface for all optimization strategies. Subclasses implement
 * specific algorithms like random search, Bayesian optimization, genetic
 * algorithms, etc.
 *
 * @details
 * The Optimizer class handles:
 * - Search space management
 * - Objective function evaluation
 * - History tracking
 * - Maximize vs minimize objective
 *
 * Subclasses must implement optimize() to define the search strategy.
 */
class Optimizer {
public:
    /**
     * @brief Create an optimizer
     * @param objective Function to optimize (returns score for a config)
     * @param search_space Search space defining valid configurations
     * @param maximize Whether to maximize (true) or minimize (false) objective
     */
    Optimizer(
        ObjectiveFunc objective,
        std::shared_ptr<SearchSpace> search_space,
        bool maximize = true
    );

    /**
     * @brief Virtual destructor
     */
    virtual ~Optimizer() = default;

    /**
     * @brief Run optimization
     * @param n_iterations Number of configurations to evaluate
     * @return Future with OptimizationResult
     *
     * Subclasses implement this to define the optimization strategy.
     */
    virtual std::future<OptimizationResult> optimize(int n_iterations) = 0;

    /**
     * @brief Evaluate a configuration
     * @param config Configuration to evaluate
     * @return Objective score (adjusted for maximize vs minimize)
     *
     * Calls the objective function and adjusts the score based on whether
     * we're maximizing or minimizing.
     */
    double evaluate_config(const std::map<std::string, std::any>& config);

    /**
     * @brief Get optimization history
     * @return Vector of optimization steps
     */
    const std::vector<OptimizationStep>& get_history() const { return history_; }

protected:
    ObjectiveFunc objective_;                      ///< Objective function
    std::shared_ptr<SearchSpace> search_space_;    ///< Search space
    bool maximize_;                                ///< Maximize vs minimize
    std::vector<OptimizationStep> history_;        ///< Evaluation history
};

/**
 * @brief Random search optimizer (baseline)
 *
 * Randomly samples configurations from the search space and evaluates them.
 * Useful as a baseline for comparing more sophisticated algorithms.
 *
 * Random search is:
 * - Simple and robust
 * - Embarrassingly parallel
 * - Works well with large search spaces
 * - Good baseline for comparison
 *
 * @example
 * @code
 * auto optimizer = RandomSearchOptimizer(objective, space, true);
 * auto result = optimizer.optimize(100).get();
 *
 * std::cout << "Best config: ";
 * for (const auto& [k, v] : result.best_config) {
 *     std::cout << k << "=" << v << " ";
 * }
 * std::cout << std::endl;
 * std::cout << "Best score: " << result.best_score << std::endl;
 * @endcode
 */
class RandomSearchOptimizer : public Optimizer {
public:
    /**
     * @brief Create random search optimizer
     * @param objective Function to optimize
     * @param search_space Search space
     * @param maximize Whether to maximize objective
     */
    RandomSearchOptimizer(
        ObjectiveFunc objective,
        std::shared_ptr<SearchSpace> search_space,
        bool maximize = true
    );

    /**
     * @brief Run random search optimization
     * @param n_iterations Number of random configurations to evaluate
     * @return Future with OptimizationResult
     *
     * Randomly samples n_iterations configurations, evaluates each,
     * and returns the best one found.
     */
    std::future<OptimizationResult> optimize(int n_iterations) override;
};

} // namespace evaluation
} // namespace agenkit

#endif // AGENKIT_EVALUATION_OPTIMIZER_HPP
