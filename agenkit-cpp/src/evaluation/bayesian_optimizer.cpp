/**
 * @file bayesian_optimizer.cpp
 * @brief Implementation of Bayesian optimization
 */

#include "agenkit/evaluation/bayesian_optimizer.hpp"
#include "agenkit/infrastructure/thread_pool.hpp"
#include <algorithm>
#include <numeric>
#include <cmath>
#include <limits>

namespace agenkit {
namespace evaluation {

// ============================================================================
// Constructor
// ============================================================================

BayesianOptimizer::BayesianOptimizer(
    std::function<double(const std::map<std::string, std::any>&)> objective,
    std::shared_ptr<SearchSpace> search_space,
    bool maximize,
    AcquisitionFunction acquisition,
    size_t n_initial,
    double xi,
    double kappa
)
    : objective_(objective)
    , search_space_(search_space)
    , maximize_(maximize)
    , acquisition_(acquisition)
    , n_initial_(n_initial)
    , xi_(xi)
    , kappa_(kappa)
    , best_score_(maximize ? -std::numeric_limits<double>::infinity()
                           : std::numeric_limits<double>::infinity())
{}

// ============================================================================
// Main Optimization
// ============================================================================

std::future<OptimizationResult> BayesianOptimizer::optimize(size_t n_iterations) {
    return infrastructure::global_thread_pool().enqueue([this, n_iterations]() {
        auto start_time = std::chrono::system_clock::now();
        history_.clear();

        // Phase 1: Random initialization
        size_t n_random = std::min(n_initial_, n_iterations);
        for (size_t i = 0; i < n_random; ++i) {
            auto config = search_space_->sample();
            double score = objective_(config);
            add_observation(config, score);
        }

        // Phase 2: Bayesian optimization with acquisition function
        for (size_t i = n_random; i < n_iterations; ++i) {
            auto next_config = propose_next();
            double score = objective_(next_config);
            add_observation(next_config, score);
        }

        auto end_time = std::chrono::system_clock::now();

        // Create result
        OptimizationResult result;
        result.best_config = best_config_;
        result.best_score = best_score_;
        result.history = history_;
        result.n_iterations = static_cast<int>(n_iterations);
        result.start_time = start_time;
        result.end_time = end_time;

        // Add metadata
        result.metadata["algorithm"] = std::string("bayesian_optimization");
        result.metadata["n_initial"] = static_cast<int>(n_initial_);
        result.metadata["maximize"] = maximize_;
        result.metadata["xi"] = xi_;
        result.metadata["kappa"] = kappa_;

        std::string acq_str;
        switch (acquisition_) {
            case AcquisitionFunction::EI:
                acq_str = "expected_improvement";
                break;
            case AcquisitionFunction::UCB:
                acq_str = "upper_confidence_bound";
                break;
            case AcquisitionFunction::PI:
                acq_str = "probability_of_improvement";
                break;
        }
        result.metadata["acquisition"] = acq_str;

        return result;
    });
}

// ============================================================================
// Getters
// ============================================================================

std::map<std::string, std::any> BayesianOptimizer::get_best_config() const {
    return best_config_;
}

double BayesianOptimizer::get_best_score() const {
    return best_score_;
}

std::vector<OptimizationStep> BayesianOptimizer::get_history() const {
    return history_;
}

// ============================================================================
// Internal Methods
// ============================================================================

void BayesianOptimizer::add_observation(
    const std::map<std::string, std::any>& config,
    double score
) {
    OptimizationStep step;
    step.config = config;
    step.score = score;
    history_.push_back(step);

    // Update best
    bool is_better = maximize_ ? (score > best_score_) : (score < best_score_);
    if (history_.size() == 1 || is_better) {
        best_score_ = score;
        best_config_ = config;
    }
}

std::map<std::string, std::any> BayesianOptimizer::propose_next(size_t n_candidates) {
    std::map<std::string, std::any> best_candidate = search_space_->sample();
    double best_acq_value = -std::numeric_limits<double>::infinity();

    // Generate and evaluate random candidates
    for (size_t i = 0; i < n_candidates; ++i) {
        auto candidate = search_space_->sample();
        double acq_value = evaluate_acquisition(candidate);

        if (acq_value > best_acq_value) {
            best_acq_value = acq_value;
            best_candidate = candidate;
        }
    }

    return best_candidate;
}

double BayesianOptimizer::evaluate_acquisition(
    const std::map<std::string, std::any>& config
) {
    // Estimate performance using local statistics
    auto [mu, sigma] = estimate_performance(config);

    // Compute acquisition function
    switch (acquisition_) {
        case AcquisitionFunction::EI:
            return expected_improvement(mu, sigma);
        case AcquisitionFunction::UCB:
            return upper_confidence_bound(mu, sigma);
        case AcquisitionFunction::PI:
            return probability_of_improvement(mu, sigma);
        default:
            return mu;
    }
}

std::pair<double, double> BayesianOptimizer::estimate_performance(
    const std::map<std::string, std::any>& config
) const {
    if (history_.empty()) {
        return {0.0, 1.0};
    }

    // Find similar configurations in history
    std::vector<double> scores;
    constexpr double similarity_threshold = 0.5;

    for (const auto& step : history_) {
        double similarity = config_similarity(config, step.config);
        if (similarity > similarity_threshold) {
            scores.push_back(step.score);
        }
    }

    // If no similar configs, use global statistics
    if (scores.empty()) {
        for (const auto& step : history_) {
            scores.push_back(step.score);
        }
    }

    // Compute mean and std
    double mu = calculate_mean(scores);
    double sigma = calculate_stddev(scores, mu);

    // Ensure non-zero sigma for numerical stability
    if (sigma < 1e-6) {
        sigma = 0.1;
    }

    return {mu, sigma};
}

double BayesianOptimizer::config_similarity(
    const std::map<std::string, std::any>& config1,
    const std::map<std::string, std::any>& config2
) const {
    if (config1.empty() || config2.empty()) {
        return 0.0;
    }

    double similarity_sum = 0.0;
    int total_count = 0;

    // Get parameter specs from search space
    const auto& parameters = search_space_->parameters();

    for (const auto& [name, spec] : parameters) {
        // Check if both configs have this parameter
        auto it1 = config1.find(name);
        auto it2 = config2.find(name);
        if (it1 == config1.end() || it2 == config2.end()) {
            continue;
        }

        total_count++;

        switch (spec.type) {
            case ParameterType::Continuous:
            case ParameterType::Integer: {
                // Normalized distance for continuous/integer parameters
                double val1 = 0.0, val2 = 0.0;

                // Extract double values
                if (it1->second.type() == typeid(double)) {
                    val1 = std::any_cast<double>(it1->second);
                } else if (it1->second.type() == typeid(int)) {
                    val1 = static_cast<double>(std::any_cast<int>(it1->second));
                }

                if (it2->second.type() == typeid(double)) {
                    val2 = std::any_cast<double>(it2->second);
                } else if (it2->second.type() == typeid(int)) {
                    val2 = static_cast<double>(std::any_cast<int>(it2->second));
                }

                double range = spec.high - spec.low;
                if (range > 0) {
                    double dist = std::abs(val1 - val2) / range;
                    similarity_sum += 1.0 - dist;  // Similarity = 1 - normalized distance
                } else {
                    // Zero range - either identical or not
                    if (val1 == val2) {
                        similarity_sum += 1.0;
                    }
                }
                break;
            }

            case ParameterType::Discrete:
            case ParameterType::Categorical: {
                // Exact match for discrete/categorical
                // Compare values (this is simplified - proper comparison would check actual values)
                bool same = false;

                // Try string comparison
                if (it1->second.type() == typeid(std::string) &&
                    it2->second.type() == typeid(std::string)) {
                    same = std::any_cast<std::string>(it1->second) ==
                           std::any_cast<std::string>(it2->second);
                }
                // Try double comparison
                else if (it1->second.type() == typeid(double) &&
                         it2->second.type() == typeid(double)) {
                    same = std::any_cast<double>(it1->second) ==
                           std::any_cast<double>(it2->second);
                }
                // Try int comparison
                else if (it1->second.type() == typeid(int) &&
                         it2->second.type() == typeid(int)) {
                    same = std::any_cast<int>(it1->second) ==
                           std::any_cast<int>(it2->second);
                }

                if (same) {
                    similarity_sum += 1.0;
                }
                break;
            }
        }
    }

    if (total_count == 0) {
        return 0.0;
    }

    return similarity_sum / static_cast<double>(total_count);
}

// ============================================================================
// Acquisition Functions
// ============================================================================

double BayesianOptimizer::expected_improvement(double mu, double sigma) const {
    if (history_.empty() || sigma == 0.0) {
        return 0.0;
    }

    double improvement = mu - best_score_ - xi_;
    double z = improvement / sigma;

    return improvement * norm_cdf(z) + sigma * norm_pdf(z);
}

double BayesianOptimizer::upper_confidence_bound(double mu, double sigma) const {
    return mu + kappa_ * sigma;
}

double BayesianOptimizer::probability_of_improvement(double mu, double sigma) const {
    if (history_.empty() || sigma == 0.0) {
        return 0.0;
    }

    double z = (mu - best_score_ - xi_) / sigma;
    return norm_cdf(z);
}

// ============================================================================
// Statistical Functions
// ============================================================================

double BayesianOptimizer::norm_cdf(double x) {
    // Standard normal cumulative distribution function
    // Using error function: CDF(x) = 0.5 * (1 + erf(x / sqrt(2)))
    return 0.5 * (1.0 + std::erf(x / std::sqrt(2.0)));
}

double BayesianOptimizer::norm_pdf(double x) {
    // Standard normal probability density function
    // PDF(x) = (1 / sqrt(2π)) * exp(-x² / 2)
    constexpr double inv_sqrt_2pi = 0.3989422804014327;  // 1 / sqrt(2π)
    return inv_sqrt_2pi * std::exp(-0.5 * x * x);
}

double BayesianOptimizer::calculate_mean(const std::vector<double>& values) {
    if (values.empty()) {
        return 0.0;
    }

    double sum = std::accumulate(values.begin(), values.end(), 0.0);
    return sum / static_cast<double>(values.size());
}

double BayesianOptimizer::calculate_stddev(
    const std::vector<double>& values,
    double mean
) {
    if (values.size() <= 1) {
        return 1.0;
    }

    double variance = 0.0;
    for (double value : values) {
        double diff = value - mean;
        variance += diff * diff;
    }

    variance /= static_cast<double>(values.size() - 1);
    return std::sqrt(variance);
}

}  // namespace evaluation
}  // namespace agenkit
