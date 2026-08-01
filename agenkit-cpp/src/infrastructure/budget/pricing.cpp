#include "agenkit/infrastructure/budget/pricing.hpp"
#include <algorithm>
#include <mutex>
#include <shared_mutex>

namespace agenkit {
namespace infrastructure {
namespace budget {

ModelPricing::ModelPricing() {
    initialize_default_pricing();
}

void ModelPricing::initialize_default_pricing() {
    // OpenAI models (November 2025 pricing)
    pricing_data_["gpt-4o"] = PricingInfo{
        "gpt-4o", "openai", 2.50, 10.00, std::nullopt
    };
    pricing_data_["gpt-4-turbo"] = PricingInfo{
        "gpt-4-turbo", "openai", 10.00, 30.00, std::nullopt
    };
    pricing_data_["gpt-3.5-turbo"] = PricingInfo{
        "gpt-3.5-turbo", "openai", 0.50, 1.50, std::nullopt
    };
    pricing_data_["o3"] = PricingInfo{
        "o3", "openai", 10.00, 40.00, std::nullopt
    };
    pricing_data_["o3-mini"] = PricingInfo{
        "o3-mini", "openai", 1.10, 4.40, std::nullopt
    };

    // Anthropic models (November 2025 pricing)
    pricing_data_["claude-opus-4"] = PricingInfo{
        "claude-opus-4", "anthropic", 15.00, 75.00, std::nullopt
    };
    pricing_data_["claude-sonnet-4"] = PricingInfo{
        "claude-sonnet-4", "anthropic", 3.00, 15.00, std::nullopt
    };
    pricing_data_["claude-sonnet-4.5"] = PricingInfo{
        "claude-sonnet-4.5", "anthropic", 3.00, 15.00, std::nullopt
    };
    pricing_data_["claude-haiku-3"] = PricingInfo{
        "claude-haiku-3", "anthropic", 0.25, 1.25, std::nullopt
    };
    pricing_data_["claude-haiku-4"] = PricingInfo{
        "claude-haiku-4", "anthropic", 0.80, 4.00, std::nullopt
    };

    // Google models (November 2025 pricing)
    pricing_data_["gemini-2.0-flash-exp"] = PricingInfo{
        "gemini-2.0-flash-exp", "google", 0.00, 0.00, std::nullopt
    };
    pricing_data_["gemini-pro"] = PricingInfo{
        "gemini-pro", "google", 0.50, 1.50, std::nullopt
    };

    // Default fallback
    pricing_data_["default"] = PricingInfo{
        "default", "unknown", 0.01, 0.01, std::nullopt
    };
}

double ModelPricing::calculate(
    const std::string& model,
    int tokens,
    const std::string& direction
) const {
    std::shared_lock lock(mutex_);

    auto it = pricing_data_.find(model);
    if (it == pricing_data_.end()) {
        it = pricing_data_.find("default");
    }

    const auto& pricing = it->second;
    double cost_per_million = (direction == "input")
        ? pricing.input_cost_per_million
        : pricing.output_cost_per_million;

    return (static_cast<double>(tokens) / 1000000.0) * cost_per_million;
}

PricingInfo ModelPricing::get_model_pricing(const std::string& model) const {
    std::shared_lock lock(mutex_);

    auto it = pricing_data_.find(model);
    if (it != pricing_data_.end()) {
        return it->second;
    }

    // Return default pricing with the requested model name
    auto default_pricing = pricing_data_.at("default");
    default_pricing.model = model;
    return default_pricing;
}

std::vector<std::string> ModelPricing::list_models() const {
    std::shared_lock lock(mutex_);

    std::vector<std::string> models;
    models.reserve(pricing_data_.size());

    for (const auto& pair : pricing_data_) {
        if (pair.first != "default") {
            models.push_back(pair.first);
        }
    }

    std::sort(models.begin(), models.end());
    return models;
}

void ModelPricing::update_pricing(
    const std::string& model,
    double input_cost,
    double output_cost
) {
    std::unique_lock lock(mutex_);

    pricing_data_[model] = PricingInfo{
        model, "custom", input_cost, output_cost, std::nullopt
    };
}

double ModelPricing::estimate_conversation_cost(
    const std::string& model,
    int turns,
    int avg_input_tokens,
    int avg_output_tokens
) const {
    double input_cost = calculate(model, turns * avg_input_tokens, "input");
    double output_cost = calculate(model, turns * avg_output_tokens, "output");
    return input_cost + output_cost;
}

std::map<std::string, double> ModelPricing::compare_models(
    const std::vector<std::string>& models,
    int input_tokens,
    int output_tokens
) const {
    std::map<std::string, double> comparison;

    for (const auto& model : models) {
        double input_cost = calculate(model, input_tokens, "input");
        double output_cost = calculate(model, output_tokens, "output");
        comparison[model] = input_cost + output_cost;
    }

    return comparison;
}

std::vector<ModelComparison> ModelPricing::compare_models_detailed(
    const std::vector<std::string>& models,
    int input_tokens,
    int output_tokens
) const {
    auto costs = compare_models(models, input_tokens, output_tokens);

    // Find cheapest
    double min_cost = std::numeric_limits<double>::max();
    for (const auto& pair : costs) {
        min_cost = std::min(min_cost, pair.second);
    }

    // Build comparison results
    std::vector<ModelComparison> results;
    for (const auto& pair : costs) {
        results.push_back(ModelComparison{
            pair.first,
            pair.second,
            pair.second - min_cost,
            pair.second / min_cost
        });
    }

    // Sort by cost (ascending)
    std::sort(results.begin(), results.end(),
        [](const ModelComparison& a, const ModelComparison& b) {
            return a.estimated_cost < b.estimated_cost;
        });

    return results;
}

} // namespace budget
} // namespace infrastructure
} // namespace agenkit
