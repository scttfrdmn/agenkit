#include "agenkit/infrastructure/checkpointing/checkpoint.hpp"
#include <iomanip>
#include <random>
#include <sstream>
#include <stdexcept>

namespace agenkit {
namespace infrastructure {
namespace checkpointing {

std::string Checkpoint::generate_uuid() {
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

Checkpoint Checkpoint::create(
    const std::string& session_id,
    const std::string& agent_name,
    size_t step_number,
    const nlohmann::json& state,
    const std::vector<core::Message>& messages
) {
    Checkpoint checkpoint;
    checkpoint.checkpoint_id = generate_uuid();
    checkpoint.session_id = session_id;
    checkpoint.agent_name = agent_name;
    checkpoint.timestamp = std::chrono::system_clock::now();
    checkpoint.step_number = step_number;
    checkpoint.state = state;
    checkpoint.messages = messages;
    checkpoint.metadata = std::nullopt;
    checkpoint.parent_checkpoint_id = std::nullopt;
    return checkpoint;
}

Checkpoint& Checkpoint::with_metadata(const nlohmann::json& metadata_) {
    metadata = metadata_;
    return *this;
}

Checkpoint& Checkpoint::with_parent(const std::string& parent_id) {
    parent_checkpoint_id = parent_id;
    return *this;
}

nlohmann::json Checkpoint::to_json_object() const {
    nlohmann::json j;
    j["checkpoint_id"] = checkpoint_id;
    j["session_id"] = session_id;
    j["agent_name"] = agent_name;

    // Timestamp as milliseconds since epoch
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        timestamp.time_since_epoch()
    ).count();
    j["timestamp"] = ms;

    j["step_number"] = step_number;
    j["state"] = state;

    // Serialize messages
    nlohmann::json messages_json = nlohmann::json::array();
    for (const auto& msg : messages) {
        messages_json.push_back(msg.to_json());
    }
    j["messages"] = messages_json;

    // Optional fields
    if (metadata.has_value()) {
        j["metadata"] = metadata.value();
    } else {
        j["metadata"] = nullptr;
    }

    if (parent_checkpoint_id.has_value()) {
        j["parent_checkpoint_id"] = parent_checkpoint_id.value();
    } else {
        j["parent_checkpoint_id"] = nullptr;
    }

    return j;
}

std::string Checkpoint::to_json() const {
    return to_json_object().dump(2);  // Pretty print with 2-space indent
}

Checkpoint Checkpoint::from_json_object(const nlohmann::json& j) {
    Checkpoint checkpoint;

    checkpoint.checkpoint_id = j["checkpoint_id"].get<std::string>();
    checkpoint.session_id = j["session_id"].get<std::string>();
    checkpoint.agent_name = j["agent_name"].get<std::string>();

    // Parse timestamp
    int64_t ms = j["timestamp"].get<int64_t>();
    checkpoint.timestamp = std::chrono::system_clock::time_point(
        std::chrono::milliseconds(ms)
    );

    checkpoint.step_number = j["step_number"].get<size_t>();
    checkpoint.state = j["state"];

    // Parse messages
    const auto& messages_json = j["messages"];
    for (const auto& msg_json : messages_json) {
        checkpoint.messages.push_back(core::Message::from_json(msg_json));
    }

    // Optional fields
    if (!j["metadata"].is_null()) {
        checkpoint.metadata = j["metadata"];
    } else {
        checkpoint.metadata = std::nullopt;
    }

    if (!j["parent_checkpoint_id"].is_null()) {
        checkpoint.parent_checkpoint_id = j["parent_checkpoint_id"].get<std::string>();
    } else {
        checkpoint.parent_checkpoint_id = std::nullopt;
    }

    return checkpoint;
}

Checkpoint Checkpoint::from_json(const std::string& json_str) {
    try {
        auto j = nlohmann::json::parse(json_str);
        return from_json_object(j);
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error(std::string("Failed to parse checkpoint JSON: ") + e.what());
    }
}

} // namespace checkpointing
} // namespace infrastructure
} // namespace agenkit
