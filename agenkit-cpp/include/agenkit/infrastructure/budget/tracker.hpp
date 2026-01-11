#pragma once

#include "agenkit/infrastructure/budget/models.hpp"
#include "agenkit/infrastructure/budget/pricing.hpp"
#include <memory>
#include <shared_mutex>
#include <optional>
#include <string>
#include <vector>

namespace agenkit {
namespace infrastructure {
namespace budget {

/// Abstract storage interface for cost records
class CostStorage {
public:
    virtual ~CostStorage() = default;

    /// Store a cost record
    virtual void store(const CostRecord& record) = 0;

    /// Query cost records with optional filters
    ///
    /// @param session_id Optional session filter
    /// @param agent_name Optional agent filter
    /// @param start_time Optional start time filter
    /// @param end_time Optional end time filter
    /// @return Vector of matching records
    virtual std::vector<CostRecord> query(
        const std::optional<std::string>& session_id = std::nullopt,
        const std::optional<std::string>& agent_name = std::nullopt,
        const std::optional<std::chrono::system_clock::time_point>& start_time = std::nullopt,
        const std::optional<std::chrono::system_clock::time_point>& end_time = std::nullopt
    ) = 0;

    /// Get total number of records
    virtual size_t count() const = 0;

    /// Clear all records
    virtual void clear() = 0;
};

/// In-memory storage implementation
class InMemoryCostStorage : public CostStorage {
public:
    InMemoryCostStorage() = default;

    void store(const CostRecord& record) override;

    std::vector<CostRecord> query(
        const std::optional<std::string>& session_id = std::nullopt,
        const std::optional<std::string>& agent_name = std::nullopt,
        const std::optional<std::chrono::system_clock::time_point>& start_time = std::nullopt,
        const std::optional<std::chrono::system_clock::time_point>& end_time = std::nullopt
    ) override;

    size_t count() const override;

    void clear() override;

private:
    mutable std::shared_mutex mutex_;
    std::vector<CostRecord> records_;
};

/// Cost tracker - Records costs and provides analytics
///
/// Thread-safe cost tracking with flexible querying.
class CostTracker {
public:
    /// Create tracker with pricing and storage
    ///
    /// @param pricing Model pricing database
    /// @param storage Cost storage backend (defaults to in-memory)
    CostTracker(
        std::shared_ptr<ModelPricing> pricing,
        std::unique_ptr<CostStorage> storage = std::make_unique<InMemoryCostStorage>()
    );

    /// Record a cost
    ///
    /// @param session_id Session identifier
    /// @param agent_name Agent name
    /// @param model Model name
    /// @param input_tokens Input token count
    /// @param output_tokens Output token count
    /// @param thinking_tokens Thinking token count (default: 0)
    /// @param metadata Optional metadata
    /// @return Created cost record
    CostRecord record_cost(
        const std::string& session_id,
        const std::string& agent_name,
        const std::string& model,
        int input_tokens,
        int output_tokens,
        int thinking_tokens = 0,
        const std::optional<nlohmann::json>& metadata = std::nullopt
    );

    /// Get total cost for session
    ///
    /// @param session_id Session identifier
    /// @return Total cost in USD
    double get_session_cost(const std::string& session_id);

    /// Get total cost for agent
    ///
    /// @param agent_name Agent name
    /// @return Total cost in USD
    double get_agent_cost(const std::string& agent_name);

    /// Get global cost (all sessions and agents)
    ///
    /// @return Total cost in USD
    double get_global_cost();

    /// Get cost breakdown by model
    ///
    /// @param session_id Optional session filter
    /// @param agent_name Optional agent filter
    /// @return Map of model -> cost
    std::map<std::string, double> get_breakdown(
        const std::optional<std::string>& session_id = std::nullopt,
        const std::optional<std::string>& agent_name = std::nullopt
    );

    /// Get top N sessions by cost
    ///
    /// @param limit Maximum number of results
    /// @return Vector of (session_id, cost) sorted by cost descending
    std::vector<std::pair<std::string, double>> get_top_sessions(size_t limit = 10);

    /// Get top N agents by cost
    ///
    /// @param limit Maximum number of results
    /// @return Vector of (agent_name, cost) sorted by cost descending
    std::vector<std::pair<std::string, double>> get_top_agents(size_t limit = 10);

    /// Get usage statistics
    ///
    /// @param session_id Optional session filter
    /// @param agent_name Optional agent filter
    /// @return Usage statistics
    UsageStats get_statistics(
        const std::optional<std::string>& session_id = std::nullopt,
        const std::optional<std::string>& agent_name = std::nullopt
    );

    /// Query records with filters
    ///
    /// @param session_id Optional session filter
    /// @param agent_name Optional agent filter
    /// @param start_time Optional start time filter
    /// @param end_time Optional end time filter
    /// @return Vector of matching records
    std::vector<CostRecord> query(
        const std::optional<std::string>& session_id = std::nullopt,
        const std::optional<std::string>& agent_name = std::nullopt,
        const std::optional<std::chrono::system_clock::time_point>& start_time = std::nullopt,
        const std::optional<std::chrono::system_clock::time_point>& end_time = std::nullopt
    );

    /// Get total number of records
    size_t count() const;

    /// Clear all records
    void clear();

private:
    std::shared_ptr<ModelPricing> pricing_;
    std::unique_ptr<CostStorage> storage_;
};

} // namespace budget
} // namespace infrastructure
} // namespace agenkit
