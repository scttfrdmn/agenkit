#include "agenkit/infrastructure/budget/tracker.hpp"
#include <algorithm>
#include <map>

namespace agenkit {
namespace infrastructure {
namespace budget {

// ============================================================================
// InMemoryCostStorage Implementation
// ============================================================================

void InMemoryCostStorage::store(const CostRecord& record) {
    std::unique_lock lock(mutex_);
    records_.push_back(record);
}

std::vector<CostRecord> InMemoryCostStorage::query(
    const std::optional<std::string>& session_id,
    const std::optional<std::string>& agent_name,
    const std::optional<std::chrono::system_clock::time_point>& start_time,
    const std::optional<std::chrono::system_clock::time_point>& end_time
) {
    std::shared_lock lock(mutex_);

    std::vector<CostRecord> results;
    for (const auto& record : records_) {
        // Apply filters
        if (session_id.has_value() && record.session_id != session_id.value()) {
            continue;
        }
        if (agent_name.has_value() && record.agent_name != agent_name.value()) {
            continue;
        }
        if (start_time.has_value() && record.timestamp < start_time.value()) {
            continue;
        }
        if (end_time.has_value() && record.timestamp > end_time.value()) {
            continue;
        }

        results.push_back(record);
    }

    return results;
}

size_t InMemoryCostStorage::count() const {
    std::shared_lock lock(mutex_);
    return records_.size();
}

void InMemoryCostStorage::clear() {
    std::unique_lock lock(mutex_);
    records_.clear();
}

// ============================================================================
// CostTracker Implementation
// ============================================================================

CostTracker::CostTracker(
    std::shared_ptr<ModelPricing> pricing,
    std::unique_ptr<CostStorage> storage
) : pricing_(pricing), storage_(std::move(storage)) {
}

CostRecord CostTracker::record_cost(
    const std::string& session_id,
    const std::string& agent_name,
    const std::string& model,
    int input_tokens,
    int output_tokens,
    int thinking_tokens,
    const std::optional<nlohmann::json>& metadata
) {
    // Calculate costs
    double input_cost = pricing_->calculate(model, input_tokens, "input");
    double output_cost = pricing_->calculate(model, output_tokens, "output");
    double thinking_cost = pricing_->calculate(model, thinking_tokens, "output");

    // Create record
    CostRecord record;
    record.record_id = CostRecord::generate_uuid();
    record.session_id = session_id;
    record.agent_name = agent_name;
    record.model = model;
    record.timestamp = std::chrono::system_clock::now();
    record.input_tokens = input_tokens;
    record.output_tokens = output_tokens;
    record.thinking_tokens = thinking_tokens;
    record.input_cost = input_cost;
    record.output_cost = output_cost;
    record.thinking_cost = thinking_cost;
    record.total_cost = input_cost + output_cost + thinking_cost;
    record.metadata = metadata;

    // Store record
    storage_->store(record);

    return record;
}

double CostTracker::get_session_cost(const std::string& session_id) {
    auto records = storage_->query(session_id, std::nullopt, std::nullopt, std::nullopt);

    double total = 0.0;
    for (const auto& record : records) {
        total += record.total_cost;
    }

    return total;
}

double CostTracker::get_agent_cost(const std::string& agent_name) {
    auto records = storage_->query(std::nullopt, agent_name, std::nullopt, std::nullopt);

    double total = 0.0;
    for (const auto& record : records) {
        total += record.total_cost;
    }

    return total;
}

double CostTracker::get_global_cost() {
    auto records = storage_->query(std::nullopt, std::nullopt, std::nullopt, std::nullopt);

    double total = 0.0;
    for (const auto& record : records) {
        total += record.total_cost;
    }

    return total;
}

std::map<std::string, double> CostTracker::get_breakdown(
    const std::optional<std::string>& session_id,
    const std::optional<std::string>& agent_name
) {
    auto records = storage_->query(session_id, agent_name, std::nullopt, std::nullopt);

    std::map<std::string, double> breakdown;
    for (const auto& record : records) {
        breakdown[record.model] += record.total_cost;
    }

    return breakdown;
}

std::vector<std::pair<std::string, double>> CostTracker::get_top_sessions(size_t limit) {
    auto records = storage_->query(std::nullopt, std::nullopt, std::nullopt, std::nullopt);

    // Aggregate by session
    std::map<std::string, double> session_costs;
    for (const auto& record : records) {
        session_costs[record.session_id] += record.total_cost;
    }

    // Convert to vector
    std::vector<std::pair<std::string, double>> results;
    for (const auto& pair : session_costs) {
        results.push_back(pair);
    }

    // Sort by cost (descending)
    std::sort(results.begin(), results.end(),
        [](const std::pair<std::string, double>& a, const std::pair<std::string, double>& b) {
            return a.second > b.second;
        });

    // Apply limit
    if (results.size() > limit) {
        results.resize(limit);
    }

    return results;
}

std::vector<std::pair<std::string, double>> CostTracker::get_top_agents(size_t limit) {
    auto records = storage_->query(std::nullopt, std::nullopt, std::nullopt, std::nullopt);

    // Aggregate by agent
    std::map<std::string, double> agent_costs;
    for (const auto& record : records) {
        agent_costs[record.agent_name] += record.total_cost;
    }

    // Convert to vector
    std::vector<std::pair<std::string, double>> results;
    for (const auto& pair : agent_costs) {
        results.push_back(pair);
    }

    // Sort by cost (descending)
    std::sort(results.begin(), results.end(),
        [](const std::pair<std::string, double>& a, const std::pair<std::string, double>& b) {
            return a.second > b.second;
        });

    // Apply limit
    if (results.size() > limit) {
        results.resize(limit);
    }

    return results;
}

UsageStats CostTracker::get_statistics(
    const std::optional<std::string>& session_id,
    const std::optional<std::string>& agent_name
) {
    auto records = storage_->query(session_id, agent_name, std::nullopt, std::nullopt);

    UsageStats stats;
    stats.total_cost = 0.0;
    stats.total_requests = static_cast<int>(records.size());
    stats.total_input_tokens = 0;
    stats.total_output_tokens = 0;
    stats.total_thinking_tokens = 0;
    stats.total_tokens = 0;

    std::map<std::string, double> by_model;

    for (const auto& record : records) {
        stats.total_cost += record.total_cost;
        stats.total_input_tokens += record.input_tokens;
        stats.total_output_tokens += record.output_tokens;
        stats.total_thinking_tokens += record.thinking_tokens;
        stats.total_tokens += record.total_tokens();
        by_model[record.model] += record.total_cost;
    }

    stats.avg_cost_per_request = (stats.total_requests > 0)
        ? stats.total_cost / stats.total_requests
        : 0.0;
    stats.avg_tokens_per_request = (stats.total_requests > 0)
        ? static_cast<double>(stats.total_tokens) / stats.total_requests
        : 0.0;
    stats.by_model = by_model;

    return stats;
}

std::vector<CostRecord> CostTracker::query(
    const std::optional<std::string>& session_id,
    const std::optional<std::string>& agent_name,
    const std::optional<std::chrono::system_clock::time_point>& start_time,
    const std::optional<std::chrono::system_clock::time_point>& end_time
) {
    return storage_->query(session_id, agent_name, start_time, end_time);
}

size_t CostTracker::count() const {
    return storage_->count();
}

void CostTracker::clear() {
    storage_->clear();
}

} // namespace budget
} // namespace infrastructure
} // namespace agenkit
