/**
 * @file prompt_optimizer.cpp
 * @brief Implementation of prompt optimization
 */

#include "agenkit/evaluation/prompt_optimizer.hpp"
#include <algorithm>
#include <random>
#include <sstream>
#include <stdexcept>
#include <regex>

namespace agenkit {
namespace evaluation {

// ============================================================================
// PromptOptimizationResult Methods
// ============================================================================

double PromptOptimizationResult::duration_seconds() const {
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time
    );
    return duration.count() / 1000.0;
}

// ============================================================================
// Constructor
// ============================================================================

PromptOptimizer::PromptOptimizer(
    std::string template_str,
    std::map<std::string, std::vector<std::string>> variations,
    ObjectiveFunction objective,
    bool maximize
)
    : template_(std::move(template_str))
    , variations_(std::move(variations))
    , objective_(std::move(objective))
    , maximize_(maximize)
{
    if (template_.empty()) {
        throw std::invalid_argument("template cannot be empty");
    }
    if (variations_.empty()) {
        throw std::invalid_argument("variations cannot be empty");
    }

    // Validate that all variations have at least one value
    for (const auto& [key, values] : variations_) {
        if (values.empty()) {
            throw std::invalid_argument("variation '" + key + "' has no values");
        }
    }
}

// ============================================================================
// Public Optimization Methods
// ============================================================================

std::future<PromptOptimizationResult> PromptOptimizer::optimize_grid() {
    return std::async(std::launch::async, [this]() {
        auto start_time = std::chrono::system_clock::now();

        // Generate all possible configurations
        auto configs = generate_all_configs();

        PromptOptimizationResult result;
        result.strategy = OptimizationStrategy::GRID;
        result.n_evaluated = static_cast<int>(configs.size());
        result.start_time = start_time;

        double best_score = maximize_ ? -std::numeric_limits<double>::infinity()
                                       : std::numeric_limits<double>::infinity();

        // Evaluate each configuration
        for (const auto& config : configs) {
            std::string prompt = fill_template(config);
            double score = evaluate_prompt(prompt);

            // Store in history
            std::map<std::string, double> scores{{"objective", score}};
            result.history.emplace_back(prompt, config, scores);

            // Update best if better
            bool is_better = maximize_ ? (score > best_score) : (score < best_score);
            if (is_better) {
                best_score = score;
                result.best_prompt = prompt;
                result.best_config = config;
                result.best_scores = scores;
            }
        }

        result.end_time = std::chrono::system_clock::now();
        return result;
    });
}

std::future<PromptOptimizationResult> PromptOptimizer::optimize_random(size_t n_samples) {
    return std::async(std::launch::async, [this, n_samples]() {
        auto start_time = std::chrono::system_clock::now();

        PromptOptimizationResult result;
        result.strategy = OptimizationStrategy::RANDOM;
        result.n_evaluated = static_cast<int>(n_samples);
        result.start_time = start_time;

        double best_score = maximize_ ? -std::numeric_limits<double>::infinity()
                                       : std::numeric_limits<double>::infinity();

        // Sample and evaluate random configurations
        for (size_t i = 0; i < n_samples; ++i) {
            auto config = sample_config();
            std::string prompt = fill_template(config);
            double score = evaluate_prompt(prompt);

            // Store in history
            std::map<std::string, double> scores{{"objective", score}};
            result.history.emplace_back(prompt, config, scores);

            // Update best if better
            bool is_better = maximize_ ? (score > best_score) : (score < best_score);
            if (is_better) {
                best_score = score;
                result.best_prompt = prompt;
                result.best_config = config;
                result.best_scores = scores;
            }
        }

        result.end_time = std::chrono::system_clock::now();
        return result;
    });
}

std::future<PromptOptimizationResult> PromptOptimizer::optimize_genetic(
    size_t population_size,
    size_t n_generations,
    double mutation_rate
) {
    return std::async(std::launch::async, [this, population_size, n_generations, mutation_rate]() {
        auto start_time = std::chrono::system_clock::now();

        PromptOptimizationResult result;
        result.strategy = OptimizationStrategy::GENETIC;
        result.start_time = start_time;

        // Initialize population with random configurations
        std::vector<std::map<std::string, std::string>> population;
        std::vector<double> fitness_scores;

        for (size_t i = 0; i < population_size; ++i) {
            population.push_back(sample_config());
        }

        // Evaluate initial population
        for (const auto& config : population) {
            std::string prompt = fill_template(config);
            double score = evaluate_prompt(prompt);
            fitness_scores.push_back(score);

            std::map<std::string, double> scores{{"objective", score}};
            result.history.emplace_back(prompt, config, scores);
        }

        // Evolution loop
        for (size_t gen = 0; gen < n_generations; ++gen) {
            // Selection: Tournament selection
            std::vector<std::map<std::string, std::string>> new_population;

            for (size_t i = 0; i < population_size; ++i) {
                // Select 2 random individuals for tournament
                static thread_local std::random_device rd;
                static thread_local std::mt19937 gen(rd());
                std::uniform_int_distribution<size_t> dist(0, population_size - 1);

                size_t idx1 = dist(gen);
                size_t idx2 = dist(gen);

                // Choose the fitter one
                size_t winner_idx = fitness_scores[idx1] > fitness_scores[idx2] ? idx1 : idx2;
                new_population.push_back(population[winner_idx]);
            }

            // Mutation
            for (auto& config : new_population) {
                config = mutate_config(config, mutation_rate);
            }

            // Replace population
            population = std::move(new_population);
            fitness_scores.clear();

            // Evaluate new population
            for (const auto& config : population) {
                std::string prompt = fill_template(config);
                double score = evaluate_prompt(prompt);
                fitness_scores.push_back(score);

                std::map<std::string, double> scores{{"objective", score}};
                result.history.emplace_back(prompt, config, scores);
            }
        }

        // Find best from all history
        result.n_evaluated = static_cast<int>(result.history.size());

        double best_score = maximize_ ? -std::numeric_limits<double>::infinity()
                                       : std::numeric_limits<double>::infinity();

        for (const auto& [prompt, config, scores] : result.history) {
            double score = scores.at("objective");
            bool is_better = maximize_ ? (score > best_score) : (score < best_score);

            if (is_better) {
                best_score = score;
                result.best_prompt = prompt;
                result.best_config = config;
                result.best_scores = scores;
            }
        }

        result.end_time = std::chrono::system_clock::now();
        return result;
    });
}

size_t PromptOptimizer::get_search_space_size() const {
    size_t total = 1;
    for (const auto& [key, values] : variations_) {
        total *= values.size();
    }
    return total;
}

// ============================================================================
// Private Helper Methods
// ============================================================================

std::string PromptOptimizer::fill_template(
    const std::map<std::string, std::string>& config
) const {
    std::string result = template_;

    // Replace each {variable} with its value
    for (const auto& [key, value] : config) {
        std::string placeholder = "{" + key + "}";

        size_t pos = 0;
        while ((pos = result.find(placeholder, pos)) != std::string::npos) {
            result.replace(pos, placeholder.length(), value);
            pos += value.length();
        }
    }

    return result;
}

std::vector<std::map<std::string, std::string>>
PromptOptimizer::generate_all_configs() const {
    std::vector<std::map<std::string, std::string>> configs;

    // Get keys and values in consistent order
    std::vector<std::string> keys;
    std::vector<std::vector<std::string>> value_lists;

    for (const auto& [key, values] : variations_) {
        keys.push_back(key);
        value_lists.push_back(values);
    }

    // Generate Cartesian product recursively
    std::function<void(size_t, std::map<std::string, std::string>)> generate;
    generate = [&](size_t depth, std::map<std::string, std::string> current) {
        if (depth == keys.size()) {
            configs.push_back(current);
            return;
        }

        const std::string& key = keys[depth];
        const auto& values = value_lists[depth];

        for (const auto& value : values) {
            auto next = current;
            next[key] = value;
            generate(depth + 1, next);
        }
    };

    generate(0, {});
    return configs;
}

std::map<std::string, std::string> PromptOptimizer::sample_config() const {
    static thread_local std::random_device rd;
    static thread_local std::mt19937 gen(rd());

    std::map<std::string, std::string> config;

    for (const auto& [key, values] : variations_) {
        std::uniform_int_distribution<size_t> dist(0, values.size() - 1);
        size_t idx = dist(gen);
        config[key] = values[idx];
    }

    return config;
}

double PromptOptimizer::evaluate_prompt(const std::string& prompt) const {
    return objective_(prompt);
}

std::map<std::string, std::string> PromptOptimizer::mutate_config(
    const std::map<std::string, std::string>& config,
    double mutation_rate
) const {
    static thread_local std::random_device rd;
    static thread_local std::mt19937 gen(rd());
    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);

    auto mutated = config;

    for (auto& [key, value] : mutated) {
        if (prob_dist(gen) < mutation_rate) {
            // Mutate: pick random value from variations
            const auto& values = variations_.at(key);
            std::uniform_int_distribution<size_t> idx_dist(0, values.size() - 1);
            mutated[key] = values[idx_dist(gen)];
        }
    }

    return mutated;
}

}  // namespace evaluation
}  // namespace agenkit
