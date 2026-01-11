#pragma once

#include "agenkit/core/message.hpp"
#include <chrono>
#include <optional>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace infrastructure {
namespace checkpointing {

/// Checkpoint - Snapshot of agent state at a specific point in time
///
/// Enables:
/// - Durable execution (resume after crashes)
/// - Time-travel debugging (replay from any checkpoint)
/// - State persistence (save/load agent state)
/// - History tracking (parent links form checkpoint chain)
struct Checkpoint {
    /// Unique checkpoint identifier (UUID v4)
    std::string checkpoint_id;

    /// Session identifier (groups related checkpoints)
    std::string session_id;

    /// Agent name/identifier
    std::string agent_name;

    /// Creation timestamp (UTC)
    std::chrono::system_clock::time_point timestamp;

    /// Sequential step number in session
    size_t step_number;

    /// Custom agent state (JSON)
    nlohmann::json state;

    /// Full conversation history (cumulative)
    std::vector<core::Message> messages;

    /// Optional metadata (cost tracking, tokens, etc.)
    std::optional<nlohmann::json> metadata;

    /// Optional parent checkpoint ID (for history chain)
    std::optional<std::string> parent_checkpoint_id;

    /// Create a new checkpoint
    ///
    /// @param session_id Session identifier
    /// @param agent_name Agent name
    /// @param step_number Step number in session
    /// @param state Agent state (JSON)
    /// @param messages Conversation history
    /// @return Checkpoint with generated UUID and current timestamp
    static Checkpoint create(
        const std::string& session_id,
        const std::string& agent_name,
        size_t step_number,
        const nlohmann::json& state,
        const std::vector<core::Message>& messages
    );

    /// Add metadata (fluent interface)
    ///
    /// @param metadata_ Metadata JSON
    /// @return *this for chaining
    Checkpoint& with_metadata(const nlohmann::json& metadata_);

    /// Set parent checkpoint (fluent interface)
    ///
    /// @param parent_id Parent checkpoint ID
    /// @return *this for chaining
    Checkpoint& with_parent(const std::string& parent_id);

    /// Serialize to JSON string
    ///
    /// @return JSON string representation
    std::string to_json() const;

    /// Deserialize from JSON string
    ///
    /// @param json_str JSON string
    /// @return Checkpoint
    /// @throws std::runtime_error if parsing fails
    static Checkpoint from_json(const std::string& json_str);

    /// Convert to JSON object
    ///
    /// @return JSON object
    nlohmann::json to_json_object() const;

    /// Create from JSON object
    ///
    /// @param j JSON object
    /// @return Checkpoint
    static Checkpoint from_json_object(const nlohmann::json& j);

private:
    /// Generate a UUID v4 string
    static std::string generate_uuid();
};

} // namespace checkpointing
} // namespace infrastructure
} // namespace agenkit
