/**
 * @file optimizer.cpp
 * @brief Implementation of optimization framework for agent configurations
 */

#include "agenkit/evaluation/optimizer.hpp"
#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>
#include <sstream>
#include <iomanip>

namespace agenkit {
namespace evaluation {

// Helper functions

static std::string time_point_to_iso(std::chrono::system_clock::time_point tp) {
    auto time_t = std::chrono::system_clock::to_time_t(tp);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S") << "Z";
    return ss.str();
}

static std::chrono::system_clock::time_point time_point_from_iso(const std::string& iso) {
    // Simplified: just return current time if parsing fails
    // In production, use a proper ISO 8601 parser
    std::tm tm = {};
    std::istringstream ss(iso);
    ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%S");
    if (ss.fail()) {
        return std::chrono::system_clock::now();
    }
    auto time_t = std::mktime(&tm);
    return std::chrono::system_clock::from_time_t(time_t);
}

static nlohmann::json any_to_json(const std::any& value) {
    // Try different types
    if (value.type() == typeid(double)) {
        return std::any_cast<double>(value);
    } else if (value.type() == typeid(int)) {
        return std::any_cast<int>(value);
    } else if (value.type() == typeid(std::string)) {
        return std::any_cast<std::string>(value);
    } else if (value.type() == typeid(bool)) {
        return std::any_cast<bool>(value);
    }
    // Default: null for unknown types
    return nullptr;
}

static std::any json_to_any(const nlohmann::json& j) {
    if (j.is_number_float()) {
        return j.get<double>();
    } else if (j.is_number_integer()) {
        return j.get<int>();
    } else if (j.is_string()) {
        return j.get<std::string>();
    } else if (j.is_boolean()) {
        return j.get<bool>();
    }
    return std::any();
}

// SearchSpace implementation

SearchSpace::SearchSpace() {
    // Initialize RNG with random seed
    std::random_device rd;
    rng_ = std::mt19937(rd());
}

void SearchSpace::add_continuous(const std::string& name, double low, double high) {
    if (low >= high) {
        throw std::invalid_argument("low must be less than high for continuous parameter");
    }
    parameters_[name] = ParameterSpec(low, high);
}

void SearchSpace::add_discrete(const std::string& name, const std::vector<double>& values) {
    if (values.empty()) {
        throw std::invalid_argument("values cannot be empty for discrete parameter");
    }
    std::vector<std::any> any_values;
    any_values.reserve(values.size());
    for (double val : values) {
        any_values.push_back(val);
    }
    parameters_[name] = ParameterSpec(any_values, ParameterType::Discrete);
}

void SearchSpace::add_integer(const std::string& name, int low, int high) {
    if (low >= high) {
        throw std::invalid_argument("low must be less than high for integer parameter");
    }
    auto spec = ParameterSpec();
    spec.type = ParameterType::Integer;
    spec.low = static_cast<double>(low);
    spec.high = static_cast<double>(high);
    parameters_[name] = spec;
}

void SearchSpace::add_categorical(const std::string& name, const std::vector<std::string>& values) {
    if (values.empty()) {
        throw std::invalid_argument("values cannot be empty for categorical parameter");
    }
    std::vector<std::any> any_values;
    any_values.reserve(values.size());
    for (const auto& val : values) {
        any_values.push_back(val);
    }
    parameters_[name] = ParameterSpec(any_values, ParameterType::Categorical);
}

std::map<std::string, std::any> SearchSpace::sample() {
    std::map<std::string, std::any> config;

    for (const auto& [name, spec] : parameters_) {
        switch (spec.type) {
            case ParameterType::Continuous: {
                std::uniform_real_distribution<double> dist(spec.low, spec.high);
                config[name] = dist(rng_);
                break;
            }
            case ParameterType::Integer: {
                std::uniform_int_distribution<int> dist(
                    static_cast<int>(spec.low),
                    static_cast<int>(spec.high)
                );
                config[name] = dist(rng_);
                break;
            }
            case ParameterType::Discrete:
            case ParameterType::Categorical: {
                std::uniform_int_distribution<size_t> dist(0, spec.values.size() - 1);
                size_t idx = dist(rng_);
                config[name] = spec.values[idx];
                break;
            }
        }
    }

    return config;
}

bool SearchSpace::validate(const std::map<std::string, std::any>& config) const {
    // Check that all required parameters are present
    for (const auto& [name, spec] : parameters_) {
        if (config.find(name) == config.end()) {
            return false;
        }

        const auto& value = config.at(name);

        switch (spec.type) {
            case ParameterType::Continuous: {
                if (value.type() != typeid(double)) {
                    return false;
                }
                double val = std::any_cast<double>(value);
                if (val < spec.low || val > spec.high) {
                    return false;
                }
                break;
            }
            case ParameterType::Integer: {
                if (value.type() != typeid(int)) {
                    return false;
                }
                int val = std::any_cast<int>(value);
                if (val < static_cast<int>(spec.low) || val > static_cast<int>(spec.high)) {
                    return false;
                }
                break;
            }
            case ParameterType::Discrete: {
                // Check if value is in the list
                bool found = false;
                for (const auto& allowed : spec.values) {
                    if (value.type() == allowed.type()) {
                        if (value.type() == typeid(double)) {
                            if (std::any_cast<double>(value) == std::any_cast<double>(allowed)) {
                                found = true;
                                break;
                            }
                        } else if (value.type() == typeid(int)) {
                            if (std::any_cast<int>(value) == std::any_cast<int>(allowed)) {
                                found = true;
                                break;
                            }
                        }
                    }
                }
                if (!found) {
                    return false;
                }
                break;
            }
            case ParameterType::Categorical: {
                if (value.type() != typeid(std::string)) {
                    return false;
                }
                // Check if value is in the list
                std::string val = std::any_cast<std::string>(value);
                bool found = false;
                for (const auto& allowed : spec.values) {
                    if (allowed.type() == typeid(std::string)) {
                        if (std::any_cast<std::string>(allowed) == val) {
                            found = true;
                            break;
                        }
                    }
                }
                if (!found) {
                    return false;
                }
                break;
            }
        }
    }

    // Check that no unknown parameters are present
    for (const auto& [name, value] : config) {
        if (parameters_.find(name) == parameters_.end()) {
            return false;
        }
    }

    return true;
}

// OptimizationStep implementation

nlohmann::json OptimizationStep::to_json() const {
    nlohmann::json j;

    nlohmann::json config_json = nlohmann::json::object();
    for (const auto& [key, value] : config) {
        config_json[key] = any_to_json(value);
    }
    j["config"] = config_json;
    j["score"] = score;

    return j;
}

// OptimizationResult implementation

double OptimizationResult::duration_seconds() const {
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time
    );
    return static_cast<double>(duration.count()) / 1000.0;
}

double OptimizationResult::get_improvement() const {
    if (history.empty()) {
        return 0.0;
    }

    double initial_score = history.front().score;
    if (std::abs(initial_score) < 1e-10) {
        return 0.0;
    }

    return ((best_score - initial_score) / std::abs(initial_score)) * 100.0;
}

nlohmann::json OptimizationResult::to_json() const {
    nlohmann::json j;

    // Best config
    nlohmann::json best_config_json = nlohmann::json::object();
    for (const auto& [key, value] : best_config) {
        best_config_json[key] = any_to_json(value);
    }
    j["best_config"] = best_config_json;
    j["best_score"] = best_score;

    // History
    nlohmann::json history_json = nlohmann::json::array();
    for (const auto& step : history) {
        history_json.push_back(step.to_json());
    }
    j["history"] = history_json;

    // Metadata
    j["n_iterations"] = n_iterations;
    j["start_time"] = time_point_to_iso(start_time);
    j["end_time"] = time_point_to_iso(end_time);
    j["duration_seconds"] = duration_seconds();
    j["improvement_percent"] = get_improvement();
    j["metadata"] = metadata;

    return j;
}

OptimizationResult OptimizationResult::from_json(const nlohmann::json& j) {
    OptimizationResult result;

    // Best config
    if (j.contains("best_config") && j["best_config"].is_object()) {
        for (const auto& [key, value] : j["best_config"].items()) {
            result.best_config[key] = json_to_any(value);
        }
    }

    result.best_score = j.value("best_score", 0.0);
    result.n_iterations = j.value("n_iterations", 0);

    // History
    if (j.contains("history") && j["history"].is_array()) {
        for (const auto& step_json : j["history"]) {
            OptimizationStep step;
            if (step_json.contains("config") && step_json["config"].is_object()) {
                for (const auto& [key, value] : step_json["config"].items()) {
                    step.config[key] = json_to_any(value);
                }
            }
            step.score = step_json.value("score", 0.0);
            result.history.push_back(step);
        }
    }

    // Timestamps
    if (j.contains("start_time") && j["start_time"].is_string()) {
        result.start_time = time_point_from_iso(j["start_time"].get<std::string>());
    } else {
        result.start_time = std::chrono::system_clock::now();
    }

    if (j.contains("end_time") && j["end_time"].is_string()) {
        result.end_time = time_point_from_iso(j["end_time"].get<std::string>());
    } else {
        result.end_time = std::chrono::system_clock::now();
    }

    // Metadata
    if (j.contains("metadata")) {
        result.metadata = j["metadata"];
    }

    return result;
}

// Optimizer implementation

Optimizer::Optimizer(
    ObjectiveFunc objective,
    std::shared_ptr<SearchSpace> search_space,
    bool maximize
)
    : objective_(std::move(objective))
    , search_space_(std::move(search_space))
    , maximize_(maximize)
{
}

double Optimizer::evaluate_config(const std::map<std::string, std::any>& config) {
    // Call objective function
    double score = objective_(config);

    // Adjust for maximize vs minimize
    // If minimizing, negate the score so "best" is always maximum
    double adjusted_score = maximize_ ? score : -score;

    // Record in history
    OptimizationStep step;
    step.config = config;
    step.score = adjusted_score;
    history_.push_back(step);

    return adjusted_score;
}

// RandomSearchOptimizer implementation

RandomSearchOptimizer::RandomSearchOptimizer(
    ObjectiveFunc objective,
    std::shared_ptr<SearchSpace> search_space,
    bool maximize
)
    : Optimizer(std::move(objective), std::move(search_space), maximize)
{
}

std::future<OptimizationResult> RandomSearchOptimizer::optimize(int n_iterations) {
    return std::async(std::launch::async, [this, n_iterations]() {
        OptimizationResult result;
        result.start_time = std::chrono::system_clock::now();
        result.n_iterations = n_iterations;

        // Clear history from any previous runs
        history_.clear();

        // Track best configuration
        double best_score = -std::numeric_limits<double>::infinity();
        std::map<std::string, std::any> best_config;

        // Random search: sample and evaluate n_iterations configurations
        for (int i = 0; i < n_iterations; ++i) {
            // Sample random configuration
            auto config = search_space_->sample();

            // Evaluate configuration
            double score = evaluate_config(config);

            // Update best if this is better
            if (score > best_score) {
                best_score = score;
                best_config = config;
            }
        }

        result.end_time = std::chrono::system_clock::now();
        result.best_config = best_config;
        result.best_score = best_score;
        result.history = history_;

        // Add metadata
        result.metadata["algorithm"] = "random_search";
        result.metadata["maximize"] = maximize_;

        return result;
    });
}

} // namespace evaluation
} // namespace agenkit
