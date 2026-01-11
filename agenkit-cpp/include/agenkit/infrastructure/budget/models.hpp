#pragma once

#include <chrono>
#include <map>
#include <optional>
#include <string>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace infrastructure {
namespace budget {

/// Cost record - Immutable record of single API call cost
///
/// Tracks token usage and calculated costs for one LLM API call.
/// All costs in USD.
struct CostRecord {
    /// Unique record identifier (UUID v4)
    std::string record_id;

    /// Session identifier (groups related interactions)
    std::string session_id;

    /// Agent name/identifier
    std::string agent_name;

    /// Model name (e.g., "claude-sonnet-4", "gpt-4")
    std::string model;

    /// Timestamp (UTC)
    std::chrono::system_clock::time_point timestamp;

    /// Input/prompt tokens
    int input_tokens;

    /// Output/completion tokens
    int output_tokens;

    /// Thinking tokens (for o3, Claude extended thinking)
    int thinking_tokens;

    /// Input cost in USD
    double input_cost;

    /// Output cost in USD
    double output_cost;

    /// Thinking cost in USD
    double thinking_cost;

    /// Total cost in USD (input + output + thinking)
    double total_cost;

    /// Optional metadata (message_id, endpoint, etc.)
    std::optional<nlohmann::json> metadata;

    /// Get total token count
    int total_tokens() const {
        return input_tokens + output_tokens + thinking_tokens;
    }

    /// Serialize to JSON
    nlohmann::json to_json() const;

    /// Deserialize from JSON
    static CostRecord from_json(const nlohmann::json& j);

    /// Generate UUID v4
    static std::string generate_uuid();
};

/// Model pricing information
struct PricingInfo {
    /// Model name
    std::string model;

    /// Provider name (openai, anthropic, google)
    std::string provider;

    /// Input cost per million tokens (USD)
    double input_cost_per_million;

    /// Output cost per million tokens (USD)
    double output_cost_per_million;

    /// Optional metadata
    std::optional<nlohmann::json> metadata;
};

/// Usage statistics
struct UsageStats {
    /// Total cost in USD
    double total_cost;

    /// Total number of requests
    int total_requests;

    /// Total input tokens
    int total_input_tokens;

    /// Total output tokens
    int total_output_tokens;

    /// Total thinking tokens
    int total_thinking_tokens;

    /// Total tokens (input + output + thinking)
    int total_tokens;

    /// Average cost per request
    double avg_cost_per_request;

    /// Average tokens per request
    double avg_tokens_per_request;

    /// Cost breakdown by model (optional)
    std::optional<std::map<std::string, double>> by_model;

    /// Serialize to JSON
    nlohmann::json to_json() const;
};

/// Model cost comparison result
struct ModelComparison {
    std::string model;
    double estimated_cost;
    double cost_difference;  // relative to cheapest
    double cost_ratio;       // relative to cheapest (1.0 = cheapest)
};

/// Budget configuration
struct BudgetConfig {
    /// Per-session budget in USD (optional)
    std::optional<double> session_budget;

    /// Per-agent budget in USD (optional)
    std::optional<double> agent_budget;

    /// Global budget in USD (optional)
    std::optional<double> global_budget;

    /// Action when budget exceeded: "error", "warning", "switch_model"
    std::string action = "error";

    /// Optional agent name override
    std::optional<std::string> agent_name_override;

    /// Create default config
    static BudgetConfig default_config() {
        return BudgetConfig{};
    }

    /// Create config with session budget
    static BudgetConfig with_session_budget(double budget) {
        BudgetConfig config;
        config.session_budget = budget;
        return config;
    }

    /// Create config with all budgets
    static BudgetConfig with_budgets(
        std::optional<double> session,
        std::optional<double> agent,
        std::optional<double> global
    ) {
        BudgetConfig config;
        config.session_budget = session;
        config.agent_budget = agent;
        config.global_budget = global;
        return config;
    }
};

/// Budget warning configuration
struct BudgetWarningConfig {
    /// Per-session budget in USD (optional)
    std::optional<double> session_budget;

    /// Per-agent budget in USD (optional)
    std::optional<double> agent_budget;

    /// Global budget in USD (optional)
    std::optional<double> global_budget;

    /// Warning thresholds (e.g., 0.5, 0.75, 0.9 for 50%, 75%, 90%)
    std::vector<double> warning_thresholds = {0.5, 0.75, 0.9};

    /// Optional agent name override
    std::optional<std::string> agent_name_override;
};

} // namespace budget
} // namespace infrastructure
} // namespace agenkit
