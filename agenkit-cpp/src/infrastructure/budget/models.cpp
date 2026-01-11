#include "agenkit/infrastructure/budget/models.hpp"
#include <random>
#include <sstream>
#include <iomanip>

namespace agenkit {
namespace infrastructure {
namespace budget {

std::string CostRecord::generate_uuid() {
    // Simple UUID v4 generation
    std::random_device rd;
    std::mt19937_64 gen(rd());
    std::uniform_int_distribution<uint64_t> dis;

    uint64_t a = dis(gen);
    uint64_t b = dis(gen);

    // Set version to 4
    b = (b & 0xFFFFFFFFFFFF0FFFULL) | 0x0000000000004000ULL;
    // Set variant to RFC4122
    b = (b & 0x3FFFFFFFFFFFFFFFULL) | 0x8000000000000000ULL;

    std::ostringstream oss;
    oss << std::hex << std::setfill('0')
        << std::setw(8) << (a >> 32)
        << "-"
        << std::setw(4) << ((a >> 16) & 0xFFFF)
        << "-"
        << std::setw(4) << (a & 0xFFFF)
        << "-"
        << std::setw(4) << (b >> 48)
        << "-"
        << std::setw(12) << (b & 0xFFFFFFFFFFFFULL);

    return oss.str();
}

nlohmann::json CostRecord::to_json() const {
    nlohmann::json j;
    j["record_id"] = record_id;
    j["session_id"] = session_id;
    j["agent_name"] = agent_name;
    j["model"] = model;

    // Timestamp as milliseconds since epoch
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        timestamp.time_since_epoch()
    ).count();
    j["timestamp"] = ms;

    j["input_tokens"] = input_tokens;
    j["output_tokens"] = output_tokens;
    j["thinking_tokens"] = thinking_tokens;
    j["input_cost"] = input_cost;
    j["output_cost"] = output_cost;
    j["thinking_cost"] = thinking_cost;
    j["total_cost"] = total_cost;

    if (metadata.has_value()) {
        j["metadata"] = metadata.value();
    } else {
        j["metadata"] = nullptr;
    }

    return j;
}

CostRecord CostRecord::from_json(const nlohmann::json& j) {
    CostRecord record;
    record.record_id = j["record_id"].get<std::string>();
    record.session_id = j["session_id"].get<std::string>();
    record.agent_name = j["agent_name"].get<std::string>();
    record.model = j["model"].get<std::string>();

    // Parse timestamp
    int64_t ms = j["timestamp"].get<int64_t>();
    record.timestamp = std::chrono::system_clock::time_point(
        std::chrono::milliseconds(ms)
    );

    record.input_tokens = j["input_tokens"].get<int>();
    record.output_tokens = j["output_tokens"].get<int>();
    record.thinking_tokens = j["thinking_tokens"].get<int>();
    record.input_cost = j["input_cost"].get<double>();
    record.output_cost = j["output_cost"].get<double>();
    record.thinking_cost = j["thinking_cost"].get<double>();
    record.total_cost = j["total_cost"].get<double>();

    if (!j["metadata"].is_null()) {
        record.metadata = j["metadata"];
    }

    return record;
}

nlohmann::json UsageStats::to_json() const {
    nlohmann::json j;
    j["total_cost"] = total_cost;
    j["total_requests"] = total_requests;
    j["total_input_tokens"] = total_input_tokens;
    j["total_output_tokens"] = total_output_tokens;
    j["total_thinking_tokens"] = total_thinking_tokens;
    j["total_tokens"] = total_tokens;
    j["avg_cost_per_request"] = avg_cost_per_request;
    j["avg_tokens_per_request"] = avg_tokens_per_request;

    if (by_model.has_value()) {
        j["by_model"] = by_model.value();
    } else {
        j["by_model"] = nullptr;
    }

    return j;
}

} // namespace budget
} // namespace infrastructure
} // namespace agenkit
