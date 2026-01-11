#pragma once

#include "agenkit/infrastructure/budget/models.hpp"
#include <map>
#include <memory>
#include <shared_mutex>
#include <string>
#include <vector>

namespace agenkit {
namespace infrastructure {
namespace budget {

/// Model pricing database (November 2025 rates)
///
/// Centralized pricing information for all major LLM providers.
/// Thread-safe for concurrent access.
class ModelPricing {
public:
    ModelPricing();

    /// Calculate cost for tokens
    ///
    /// @param model Model name
    /// @param tokens Token count
    /// @param direction "input" or "output"
    /// @return Cost in USD
    double calculate(
        const std::string& model,
        int tokens,
        const std::string& direction
    ) const;

    /// Get pricing info for model
    ///
    /// @param model Model name
    /// @return Pricing info (uses default if not found)
    PricingInfo get_model_pricing(const std::string& model) const;

    /// List all supported models
    ///
    /// @return Vector of model names
    std::vector<std::string> list_models() const;

    /// Update pricing (for testing/custom deployments)
    ///
    /// @param model Model name
    /// @param input_cost Input cost per million tokens
    /// @param output_cost Output cost per million tokens
    void update_pricing(
        const std::string& model,
        double input_cost,
        double output_cost
    );

    /// Estimate conversation cost
    ///
    /// @param model Model name
    /// @param turns Number of conversation turns
    /// @param avg_input_tokens Average input tokens per turn
    /// @param avg_output_tokens Average output tokens per turn
    /// @return Estimated total cost in USD
    double estimate_conversation_cost(
        const std::string& model,
        int turns,
        int avg_input_tokens,
        int avg_output_tokens
    ) const;

    /// Compare models by cost
    ///
    /// @param models Vector of model names to compare
    /// @param input_tokens Input token count
    /// @param output_tokens Output token count
    /// @return Map of model -> estimated cost
    std::map<std::string, double> compare_models(
        const std::vector<std::string>& models,
        int input_tokens,
        int output_tokens
    ) const;

    /// Get detailed cost comparison
    ///
    /// @param models Vector of model names to compare
    /// @param input_tokens Input token count
    /// @param output_tokens Output token count
    /// @return Vector of ModelComparison sorted by cost
    std::vector<ModelComparison> compare_models_detailed(
        const std::vector<std::string>& models,
        int input_tokens,
        int output_tokens
    ) const;

private:
    mutable std::shared_mutex mutex_;
    std::map<std::string, PricingInfo> pricing_data_;

    void initialize_default_pricing();
};

} // namespace budget
} // namespace infrastructure
} // namespace agenkit
