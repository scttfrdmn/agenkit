/**
 * @file bayesian_optimizer.hpp
 * @brief Bayesian optimization for hyperparameter tuning
 *
 * This module implements Bayesian optimization using a simplified surrogate
 * model based on local statistics rather than full Gaussian Process regression.
 * This approach avoids heavy dependencies while still providing effective
 * optimization through intelligent exploration-exploitation balance.
 *
 * Key Features:
 * - Three acquisition functions: Expected Improvement, Upper Confidence Bound,
 *   Probability of Improvement
 * - Simplified surrogate model using local neighborhood statistics
 * - Configuration similarity metric for finding related configs
 * - No external ML library dependencies
 *
 * Algorithm:
 * 1. Sample n_initial random configurations (exploration phase)
 * 2. Build surrogate model from observations
 * 3. Use acquisition function to propose next configuration
 * 4. Evaluate and update model
 * 5. Repeat until n_iterations reached
 *
 * The simplified surrogate model:
 * - For each candidate, find similar configs in history
 * - Compute mean and std of scores from similar configs
 * - Use these statistics in acquisition functions
 * - Falls back to global statistics if no similar configs found
 *
 * @example
 * ```cpp
 * // Define search space
 * auto space = std::make_shared<SearchSpace>();
 * space->add_continuous("temperature", 0.0, 1.0);
 * space->add_continuous("top_p", 0.0, 1.0);
 *
 * // Define objective function
 * auto objective = [](const std::map<std::string, std::any>& config) {
 *     return evaluate_agent_with_config(config);
 * };
 *
 * // Create optimizer
 * BayesianOptimizer optimizer(
 *     objective,
 *     space,
 *     true,  // maximize
 *     AcquisitionFunction::EI,
 *     5,     // n_initial
 *     0.01,  // xi
 *     2.576  // kappa
 * );
 *
 * // Run optimization
 * auto result = optimizer.optimize(50).get();
 * std::cout << "Best score: " << result.best_score << std::endl;
 * ```
 */

#pragma once

#include "agenkit/evaluation/optimizer.hpp"
#include <cmath>
#include <algorithm>
#include <limits>

namespace agenkit {
namespace evaluation {

/**
 * @brief Acquisition function types for Bayesian optimization
 *
 * Acquisition functions balance exploration (trying new regions) and
 * exploitation (refining known good regions).
 */
enum class AcquisitionFunction {
    /**
     * @brief Expected Improvement (EI)
     *
     * Measures the expected amount of improvement over the current best.
     * Good balance of exploration and exploitation.
     * Best for: General purpose optimization
     */
    EI,

    /**
     * @brief Upper Confidence Bound (UCB)
     *
     * Optimistic estimate of the objective value.
     * More exploratory than EI.
     * Best for: Large search spaces, early exploration
     */
    UCB,

    /**
     * @brief Probability of Improvement (PI)
     *
     * Probability that a point improves over the current best.
     * More exploitative than EI.
     * Best for: Fine-tuning known good regions
     */
    PI
};

/**
 * @brief Bayesian optimizer using simplified surrogate model
 *
 * Implements Bayesian optimization without requiring full Gaussian Process
 * regression. Uses local statistics from configuration history to estimate
 * performance and guide search via acquisition functions.
 *
 * Key Differences from Full GP:
 * - No kernel matrix computation (O(n²) → O(n))
 * - No matrix inversion required
 * - Simpler uncertainty estimates
 * - Still effective for moderate-dimensional problems
 *
 * @example
 * ```cpp
 * // Optimize agent hyperparameters
 * auto objective = [&test_cases](const auto& config) {
 *     auto agent = create_agent(config);
 *     return evaluate_agent(agent, test_cases);
 * };
 *
 * BayesianOptimizer optimizer(objective, search_space, true);
 * auto result = optimizer.optimize(100).get();
 *
 * // Use best configuration
 * auto best_agent = create_agent(result.best_config);
 * ```
 */
class BayesianOptimizer {
public:
    /**
     * @brief Construct Bayesian optimizer
     *
     * @param objective Function that evaluates a configuration and returns score
     * @param search_space Parameter search space
     * @param maximize Whether to maximize (true) or minimize (false) objective
     * @param acquisition Acquisition function type (default: EI)
     * @param n_initial Number of random initial samples (default: 5)
     * @param xi Exploration parameter for EI/PI (default: 0.01)
     * @param kappa Exploration parameter for UCB (default: 2.576 for 99% confidence)
     */
    explicit BayesianOptimizer(
        std::function<double(const std::map<std::string, std::any>&)> objective,
        std::shared_ptr<SearchSpace> search_space,
        bool maximize = true,
        AcquisitionFunction acquisition = AcquisitionFunction::EI,
        size_t n_initial = 5,
        double xi = 0.01,
        double kappa = 2.576
    );

    /**
     * @brief Run Bayesian optimization
     *
     * Performs n_iterations evaluations:
     * - First n_initial: random exploration
     * - Remaining: guided by acquisition function
     *
     * @param n_iterations Total number of evaluations
     * @return Future with optimization result containing best config and history
     */
    std::future<OptimizationResult> optimize(size_t n_iterations);

    /**
     * @brief Get current best configuration
     */
    std::map<std::string, std::any> get_best_config() const;

    /**
     * @brief Get current best score
     */
    double get_best_score() const;

    /**
     * @brief Get optimization history
     */
    std::vector<OptimizationStep> get_history() const;

private:
    /**
     * @brief Add observation to history and update best
     */
    void add_observation(const std::map<std::string, std::any>& config, double score);

    /**
     * @brief Propose next configuration using acquisition function
     *
     * Generates n_candidates random samples and selects the one with
     * highest acquisition value.
     *
     * @param n_candidates Number of candidates to evaluate (default: 1000)
     * @return Next configuration to evaluate
     */
    std::map<std::string, std::any> propose_next(size_t n_candidates = 1000);

    /**
     * @brief Evaluate acquisition function for a configuration
     *
     * Estimates performance statistics and computes acquisition value
     * based on selected acquisition function.
     *
     * @param config Configuration to evaluate
     * @return Acquisition function value (higher is better)
     */
    double evaluate_acquisition(const std::map<std::string, std::any>& config);

    /**
     * @brief Estimate mean and std of performance for a configuration
     *
     * Simplified surrogate model:
     * 1. Find configurations in history similar to candidate
     * 2. Compute mean and std of their scores
     * 3. If no similar configs, use global statistics
     *
     * @param config Configuration to estimate
     * @return Pair of (mean, std_dev) estimates
     */
    std::pair<double, double> estimate_performance(
        const std::map<std::string, std::any>& config
    ) const;

    /**
     * @brief Compute similarity between two configurations
     *
     * Returns value in [0, 1] where:
     * - 1.0 = identical configurations
     * - 0.0 = maximally different
     *
     * For continuous/integer params: normalized distance
     * For categorical/discrete: exact match or not
     *
     * @param config1 First configuration
     * @param config2 Second configuration
     * @return Similarity score in [0, 1]
     */
    double config_similarity(
        const std::map<std::string, std::any>& config1,
        const std::map<std::string, std::any>& config2
    ) const;

    /**
     * @brief Expected Improvement acquisition function
     *
     * EI(x) = (μ(x) - f(x*) - ξ) * Φ(Z) + σ(x) * φ(Z)
     * where Z = (μ(x) - f(x*) - ξ) / σ(x)
     *
     * @param mu Predicted mean
     * @param sigma Predicted std deviation
     * @return Expected improvement value
     */
    double expected_improvement(double mu, double sigma) const;

    /**
     * @brief Upper Confidence Bound acquisition function
     *
     * UCB(x) = μ(x) + κ * σ(x)
     *
     * @param mu Predicted mean
     * @param sigma Predicted std deviation
     * @return UCB value
     */
    double upper_confidence_bound(double mu, double sigma) const;

    /**
     * @brief Probability of Improvement acquisition function
     *
     * PI(x) = Φ((μ(x) - f(x*) - ξ) / σ(x))
     *
     * @param mu Predicted mean
     * @param sigma Predicted std deviation
     * @return Probability of improvement
     */
    double probability_of_improvement(double mu, double sigma) const;

    /**
     * @brief Standard normal cumulative distribution function
     */
    static double norm_cdf(double x);

    /**
     * @brief Standard normal probability density function
     */
    static double norm_pdf(double x);

    /**
     * @brief Calculate mean of vector
     */
    static double calculate_mean(const std::vector<double>& values);

    /**
     * @brief Calculate standard deviation of vector
     */
    static double calculate_stddev(const std::vector<double>& values, double mean);

    // Member variables
    std::function<double(const std::map<std::string, std::any>&)> objective_;
    std::shared_ptr<SearchSpace> search_space_;
    bool maximize_;
    AcquisitionFunction acquisition_;
    size_t n_initial_;
    double xi_;       ///< Exploration parameter for EI/PI
    double kappa_;    ///< Exploration parameter for UCB

    std::vector<OptimizationStep> history_;
    std::map<std::string, std::any> best_config_;
    double best_score_;
};

}  // namespace evaluation
}  // namespace agenkit
